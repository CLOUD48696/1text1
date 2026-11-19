import asyncio
import json
import time

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.database import Store
from app.llm.demo import DemoLLM, make_roster
from app.main import create_app


@pytest.fixture
def settings(tmp_path):
    return Settings(_env_file=None, database_url=f'sqlite:///{(tmp_path / "test.db").as_posix()}',
                    app_mode='demo', demo_delay=0.01, max_turns=4, seed_on_start=False)


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def wait_for(client, did, states, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f'/api/discussions/{did}')
        assert response.status_code == 200
        snapshot = response.json()
        if snapshot['discussion']['status'] in states: return snapshot
        time.sleep(0.02)
    pytest.fail(f'Timed out waiting for {states}: {snapshot}')


def create(client, topic='小团队应该优先使用 AI 工具还是招聘？'):
    response = client.post('/api/discussions', json={'topic': topic, 'expert_count': 4})
    assert response.status_code == 202
    return response.json()['discussion_id']


def test_verbose_expert_cannot_end_the_panel(settings):
    class VerboseFirst(DemoLLM):
        attempts = []

        async def generate(self, task, context, schema):
            if task == 'intent':
                return {'action': 'raise', 'urgency': 1, 'public_focus': '讨论工作意义'}
            if task == 'speech' and len(self.attempts) < 2:
                self.attempts.append(context['person']['id'])
                return {'content': '工作可以创造价值。它也联结社会。还要考虑收入。'}
            return await super().generate(task, context, schema)

    model = VerboseFirst()
    with TestClient(create_app(settings, model)) as client:
        did = create(client, 'ai时代，人类是否还需要工作')
        wait_for(client, did, {'ready'})
        client.post(f'/api/discussions/{did}/start')
        room = wait_for(client, did, {'completed', 'failed'})
        assert room['discussion']['status'] == 'completed'
        assert len(model.attempts) == 2
        assert room['messages'][1]['participant_id'] != model.attempts[0]
        assert all('还要考虑收入' not in m['content'] for m in room['messages'])


def test_roster_requires_confirmation_and_start_is_idempotent(client):
    did = create(client)
    ready = wait_for(client, did, {'ready'})
    assert len(ready['participants']) == 5
    assert not ready['messages']
    first = client.post(f'/api/discussions/{did}/start')
    second = client.post(f'/api/discussions/{did}/start')
    assert first.status_code == second.status_code == 202
    result = wait_for(client, did, {'completed', 'failed'})
    assert result['discussion']['status'] == 'completed'
    assert result['discussion']['summary']
    assert sum('欢迎来到本场圆桌' in m['content'] for m in result['messages']) == 1
    assert len(result['messages']) == 7  # Opening + four experts + follow-up + closing.
    assert result['insights']
    assert all(p['status'] == 'idle' for p in result['participants'])
    assert client.post(f'/api/discussions/{did}/start').status_code == 409


def test_concurrent_discussions_and_events_are_isolated(client):
    a, b = create(client, '企业是否应该实行四天工作制？'), create(client, '高校应该怎样允许学生使用 AI？')
    for did in (a, b):
        wait_for(client, did, {'ready'})
        assert client.post(f'/api/discussions/{did}/start').status_code == 202
    one, two = [wait_for(client, did, {'completed', 'failed'}) for did in (a, b)]
    for state in (one, two):
        assert state['discussion']['status'] == 'completed'
        person_ids = {p['id'] for p in state['participants']}
        message_ids = {m['id'] for m in state['messages']}
        assert all(m['participant_id'] in person_ids for m in state['messages'])
        assert all(set(i['evidence_message_ids']) <= message_ids for i in state['insights'])
    assert {m['id'] for m in one['messages']}.isdisjoint(m['id'] for m in two['messages'])
    events = client.app.state.store.events(a)
    assert all(e['discussion_id'] == a for e in events)
    assert [e['sequence'] for e in events] == list(range(1, len(events) + 1))
    first_insight = next(e['sequence'] for e in events if e['type'] == 'insights.updated' and e['data']['insights'])
    assert first_insight < next(e['sequence'] for e in events if e['type'] == 'discussion.completed')


def test_sse_replay_prefers_last_event_id_and_never_restarts(client):
    did = create(client)
    wait_for(client, did, {'ready'})
    client.post(f'/api/discussions/{did}/start')
    completed = wait_for(client, did, {'completed'})
    response = client.get(f'/api/discussions/{did}/events?after=0', headers={'Last-Event-ID': '3'})
    assert response.status_code == 200
    assert 'text/event-stream' in response.headers['content-type']
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]
    assert events[0]['sequence'] == 4
    assert events[-1]['sequence'] == completed['last_event_sequence']
    assert len(wait_for(client, did, {'completed'})['messages']) == len(completed['messages'])
    assert client.get(f'/api/discussions/{did}/events?after=999999').status_code == 422
    assert client.get(f'/api/discussions/{did}/events', headers={'Last-Event-ID': 'invalid'}).status_code == 422


def test_cross_room_author_and_reply_rejected(client):
    a, b = create(client), create(client)
    one, two = [wait_for(client, did, {'ready'}) for did in (a, b)]
    store = client.app.state.store
    with pytest.raises(ValueError): store.message(a, two['participants'][0]['id'], '非法跨讨论发言')
    foreign = store.message(b, two['participants'][0]['id'], '这是另一个讨论中的发言')
    with pytest.raises(ValueError): store.message(a, one['participants'][0]['id'], '非法跨讨论引用', foreign['id'])


def test_validation_and_missing_discussion(client):
    assert client.post('/api/discussions', json={'topic': '   ', 'expert_count': 4}).status_code == 422
    assert client.post('/api/discussions', json={'topic': '正常议题内容', 'expert_count': 12}).status_code == 422
    assert client.get('/api/discussions/missing').status_code == 404
    assert client.get('/api/discussions/missing/events').status_code == 404
    assert client.get('/api/health').json() == {'status': 'ok', 'mode': 'demo'}


