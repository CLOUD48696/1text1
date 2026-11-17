from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def uid(): return str(uuid4())
def now(): return datetime.now(timezone.utc).isoformat()


class Base(DeclarativeBase):
    pass


class Discussion(Base):
    __tablename__ = 'discussions'
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    topic: Mapped[str]
    expert_count: Mapped[int]
    status: Mapped[str] = mapped_column(default='generating')
    phase: Mapped[str] = mapped_column(default='roster')
    mode: Mapped[str]
    summary: Mapped[str | None]
    error: Mapped[str | None]
    event_seq: Mapped[int] = mapped_column(default=0)
    message_seq: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[str] = mapped_column(default=now)
    updated_at: Mapped[str] = mapped_column(default=now)


class Participant(Base):
    __tablename__ = 'participants'
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    discussion_id: Mapped[str] = mapped_column(ForeignKey('discussions.id'), index=True)
    position: Mapped[int]
    role: Mapped[str]
    name: Mapped[str]
    profession: Mapped[str]
    title: Mapped[str]
    stance: Mapped[str]
    color: Mapped[str]
    status: Mapped[str] = mapped_column(default='idle')
    public_focus: Mapped[str] = mapped_column(default='倾听其他嘉宾的观点')


class Message(Base):
    __tablename__ = 'messages'
    __table_args__ = (UniqueConstraint('discussion_id', 'sequence'),)
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    discussion_id: Mapped[str] = mapped_column(ForeignKey('discussions.id'), index=True)
    participant_id: Mapped[str] = mapped_column(ForeignKey('participants.id'))
    sequence: Mapped[int]
    content: Mapped[str]
    reply_to_message_id: Mapped[str | None] = mapped_column(ForeignKey('messages.id'))
    created_at: Mapped[str] = mapped_column(default=now)


class Insight(Base):
    __tablename__ = 'insights'
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    discussion_id: Mapped[str] = mapped_column(ForeignKey('discussions.id'), index=True)
    kind: Mapped[str]
    content: Mapped[str]
    evidence_message_ids: Mapped[list] = mapped_column(JSON)
    updated_at: Mapped[str] = mapped_column(default=now)


class Event(Base):
    __tablename__ = 'events'
    __table_args__ = (UniqueConstraint('discussion_id', 'sequence'),)
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    discussion_id: Mapped[str] = mapped_column(ForeignKey('discussions.id'), index=True)
    sequence: Mapped[int]
    type: Mapped[str]
    data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(default=now)
