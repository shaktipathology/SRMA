from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.db import engine
from app.routers import health, papers, reviews, protocol, search, screening
from app.routers import grade, sof, manuscript, prisma_check, stubs, meta, fulltext_screen, extract


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
app.include_router(grade.router, prefix="/api/v1/grade", tags=["grade"])
app.include_router(sof.router, prefix="/api/v1/sof", tags=["sof"])
app.include_router(manuscript.router, prefix="/api/v1/manuscript", tags=["manuscript"])
app.include_router(prisma_check.router, prefix="/api/v1/prisma", tags=["prisma"])
app.include_router(meta.router, prefix="/api/v1/meta", tags=["meta-analysis"])
app.include_router(fulltext_screen.router, prefix="/api/v1/fulltext", tags=["fulltext-screening"])
app.include_router(extract.router, prefix="/api/v1/extract", tags=["extract"])
app.include_router(stubs.router, prefix="/api/v1", tags=["stubs"])


@app.get("/")
async def root():
    return {"message": "SRMA Engine API", "version": "0.1.0"}
