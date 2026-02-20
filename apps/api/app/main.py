from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.db import engine
from app.routers import health, papers, reviews, protocol, search, screening


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown — dispose connection pool cleanly
    await engine.dispose()


app = FastAPI(
    title="SRMA Engine API",
    description="Systematic Review & Meta-Analysis Engine",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(papers.router, prefix="/api/v1/papers", tags=["papers"])
app.include_router(reviews.router, prefix="/api/v1/reviews", tags=["reviews"])
app.include_router(protocol.router, prefix="/api/v1/protocol", tags=["protocol"])
app.include_router(search.router, prefix="/api/v1/search", tags=["search"])
app.include_router(screening.router, prefix="/api/v1/screen", tags=["screening"])


@app.get("/")
async def root():
    return {"message": "SRMA Engine API", "version": "0.1.0"}
