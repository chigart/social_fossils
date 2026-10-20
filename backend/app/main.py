from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.analytics import router as analytics_router

app = FastAPI(
    title="Social Fossils API",
    description="Analyze personal messaging history.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(analytics_router)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "social-fossils-api",
    }