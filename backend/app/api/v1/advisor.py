from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.aqi import get_aqi_service
from app.db.session import get_db
from app.schemas.advisor import (
    IndoorAdvisorRequest,
    IndoorAdvisorResponse,
    RecommendationsRequest,
    RecommendationsResponse,
    RoutinePlanRequest,
    RoutinePlanResponse,
)
from app.services.aqi_service import AQIService
from app.services.langgraph_agent import BreatheWiseAgentService
from app.services.routine_service import build_smart_daily_routine

router = APIRouter(prefix="/advisor", tags=["advisor"])

_shared_agent_service: BreatheWiseAgentService | None = None


def get_agent_service(aqi_service: AQIService = Depends(get_aqi_service)) -> BreatheWiseAgentService:
    global _shared_agent_service
    if _shared_agent_service is None or _shared_agent_service.aqi_service is not aqi_service:
        _shared_agent_service = BreatheWiseAgentService(aqi_service=aqi_service)
    return _shared_agent_service


@router.post("/recommendations", response_model=RecommendationsResponse)
async def generate_personalized_recommendations(
    payload: RecommendationsRequest,
    db: AsyncSession = Depends(get_db),
    agent: BreatheWiseAgentService = Depends(get_agent_service),
) -> RecommendationsResponse:
    """Generate personalized, evidence-grounded exposure & emission recommendations via LangGraph."""
    return await agent.run_recommendations(payload, db=db)


@router.post("/indoor", response_model=IndoorAdvisorResponse)
async def assess_indoor_air_quality(
    payload: IndoorAdvisorRequest,
    db: AsyncSession = Depends(get_db),
    agent: BreatheWiseAgentService = Depends(get_agent_service),
) -> IndoorAdvisorResponse:
    """Run deterministic room CADR/ACH & indoor risk assessment paired with grounded guidance."""
    return await agent.run_indoor_advisor(payload, db=db)


@router.post("/routine", response_model=RoutinePlanResponse)
async def plan_smart_daily_routine(
    payload: RoutinePlanRequest,
    db: AsyncSession = Depends(get_db),
    agent: BreatheWiseAgentService = Depends(get_agent_service),
) -> RoutinePlanResponse:
    """Build a pollution-aware hourly daily routine using forecast AQI and deterministic swaps."""
    return await build_smart_daily_routine(
        payload,
        aqi_service=agent.aqi_service,
        retriever=agent.retriever,
        db=db,
    )
