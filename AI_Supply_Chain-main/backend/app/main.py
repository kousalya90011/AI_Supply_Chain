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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():

    initialize_database()


app.include_router(data_router)
app.include_router(analytics_router)
app.include_router(forecast_router)
app.include_router(evaluation_router)
app.include_router(query_router)
app.include_router(audit_router)


@app.get("/")
def root():

    return {
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
def health():

    return {
        "status": "healthy"
    }