async def run(container) -> None:
    result = await container.engine.run_cycle()
    container.logger.info("cycle complete", status=result.status.value, detail=result.detail)
