import { useCallback, useEffect, useRef, useState } from 'react'
import type { CSSProperties, FormEvent } from 'react'
import { ArrowDown, ArrowLeft, ArrowRight, AudioLines, Check, ChevronRight, CircleDot, Compass, GitBranch, Layers3, LoaderCircle, MessageCircle, Mic2, Plus, Radio, RefreshCw, Sparkles, Users, X } from 'lucide-react'
import { api } from './api'
import { useStudio } from './store'
import { preview } from './demo'
import type { Discussion, Participant, Snapshot, StudioEvent } from './types'

const labels: Record<string, string> = { generating: '邀请嘉宾中', ready: '待开场', running: '讨论进行中', completed: '已结束', failed: '发生错误', interrupted: '已中断' }
const phases: Record<string, string> = { opening: '主持人开场', discussion: '观点交锋', synthesis: '梳理观点', closing: '主持人总结', roster: '准备阵容' }
const prompts = ['小型软件团队应该优先使用 AI 编程工具还是增加招聘？', '企业是否应实行每周四天工作制？', '高校课程应如何允许学生使用生成式 AI？']
const terminal = (status: string) => ['completed', 'failed', 'interrupted'].includes(status)
const isPreview = new URLSearchParams(location.search).has('preview')

function Avatar({ person, small = false }: { person: Participant; small?: boolean }) {
  return <span className={`avatar ${small ? 'small' : ''}`} style={{ '--person': person.color } as CSSProperties}>{person.role === 'host' ? <Mic2 size={small ? 16 : 21} /> : person.name.slice(-2)}</span>
}

