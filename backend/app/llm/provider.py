import json

import httpx
from pydantic import BaseModel

from app.config import Settings
from app.llm.prompts import SYSTEM, TASKS


class ProviderLLM:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = httpx.AsyncClient(timeout=settings.llm_timeout)

    async def generate(self, task: str, context: dict, schema: type[BaseModel]) -> dict:
        request = {
            'model': self.settings.llm_model,
            'messages': [
                {'role': 'system', 'content': SYSTEM + '\n任务：' + TASKS[task] + '\nJSON Schema：' + json.dumps(schema.model_json_schema(), ensure_ascii=False)},
                {'role': 'user', 'content': json.dumps(context, ensure_ascii=False)},
            ],
        }
        if self.settings.llm_json_mode: request['response_format'] = {'type': 'json_object'}
        response = await self.client.post(self.settings.llm_base_url.rstrip('/') + '/chat/completions',
                                          headers={'Authorization': f'Bearer {self.settings.llm_api_key}'}, json=request)
        response.raise_for_status()
        text = response.json()['choices'][0]['message']['content']
        # Do not display provider reasoning_content or return raw provider errors to the browser.
        return json.loads(text)

    async def close(self):
        await self.client.aclose()
