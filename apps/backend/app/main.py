from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import otp, pre_call, war_room, webhooks
from app.db import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="RasenLoop Enterprise Backend", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pre_call.router)
app.include_router(webhooks.router)
app.include_router(otp.router)
app.include_router(war_room.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "rasenloop-backend"}
