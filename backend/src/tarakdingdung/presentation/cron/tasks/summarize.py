async def run(container) -> None:
    result = await container.news_summarizer.summarize()
    container.logger.info("news summarized", produced=result is not None)
