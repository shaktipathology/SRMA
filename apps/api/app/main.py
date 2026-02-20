from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import health, papers, reviews

app = FastAPI(
    title="SRMA Engine API",
    description="Systematic Review & Meta-Analysis Engine",
    version="0.1.0",
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


@app.get("/")
async def root():
    return {"message": "SRMA Engine API", "version": "0.1.0"}
