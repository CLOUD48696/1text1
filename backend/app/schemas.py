from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

COLORS = ['#b46d43', '#557b9a', '#8b6ca8', '#56866e', '#b08b38', '#a85f7f']


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class CreateDiscussion(StrictModel):
    topic: str = Field(min_length=4, max_length=240)
    expert_count: int = Field(default=4, ge=2, le=6)

    @field_validator('topic', mode='before')
    @classmethod
    def trim_topic(cls, value):
        return value.strip() if isinstance(value, str) else value


class Persona(StrictModel):
    name: str = Field(min_length=1, max_length=30)
    profession: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=50)
    stance: str = Field(min_length=4, max_length=180)


class Roster(StrictModel):
    host: Persona
    experts: list[Persona] = Field(min_length=2, max_length=6)


class Intent(StrictModel):
    action: Literal['wait', 'raise', 'supplement', 'rebut']
    target_message_id: str | None = None
    urgency: float = Field(ge=0, le=1)
    public_focus: str = Field(min_length=1, max_length=80)


class Speech(StrictModel):
    content: str = Field(min_length=4, max_length=420)


class Summary(StrictModel):
    content: str = Field(min_length=10, max_length=1600)


class InsightDraft(StrictModel):
    kind: Literal['consensus', 'disagreement']
    content: str = Field(min_length=4, max_length=200)
    evidence_message_ids: list[str] = Field(min_length=2, max_length=8)


class Insights(StrictModel):
    items: list[InsightDraft] = Field(max_length=8)
