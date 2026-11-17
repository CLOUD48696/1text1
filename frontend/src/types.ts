export type Status =
  "generating" | "ready" | "running" | "completed" | "failed" | "interrupted";
export interface Discussion {
  id: string;
  topic: string;
  expert_count: number;
  status: Status;
  phase: string;
  mode: "demo" | "live";
  summary: string | null;
  error: string | null;
  created_at: string;
}
export interface Participant {
  id: string;
  role: "host" | "expert";
  name: string;
  profession: string;
  title: string;
  stance: string;
  color: string;
  status: "idle" | "preparing" | "speaking";
  public_focus: string;
}
export interface Message {
  id: string;
  participant_id: string;
  sequence: number;
  content: string;
  reply_to_message_id: string | null;
  created_at: string;
}
export interface Insight {
  id: string;
  kind: "consensus" | "disagreement";
  content: string;
  evidence_message_ids: string[];
}
export interface Snapshot {
  discussion: Discussion;
  participants: Participant[];
  messages: Message[];
  insights: Insight[];
  last_event_sequence: number;
}
export interface StudioEvent {
  discussion_id: string;
  sequence: number;
  type: string;
  data: Record<string, unknown>;
}
