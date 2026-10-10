"""Assistant API endpoints and error mappings."""

from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException

from app.assistant.factory import get_assistant_service
from app.assistant.provider import (
    ProviderAuthError,
    ProviderError,
    ProviderInvalidResponseError,
    ProviderQuotaError,
    ProviderTimeoutError,
)
from app.assistant.schemas import AssistantChatRequest, AssistantChatResponse
from app.assistant.service import AssistantService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])


@router.post("/chat", response_model=AssistantChatResponse)
async def chat_with_assistant(
    request: AssistantChatRequest,
    service: AssistantService = Depends(get_assistant_service),
) -> AssistantChatResponse:
    """Chat with the AI decision-support assistant using allowlisted deterministic financial tools."""
    try:
        return await service.chat(request)
    except ProviderAuthError as exc:
        logger.warning("Provider authentication failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="AI Assistant service is not configured. Missing or invalid API key.",
        ) from exc
    except ProviderQuotaError as exc:
        logger.warning("Provider quota exhausted or rate limit hit: %s", exc)
        raise HTTPException(
            status_code=429,
            detail=f"AI Assistant quota or rate limit exceeded: {str(exc)}",
        ) from exc
    except ProviderTimeoutError as exc:

        logger.error("Provider timed out: %s", exc)
        raise HTTPException(
            status_code=504,
            detail="AI Assistant provider request timed out.",
        ) from exc
    except ProviderInvalidResponseError as exc:
        logger.error("Provider returned invalid response: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="AI Assistant returned an invalid or non-conforming response.",
        ) from exc
    except ProviderError as exc:
        logger.error("Provider execution error: %s", exc)
        raise HTTPException(
            status_code=502,
            detail=f"AI Assistant provider error: {str(exc)}",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