export default function App() {
  const [selected, select] = useState<string | null>(() => isPreview ? 'preview' : location.hash.slice(1) || null)
  const [items, setItems] = useState<Discussion[]>([])
  const [mode, setMode] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [connected, setConnected] = useState(false)
  const [filter, setFilter] = useState('all')
  const [topic, setTopic] = useState('')
  const [count, setCount] = useState(4)
  const [tab, setTab] = useState('live')
  const [following, setFollowing] = useState(true)
  const [unread, setUnread] = useState(false)
  const scroll = useRef<HTMLDivElement>(null)
  const snapshot = useStudio(s => s.snapshot)
  const refresh = useCallback(async () => {
    try { const [list, health] = await Promise.all([api<{ items: Discussion[] }>('/discussions?limit=100'), api<{ mode: string }>('/health')]); setItems(list.items); setMode(health.mode); setError('') }
    catch (e) { setError((e as Error).message) }
  }, [])
  useEffect(() => { if (!isPreview) { void refresh(); const timer = setInterval(refresh, 8000); return () => clearInterval(timer) } }, [refresh])
  useEffect(() => {
    const onHash = () => select(location.hash.slice(1) || null)
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])
  const navigate = (id: string | null) => { location.hash = id || ''; select(id); setTab('live'); setFollowing(true); setUnread(false); setError('') }

  useEffect(() => {
    useStudio.getState().set(null)
    setConnected(false)
    if (!selected) return
    if (isPreview) { useStudio.getState().set(preview); setMode('demo'); return }
    let alive = true
    let stream: EventSource | undefined
    api<Snapshot>(`/discussions/${selected}`).then(s => {
      if (!alive) return
      useStudio.getState().set(s)
      if (terminal(s.discussion.status)) return
      stream = new EventSource(`/api/discussions/${selected}/events?after=${s.last_event_sequence}`)
      stream.onopen = () => { if (alive) setConnected(true) }
      stream.onerror = () => { if (alive) setConnected(false) }
      stream.onmessage = (message) => {
        if (!alive) return
        const event = JSON.parse(message.data) as StudioEvent
        useStudio.getState().apply(event)
        const current = useStudio.getState().snapshot
        if (current && terminal(current.discussion.status)) { stream?.close(); setConnected(false); void refresh() }
      }
    }).catch(e => { if (alive) setError(e.message) })
    return () => { alive = false; stream?.close() }
  }, [selected, refresh])

  useEffect(() => {
    if (following) { scroll.current?.scrollTo({ top: scroll.current.scrollHeight, behavior: 'smooth' }); setUnread(false) }
    else setUnread(true)
  }, [snapshot?.messages.length, following])

  async function create(event?: FormEvent) {
    event?.preventDefault(); setBusy(true); setError('')
    try { const result = await api<{ discussion_id: string }>('/discussions', { topic, expert_count: count }); navigate(result.discussion_id); void refresh() }
    catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }
  async function action(path: string) {
    setBusy(true); setError('')
    try { await api(`/discussions/${selected}/${path}`, {}); const fresh = await api<Snapshot>(`/discussions/${selected}`); useStudio.getState().set(fresh)
      // Reopen the subscription after retrying a terminal generation failure.
      if (path === 'retry-generation') { select(null); setTimeout(() => select(selected), 0) }
    } catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }
  const room = snapshot?.discussion
  const experts = snapshot?.participants.filter(p => p.role === 'expert') || []
  const visible = items.filter(d => filter === 'all' || (filter === 'active' ? ['running', 'generating', 'ready'].includes(d.status) : d.status === 'completed'))
  const participants = snapshot?.participants || []
  const locate = (id: string) => { setTab('live'); setFollowing(false); setTimeout(() => { const target = document.getElementById(`message-${id}`); target?.scrollIntoView({ block: 'center', behavior: 'smooth' }); target?.classList.add('referenced'); setTimeout(() => target?.classList.remove('referenced'), 2000) }, 50) }

  return <div className="app-shell">
    <header className="topbar">
      <button className="brand" onClick={() => navigate(null)} aria-label="返回首页"><span className="brand-mark"><AudioLines size={23} /></span><span>Panel<span className="brand-light"> Studio</span><small>AI 圆桌讨论</small></span></button>
      <nav><button className={!selected ? 'nav-item active' : 'nav-item'} onClick={() => navigate(null)}><Compass size={16} />讨论空间</button><span className="nav-divider"/><span className="mode-tag"><span className="tiny-dot"/>{mode === 'live' ? '真实模型' : '演示模式'}</span></nav>
      <div className="workspace-label">个人工作空间<span className="user-avatar">我</span></div>
    </header>
    {error && <div className="error-banner" role="alert"><span>{error}</span><button onClick={() => { setError(''); void refresh() }} aria-label="重试连接"><RefreshCw size={15}/></button><button onClick={() => setError('')} aria-label="关闭提示"><X size={15}/></button></div>}
    {!selected ? <main className="home-scroll">
      <div className="home-content">
        <div className="hero-top"><span className="eyebrow"><span className="tiny-dot"/> A SPACE FOR DIFFERENT PERSPECTIVES</span><span className="edition">YOUR THINKING ROOM / 01</span></div>
        <section className="hero"><div><h1>让观点相遇，<br/><span>让思考发生。</span></h1><p>一个议题，多种视角。邀请 AI 专家围坐一桌，<br className="desktop-break"/>在对话与交锋中，找到更完整的答案。</p><div className="hero-benefits"><span><Users size={15}/>多元专家视角</span><span><Radio size={15}/>实时圆桌讨论</span><span><GitBranch size={15}/>共识与分歧</span></div></div>
          <div className="roundtable-art" aria-hidden="true"><div className="orbit orbit-outer"/><div className="orbit orbit-inner"/><div className="table-center"><AudioLines size={36}/><span>THINK TOGETHER</span></div>{['策略','技术','研究','实践'].map((name,i)=><div className={`seat seat-${i}`} key={name}><span>{['策','技','研','实'][i]}</span><small>{name}视角</small></div>)}<span className="art-note"><span className="tiny-dot"/> 好问题，值得一场讨论</span></div>
        </section>
        <section className="create-panel"><div className="section-heading"><span className="icon-box"><Sparkles size={19}/></span><div><h2>开启一场新讨论</h2><p>把你正在思考的问题带到桌上</p></div><span className="step-hint">01 议题 <ChevronRight size={12}/> 02 嘉宾 <ChevronRight size={12}/> 03 开场</span></div>
          <form onSubmit={create}><label className="sr-only" htmlFor="topic">讨论话题</label><textarea id="topic" placeholder="例如：AI 编程时代，小团队应该优先投资工具还是人才？" value={topic} onChange={e=>setTopic(e.target.value)} maxLength={240} minLength={4} required/><div className="create-footer"><div className="count-control"><Users size={16}/><span>专家人数</span><div className="stepper"><button type="button" aria-label="减少专家" disabled={count<=2} onClick={()=>setCount(count-1)}>−</button><strong>{count}</strong><button type="button" aria-label="增加专家" disabled={count>=6} onClick={()=>setCount(count+1)}>+</button></div><small>另配 1 位主持人</small></div><button className="primary" disabled={busy || topic.trim().length<4}>{busy ? <LoaderCircle className="spin" size={17}/> : <Sparkles size={17}/>}生成嘉宾阵容<ArrowRight size={16}/></button></div></form>
          <div className="suggestions"><span>试试这些话题</span>{prompts.map((t,i)=><button key={t} onClick={()=>setTopic(t)}>{['AI 与团队效率','四天工作制','AI 走进课堂'][i]}<ArrowRight size={12}/></button>)}</div>
        </section>
        <section className="discussions"><div className="list-heading"><div><h2>讨论空间 <span className="count-badge">{items.length}</span></h2><p>继续未完的思考，或回看观点的碰撞</p></div><div className="filters">{[['all','全部'],['active','进行中'],['completed','已结束']].map(([key,title])=><button className={filter===key?'chosen':''} key={key} onClick={()=>setFilter(key)}>{title}</button>)}</div></div><div className="discussion-grid">{visible.map((d,i)=><button className="discussion-card" key={d.id} onClick={()=>navigate(d.id)}><div className="card-top"><span className="card-icon"><MessageCircle size={19}/></span><span className={`status-pill ${d.status}`}><span className="tiny-dot"/>{labels[d.status]}</span></div><h3>{d.topic}</h3><div className="card-bottom"><span className="mini-avatars">{['研','策','技'].map((x,j)=><i key={x} style={{background:['#eeded0','#dce7ee','#e7dff0'][(i+j)%3]}}>{x}</i>)}<small>{d.expert_count} 位专家</small></span><ArrowRight size={17}/></div></button>)}</div>{!visible.length && <div className="empty-list"><Layers3 size={26}/><p>{items.length ? '这个分类还没有讨论' : '第一场好讨论，从你的问题开始'}</p></div>}</section>
        <footer className="home-footer"><span>Panel Studio · 为更深入的思考留一个位置</span><span>{mode==='live'?'AI 观点供参考，请核实事实':'演示模式使用预设内容，不调用大模型'}</span></footer>
      </div>
    </main> : !snapshot ? <main className="loading"><LoaderCircle className="spin"/><p>{error ? '暂时无法打开讨论' : '正在进入讨论空间…'}</p><button className="secondary" onClick={()=>navigate(null)}>返回讨论空间</button></main> : <>
      <div className="room-heading"><button className="icon-button" onClick={()=>navigate(null)} aria-label="返回讨论列表"><ArrowLeft size={20}/></button><div className="room-title"><div className="eyebrow">PANEL ROOM <span> / {room!.mode==='demo'?'演示内容':'AI LIVE'}</span></div><h1>{room!.topic}</h1></div><span className={`status-pill ${room!.status}`}><span className="tiny-dot"/>{labels[room!.status]}</span></div>
      {room!.status === 'generating' ? <main className="loading"><div className="loading-symbol"><Sparkles size={30}/></div><h2>正在邀请不同视角的声音</h2><p>围绕你的议题，寻找专业与立场互补的嘉宾…</p><LoaderCircle className="spin" size={19}/></main> : room!.status === 'ready' ? <main className="roster-scroll"><div className="roster-heading"><span className="eyebrow">MEET YOUR PANEL</span><h2>嘉宾已就位，讨论由你开启。</h2><p>1 位主持人 · {experts.length} 位专家 · 多种看待问题的方式</p></div><div className="roster-grid">{participants.map(p=><article className="roster-card" key={p.id}><Avatar person={p}/><span className="role-label">{p.role==='host'?'圆桌主持人':'专家嘉宾'}</span><h3>{p.name}</h3><p>{p.profession} · {p.title}</p><blockquote>{p.stance}</blockquote></article>)}</div><div className="roster-cta"><p>{room!.mode==='demo'?'当前为演示模式，内容由预设规则生成。':'嘉宾为 AI 生成的虚构角色，观点供讨论参考。'}</p><button className="primary" onClick={()=>action('start')} disabled={busy}>{busy?<LoaderCircle className="spin" size={18}/>:<Radio size={18}/>}确认阵容，开始讨论<ArrowRight size={17}/></button></div></main> : <>
        <div className="room-toolbar"><span><span className={`connection-dot ${connected?'online':''}`}/>{terminal(room!.status)?'讨论记录已保存':connected?'实时连接已建立':'正在连接 / 自动重试'}</span><span>{phases[room!.phase] || '圆桌讨论'}<span className="toolbar-divider">/</span>{snapshot.messages.length} 条发言</span></div>
        <div className="mobile-tabs">{[['people','嘉宾'],['live','现场'],['insights','观点']].map(([key,title])=><button className={tab===key?'active':''} onClick={()=>setTab(key)} key={key}>{title}</button>)}</div>
        <main className={`studio-layout tab-${tab}`}>
          <aside className="people-panel panel"><div className="panel-heading"><h2><Users size={16}/>圆桌嘉宾</h2><span>{participants.length}</span></div><div className="people-scroll">{participants.map(p=><article className={`person-card ${p.status}`} key={p.id} style={{'--person':p.color} as CSSProperties}><div className="person-top"><Avatar person={p}/><div><h3>{p.name}{p.role==='host'&&<span className="host-label">主持人</span>}</h3><p>{p.profession}</p></div><span className={`person-indicator ${p.status}`}>{p.status==='speaking'?<AudioLines size={17}/>:<span/>}</span></div><p className="person-stance">{p.stance}</p><div className="focus"><span>{p.status==='speaking'?'正在发言':p.status==='preparing'?'准备发言':'当前关注'}</span><p>{p.public_focus || '倾听其他嘉宾的观点'}</p></div></article>)}</div><div className="panel-footnote"><CircleDot size={13}/>不同立场，共同探索</div></aside>
          <section className="transcript-panel panel"><div className="panel-heading"><h2><Radio size={16}/>讨论现场</h2><span className="live-label">{room!.status==='running'?'ON AIR':'TRANSCRIPT'}</span></div><div className="transcript-scroll" ref={scroll} onScroll={()=>{const el=scroll.current;if(el)setFollowing(el.scrollHeight-el.scrollTop-el.clientHeight<65)}}><div className="transcript-start"><span/>讨论从一个好问题开始<span/></div>{snapshot.messages.map(m=>{const p=participants.find(p=>p.id===m.participant_id); if(!p)return null; const target=snapshot.messages.find(x=>x.id===m.reply_to_message_id); const targetName=participants.find(x=>x.id===target?.participant_id)?.name;return <article id={`message-${m.id}`} className={`message ${p.role}`} key={m.id}><Avatar person={p} small/><div className="message-body"><div className="message-meta"><strong style={{color:p.color}}>{p.name}</strong><span>{p.title}</span><time>{String(m.sequence).padStart(2,'0')}</time></div>{target&&<button className="reply-link" onClick={()=>locate(target.id)}>回应 {targetName} 的观点</button>}<p>{m.content}</p></div></article>})}{room!.status==='running'&&<div className="thinking-line"><span/><span/><span/><small>让观点继续交汇</small></div>}{room!.summary&&<div className="summary-card"><span className="eyebrow"><Check size={14}/> 本场讨论已结束</span><h3>带着更完整的视角，继续思考。</h3><p>主持人的总结已记录在上方。共识与分歧保留在观点面板中。</p><button className="secondary" onClick={()=>navigate(null)}>发起新的讨论<Plus size={15}/></button></div>}{['failed','interrupted'].includes(room!.status)&&<div className="summary-card error-card"><h3>{room!.status==='interrupted'?'这场讨论已中断':'暂时无法继续讨论'}</h3><p>{room!.error || '服务已重启，已有内容已保留。你可以重新发起讨论。'}</p>{snapshot.messages.length===0&&room!.status==='failed'?<button className="secondary" disabled={busy} onClick={()=>action('retry-generation')}>重试嘉宾生成</button>:<button className="secondary" onClick={()=>{setTopic(room!.topic);navigate(null)}}>使用相同话题重新开始</button>}</div>}</div>{unread&&!following&&<button className="new-messages" onClick={()=>setFollowing(true)}><ArrowDown size={14}/>查看新发言</button>}<div className="transcript-footer"><Mic2 size={14}/><span>你正在旁听 · 主持人将引导讨论节奏</span></div></section>
          <aside className="insights-panel panel"><div className="panel-heading"><h2><GitBranch size={16}/>思考的脉络</h2><span className="insight-count">{snapshot.insights.length}</span></div><div className="insights-scroll"><p className="insights-intro">在交锋中，发现靠近与不同。</p>{(['consensus','disagreement'] as const).map(kind=><section className={`insight-section ${kind}`} key={kind}><h3>{kind==='consensus'?<Check size={16}/>:<GitBranch size={16}/>} {kind==='consensus'?'正在形成的共识':'值得继续的分歧'}<span>{snapshot.insights.filter(i=>i.kind===kind).length}</span></h3>{snapshot.insights.filter(i=>i.kind===kind).map((insight,i)=><article className="insight-card" key={insight.id}><span className="insight-number">{String(i+1).padStart(2,'0')}</span><p>{insight.content}</p><div className="evidence">{insight.evidence_message_ids.map(id=>{const msg=snapshot.messages.find(m=>m.id===id);const person=participants.find(p=>p.id===msg?.participant_id);return person?<button key={id} onClick={()=>locate(id)} title="查看原始发言">{person.name}<ChevronRight size={11}/></button>:null})}</div></article>)}{!snapshot.insights.some(i=>i.kind===kind)&&<div className="insight-placeholder">{terminal(room!.status)?'本场暂无足够证据支持此类观点':'等待更多观点，逐步提炼…'}</div>}</section>)}<div className="insight-note"><Sparkles size={16}/><p>观点随讨论持续更新。<br/>点击姓名，可以回到对应发言。</p></div></div></aside>
        </main>
      </>}
    </>}
  </div>
}
