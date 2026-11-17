import json

import httpx
import pytest

from app.config import Settings
from app.llm.provider import ProviderLLM
from app.schemas import Speech


@pytest.mark.asyncio
async def test_provider_sends_schema_and_returns_only_public_content():
    settings = Settings(_env_file=None, app_mode='live', llm_api_key='test-only-key', llm_model='test-model', llm_json_mode=True)
    model = ProviderLLM(settings)
    await model.client.aclose()
    def handler(request):
        payload = json.loads(request.content)
        assert request.headers['authorization'] == 'Bearer test-only-key'
        assert payload['response_format'] == {'type': 'json_object'}
        assert 'JSON Schema' in payload['messages'][0]['content']
        return httpx.Response(200, json={'choices': [{'message': {'content': '{"content":"这是可公开展示的发言。"}', 'reasoning_content': 'hidden'}}]})
    model.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        result = await model.generate('speech', {'topic': '测试主题'}, Speech)
        assert result == {'content': '这是可公开展示的发言。'}
    finally:
        await model.close()
