import { useEffect, useRef, useState } from "react";
import type { CSSProperties } from "react";
import {
  ArrowDown,
  AudioLines,
  Check,
  ChevronRight,
  CircleDot,
  GitBranch,
  Mic2,
  Plus,
  Radio,
  Sparkles,
  Users,
} from "lucide-react";
import type { Snapshot } from "../types";
import { phases, terminal } from "../presentation";
import Avatar from "./Avatar";
interface Props {
  snapshot: Snapshot;
  connected: boolean;
  busy: boolean;
  action: (path: string) => Promise<void>;
  navigate: (id: string | null) => void;
  setTopic: (v: string) => void;
}
export default function Studio({
  snapshot,
  connected,
  busy,
  action,
  navigate,
  setTopic,
}: Props) {
  const room = snapshot.discussion;
  const participants = snapshot.participants;
  const [tab, setTab] = useState("live");
  const [following, setFollowing] = useState(true);
  const [unread, setUnread] = useState(false);
  const scroll = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (following) {
      scroll.current?.scrollTo({
        top: scroll.current.scrollHeight,
        behavior: "instant",
      });
      setUnread(false);
    } else setUnread(true);
  }, [snapshot?.messages.length, following]);

  const locate = (id: string) => {
    setTab("live");
    setFollowing(false);
    setTimeout(() => {
      const target = document.getElementById(`message-${id}`);
      target?.scrollIntoView({ block: "center", behavior: "smooth" });
      target?.classList.add("referenced");
      setTimeout(() => target?.classList.remove("referenced"), 2000);
    }, 50);
  };
  return (
    <>
      <div className="room-toolbar">
        <span>
          <span className={`connection-dot ${connected ? "online" : ""}`} />
          {terminal(room!.status)
            ? "讨论记录已保存"
            : connected
              ? "实时连接已建立"
              : "正在连接 / 自动重试"}
        </span>
        <span>
          {phases[room!.phase] || "圆桌讨论"}
          <span className="toolbar-divider">/</span>
          {snapshot.messages.length} 条发言
        </span>
      </div>
      <div className="mobile-tabs">
        {[
          ["people", "嘉宾"],
          ["live", "现场"],
          ["insights", "观点"],
        ].map(([key, title]) => (
          <button
            className={tab === key ? "active" : ""}
            onClick={() => setTab(key)}
            key={key}
          >
            {title}
          </button>
        ))}
      </div>
      <main className={`studio-layout tab-${tab}`}>
        <aside className="people-panel panel">
          <div className="panel-heading">
            <h2>
              <Users size={16} />
              圆桌嘉宾
            </h2>
            <span>{participants.length}</span>
          </div>
          <div className="people-scroll">
            {participants.map((p) => (
              <article
                className={`person-card ${p.status}`}
                key={p.id}
                style={{ "--person": p.color } as CSSProperties}
              >
                <div className="person-top">
                  <Avatar person={p} />
                  <div>
                    <h3>
                      {p.name}
                      {p.role === "host" && (
                        <span className="host-label">主持人</span>
                      )}
                    </h3>
                    <p>{p.profession}</p>
                  </div>
                  <span className={`person-indicator ${p.status}`}>
                    {p.status === "speaking" ? (
                      <AudioLines size={17} />
                    ) : (
                      <span />
                    )}
                  </span>
                </div>
                <p className="person-stance">{p.stance}</p>
                <div className="focus">
                  <span>
                    {p.status === "speaking"
                      ? "正在发言"
                      : p.status === "preparing"
                        ? "准备发言"
                        : "当前关注"}
                  </span>
                  <p>{p.public_focus || "倾听其他嘉宾的观点"}</p>
                </div>
              </article>
            ))}
          </div>
          <div className="panel-footnote">
            <CircleDot size={13} />
            不同立场，共同探索
          </div>
        </aside>
        <section className="transcript-panel panel">
          <div className="panel-heading">
            <h2>
              <Radio size={16} />
              讨论现场
            </h2>
            <span className="live-label">
              {room!.status === "running" ? "ON AIR" : "TRANSCRIPT"}
            </span>
          </div>
          <div
            className="transcript-scroll"
            ref={scroll}
            onScroll={() => {
              const el = scroll.current;
              if (el)
                setFollowing(
                  el.scrollHeight - el.scrollTop - el.clientHeight < 65,
                );
            }}
          >
            <div className="transcript-start">
              <span />
              讨论从一个好问题开始
              <span />
            </div>
            {snapshot.messages.map((m) => {
              const p = participants.find((p) => p.id === m.participant_id);
              if (!p) return null;
              const target = snapshot.messages.find(
                (x) => x.id === m.reply_to_message_id,
              );
              const targetName = participants.find(
                (x) => x.id === target?.participant_id,
              )?.name;
              return (
                <article
                  id={`message-${m.id}`}
                  className={`message ${p.role}`}
                  key={m.id}
                >
                  <Avatar person={p} small />
                  <div className="message-body">
                    <div className="message-meta">
                      <strong style={{ color: p.color }}>{p.name}</strong>
                      <span>{p.title}</span>
                      <time>{String(m.sequence).padStart(2, "0")}</time>
                    </div>
                    {target && (
                      <button
                        className="reply-link"
                        onClick={() => locate(target.id)}
                      >
                        回应 {targetName} 的观点
                      </button>
                    )}
                    <p>{m.content}</p>
                  </div>
                </article>
              );
            })}
            {room!.status === "running" && (
              <div className="thinking-line">
                <span />
                <span />
                <span />
                <small>让观点继续交汇</small>
              </div>
            )}
            {room!.summary && (
              <div className="summary-card">
                <span className="eyebrow">
                  <Check size={14} /> 本场讨论已结束
                </span>
                <h3>带着更完整的视角，继续思考。</h3>
                <p>主持人的总结已记录在上方。共识与分歧保留在观点面板中。</p>
                <button className="secondary" onClick={() => navigate(null)}>
                  发起新的讨论
                  <Plus size={15} />
                </button>
              </div>
            )}
            {["failed", "interrupted"].includes(room!.status) && (
              <div className="summary-card error-card">
                <h3>
                  {room!.status === "interrupted"
                    ? "这场讨论已中断"
                    : "暂时无法继续讨论"}
                </h3>
                <p>
                  {room!.error ||
                    "服务已重启，已有内容已保留。你可以重新发起讨论。"}
                </p>
                {snapshot.messages.length === 0 && room!.status === "failed" ? (
                  <button
                    className="secondary"
                    disabled={busy}
                    onClick={() => action("retry-generation")}
                  >
                    重试嘉宾生成
                  </button>
                ) : (
                  <button
                    className="secondary"
                    onClick={() => {
                      setTopic(room!.topic);
                      navigate(null);
                    }}
                  >
                    使用相同话题重新开始
                  </button>
                )}
              </div>
            )}
          </div>
          {unread && !following && (
            <button className="new-messages" onClick={() => setFollowing(true)}>
              <ArrowDown size={14} />
              查看新发言
            </button>
          )}
          <div className="transcript-footer">
            <Mic2 size={14} />
            <span>你正在旁听 · 主持人将引导讨论节奏</span>
          </div>
        </section>
        <aside className="insights-panel panel">
          <div className="panel-heading">
            <h2>
              <GitBranch size={16} />
              思考的脉络
            </h2>
            <span className="insight-count">{snapshot.insights.length}</span>
          </div>
          <div className="insights-scroll">
            <p className="insights-intro">在交锋中，发现靠近与不同。</p>
            {(["consensus", "disagreement"] as const).map((kind) => (
              <section className={`insight-section ${kind}`} key={kind}>
                <h3>
                  {kind === "consensus" ? (
                    <Check size={16} />
                  ) : (
                    <GitBranch size={16} />
                  )}{" "}
                  {kind === "consensus" ? "正在形成的共识" : "值得继续的分歧"}
                  <span>
                    {snapshot.insights.filter((i) => i.kind === kind).length}
                  </span>
                </h3>
                {snapshot.insights
                  .filter((i) => i.kind === kind)
                  .map((insight, i) => (
                    <article className="insight-card" key={insight.id}>
                      <span className="insight-number">
                        {String(i + 1).padStart(2, "0")}
                      </span>
                      <p>{insight.content}</p>
                      <div className="evidence">
                        {insight.evidence_message_ids.map((id) => {
                          const msg = snapshot.messages.find(
                            (m) => m.id === id,
                          );
                          const person = participants.find(
                            (p) => p.id === msg?.participant_id,
                          );
                          return person ? (
                            <button
                              key={id}
                              onClick={() => locate(id)}
                              title="查看原始发言"
                            >
                              {person.name}
                              <ChevronRight size={11} />
                            </button>
                          ) : null;
                        })}
                      </div>
                    </article>
                  ))}
                {!snapshot.insights.some((i) => i.kind === kind) && (
                  <div className="insight-placeholder">
                    {terminal(room!.status)
                      ? "本场暂无足够证据支持此类观点"
                      : "等待更多观点，逐步提炼…"}
                  </div>
                )}
              </section>
            ))}
            <div className="insight-note">
              <Sparkles size={16} />
              <p>
                观点随讨论持续更新。
                <br />
                点击姓名，可以回到对应发言。
              </p>
            </div>
          </div>
        </aside>
      </main>
    </>
  );
}
