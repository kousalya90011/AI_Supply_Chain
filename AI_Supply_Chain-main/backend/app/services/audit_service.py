from __future__ import annotations

import json
from typing import Any

from app.models.database import SessionLocal
from app.models.entities import AuditTrace


class AuditService:

    def record(
        self,
        query: str,
        agent_name: str,
        input_data: Any,
        output_data: Any
    ) -> None:

        db = SessionLocal()

        try:

            trace = AuditTrace(
                query=query,
                agent_name=agent_name,
                input_data=json.dumps(
                    input_data,
                    default=str
                ),
                output_data=json.dumps(
                    output_data,
                    default=str
                )
            )

            db.add(trace)

            db.commit()

        except Exception:

            db.rollback()
            raise

        finally:

            db.close()

    def get_recent(
        self,
        limit: int = 50
    ) -> list[dict[str, Any]]:

        db = SessionLocal()

        try:

            records = (
                db.query(AuditTrace)
                .order_by(
                    AuditTrace.created_at.desc()
                )
                .limit(limit)
                .all()
            )

            return [
                {
                    "id": record.id,
                    "query": record.query,
                    "agent_name": record.agent_name,
                    "input_data": record.input_data,
                    "output_data": record.output_data,
                    "created_at": (
                        record.created_at.isoformat()
                        if record.created_at
                        else None
                    )
                }
                for record in records
            ]

        finally:

            db.close()
            