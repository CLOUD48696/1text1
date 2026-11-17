"""Deterministic, explicitly labelled demo data. Never used as a live-mode fallback."""
import asyncio
import hashlib

from app.schemas import Roster

TOPICS = [
    '小型软件团队应该优先使用 AI 编程工具还是增加招聘？',
    '企业是否应实行每周四天工作制？',
    '高校课程应如何允许学生使用生成式 AI？',
    '初创产品应该先增长还是先盈利？',
    '城市中心是否应限制私人汽车通行？',
]
DOMAINS = [
    (['技术负责人', '组织研究者', '产品策略师', '创业者', '安全工程师', '财务顾问'], '交付效率', '人才培养', '工具试点'),
    (['人力资源顾问', '组织研究者', '运营负责人', '劳动关系学者', '客户服务主管', '财务顾问'], '单位时间产出', '工作强度', '团队排班试点'),
    (['教学研究者', '教育伦理学者', '课程设计师', '学生发展顾问', '技术教育专家', '学术诚信顾问'], '学习效果', '独立思考能力', '课程试点'),
    (['增长负责人', '投资研究者', '产品策略师', '创业者', '客户成功经理', '财务顾问'], '用户增长', '现金流安全', '分阶段预算实验'),
    (['城市规划师', '交通研究者', '公共政策顾问', '社区服务者', '无障碍设计师', '经济研究者'], '通行效率', '出行公平', '区域交通试点'),
]


def domain(topic):
    if '工作制' in topic: return DOMAINS[1]
    if any(w in topic for w in ['高校', '课堂', '学生']): return DOMAINS[2]
    if any(w in topic for w in ['盈利', '增长']): return DOMAINS[3]
    if any(w in topic for w in ['城市', '汽车', '交通']): return DOMAINS[4]
    if any(w in topic for w in ['AI', '编程', '招聘']): return DOMAINS[0]
    return (['领域研究者', '风险分析师', '实践顾问', '组织策略师', '伦理研究者', '评估专家'], '短期收益', '长期影响', '小范围试点')


def make_roster(topic, count):
    jobs, gain, risk, pilot = domain(topic)
    names = ['陈予安', '沈言', '周以宁', '许清和', '方予时', '陆知远']
    stances = [f'优先验证{gain}，再扩大投入', f'不能忽略{risk}与隐性代价', f'以{pilot}的实际证据做决策', '先明确目标和资源约束，再选择路径', '关注受影响人群与失效风险', '重视可持续成本与退出条件']
    return Roster.model_validate({'host': {'name': '林知', 'profession': '议题观察者', 'title': '圆桌主持人', 'stance': '让不同视角充分表达，用证据梳理争议'}, 'experts': [dict(name=names[i], profession=jobs[i], title=['资深实践者', '研究顾问', '策略负责人', '项目负责人', '独立研究员', '评估顾问'][i], stance=stances[i]) for i in range(count)]})


