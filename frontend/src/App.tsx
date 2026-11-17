import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import {
  ArrowLeft,
  AudioLines,
  Compass,
  LoaderCircle,
  RefreshCw,
  Sparkles,
  X,
} from "lucide-react";
import { api } from "./api";
import { useStudio } from "./store";
import type { Discussion, Snapshot, StudioEvent } from "./types";
import { labels, terminal } from "./presentation";
import Home from "./components/Home";
import Roster from "./components/Roster";
import Studio from "./components/Studio";

export default function App() {
  const [selected, select] = useState<string | null>(
    () => location.hash.slice(1) || null,
  );
  const [items, setItems] = useState<Discussion[]>([]);
  const [mode, setMode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [connected, setConnected] = useState(false);
  const [filter, setFilter] = useState("all");
  const [topic, setTopic] = useState("");
  const [count, setCount] = useState(4);
  const [subscriptionVersion, reconnect] = useState(0);
  const activeRoom = useRef(selected);
  activeRoom.current = selected;
  const snapshot = useStudio((s) => s.snapshot);
  const refresh = useCallback(async () => {
    try {
      const [list, health] = await Promise.all([
        api<{ items: Discussion[] }>("/discussions?limit=100"),
        api<{ mode: string }>("/health"),
      ]);
      setItems(list.items);
      setMode(health.mode);
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);
  useEffect(() => {
    void refresh();
    const timer = setInterval(refresh, 8000);
    return () => clearInterval(timer);
  }, [refresh]);
  useEffect(() => {
    const onHash = () => select(location.hash.slice(1) || null);
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  const navigate = (id: string | null) => {
    location.hash = id || "";
    select(id);
    setError("");
  };

  useEffect(() => {
    useStudio.getState().set(null);
    setConnected(false);
    if (!selected) return;
    let alive = true;
    let stream: EventSource | undefined;
    api<Snapshot>(`/discussions/${selected}`)
      .then((s) => {
        if (!alive) return;
        useStudio.getState().set(s);
        if (terminal(s.discussion.status)) return;
        stream = new EventSource(
          `/api/discussions/${selected}/events?after=${s.last_event_sequence}`,
        );
        stream.onopen = () => {
          if (alive) setConnected(true);
        };
        stream.onerror = () => {
          if (alive) setConnected(false);
        };
        stream.onmessage = (message) => {
          if (!alive) return;
          const event = JSON.parse(message.data) as StudioEvent;
          useStudio.getState().apply(event);
          const current = useStudio.getState().snapshot;
          if (current && terminal(current.discussion.status)) {
            stream?.close();
            setConnected(false);
            void refresh();
          }
        };
      })
      .catch((e) => {
        if (alive) setError(e.message);
      });
    return () => {
      alive = false;
      stream?.close();
    };
  }, [selected, refresh, subscriptionVersion]);

  async function create(event?: FormEvent) {
    event?.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await api<{ discussion_id: string }>("/discussions", {
        topic,
        expert_count: count,
      });
      navigate(result.discussion_id);
      void refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function action(path: string) {
    const target = selected;
    setBusy(true);
    setError("");
    try {
      await api(`/discussions/${target}/${path}`, {});
      // Reopen the subscription after retrying a terminal generation failure.
      if (path === "retry-generation" && activeRoom.current === target) {
        reconnect((version) => version + 1);
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const room = snapshot?.discussion;

  return (
    <div className="app-shell">
      <header className="topbar">
        <button
          className="brand"
          onClick={() => navigate(null)}
          aria-label="返回首页"
        >
          <span className="brand-mark">
            <AudioLines size={23} />
          </span>
          <span>
            Panel<span className="brand-light"> Studio</span>
            <small>AI 圆桌讨论</small>
          </span>
        </button>
        <nav>
          <button
            className={!selected ? "nav-item active" : "nav-item"}
            onClick={() => navigate(null)}
          >
            <Compass size={16} />
            讨论空间
          </button>
          <span className="nav-divider" />
          <span className="mode-tag">
            <span className="tiny-dot" />
            {(room?.mode || mode) === "live"
              ? "真实模型"
              : (room?.mode || mode) === "demo"
                ? "演示模式"
                : "连接中"}
          </span>
        </nav>
        <div className="workspace-label">
          个人工作空间<span className="user-avatar">我</span>
        </div>
      </header>
      {error && (
        <div className="error-banner" role="alert">
          <span>{error}</span>
          <button
            onClick={() => {
              setError("");
              void refresh();
            }}
            aria-label="重试连接"
          >
            <RefreshCw size={15} />
          </button>
          <button onClick={() => setError("")} aria-label="关闭提示">
            <X size={15} />
          </button>
        </div>
      )}
      {!selected ? (
        <Home
          {...{
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
          }}
        />
      ) : !snapshot ? (
        <main className="loading">
          <LoaderCircle className="spin" />
          <p>{error ? "暂时无法打开讨论" : "正在进入讨论空间…"}</p>
          <button className="secondary" onClick={() => navigate(null)}>
            返回讨论空间
          </button>
        </main>
      ) : (
        <>
          <div className="room-heading">
            <button
              className="icon-button"
              onClick={() => navigate(null)}
              aria-label="返回讨论列表"
            >
              <ArrowLeft size={20} />
            </button>
            <div className="room-title">
              <div className="eyebrow">
                PANEL ROOM{" "}
                <span> / {room!.mode === "demo" ? "演示内容" : "AI LIVE"}</span>
              </div>
              <h1>{room!.topic}</h1>
            </div>
            <span className={`status-pill ${room!.status}`}>
              <span className="tiny-dot" />
              {labels[room!.status]}
            </span>
          </div>
          {room!.status === "generating" ? (
            <main className="loading">
              <div className="loading-symbol">
                <Sparkles size={30} />
              </div>
              <h2>正在邀请不同视角的声音</h2>
              <p>围绕你的议题，寻找专业与立场互补的嘉宾…</p>
              <LoaderCircle className="spin" size={19} />
            </main>
          ) : room!.status === "ready" ? (
            <Roster {...{ snapshot, busy, action }} />
          ) : (
            <Studio
              key={room!.id}
              {...{ snapshot, connected, busy, action, navigate, setTopic }}
            />
          )}
        </>
      )}
    </div>
  );
}
