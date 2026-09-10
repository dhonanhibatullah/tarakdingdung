async def run(container) -> None:
    result = await container.collection.collect()
    container.logger.info("collection complete", failed=result.failed)
