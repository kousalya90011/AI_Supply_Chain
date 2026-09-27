from fastapi import APIRouter
from pydantic import BaseModel

from app.services.query_service import QueryService


router = APIRouter(
    prefix="/api/query",
    tags=["AI Query"]
)


class QueryRequest(BaseModel):

    query: str


query_service = QueryService()


@router.post("")
def ask_query(request: QueryRequest):

    result = query_service.query(
        request.query
    )

    return {
        "query": request.query,
        **result
    }