from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def create_session_factory(
    dsn: str, pool_size: int = 20
) -> async_sessionmaker:
    engine = create_async_engine(dsn, pool_size=pool_size, pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False)
