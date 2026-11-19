import asyncio
import logging
import re
from dataclasses import dataclass
from time import monotonic

from app.config import Settings
from app.database import StateConflict, Store
from app.llm.base import LLMClient
from app.llm.demo import DemoLLM
from app.llm.provider import ProviderLLM
from app.schemas import ExpertSpeech, Insights, Intent, Roster, Speech, Summary
from app.services.scheduler import choose_speaker, validate_evidence, validate_roster


@dataclass
class Budget:
    calls: int = 0


class InvalidExpertSpeech(ValueError):
    pass


logger = logging.getLogger(__name__)


class Engine:
    def __init__(self, store: Store, settings: Settings, client: LLMClient | None = None):
        self.store, self.settings = store, settings
        self.demo = DemoLLM(settings.demo_delay)
        self.client = client or (ProviderLLM(settings) if settings.app_mode == 'live' else self.demo)
        self.semaphore = asyncio.Semaphore(settings.llm_concurrency)
        self.tasks: dict[str, asyncio.Task] = {}

    async def call(self, did, task, context, schema, budget, check=None):
        mode = self.store.snapshot(did)['discussion']['mode']
        client = self.demo if mode == 'demo' and self.settings.app_mode == 'live' else self.client
        for attempt in range(2):
            if budget.calls >= self.settings.max_calls:
                raise RuntimeError('模型调用预算已用完')
            budget.calls += 1
            try:
                async with asyncio.timeout(self.settings.llm_timeout):
                    async with self.semaphore:
                        data = await client.generate(task, context, schema)
                parsed = schema.model_validate(data)
                if check: check(parsed)
                return parsed
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if attempt == 1:
                    logger.warning('discussion=%s task=%s error_type=%s', did, task, type(exc).__name__)
                    if task == 'speech' and isinstance(exc, ValueError):
                        raise InvalidExpertSpeech('专家发言未通过格式校验') from exc
                    raise
                feedback = ('请只回答一个要点，用一句 40–90 字的完整中文句子，返回含 content 的 JSON 对象。'
                            if task == 'speech' else '上次输出未通过结构/业务校验或请求失败，请严格按要求重试。')
                context = {**context, 'format_feedback': feedback}
                await asyncio.sleep(0.1)

    def context(self, did):
        snapshot = self.store.snapshot(did)
        people = {p['id']: p for p in snapshot['participants']}
        messages = [{**m, 'name': people[m['participant_id']]['name'], 'role': people[m['participant_id']]['role']} for m in snapshot['messages']]
        earlier = {}
        for message in messages[:-12]:
            earlier[message['participant_id']] = {'name': message['name'], 'position_excerpt': message['content'][:180]}
        return {'topic': snapshot['discussion']['topic'], 'participants': snapshot['participants'],
                'messages': messages[-12:], 'earlier_positions': list(earlier.values()),
                'insights': snapshot['insights']}

    def spawn(self, did, coroutine):
        task = asyncio.create_task(self.guard(did, coroutine))
        self.tasks[did] = task
        def finished(done):
            if self.tasks.get(did) is done: self.tasks.pop(did, None)
        task.add_done_callback(finished)

    async def guard(self, did, coroutine):
        try:
            # The wall-clock cap includes provider latency and retries.
            async with asyncio.timeout(self.settings.max_duration + self.settings.llm_timeout * 2):
                await coroutine
        except asyncio.CancelledError:
            self.store.transition(did, 'interrupted', error='服务已停止，已有内容已保存。')
            raise
        except Exception:
            self.store.transition(did, 'failed', error='模型请求或输出校验失败，已保留现有内容。请检查后端配置、网络及额度后重试。')

    def create(self, topic, count):
        room = self.store.create(topic, count, self.settings.app_mode)
        self.spawn(room['id'], self.generate_roster(room['id']))
        return room

    async def generate_roster(self, did):
        room = self.store.snapshot(did)['discussion']
        roster = await self.call(did, 'roster', {'topic': room['topic'], 'expert_count': room['expert_count']},
                                 Roster, Budget(), lambda result: validate_roster(result, room['expert_count']))
        self.store.roster(did, roster)

    def start(self, did):
        room = self.store.snapshot(did)['discussion']
        if room['status'] == 'running': return room
        if did in self.tasks and not self.tasks[did].done(): raise StateConflict('嘉宾生成尚未完成，请稍后开始')
        self.store.transition(did, 'running', phase='opening', expected={'ready'})
        self.spawn(did, self.run(did))
        return self.store.snapshot(did)['discussion']

    def retry_generation(self, did):
        snapshot = self.store.snapshot(did)
        if snapshot['messages'] or snapshot['discussion']['phase'] != 'roster':
            raise StateConflict('已有演播记录，请新建讨论')
        if did in self.tasks and not self.tasks[did].done(): raise StateConflict('任务尚未停止')
        self.store.transition(did, 'generating', expected={'failed'})
        self.spawn(did, self.generate_roster(did))

    async def say(self, did, person, task, budget, intent=None):
        self.store.states(did, {person['id']: {'status': 'preparing'}})
        context = {**self.context(did), 'person': person}
        if intent: context['intent'] = intent.model_dump()
        def validate_speech(result):
            if task == 'speech':
                chunks = [s for s in re.split(r'[。！？!?]+', result.content) if s.strip(' ”"\n')]
                if len(chunks) > 2 or len(result.content) > 220:
                    raise ValueError('专家每次发言需限制为 1–2 句，最多 220 字')
        schema = {'summary': Summary, 'speech': ExpertSpeech}.get(task, Speech)
        response = await self.call(did, task, context, schema, budget, validate_speech)
        self.store.states(did, {person['id']: {'status': 'speaking'}})
        self.store.message(did, person['id'], response.content, intent.target_message_id if intent else None)
        await asyncio.sleep(self.settings.demo_delay if self.store.snapshot(did)['discussion']['mode'] == 'demo' else 0.5)
        self.store.states(did, {})
        return response.content

    async def run(self, did):
        snapshot = self.store.snapshot(did)
        host = next(p for p in snapshot['participants'] if p['role'] == 'host')
        experts = [p for p in snapshot['participants'] if p['role'] == 'expert']
        budget, history, waiting = Budget(), [], {}
        started = monotonic()
        await self.say(did, host, 'opening', budget)
        self.store.transition(did, 'running', phase='discussion')
        empty_rounds = 0
        for _ in range(self.settings.max_turns * 2):
            if len(history) >= self.settings.max_turns or monotonic() - started >= self.settings.max_duration:
                break
            # Reserve two calls for the final summary and enough for a worst-case round.
            if budget.calls + len(experts) * 2 + 8 > self.settings.max_calls: break
            context = self.context(did)
            valid_ids = {m['id'] for m in context['messages']}
            def check_intent(intent):
                if intent.target_message_id and intent.target_message_id not in valid_ids:
                    raise ValueError('意图引用了无效消息')
            results = await asyncio.gather(*(self.call(did, 'intent', {**context, 'person': p}, Intent, budget, check_intent) for p in experts), return_exceptions=True)
            intents = {p['id']: result for p, result in zip(experts, results) if isinstance(result, Intent)}
            if not intents: raise RuntimeError('所有专家的意图请求均失败')
            for pid, intent in intents.items():
                waiting[pid] = waiting.get(pid, 0) + 1 if intent.action != 'wait' else 0
            self.store.states(did, {pid: {'status': 'preparing' if i.action != 'wait' else 'idle', 'public_focus': i.public_focus} for pid, i in intents.items()})
            winner = choose_speaker(intents, history, waiting)
            rejected = False
            while winner is not None:
                person = next(p for p in experts if p['id'] == winner)
                try:
                    await self.say(did, person, 'speech', budget, intents[winner])
                    break
                except InvalidExpertSpeech:
                    rejected = True
                    del intents[winner]
                    winner = choose_speaker(intents, history, waiting) if budget.calls + 4 <= self.settings.max_calls else None
            if winner is None:
                empty_rounds += 1
                if empty_rounds >= 2:
                    if rejected and not history:
                        raise InvalidExpertSpeech('连续两轮没有合格的专家发言')
                    break
                await self.say(did, host, 'followup', budget)
                continue
            empty_rounds = 0
            history.append(winner)
            waiting[winner] = 0
            if len(history) >= 2:
                extracted = await self.call(did, 'insights', self.context(did), Insights, budget)
                state = self.store.snapshot(did)
                valid = validate_evidence(extracted.items, state['messages'], {p['id']: p['role'] for p in experts})
                self.store.insights(did, valid)
            if len(history) == max(2, self.settings.max_turns // 2):
                await self.say(did, host, 'followup', budget)
        self.store.transition(did, 'running', phase='closing')
        summary = await self.say(did, host, 'summary', budget)
        self.store.transition(did, 'completed', phase='closing', summary=summary)

    async def close(self):
        pending = list(self.tasks.values())
        for task in pending: task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        await self.client.close()
