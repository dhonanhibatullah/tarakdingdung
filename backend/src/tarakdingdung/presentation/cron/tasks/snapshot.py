async def run(container) -> None:
    snapshot = await container.snapshot.take()
    container.logger.info("snapshot taken", equity=str(snapshot.equity))
