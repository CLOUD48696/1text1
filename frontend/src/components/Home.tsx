import type { FormEvent } from "react";
import {
  ArrowRight,
  AudioLines,
  ChevronRight,
  GitBranch,
  Layers3,
  LoaderCircle,
  MessageCircle,
  Radio,
  Sparkles,
  Users,
} from "lucide-react";
import type { Discussion } from "../types";
import { labels, prompts } from "../presentation";
interface Props {
  items: Discussion[];
  topic: string;
  count: number;
  filter: string;
  mode: string;
  busy: boolean;
  setTopic: (v: string) => void;
  setCount: (v: number) => void;
  setFilter: (v: string) => void;
  create: (event?: FormEvent) => Promise<void>;
  navigate: (id: string | null) => void;
}
export default function Home({
  items,
  topic,
  count,
  filter,
  mode,
  busy,
  setTopic,
  setCount,
  setFilter,
  create,
  navigate,
}: Props) {
  const visible = items.filter(
    (d) =>
      filter === "all" ||
      (filter === "active"
        ? ["running", "generating", "ready"].includes(d.status)
        : d.status === "completed"),
  );
  return (
    <main className="home-scroll">
      <div className="home-content">
        <div className="hero-top">
          <span className="eyebrow">
            <span className="tiny-dot" /> A SPACE FOR DIFFERENT PERSPECTIVES
          </span>
          <span className="edition">YOUR THINKING ROOM / 01</span>
        </div>
        <section className="hero">
          <div>
            <h1>
              让观点相遇，
              <br />
              <span>让思考发生。</span>
            </h1>
            <p>
              一个议题，多种视角。邀请 AI 专家围坐一桌，
              <br className="desktop-break" />
              在对话与交锋中，找到更完整的答案。
            </p>
            <div className="hero-benefits">
              <span>
                <Users size={15} />
                多元专家视角
              </span>
              <span>
                <Radio size={15} />
                实时圆桌讨论
              </span>
              <span>
                <GitBranch size={15} />
                共识与分歧
              </span>
            </div>
          </div>
          <div className="roundtable-art" aria-hidden="true">
            <div className="orbit orbit-outer" />
            <div className="orbit orbit-inner" />
            <div className="table-center">
              <AudioLines size={36} />
              <span>THINK TOGETHER</span>
            </div>
            {["策略", "技术", "研究", "实践"].map((name, i) => (
              <div className={`seat seat-${i}`} key={name}>
                <span>{["策", "技", "研", "实"][i]}</span>
                <small>{name}视角</small>
              </div>
            ))}
            <span className="art-note">
              <span className="tiny-dot" /> 好问题，值得一场讨论
            </span>
          </div>
        </section>
        <section className="create-panel">
          <div className="section-heading">
            <span className="icon-box">
              <Sparkles size={19} />
            </span>
            <div>
              <h2>开启一场新讨论</h2>
              <p>把你正在思考的问题带到桌上</p>
            </div>
            <span className="step-hint">
              01 议题 <ChevronRight size={12} /> 02 嘉宾{" "}
              <ChevronRight size={12} /> 03 开场
            </span>
          </div>
          <form onSubmit={create}>
            <label className="sr-only" htmlFor="topic">
              讨论话题
            </label>
            <textarea
              id="topic"
              placeholder="例如：AI 编程时代，小团队应该优先投资工具还是人才？"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              maxLength={240}
              minLength={4}
              required
            />
            <div className="create-footer">
              <div className="count-control">
                <Users size={16} />
                <span>专家人数</span>
                <div className="stepper">
                  <button
                    type="button"
                    aria-label="减少专家"
                    disabled={count <= 2}
                    onClick={() => setCount(count - 1)}
                  >
                    −
                  </button>
                  <strong>{count}</strong>
                  <button
                    type="button"
                    aria-label="增加专家"
                    disabled={count >= 6}
                    onClick={() => setCount(count + 1)}
                  >
                    +
                  </button>
                </div>
                <small>另配 1 位主持人</small>
              </div>
              <button
                className="primary"
                disabled={busy || topic.trim().length < 4}
              >
                {busy ? (
                  <LoaderCircle className="spin" size={17} />
                ) : (
                  <Sparkles size={17} />
                )}
                生成嘉宾阵容
                <ArrowRight size={16} />
              </button>
            </div>
          </form>
          <div className="suggestions">
            <span>试试这些话题</span>
            {prompts.map((t, i) => (
              <button key={t} onClick={() => setTopic(t)}>
                {["AI 与团队效率", "四天工作制", "AI 走进课堂"][i]}
                <ArrowRight size={12} />
              </button>
            ))}
          </div>
        </section>
        <section className="discussions">
          <div className="list-heading">
            <div>
              <h2>
                讨论空间 <span className="count-badge">{items.length}</span>
              </h2>
              <p>继续未完的思考，或回看观点的碰撞</p>
            </div>
            <div className="filters">
              {[
                ["all", "全部"],
                ["active", "进行中"],
                ["completed", "已结束"],
              ].map(([key, title]) => (
                <button
                  className={filter === key ? "chosen" : ""}
                  key={key}
                  onClick={() => setFilter(key)}
                >
                  {title}
                </button>
              ))}
            </div>
          </div>
          <div className="discussion-grid">
            {visible.map((d, i) => (
              <button
                className="discussion-card"
                key={d.id}
                onClick={() => navigate(d.id)}
              >
                <div className="card-top">
                  <span className="card-icon">
                    <MessageCircle size={19} />
                  </span>
                  <span className={`status-pill ${d.status}`}>
                    <span className="tiny-dot" />
                    {labels[d.status]}
                  </span>
                </div>
                <h3>{d.topic}</h3>
                <div className="card-bottom">
                  <span className="mini-avatars">
                    {["研", "策", "技"].map((x, j) => (
                      <i
                        key={x}
                        style={{
                          background: ["#eeded0", "#dce7ee", "#e7dff0"][
                            (i + j) % 3
                          ],
                        }}
                      >
                        {x}
                      </i>
                    ))}
                    <small>{d.expert_count} 位专家</small>
                  </span>
                  <ArrowRight size={17} />
                </div>
              </button>
            ))}
          </div>
          {!visible.length && (
            <div className="empty-list">
              <Layers3 size={26} />
              <p>
                {items.length
                  ? "这个分类还没有讨论"
                  : "第一场好讨论，从你的问题开始"}
              </p>
            </div>
          )}
        </section>
        <footer className="home-footer">
          <span>Panel Studio · 为更深入的思考留一个位置</span>
          <span>
            {mode === "live"
              ? "AI 观点供参考，请核实事实"
              : "演示模式使用预设内容，不调用大模型"}
          </span>
        </footer>
      </div>
    </main>
  );
}
