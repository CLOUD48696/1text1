import pytest
from pydantic import ValidationError

from app.schemas import CreateDiscussion, InsightDraft, Intent, Persona, Roster
from app.services.scheduler import choose_speaker, validate_evidence, validate_roster


def intent(action='raise', urgency=0.5, target=None):
    return Intent(action=action, urgency=urgency, target_message_id=target, public_focus='关注实际成本')


def test_direct_rebuttal_can_jump_queue():
    result = choose_speaker({'a': intent(), 'b': intent('rebut', 0.8, 'm1')}, [], {})
    assert result == 'b'


def test_speaker_cannot_dominate_three_consecutive_turns():
    assert choose_speaker({'a': intent(urgency=1), 'b': intent(urgency=0.1)}, ['a', 'a'], {}) == 'b'


def test_waiting_weight_prevents_starvation():
    assert choose_speaker({'a': intent(urgency=1), 'b': intent(urgency=0.2)}, [], {'b': 8}) == 'b'


def test_wait_never_enters_speaking_queue():
    assert choose_speaker({'a': intent('wait', 1)}, [], {'a': 100}) is None


def test_no_automatic_round_robin():
    assert choose_speaker({'a': intent('wait'), 'b': intent(urgency=0.1), 'c': intent(urgency=1)}, ['a'], {}) == 'c'


def test_only_speaker_cannot_bypass_consecutive_limit():
    assert choose_speaker({'a': intent()}, ['a', 'a'], {}) is None


def test_insights_require_two_experts_and_local_evidence():
    people = {'a': 'expert', 'b': 'expert', 'h': 'host'}
    messages = [dict(id='m1', participant_id='a'), dict(id='m2', participant_id='b'), dict(id='m3', participant_id='h')]
    def draft(ids): return InsightDraft(kind='consensus', content='需要先通过试点检验效果', evidence_message_ids=ids)
    assert len(validate_evidence([draft(['m1', 'm2'])], messages, people)) == 1
    assert validate_evidence([draft(['m1', 'foreign'])], messages, people) == []
    assert validate_evidence([draft(['m1', 'm3'])], messages, people) == []
    assert validate_evidence([draft(['m1', 'm1'])], messages, people) == []


def test_roster_count_and_duplicate_names_are_rejected():
    def person(name): return Persona(name=name, profession='研究者', title='顾问', stance='关注长期能力建设')
    roster = Roster(host=person('主持人'), experts=[person('甲'), person('乙')])
    validate_roster(roster, 2)
    with pytest.raises(ValueError): validate_roster(roster, 4)
    roster.experts[1].name = '甲'
    with pytest.raises(ValueError): validate_roster(roster, 2)


def test_invalid_or_blank_topic_rejected():
    with pytest.raises(ValidationError): CreateDiscussion(topic='    ')
    with pytest.raises(ValidationError): CreateDiscussion(topic='这是一个正常议题', expert_count=9)
    assert CreateDiscussion(topic='  讨论产品增长策略  ').topic == '讨论产品增长策略'
