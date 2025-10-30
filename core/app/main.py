import uvicorn
import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, BackgroundTasks
from fastapi.routing import APIRoute
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from routes import base, auth, exchange, api, thread, openapi, statistics, dashboard
from aosicoaLogger.log import log

from utils.scheduler_utils import scheduler
from db import crud
from db.database import SessionLocal, engine
from routes.thread import threads, thread_lock
import importlib

from v4_client_py import IndexerClient
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.welcome()

    db = SessionLocal()
    db_threads = crud.get_all_threads(db)
    for db_thread in db_threads:
        if db_thread.status == "running":
            module_name = f"threads.{db_thread.strategy}.main"
            strategy_module = importlib.import_module(module_name)
            strategy_instance = getattr(strategy_module, 'strategy')

            thread = strategy_instance(db_thread.id, db_thread.user_id, db_thread.pair, "bitmex", db_thread.qty, db_thread.leverage, "")
            with thread_lock:
                threads.append(thread)
            thread.start()

    scheduler.start()

    yield

    scheduler.shutdown()

app = FastAPI(
    swagger_ui_parameters=openapi.get_swagger_ui_parameters(),
    lifespan=lifespan
)

cors_allowed_origins_str = os.getenv("CORS_ALLOWED_ORIGINS", "")
origins = cors_allowed_origins_str.split(",") if cors_allowed_origins_str else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(base.router, tags=["Status"])
app.include_router(dashboard.router, tags=["Dashboard"], prefix="/dashboard")
app.include_router(auth.router, tags=["Auth"], prefix="/auth")
app.include_router(api.router, tags=["Api Keys"], prefix="/key")
app.include_router(thread.router, tags=["Thread"], prefix="/thread")
app.include_router(exchange.router, tags=["Exchange"], prefix="/exchange")
app.include_router(statistics.router, tags=["Statistics"], prefix="/stats")

app.openapi = openapi.get_openapi_configuration(app)

if __name__ == "__main__":
    # use 80 for production
    uvicorn.run(
        "main:app",
        host="0.0.0.0", 
        port=8000,
        reload=True
    )
