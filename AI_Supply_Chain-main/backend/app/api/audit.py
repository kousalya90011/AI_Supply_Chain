from fastapi import APIRouter, HTTPException, Query

from app.services.audit_service import AuditService


router = APIRouter(
    prefix="/api/audit",
    tags=["Audit"]
)

audit_service = AuditService()


@router.get("/recent")
def get_recent_audits(
    limit: int = Query(
        default=50,
        ge=1,
        le=500
    )
):

    try:

        records = audit_service.get_recent(
            limit=limit
        )

        return {
            "status": "success",
            "count": len(records),
            "records": records
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )