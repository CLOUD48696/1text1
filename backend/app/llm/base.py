from typing import Protocol

from pydantic import BaseModel


class LLMClient(Protocol):
    async def generate(self, task: str, context: dict, schema: type[BaseModel]) -> dict: ...
    async def close(self) -> None: ...
