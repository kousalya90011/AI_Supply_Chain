from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models.database import initialize_database

from app.api.data import router as data_router
from app.api.analytics import router as analytics_router
from app.api.forecast import router as forecast_router
from app.api.evaluation import router as evaluation_router
from app.api.query import router as query_router
from app.api.audit import router as audit_router
from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.suppliers import router as suppliers_router
from app.api.products import router as products_router
from app.api.orders import router as orders_router
from app.api.inventory import router as inventory_router
from app.api.offers import router as offers_router
from app.api.retrieval import router as retrieval_router

from app.services.auth_service import ensure_default_admin
from app.models.database import SessionLocal

from app.llm.client import LLMClient


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "AI-powered Supply Chain Risk Intelligence "
        "and Investigation Platform using hybrid RAG: "
        "semantic planning + structured analytics + "
        "evidence-grounded answer generation"
    )
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# STARTUP
# =========================================================

@app.on_event("startup")
def startup_event():

    initialize_database()

    db = SessionLocal()

    try:
        ensure_default_admin(db)
    finally:
        db.close()


# =========================================================
# ROUTERS
# =========================================================

app.include_router(data_router)
app.include_router(analytics_router)
app.include_router(forecast_router)
app.include_router(evaluation_router)
app.include_router(query_router)
app.include_router(audit_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(suppliers_router)
app.include_router(products_router)
app.include_router(orders_router)
app.include_router(inventory_router)
app.include_router(offers_router)
app.include_router(retrieval_router)


# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root():

    return {
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
def health():

    llm_status = "not_configured"
    llm_reason = "LLM configuration is incomplete."

    try:

        llm = LLMClient()

        provider = str(
            getattr(llm, "provider", "")
            or getattr(settings, "LLM_PROVIDER", "")
            or ""
        ).strip()

        base_url = str(
            getattr(llm, "base_url", "")
            or getattr(settings, "LLM_BASE_URL", "")
            or ""
        ).strip()

        api_key = str(
            getattr(llm, "api_key", "")
            or getattr(settings, "LLM_API_KEY", "")
            or ""
        ).strip()

        model = str(
            getattr(llm, "model", "")
            or getattr(settings, "LLM_MODEL", "")
            or ""
        ).strip()

        if not provider:
            llm_reason = "LLM provider is not configured."

        elif not base_url:
            llm_reason = "LLM base URL is not configured."

        elif not api_key:
            llm_reason = "LLM API key is not configured."

        elif not model:
            llm_reason = "LLM model is not configured."

        else:
            llm_status = "configured"
            llm_reason = "LLM configuration is available."

    except Exception as exc:

        llm_status = "error"

        # Do not expose credentials or secrets.
        llm_reason = (
            "LLM configuration could not be inspected."
        )

    return {
        "status": "healthy",
        "phase": 7,
        "llm_status": llm_status,
        "llm_configured": llm_status == "configured",
        "llm_reason": llm_reason,
    }
