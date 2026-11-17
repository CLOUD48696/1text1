import { ArrowRight, LoaderCircle, Radio } from "lucide-react";
import type { Snapshot } from "../types";
import Avatar from "./Avatar";
interface Props {
  snapshot: Snapshot;
  busy: boolean;
  action: (path: string) => Promise<void>;
}
export default function Roster({ snapshot, busy, action }: Props) {
  const room = snapshot.discussion;
  const participants = snapshot.participants;
  const experts = participants.filter((p) => p.role === "expert");
  return (
    <main className="roster-scroll">
      <div className="roster-heading">
        <span className="eyebrow">MEET YOUR PANEL</span>
        <h2>嘉宾已就位，讨论由你开启。</h2>
        <p>1 位主持人 · {experts.length} 位专家 · 多种看待问题的方式</p>
      </div>
      <div className="roster-grid">
        {participants.map((p) => (
          <article className="roster-card" key={p.id}>
            <Avatar person={p} />
            <span className="role-label">
              {p.role === "host" ? "圆桌主持人" : "专家嘉宾"}
            </span>
            <h3>{p.name}</h3>
            <p>
              {p.profession} · {p.title}
            </p>
            <blockquote>{p.stance}</blockquote>
          </article>
        ))}
      </div>
      <div className="roster-cta">
        <p>
          {room!.mode === "demo"
            ? "当前为演示模式，内容由预设规则生成。"
            : "嘉宾为 AI 生成的虚构角色，观点供讨论参考。"}
        </p>
        <button
          className="primary"
          onClick={() => action("start")}
          disabled={busy}
        >
          {busy ? (
            <LoaderCircle className="spin" size={18} />
          ) : (
            <Radio size={18} />
          )}
          确认阵容，开始讨论
          <ArrowRight size={17} />
        </button>
      </div>
    </main>
  );
}
