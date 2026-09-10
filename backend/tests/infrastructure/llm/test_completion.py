import json

import httpx

from tarakdingdung.domain.contracts.llm.completion import Message
from tarakdingdung.infrastructure.llm.openai_compatible import (
    HttpOpenAiCompatibleCompletion,
)


async def test_complete_returns_content():
    captured = {}

    def handler(request):
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        captured["auth"] = request.headers.get("authorization")
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"weights": []}'}}]},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    completion = HttpOpenAiCompatibleCompletion(
        client, base_url="https://api.example.com", api_key="key", model="deepseek-v4-pro"
    )
    result = await completion.complete(
        [Message(role="system", content="you are a trader")]
    )

    assert result == '{"weights": []}'
    assert captured["url"] == "https://api.example.com/chat/completions"
    assert captured["auth"] == "Bearer key"
    assert captured["body"]["model"] == "deepseek-v4-pro"
    assert captured["body"]["messages"] == [
        {"role": "system", "content": "you are a trader"}
    ]
    assert "response_format" not in captured["body"]


async def test_complete_requests_json_mode():
    captured = {}

    def handler(request):
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    completion = HttpOpenAiCompatibleCompletion(
        client, base_url="https://api.example.com", api_key="key", model="m"
    )
    await completion.complete([], json_schema="{...}")
    assert captured["body"]["response_format"] == {"type": "json_object"}
