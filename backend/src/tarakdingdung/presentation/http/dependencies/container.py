from fastapi import Request

from tarakdingdung.composition.main.application import Container


def get_container(request: Request) -> Container:
    return request.app.state.container


def get_settings(request: Request):
    return request.app.state.settings
