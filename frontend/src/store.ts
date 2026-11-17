import { create } from 'zustand'
import type { Snapshot, StudioEvent, Discussion, Participant, Message, Insight } from './types'

interface Store { snapshot: Snapshot | null; set: (s: Snapshot | null) => void; apply: (e: StudioEvent) => void }
export const useStudio = create<Store>((set) => ({
  snapshot: null,
  set: (snapshot) => set({ snapshot }),
  apply: (e) => set(({ snapshot: s }) => {
    if (!s || s.discussion.id !== e.discussion_id || e.sequence <= s.last_event_sequence) return {}
    const next = { ...s, last_event_sequence: e.sequence }
    if (e.data.discussion) next.discussion = e.data.discussion as Discussion
    if (e.data.participants) next.participants = e.data.participants as Participant[]
    if (e.data.message) {
      const message = e.data.message as Message
      next.messages = s.messages.some(m => m.id === message.id) ? s.messages : [...s.messages, message]
    }
    if (e.data.insights) next.insights = e.data.insights as Insight[]
    return { snapshot: next }
  }),
}))