class DemoLLM:
    def __init__(self, delay=0): self.delay = delay

    async def generate(self, task, context, schema):
        await asyncio.sleep(self.delay)
        topic = context['topic']
        _, gain, risk, pilot = domain(topic)
        messages = context.get('messages', [])
        if task == 'roster': return make_roster(topic, context['expert_count']).model_dump()
        if task == 'intent':
            p = context['person']
            last = messages[-1] if messages else None
            recent = [m for m in messages if m['participant_id'] == p['id']]
            if last and last['participant_id'] == p['id']:
                action, urgency = 'wait', 0.1
            else:
                score = int(hashlib.sha256(f"{p['name']}:{len(messages)}:{topic}".encode()).hexdigest()[:4], 16)
                action = 'rebut' if p['position'] % 2 == 0 and last and last.get('role') != 'host' else 'supplement' if recent else 'raise'
                urgency = 0.35 + (score % 65) / 100
            return dict(action=action, urgency=urgency, target_message_id=last['id'] if last and last.get('role') != 'host' else None, public_focus=p['stance'][:80])
        if task == 'opening': return {'content': f'欢迎来到本场圆桌，我们围绕“{topic}”展开讨论。请各位先说明自己的判断，以及最希望被验证的一个条件。'}
        if task == 'followup': return {'content': f'我们已经看到了{gain}与{risk}之间的张力。如果先做一次{pilot}，什么结果会让各位改变原来的判断？'}
        if task == 'speech':
            person = context['person']
            prior = sum(m['participant_id'] == person['id'] for m in messages)
            variants = [
                [f'我支持先验证{gain}，用{pilot}积累证据后再扩大投入。需要同时记录成本和受影响人群的反馈，不能只看一个漂亮的效率指标。', f'回应前面的担忧，我支持先做{pilot}，但希望优先验证{gain}。试点必须有退出条件，结果不理想时及时调整。'],
                [f'我同意先做{pilot}，但对把{gain}放在首位持保留意见。{risk}应成为独立的验收条件，否则短期效果可能掩盖长期代价。', f'我仍然支持先做{pilot}，分歧在于评价权重。我会优先保护{risk}，而不只是追求{gain}。'],
                [f'我赞成先做{pilot}，并在开始前约定比较基线。只有让{gain}和{risk}都进入评价表，讨论才不会停留在各自偏好的故事里。', f'我同意前面关于隐性成本的提醒，所以{pilot}需要留出反馈窗口。我的建议是先比较不同群体的结果，再判断是否值得扩大。'],
                [f'我支持先做{pilot}，但要把资源上限和失败后的退出方案说清楚。对于{gain}，我的立场是先验证能否持续，再谈规模化。', f'回应前面的观点，{pilot}可以帮助我们降低决策的不确定性。若{risk}出现明显恶化，即使短期指标改善，也应暂停扩展。'],
                [f'我同意先做{pilot}，并重点观察谁承担额外成本。关于{gain}的平均数字，不能代替对不同群体的分别评估。', f'我的补充是给{pilot}建立投诉和纠偏渠道。只有负面影响可以被及时看见，试点结果才有说服力。'],
                [f'我支持先做{pilot}，但需要核算持续成本。即便{gain}得到改善，也应确认现有预算能否长期承担。', f'我更关心试点结束后有没有明确的继续或停止标准。请把{risk}和长期投入一并列入决策依据。'],
            ]
            text = variants[(person['position']-1) % 6][prior % 2]
            return {'content': text}
        if task == 'insights':
            expert_messages = [m for m in messages if m.get('role') == 'expert']
            authors = {}
            for message in expert_messages: authors.setdefault(message['participant_id'], message)
            if len(authors) < 2: return {'items': []}
            evidence = [m['id'] for m in list(authors.values())[:4]]
            items = [dict(kind='consensus', content=f'先开展{pilot}，用实际证据决定是否扩大投入。', evidence_message_ids=evidence)]
            supportive = next((m for m in expert_messages if '优先验证' in m['content']), None)
            skeptical = next((m for m in expert_messages if '持保留意见' in m['content'] or '优先保护' in m['content']), None)
            if supportive and skeptical and supportive['participant_id'] != skeptical['participant_id']:
                items.append(dict(kind='disagreement', content=f'决策时应优先推动{gain}，还是优先保护{risk}？', evidence_message_ids=[supportive['id'], skeptical['id']]))
            return {'items': items}
        if task == 'summary':
            insights = context.get('insights', [])
            shared = '；'.join(i['content'] for i in insights if i['kind'] == 'consensus')
            divided = '；'.join(i['content'] for i in insights if i['kind'] == 'disagreement')
            return {'content': f'今天关于“{topic}”的讨论到这里告一段落。' + (f'已有证据支持的共识是：{shared}' if shared else '目前还没有足够证据确认共同立场。') + (f'仍待讨论的问题是：{divided}' if divided else '已记录的发言尚不足以提炼明确的立场分歧。') + '下一步可以把讨论中的判断转成可观察的指标，在有限范围内验证，并根据反馈调整方案。以上为预设演示内容，不代表真实专家或真实模型的结论。'}
        raise ValueError('Unknown demo task')

    async def close(self): pass
