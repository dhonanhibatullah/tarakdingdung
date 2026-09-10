from fastapi import APIRouter, Depends

from tarakdingdung.presentation.http.dependencies.container import get_settings

router = APIRouter(tags=["version"])


@router.get("/api/version")
async def version(settings=Depends(get_settings)):
    return {"name": settings.app_name, "version": settings.app_version}
