from fastapi import APIRouter, HTTPException

from app.services.data_service import DataService


router = APIRouter(
    prefix="/api/data",
    tags=["Data"]
)

data_service = DataService()


@router.get("/status")
def data_status():

    try:

        result = data_service.load_data()

        datasets = result["datasets"]

        return {
            "status": "success",
            "datasets": {
                name: {
                    "rows": len(df),
                    "columns": len(df.columns)
                }
                for name, df in datasets.items()
            },
            "validation": result["validation"]
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )

@router.get("/columns")
def data_columns():
    try:
        result = data_service.load_data()

        return {
            name: list(df.columns)
            for name, df in result["datasets"].items()
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )