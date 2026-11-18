from threading import RLock

from sqlalchemy import create_engine, delete, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base, Discussion, Event, Insight, Message, Participant, now, uid
from app.schemas import COLORS, Roster


def dump(record):
    return {column.name: getattr(record, column.name) for column in record.__table__.columns}


class StateConflict(Exception):
    pass


class Store:
    """Short synchronous transactions, serialized inside this single-process MVP."""
    def __init__(self, url: str):
        options = {'poolclass': StaticPool} if ':memory:' in url else {}
        self.engine = create_engine(url, connect_args={'check_same_thread': False, 'timeout': 10}, **options)
        @event.listens_for(self.engine, 'connect')
        def configure(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
            connection.execute('PRAGMA busy_timeout=10000')
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)
        self.lock = RLock()

    def initialize(self):
        Base.metadata.create_all(self.engine)

    def _room(self, session, did):
        room = session.get(Discussion, did)
        if room is None:
            raise KeyError(did)
        return room

    def _rows(self, session, model, did):
        query = select(model).where(model.discussion_id == did)
        if model is Participant: query = query.order_by(model.position)
        if model in (Message, Event): query = query.order_by(model.sequence)
        return list(session.scalars(query))

    def _emit(self, session, room, kind, data):
        room.event_seq += 1
        room.updated_at = now()
        session.flush()
        # Include current metadata so status and the cursor advance atomically.
        session.add(Event(discussion_id=room.id, sequence=room.event_seq, type=kind,
                          data={'discussion': dump(room), **data}))

    def create(self, topic, count, mode, did=None):
        with self.lock, self.sessions.begin() as session:
            room = Discussion(id=did or uid(), topic=topic, expert_count=count, mode=mode)
            session.add(room)
            session.flush()
            return dump(room)

    def list(self, limit=50, cursor=0, category='all'):
        with self.lock, self.sessions() as session:
            query = select(Discussion)
            if category == 'active':
                query = query.where(Discussion.status.in_(['generating', 'ready', 'running']))
            elif category == 'completed':
                query = query.where(Discussion.status == 'completed')
            rows = session.scalars(query.order_by(Discussion.created_at.desc(), Discussion.id).offset(cursor).limit(limit + 1)).all()
            return {'items': [dump(r) for r in rows[:limit]], 'next_cursor': cursor + limit if len(rows) > limit else None}

    def snapshot(self, did):
        with self.lock, self.sessions() as session:
            room = self._room(session, did)
            return {'discussion': dump(room), 'participants': [dump(x) for x in self._rows(session, Participant, did)],
                    'messages': [dump(x) for x in self._rows(session, Message, did)],
                    'insights': [dump(x) for x in self._rows(session, Insight, did)], 'last_event_sequence': room.event_seq}

    def roster(self, did, roster: Roster):
        with self.lock, self.sessions.begin() as session:
            room = self._room(session, did)
            if room.status != 'generating': raise StateConflict('当前状态不允许生成嘉宾')
            session.execute(delete(Participant).where(Participant.discussion_id == did))
            for i, person in enumerate([roster.host, *roster.experts]):
                session.add(Participant(discussion_id=did, position=i, role='host' if i == 0 else 'expert',
                                        color='#245b49' if i == 0 else COLORS[i-1], **person.model_dump()))
            room.status = 'ready'
            session.flush()
            self._emit(session, room, 'roster.ready', {'participants': [dump(p) for p in self._rows(session, Participant, did)]})

    def transition(self, did, status, phase=None, expected=None, error=None, summary=None):
        with self.lock, self.sessions.begin() as session:
            room = self._room(session, did)
            if expected and room.status not in expected: raise StateConflict('当前讨论状态不允许此操作')
            room.status = status
            room.error = error
            if phase is not None: room.phase = phase
            if summary is not None: room.summary = summary
            participants = self._rows(session, Participant, did)
            if status in ('completed', 'failed', 'interrupted'):
                for p in participants: p.status = 'idle'
            self._emit(session, room, f'discussion.{status}', {'participants': [dump(p) for p in participants]})

    def states(self, did, changes):
        with self.lock, self.sessions.begin() as session:
            room = self._room(session, did)
            people = self._rows(session, Participant, did)
            for p in people:
                change = changes.get(p.id, {})
                p.status = change.get('status', 'idle')
                p.public_focus = change.get('public_focus', p.public_focus)
            self._emit(session, room, 'participant.updated', {'participants': [dump(p) for p in people]})

    def message(self, did, pid, content, reply_to=None):
        with self.lock, self.sessions.begin() as session:
            room = self._room(session, did)
            person = session.get(Participant, pid)
            if not person or person.discussion_id != did: raise ValueError('发言人不属于当前讨论')
            if reply_to:
                target = session.get(Message, reply_to)
                if not target or target.discussion_id != did: raise ValueError('引用消息不属于当前讨论')
            room.message_seq += 1
            message = Message(discussion_id=did, participant_id=pid, sequence=room.message_seq, content=content, reply_to_message_id=reply_to)
            session.add(message)
            session.flush()
            data = dump(message)
            self._emit(session, room, 'message.created', {'message': data})
            return data

    def insights(self, did, drafts):
        with self.lock, self.sessions.begin() as session:
            room = self._room(session, did)
            previous = {(i.kind, i.content): i for i in self._rows(session, Insight, did)}
            retained = set()
            for item in drafts:
                key = (item.kind, item.content)
                current = previous.get(key)
                if current:
                    current.evidence_message_ids = item.evidence_message_ids
                    current.updated_at = now()
                    retained.add(current.id)
                else:
                    current = Insight(discussion_id=did, **item.model_dump())
                    session.add(current)
                    session.flush()
                    retained.add(current.id)
            for old in previous.values():
                if old.id not in retained: session.delete(old)
            session.flush()
            self._emit(session, room, 'insights.updated', {'insights': [dump(i) for i in self._rows(session, Insight, did)]})

    def events(self, did, after=0):
        with self.lock, self.sessions() as session:
            self._room(session, did)
            query = select(Event).where(Event.discussion_id == did, Event.sequence > after).order_by(Event.sequence).limit(100)
            return [dump(e) for e in session.scalars(query)]

    def interrupt_unfinished(self):
        with self.sessions() as session:
            ids = list(session.scalars(select(Discussion.id).where(Discussion.status.in_(['running', 'generating']))))
        for did in ids:
            self.transition(did, 'interrupted', error='服务已重启，已有内容已保存。请重新发起讨论。')
