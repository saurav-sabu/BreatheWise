import httpx
import pytest

from app.core.security import SlidingWindowRateLimiterMiddleware
from app.db.session import get_db
from app.main import create_app


@pytest.fixture
async def community_client(db_session):
    app = create_app()

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield client


async def test_community_crud_sanitization_and_moderation(community_client: httpx.AsyncClient):
    # Create valid post with HTML tags stripped
    r_create = await community_client.post(
        "/api/v1/community/posts",
        json={
            "city": "Delhi",
            "neighborhood": "Dwarka",
            "author_alias": "CleanAirParent",
            "post_type": "pledge",
            "title": "<b>Metro</b> Commute Pledge",
            "body": "Switching 4 days/week from petrol car to metro rail this winter.",
            "action_tag": "metro_commute",
        },
    )
    assert r_create.status_code == 201
    created = r_create.json()
    assert created["title"] == "Metro Commute Pledge"
    assert created["moderation_status"] == "published"

    # Reject PII (email / phone)
    r_pii = await community_client.post(
        "/api/v1/community/posts",
        json={
            "city": "Delhi",
            "author_alias": "User1",
            "post_type": "tip",
            "title": "Contact me",
            "body": "Reach out at private.email@example.com for filters.",
        },
    )
    assert r_pii.status_code == 400

    # Reject unsupported medical claims
    r_med = await community_client.post(
        "/api/v1/community/posts",
        json={
            "city": "Delhi",
            "author_alias": "User2",
            "post_type": "tip",
            "title": "Magic cure",
            "body": "This herb cures asthma permanently even in severe smog.",
        },
    )
    assert r_med.status_code == 400

    # List feed and verify user-contributed provenance disclaimer
    r_feed = await community_client.get("/api/v1/community/posts", params={"city": "Delhi"})
    assert r_feed.status_code == 200
    feed = r_feed.json()
    assert feed["data_classification"] == "user_contributed_unverified"
    assert "NOT official sensor measurements" in feed["disclaimer"]
    assert feed["count"] == 1

    # Upvote
    r_up = await community_client.post(f"/api/v1/community/posts/{created['id']}/upvote")
    assert r_up.status_code == 200
    assert r_up.json()["upvotes"] == 1

    # Report twice -> auto-flagged and excluded from default feed
    r_rep1 = await community_client.post(
        f"/api/v1/community/posts/{created['id']}/report",
        json={"reason": "misinformation"},
    )
    assert r_rep1.status_code == 200
    assert r_rep1.json()["moderation_status"] == "published"

    r_rep2 = await community_client.post(
        f"/api/v1/community/posts/{created['id']}/report",
        json={"reason": "spam"},
    )
    assert r_rep2.status_code == 200
    assert r_rep2.json()["moderation_status"] == "flagged"

    r_feed_after = await community_client.get("/api/v1/community/posts", params={"city": "Delhi"})
    assert r_feed_after.json()["count"] == 0

    r_sum = await community_client.get("/api/v1/community/summary", params={"city": "Delhi"})
    assert r_sum.status_code == 200
    assert r_sum.json()["flagged_or_hidden_count"] == 1


async def test_security_headers_and_rate_limiter(db_session):
    app = create_app()

    # Tighten rate limit middleware for explicit 429 check
    for mw in app.user_middleware:
        if mw.cls is SlidingWindowRateLimiterMiddleware:
            mw.kwargs["max_requests_per_minute"] = 3

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        r1 = await client.get("/api/v1/community/summary", params={"city": "Delhi"})
        assert r1.status_code == 200
        assert r1.headers.get("X-Content-Type-Options") == "nosniff"
        assert r1.headers.get("X-Frame-Options") == "DENY"

        await client.get("/api/v1/community/summary", params={"city": "Delhi"})
        await client.get("/api/v1/community/summary", params={"city": "Delhi"})
        r4 = await client.get("/api/v1/community/summary", params={"city": "Delhi"})
        assert r4.status_code == 429
