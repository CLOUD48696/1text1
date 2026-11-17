import type { CSSProperties } from "react";
import { Mic2 } from "lucide-react";
import type { Participant } from "../types";
export default function Avatar({
  person,
  small = false,
}: {
  person: Participant;
  small?: boolean;
}) {
  return (
    <span
      className={`avatar ${small ? "small" : ""}`}
      style={{ "--person": person.color } as CSSProperties}
    >
      {person.role === "host" ? (
        <Mic2 size={small ? 16 : 21} />
      ) : (
        person.name.slice(-2)
      )}
    </span>
  );
}
