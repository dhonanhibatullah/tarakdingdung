import httpx

from tarakdingdung.domain.contracts.llm.completion import Completion, Message


class HttpOpenAiCompatibleCompletion(Completion):
    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        api_key: str,
        model: str,
    ) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model

    async def complete(
        self, messages: list[Message], *, json_schema: str | None = None
    ) -> str:
        payload: dict = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        if json_schema is not None:
            payload["response_format"] = {"type": "json_object"}

        resp = await self._client.post(
            f"{self._base_url}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {self._api_key}"},
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
