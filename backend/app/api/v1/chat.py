from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.advisor import get_agent_service
from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.langgraph_agent import BreatheWiseAgentService

router = APIRouter(tags=["assistant"])


@router.post("/chat", response_model=ChatResponse)
async def chat_with_assistant(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
    agent: BreatheWiseAgentService = Depends(get_agent_service),
) -> ChatResponse:
    """Conversational urban air quality assistant backed by Qdrant RAG, LangGraph, and thread history."""
    return await agent.run_chat(payload, db=db)
