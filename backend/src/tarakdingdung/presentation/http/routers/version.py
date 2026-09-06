from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

router = APIRouter(tags=["Version"])


@router.get("", response_class=PlainTextResponse)
async def version_get(request: Request) -> str:
    return request.app.state.app_version
