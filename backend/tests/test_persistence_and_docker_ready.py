import os
import pytest
from qdrant_client import QdrantClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.db.models import CommunityPost, HouseholdProfile, ImpactActionLog
from app.db.session import build_engine, close_db, init_db
from app.services.embeddings import EmbeddingManager
from app.services.retrieval import KnowledgeRetriever, RetrievalConfig
from tests.test_embeddings_and_qdrant_rag import MockKeywordEmbeddingProvider


async def test_disk_database_persistence_across_restart(tmp_path):
    db_file = tmp_path / "persist_test.db"
    db_url = f"sqlite+aiosqlite:///{db_file.as_posix()}"

    engine1 = build_engine(db_url)
    await init_db(engine1)
    sf1 = async_sessionmaker(bind=engine1, class_=AsyncSession, expire_on_commit=False)
    async with sf1() as session:
        session.add(
            HouseholdProfile(
                id="persist-fam",
                name="Persistent Family",
                city="Delhi",
                country="India",
                latitude=28.6139,
                longitude=77.2090,
            )
        )
        session.add(
            ImpactActionLog(
                profile_id="persist-fam",
                action_key="metro_commute_15km",
                action_label="Metro",
                category="mobility",
                quantity=1.0,
                unit="day",
                co2e_kg_avoided=2.355,
                pm25_g_avoided=0.39,
                exposure_hours_saved=0.75,
            )
        )
        session.add(
            CommunityPost(
                city="Delhi",
                neighborhood="Rohini",
                author_alias="PersistTester",
                post_type="pledge",
                title="Persistent Pledge",
                body="Testing database persistence across engine restarts.",
            )
        )
        await session.commit()
    await close_db(engine1)

    # Re-open fresh engine pointing to same file
    engine2 = build_engine(db_url)
    sf2 = async_sessionmaker(bind=engine2, class_=AsyncSession, expire_on_commit=False)
    async with sf2() as session2:
        prof = await session2.scalar(select(HouseholdProfile).where(HouseholdProfile.id == "persist-fam"))
        imp = await session2.scalar(select(ImpactActionLog).where(ImpactActionLog.profile_id == "persist-fam"))
        post = await session2.scalar(select(CommunityPost).where(CommunityPost.author_alias == "PersistTester"))
        assert prof is not None and prof.name == "Persistent Family"
        assert imp is not None and imp.co2e_kg_avoided == 2.355
        assert post is not None and post.title == "Persistent Pledge"
    await close_db(engine2)


def test_disk_qdrant_persistence_across_restart(tmp_path):
    qdrant_dir = str(tmp_path / "qdrant_disk")
    emb = EmbeddingManager(
        settings=Settings(QDRANT_URL=qdrant_dir, QDRANT_COLLECTION="persist_bw"),
        primary_provider=MockKeywordEmbeddingProvider(),
    )
    client1 = QdrantClient(path=qdrant_dir)
    r1 = KnowledgeRetriever(
        settings=Settings(QDRANT_URL=qdrant_dir, QDRANT_COLLECTION="persist_bw"),
        embedding_manager=emb,
        qdrant_client=client1,
    )
    ready, _, dim, _, _ = r1.ensure_qdrant_indexed()
    assert ready is True and dim == 6
    client1.close()

    # Re-open from disk and search without re-creating collection
    client2 = QdrantClient(path=qdrant_dir)
    r2 = KnowledgeRetriever(
        settings=Settings(QDRANT_URL=qdrant_dir, QDRANT_COLLECTION="persist_bw"),
        embedding_manager=emb,
        qdrant_client=client2,
    )
    res = r2.retrieve("HEPA CADR filtration", config=RetrievalConfig(mode="dense", top_k=2, score_threshold=0.2))
    assert len(res.citations) >= 1
    client2.close()


@pytest.mark.skipif(
    not os.getenv("TEST_POSTGRES_URL") or not os.getenv("TEST_QDRANT_URL"),
    reason="Set TEST_POSTGRES_URL and TEST_QDRANT_URL to run live Docker container integration tests.",
)
async def test_live_docker_postgres_and_qdrant_integration():
    from uuid import uuid4
    from sqlalchemy import delete

    pg_url = os.environ["TEST_POSTGRES_URL"]
    qdrant_url = os.environ["TEST_QDRANT_URL"]
    test_id = f"docker-pg-{uuid4().hex[:8]}"

    engine = build_engine(pg_url)
    await init_db(engine)
    sf = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with sf() as session:
        session.add(
            HouseholdProfile(
                id=test_id,
                name="Docker Check",
                city="Delhi",
                country="India",
                latitude=28.6139,
                longitude=77.2090,
            )
        )
        await session.commit()
        found = await session.scalar(select(HouseholdProfile).where(HouseholdProfile.id == test_id))
        assert found is not None and found.name == "Docker Check"
        await session.execute(delete(HouseholdProfile).where(HouseholdProfile.id == test_id))
        await session.commit()
    await close_db(engine)

    client = QdrantClient(url=qdrant_url, timeout=5.0)
    collections = client.get_collections()
    assert collections is not None
