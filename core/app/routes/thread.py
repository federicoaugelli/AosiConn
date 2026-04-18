from fastapi import APIRouter, BackgroundTasks, File, UploadFile, HTTPException, Depends
from typing import Dict, Annotated
import os, zipfile, shutil, json, threading, importlib
from schemas import threads as thread_schema
from auth.auth_bearer import JWTBearer
from utils.router_utils import *
from utils.scheduler_utils import scheduler
from utils.scheduler_manager import scheduler_manager
from datetime import datetime, timedelta
from db import crud, schemas
from db.database import SessionLocal, engine, get_db
from sqlalchemy.orm import Session

router = APIRouter()

thread_folder = "threads"


@router.get("/")
async def get_threads(
    user_id: str = Depends(JWTBearer()), dependencies=Depends(JWTBearer())
) -> Dict[str, object]:
    uid = get_user_id(user_id)

    threads_list = []
    invalid_threads = []

    for thread in os.listdir("threads"):
        thread_path = f"threads/{thread}"
        if not os.path.isdir(thread_path):
            continue
        config_path = f"{thread_path}/config.json"
        try:
            with open(config_path, "r") as config_file:
                config = json.load(config_file)
            if "name" in config and "description" in config and "author" in config:
                threads_list.append(
                    {
                        "filename": thread,
                        "name": config["name"],
                        "description": config["description"],
                        "author": config["author"],
                    }
                )
            else:
                invalid_threads.append(
                    {"filename": thread, "error": "missing required fields"}
                )
        except Exception as e:
            # Log the bad thread but don't break the whole listing
            invalid_threads.append({"filename": thread, "error": str(e)})

    return {"threads": threads_list, "invalid": invalid_threads}


@router.post("/upload/")
async def upload_thread(
    file: UploadFile,
    user_id: str = Depends(JWTBearer()),
    dependencies=Depends(JWTBearer()),
):
    if file.filename.endswith(".zip"):
        with open(f"threads/{file.filename}", "wb") as buffer:
            buffer.write(file.file.read())

        with zipfile.ZipFile(f"threads/{file.filename}", "r") as zip_ref:
            zip_ref.extractall(f"threads/")

        os.remove(f"threads/{file.filename}")

        # check there's at least one python file and a config.json file
        if not os.path.exists(f"threads/{file.filename[:-4]}/config.json"):
            # os.rmdir(f"threads/{file.filename[:-4]}")
            raise HTTPException(status_code=400, detail="Config file not found")

        if not os.path.exists(f"threads/{file.filename[:-4]}/main.py"):
            raise HTTPException(status_code=400, detail="main.py file not found")

        if not any(
            file.endswith(".py") for file in os.listdir(f"threads/{file.filename[:-4]}")
        ):
            # os.rmdir(f"threads/{file.filename[:-4]}")
            raise HTTPException(status_code=400, detail="Python file not found")

    else:
        raise HTTPException(status_code=400, detail="File must be a zip file")


    return {f"{filename} ingested successfully"}


@router.delete("/{thread_name}/")
async def delete_threads(
    thread_name: str,
    user_id: str = Depends(JWTBearer()),
    dependencies=Depends(JWTBearer()),
) -> Dict:
    if not os.path.exists(f"threads/{thread_name}"):
        raise HTTPException(status_code=404, detail="Thread not found")

    try:
        shutil.rmtree(f"threads/{thread_name}")

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=f"Permission error: {e}")

    except OSError as e:
        raise HTTPException(status_code=500, detail=f"OS error: {e}")

    return {"Thread": "Deleted"}


@router.get("/instance")
async def get_all_working_threads(
    thread_id: int | None = None,
    user_id: str = Depends(JWTBearer()),
    db: Session = Depends(get_db),
):
    uid = get_user_id(user_id)
    try:
        if thread_id is None:
            db_threads = crud.get_threads(db, uid)
            return db_threads
        else:
            db_thread = crud.get_thread(db, thread_id)
            if db_thread is None or db_thread.user_id != uid:
                raise HTTPException(status_code=404, detail="Thread not found")
            return db_thread
    except Exception as e:
        return {"error": str(e)}


@router.post("/instance")
async def create_working_thread(
    body: thread_schema.insert_strategy,
    user_id: str = Depends(JWTBearer()),
    db: Session = Depends(get_db),
) -> Dict:
    user_id = get_user_id(user_id)
    try:
        module_name = f"threads.{body.strategy}.main"
        strategy_module = importlib.import_module(module_name)
        strategy_class = getattr(strategy_module, "Strategy")

        db_thread = crud.create_thread(
            db,
            user_id,
            body.pair,
            body.exchange,
            body.qty,
            body.leverage,
            body.message,
            body.strategy,
        )

        strategy_instance = strategy_class(
            db_thread.id,
            user_id,
            body.pair,
            body.exchange,
            body.qty,
            body.leverage,
            body.message,
        )

        scheduler_manager.add_strategy(db_thread, strategy_instance)

        return {"thread id: ": db_thread.id}

    except ModuleNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Module not found, {e}")

    except Exception as e:
        return {"error": str(e)}


@router.put("/instance")
async def update_working_thread(
    body: thread_schema.update_strategy,
    user_id: str = Depends(JWTBearer()),
    db: Session = Depends(get_db),
) -> Dict:
    uid = get_user_id(user_id)
    try:
        db_thread = crud.get_thread(db, body.thread_id)
        if db_thread is None or db_thread.user_id != uid:
            raise HTTPException(status_code=404, detail="Thread not found")

        update_data = body.model_dump(exclude_unset=True)
        update_data.pop("thread_id", None)  # don't overwrite the PK

        for key, value in update_data.items():
            setattr(db_thread, key, value)

        crud.update_thread(db, db_thread)

        # Also update the live scheduler instance so changes take effect immediately
        if update_data:
            scheduler_manager.update_strategy_instance(body.thread_id, **update_data)

        return {"thread": "updated", "applied": list(update_data.keys())}
    except HTTPException:
        raise
    except Exception as e:
        return {"error": str(e)}


@router.delete("/instance")
async def delete_working_thread(
    thread_id: int,
    user_id: str = Depends(JWTBearer()),
    db: Session = Depends(get_db),
) -> Dict:
    uid = get_user_id(user_id)
    try:
        db_thread = crud.get_thread(db, thread_id)
        if db_thread is None or db_thread.user_id != uid:
            raise HTTPException(status_code=404, detail="Thread not found")

        scheduler_manager.stop_strategy(thread_id)
        crud.delete_thread(db, thread_id)

        return {"thread": "deleted"}
    except Exception as e:
        return {"error": str(e)}
