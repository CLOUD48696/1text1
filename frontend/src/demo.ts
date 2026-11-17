import type { Snapshot } from './types'

// Design-stage preview only; the application uses the backend unless ?preview=1.
export const preview: Snapshot = {
  discussion: { id: 'preview', topic: 'AI 编程时代，小团队应该优先投资工具还是人才？', expert_count: 4, status: 'running', phase: 'discussion', mode: 'demo', summary: null, error: null, created_at: new Date().toISOString() },
  participants: [
    { id: 'h', role: 'host', name: '林知', profession: '科技观察者', title: '圆桌主持人', stance: '让不同观点被看见', color: '#245b49', status: 'idle', public_focus: '梳理效率与长期能力的关系' },
    { id: 'a', role: 'expert', name: '陈予安', profession: '技术负责人', title: 'CTO', stance: '先用工具释放团队生产力', color: '#b46d43', status: 'speaking', public_focus: '关注真实交付效率' },
    { id: 'b', role: 'expert', name: '沈言', profession: '组织研究者', title: '人才发展顾问', stance: '人才判断力才是长期优势', color: '#557b9a', status: 'preparing', public_focus: '关注团队能力的长期积累' },
    { id: 'c', role: 'expert', name: '周以宁', profession: '产品策略师', title: '产品负责人', stance: '从当前业务瓶颈出发', color: '#8b6ca8', status: 'idle', public_focus: '关注投入产出与验证周期' },
    { id: 'd', role: 'expert', name: '许清和', profession: '创业者', title: '联合创始人', stance: '小范围试验再扩大投入', color: '#56866e', status: 'idle', public_focus: '关注有限预算的配置' },
  ],
  messages: [
    { id: 'm1', participant_id: 'h', sequence: 1, content: '欢迎来到今天的圆桌。当 AI 能承担越来越多的编码工作，小团队的下一笔预算应该投向哪里？我们先从眼前的业务瓶颈谈起。', reply_to_message_id: null, created_at: new Date().toISOString() },
    { id: 'm2', participant_id: 'a', sequence: 2, content: '我倾向于先投资工具，但前提是团队已经具备判断代码质量的能力。用两周试点测量交付周期，比直接扩充编制更容易验证效果。', reply_to_message_id: null, created_at: new Date().toISOString() },
    { id: 'm3', participant_id: 'b', sequence: 3, content: '我同意先试点，不过交付速度不能替代人才成长。如果把节约的时间全部用于增加需求，团队可能永远没有机会补齐架构与业务判断力。', reply_to_message_id: 'm2', created_at: new Date().toISOString() },
  ],
  insights: [
    { id: 'i1', kind: 'consensus', content: '先进行小范围试点，再决定是否扩大投入。', evidence_message_ids: ['m2', 'm3'] },
    { id: 'i2', kind: 'disagreement', content: '工具带来的效率收益，应优先转化为交付量还是人才成长？', evidence_message_ids: ['m2', 'm3'] },
  ], last_event_sequence: 1,
}
