from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.entities import User
from app.query.scope import QueryScope
from app.services.auth_service import get_current_user
from app.services.query_service import QueryService


router = APIRouter(
    prefix="/api/query",
    tags=["AI Query"],
)


class QueryRequest(BaseModel):
    query: str
    # Accept and safely ignore any client-supplied role or supplier_id overrides
    role: str | None = None
    supplier_id: str | None = None


query_service = QueryService()


@router.post("")
def ask_query(
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    # Strictly construct user_scope from authenticated JWT user context.
    # Never trust payload role or supplier_id.
    user_scope = QueryScope.from_user(current_user)

    result = query_service.query(
        query=request.query,
        user_scope=user_scope,
        db=db,
    )

    return {
        "query": request.query,
        **result,
    }