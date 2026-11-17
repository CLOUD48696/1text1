from app.schemas import InsightDraft, Intent, Roster


def choose_speaker(intents: dict[str, Intent], history: list[str], waiting: dict[str, int]) -> str | None:
    """Deterministic arbitration of autonomous intents, never a round-robin queue."""
    candidates = []
    for person_id, intent in intents.items():
        if intent.action == 'wait' or history[-2:] == [person_id, person_id]:
            continue
        score = intent.urgency + min(waiting.get(person_id, 0), 10) * 0.15
        if intent.action == 'rebut' and intent.target_message_id:
            score += 0.3
        if history and history[-1] == person_id:
            score -= 0.35
        candidates.append((score, person_id))
    return max(candidates)[1] if candidates else None


def validate_roster(roster: Roster, count: int):
    if len(roster.experts) != count:
        raise ValueError('专家人数与请求不一致')
    names = [p.name.strip() for p in [roster.host, *roster.experts]]
    if len(set(names)) != len(names):
        raise ValueError('嘉宾姓名不能重复')


def validate_evidence(drafts: list[InsightDraft], messages: list[dict], roles: dict[str, str]) -> list[InsightDraft]:
    by_id = {m['id']: m for m in messages}
    valid, seen = [], set()
    for item in drafts:
        ids = set(item.evidence_message_ids)
        if not ids.issubset(by_id):
            continue
        authors = {by_id[mid]['participant_id'] for mid in ids}
        experts = {pid for pid in authors if roles.get(pid) == 'expert'}
        key = (item.kind, item.content.strip())
        if len(experts) >= 2 and key not in seen:
            item.evidence_message_ids = list(dict.fromkeys(item.evidence_message_ids))
            valid.append(item)
            seen.add(key)
    return valid
