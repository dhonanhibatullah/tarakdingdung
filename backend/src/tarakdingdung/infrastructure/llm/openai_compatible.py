import asyncio

import httpx

from tarakdingdung.domain.contracts.llm.completion import Completion, Message

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class HttpOpenAiCompatibleCompletion(Completion):
    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        api_key: str,
        model: str,
        max_retries: int = 3,
    ) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._max_retries = max_retries

    async def complete(
        self, messages: list[Message], *, json_schema: str | None = None
    ) -> str:
        payload: dict = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        if json_schema is not None:
            payload["response_format"] = {"type": "json_object"}

        for attempt in range(self._max_retries):
            try:
                resp = await self._client.post(
                    f"{self._base_url}/chat/completions",
                    json=payload,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            except httpx.TimeoutException:
                if attempt == self._max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
            except httpx.HTTPStatusError as exc:
                if (
                    exc.response.status_code in _RETRYABLE_STATUS
                    and attempt < self._max_retries - 1
                ):
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise

