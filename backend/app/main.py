from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models
from .database import engine
from .migrations import run_lightweight_migrations
from .routers import bids, crawl_jobs, outreach, solicitations

models.Base.metadata.create_all(bind=engine)
run_lightweight_migrations(engine)

app = FastAPI(title="Gov Bid Sourcing API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(solicitations.router)
app.include_router(crawl_jobs.router)
app.include_router(outreach.router)
app.include_router(bids.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
