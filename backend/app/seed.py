import asyncio
from uuid import NAMESPACE_URL, uuid5

from app.config import Settings
from app.database import Store
from app.llm.demo import DemoLLM, TOPICS, make_roster
from app.schemas import Insights, Speech, Summary
from app.services.scheduler import validate_evidence


async def seed(store):
    demo = DemoLLM()
    for index, topic in enumerate(TOPICS):
        did = str(uuid5(NAMESPACE_URL, 'panel-studio-seed-v1:' + topic))
        try:
            store.snapshot(did)
            continue
        except KeyError:
            pass
        store.create(topic, 4, 'demo', did=did)
        store.roster(did, make_roster(topic, 4))
        # A saved example with evidence, plus four ready-to-start demo rosters.
        if index == 0:
            people = store.snapshot(did)['participants']
            host, a, b = people[:3]
            store.transition(did, 'running', phase='opening')
            opening = await demo.generate('opening', {'topic': topic}, Speech)
            store.message(did, host['id'], opening['content'])
            first = await demo.generate('speech', {'topic': topic, 'person': a, 'messages': []}, Speech)
            m1 = store.message(did, a['id'], first['content'])
            second = await demo.generate('speech', {'topic': topic, 'person': b, 'messages': []}, Speech)
            store.message(did, b['id'], second['content'], m1['id'])
            state = store.snapshot(did)
            roles = {p['id']: p['role'] for p in people}
            context = {'topic': topic, 'messages': [{**m, 'role': roles[m['participant_id']]} for m in state['messages']]}
            items = Insights.model_validate(await demo.generate('insights', context, Insights))
            store.insights(did, validate_evidence(items.items, state['messages'], roles))
            summary = await demo.generate('summary', {**context, 'insights': store.snapshot(did)['insights']}, Summary)
            store.message(did, host['id'], summary['content'])
            store.transition(did, 'completed', phase='closing', summary=summary['content'])


if __name__ == '__main__':
    store = Store(Settings().database_url)
    store.initialize()
    asyncio.run(seed(store))
    print('SQLite 已初始化，5 组种子数据就绪。重复执行不会重复插入。')