def test_provider_failure_is_sanitized_and_can_retry(settings):
    class Broken(DemoLLM):
        async def generate(self, *args): raise RuntimeError('SECRET_PROVIDER_KEY_DO_NOT_LEAK')
    with TestClient(create_app(settings, Broken())) as client:
        did = create(client)
        failed = wait_for(client, did, {'failed'})
        assert 'SECRET' not in json.dumps(failed)
        assert not failed['messages']
        client.app.state.engine.client = DemoLLM()
        assert client.post(f'/api/discussions/{did}/retry-generation').status_code == 202
        assert len(wait_for(client, did, {'ready'})['participants']) == 5


def test_wrong_roster_count_is_retried(settings):
    class WrongOnce(DemoLLM):
        calls = 0
        async def generate(self, task, context, schema):
            if task == 'roster':
                self.calls += 1
                if self.calls == 1: return make_roster(context['topic'], 2).model_dump()
            return await super().generate(task, context, schema)
    model = WrongOnce()
    with TestClient(create_app(settings, model)) as client:
        did = create(client)
        assert len(wait_for(client, did, {'ready'})['participants']) == 5
        assert model.calls == 2


def test_restart_marks_unfinished_discussions(settings):
    store = Store(settings.database_url)
    store.initialize()
    did = store.create('正在进行的演示议题', 4, 'demo')['id']
    store.roster(did, make_roster('正在进行的演示议题', 4))
    store.transition(did, 'running', phase='discussion')
    store.engine.dispose()
    with TestClient(create_app(settings)) as client:
        state = client.get(f'/api/discussions/{did}').json()
        assert state['discussion']['status'] == 'interrupted'
        assert all(p['status'] == 'idle' for p in state['participants'])


def test_seed_is_idempotent_and_contains_five_rosters(settings):
    settings.seed_on_start = True
    for _ in range(2):
        with TestClient(create_app(settings)) as client:
            rooms = client.get('/api/discussions').json()['items']
            assert len(rooms) == 5
            assert {r['status'] for r in rooms} == {'ready', 'completed'}
            assert all(len(client.get(f'/api/discussions/{r["id"]}').json()['participants']) == 5 for r in rooms)


def test_live_mode_requires_backend_credentials():
    with pytest.raises(ValueError): Settings(_env_file=None, app_mode='live', llm_api_key='', llm_model='')


def test_timeout_is_bounded_and_does_not_leak_provider_error(settings):
    class Slow(DemoLLM):
        async def generate(self, *args): await asyncio.sleep(10)
    settings.llm_timeout = 0.02
    with TestClient(create_app(settings, Slow())) as client:
        did = create(client)
        assert wait_for(client, did, {'failed'}, timeout=3)['discussion']['error']


def test_all_waiting_intents_trigger_host_then_finish(settings):
    class Quiet(DemoLLM):
        async def generate(self, task, context, schema):
            if task == 'intent': return {'action': 'wait', 'target_message_id': None, 'urgency': 0, 'public_focus': '暂时没有新的观点'}
            return await super().generate(task, context, schema)
    with TestClient(create_app(settings, Quiet())) as client:
        did = create(client)
        wait_for(client, did, {'ready'})
        client.post(f'/api/discussions/{did}/start')
        result = wait_for(client, did, {'completed', 'failed'})
        assert result['discussion']['status'] == 'completed'
        assert len(result['messages']) == 3
        assert not result['insights']


def test_call_budget_reserves_summary(settings):
    settings.max_calls = 20
    with TestClient(create_app(settings)) as client:
        did = create(client)
        wait_for(client, did, {'ready'})
        client.post(f'/api/discussions/{did}/start')
        result = wait_for(client, did, {'completed', 'failed'})
        assert result['discussion']['status'] == 'completed'
        assert result['discussion']['summary']
        assert len(result['messages']) <= 7


def test_demo_seed_contains_supported_disagreement(settings):
    settings.seed_on_start = True
    with TestClient(create_app(settings)) as client:
        completed = next(r for r in client.get('/api/discussions').json()['items'] if r['status'] == 'completed')
        state = client.get(f'/api/discussions/{completed["id"]}').json()
        assert {i['kind'] for i in state['insights']} == {'consensus', 'disagreement'}


def test_list_filter_finds_old_active_room_before_paginating(client):
    store = client.app.state.store
    active = store.create('很早创建但仍待确认的讨论', 4, 'demo')['id']
    store.roster(active, make_roster('很早创建但仍待确认的讨论', 4))
    finished = []
    for index in range(105):
        did = store.create(f'已结束的历史讨论 {index}', 4, 'demo')['id']
        store.transition(did, 'completed')
        finished.append(did)
    response = client.get('/api/discussions?filter=active&limit=20').json()
    assert [item['id'] for item in response['items']] == [active]
    assert response['next_cursor'] is None
    seen, cursor = [], 0
    while cursor is not None:
        page = client.get(f'/api/discussions?filter=completed&limit=20&cursor={cursor}').json()
        assert all(item['status'] == 'completed' for item in page['items'])
        seen.extend(item['id'] for item in page['items'])
        cursor = page['next_cursor']
    assert len(seen) == len(set(seen)) == 105
    assert set(seen) == set(finished)
    assert client.get('/api/discussions?filter=all&limit=100').json()['next_cursor'] == 100
    assert client.get('/api/discussions?filter=completed&cursor=105').json() == {'items': [], 'next_cursor': None}


def test_list_rejects_unknown_filter(client):
    assert client.get('/api/discussions?filter=unknown').status_code == 422
