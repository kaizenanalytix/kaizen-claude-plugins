"""
Shared Pytest fixtures for the backend test suite.

Copy this file into the project's test root (or merge these fixtures into
an existing conftest.py). Every module's tests should import these
fixtures instead of redefining their own test client, test DB session, or
fake repositories.
"""

from collections.abc import AsyncGenerator, Generator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.app import create_app
from app.core.database import Base, get_db_session

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def test_engine():
    """A single in-memory SQLite engine for the whole test session."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(test_engine) -> Generator[Session, None, None]:
    """A transactional session, rolled back after every test."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection)
    session = session_factory()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """
    An async client against the real app over ASGI (no real network socket),
    with get_db_session overridden to use the per-test transactional session
    above instead of a real connection pool.

    Async, not FastAPI's sync TestClient, so tests exercise routes/services
    the same way they actually run in production: on the event loop. A sync
    client wraps every call in its own event-loop spin-up, which can hide a
    bug that only shows up when something genuinely awaits concurrently with
    other work on the same loop.
    """
    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """
    A ready-made Authorization header for routes behind get_current_user.
    Adjust the token/scheme to match the project's actual auth mechanism.

    If auth is verified by middleware rather than a Depends()-based check
    (a signed-request scheme, for example) -- not just this project's own
    get_current_user -- replace this fixture with one that computes real
    headers per the project's actual signing logic instead. See
    references/testing-custom-auth.md: dependency_overrides cannot intercept
    middleware at all, so a static header here would never reach a route
    protected that way.
    """
    return {"Authorization": "Bearer test-token"}


class FakeProductRepository:
    """
    In-memory fake implementing the same Protocol as
    SqlAlchemyProductRepository, for unit-testing services with no
    database involved.
    """

    def __init__(self) -> None:
        self._products: dict[int, "Product"] = {}
        self._next_id = 1

    def get(self, product_id: int) -> "Product | None":
        return self._products.get(product_id)

    def list(self, search: str | None) -> list["Product"]:
        values = list(self._products.values())
        if search:
            values = [p for p in values if search.lower() in p.name.lower()]
        return values

    def save(self, product: "Product") -> "Product":
        if product.id is None:
            product.id = self._next_id
            self._next_id += 1
        self._products[product.id] = product
        return product


@pytest.fixture
def fake_product_repository() -> FakeProductRepository:
    """A fresh in-memory ProductRepository fake for every test."""
    return FakeProductRepository()
