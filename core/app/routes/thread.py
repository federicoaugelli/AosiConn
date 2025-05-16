from fastapi import APIRouter, BackgroundTasks, File, UploadFile, HTTPException, Depends
from typing import Dict, Annotated
import os, zipfile, shutil, json, threading, importlib
from schemas import threads as thread_schema
from auth.auth_bearer import JWTBearer
from utils.router_utils import *
from utils.scheduler_utils import scheduler
from datetime import datetime, timedelta

router = APIRouter()

thread_folder = "threads"
# TODO replace this with a database
threads = []
thread_lock = threading.Lock()


@scheduler.scheduled_job('interval', seconds=60)
def health_check():
    for thread in threads:
        _timestamp = datetime.now()
        if _timestamp - thread.timestamp > timedelta(seconds=thread.timedelta) or thread.kill_it == True:
            print(f"delta: {_timestamp - thread.timestamp}, timedelta: {thread.timedelta}")
            thread.stop()
            threads.remove(thread)


@router.get("/")
async def get_threads(user_id: str = Depends(JWTBearer()), dependencies=Depends(JWTBearer())) -> Dict[str, object]:
    
    uid = get_user_id(user_id) # useful for getting only the threads that the user has access to

    threads_list = []

    for thread in os.listdir("threads"):
        thread_path = f"threads/{thread}"
        if os.path.isdir(thread_path):
            with open(f"{thread_path}/config.json", "r") as config_file:
                config = json.load(config_file)
                if "name" in config and "description" in config and "author" in config:
                    threads_list.append({
                        "filename": thread,
                        "name": config["name"],
                        "description": config["description"],
                        "author": config["author"]
                    })
                else:
                    # TODO check if the config file is missing required fields inside the upload function
                    raise HTTPException(status_code=400, detail="Config file is missing required fields")

    return {"threads": threads_list}


@router.post("/upload/")
async def upload_thread(file: UploadFile, user_id: str = Depends(JWTBearer()), dependencies=Depends(JWTBearer())):
    
    if file.filename.endswith(".zip"):
    
        with open(f"threads/{file.filename}", "wb") as buffer:
            buffer.write(file.file.read())
        
        with zipfile.ZipFile(f"threads/{file.filename}", "r") as zip_ref:
            zip_ref.extractall(f"threads/")
        
        os.remove(f"threads/{file.filename}")

        #check there's at least one python file and a config.json file
        if not os.path.exists(f"threads/{file.filename[:-4]}/config.json"):
            #os.rmdir(f"threads/{file.filename[:-4]}")
            raise HTTPException(status_code=400, detail="Config file not found")

        if not any(file.endswith(".py") for file in os.listdir(f"threads/{file.filename[:-4]}")):
            #os.rmdir(f"threads/{file.filename[:-4]}")
            raise HTTPException(status_code=400, detail="Python file not found")

    else:
        raise HTTPException(status_code=400, detail="File must be a zip file") 
    
    filename = file.filename[:-4]

    #change the name of the python file inside the folder to main
    for file in os.listdir(f"threads/{filename}"):
        if file.endswith(".py"):
            os.rename(f"threads/{filename}/{file}", f"threads/{filename}/main.py")

    return {
        f"{filename} ingested successfully"
    }


@router.delete("/{thread_name}/")
async def delete_threads(thread_name: str, user_id: str = Depends(JWTBearer()), dependencies=Depends(JWTBearer())) -> Dict:

    if not os.path.exists(f"threads/{thread_name}"):
        raise HTTPException(status_code=404, detail="Thread not found")

    try:
        shutil.rmtree(f"threads/{thread_name}")

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=f"Permission error: {e}")

    except OSError as e:
        raise HTTPException(status_code=500, detail=f"OS error: {e}")
    
    return {
        "Thread": "Deleted"
    }

# TODO if thread dies it still shows up in the list
@router.get("/instance")
async def get_all_working_threads(thread_id: int | None = None, user_id: str = Depends(JWTBearer()), dependencies=Depends(JWTBearer())) -> Dict:
    uid = get_user_id(user_id)
    try:
        if thread_id == None:
            with thread_lock:
                threads_list = [{'thread_id': id(t), 'action': t.last_action, 'pair': t.pair, 'exchange': t.exchange, 'qty': t.qty, 'leverage': t.leverage, 'message': t.message} for t in threads if t.user_id == uid]
                
                return {
                    'thread': threads_list
                }
        else:
            t = next((t for t in threads if id(t) == thread_id and t.user_id == uid), None)
    
            if t == None:
                raise HTTPException(status_code=404, detail="Thread not found")

            thread = {'thread_id': id(t), 'action': t.last_action, 'pair': t.pair, 'exchange': t.exchange, 'qty': t.qty, 'leverage': t.leverage, 'message': t.message}
            
            if t.kill_it == True:
                threads.remove(t)
                raise HTTPException(status_code=404, detail="Thread not found")

            return {
                'thread': thread
            }

    except Exception as e:
        return {"error": str(e)}

@router.post("/instance")
async def create_working_thread(body: thread_schema.insert_strategy, user_id: str = Depends(JWTBearer()), dependencies=Depends(JWTBearer())) -> Dict:
    user_id = get_user_id(user_id)
    try:
        #init = globals().get(body.strategy)
        module_name = f"threads.{body.strategy}.main"
        strategy_module = importlib.import_module(module_name)
        strategy_instance = getattr(strategy_module, 'strategy')
        thread = strategy_instance(user_id,  body.pair, body.exchange, body.qty, body.leverage, body.message)
        with thread_lock:
            threads.append(thread)
        thread.start()
        return {
            "thread id: ": id(thread)
        }
    
    except ModuleNotFoundError as e:
        raise HTTPException(status_code=404, detail="Module not found")

    except Exception as e:
        return {"error": str(e)}

@router.put("/instance")
async def update_working_thread(body: thread_schema.update_strategy, user_id: str = Depends(JWTBearer()), dependencies=Depends(JWTBearer())) -> Dict:
    uid = get_user_id(user_id)
    try:
        thread = next((t for t in threads if id(t) == body.thread_id and t.user_id == uid), None)
        if thread == None:
            raise HTTPException(status_code=404, detail="Thread not found")
        else:
            thread.update(body.pair, body.exchange, body.qty, body.leverage, body.message)
        return {
            "thread": "updated"
        }
    except Exception as e:
        return {"error": str(e)}

@router.delete("/instance")
async def delete_working_thread(thread_id: int, user_id: str = Depends(JWTBearer()), dependencies=Depends(JWTBearer())) -> Dict:
    uid = get_user_id(user_id)
    try:
        thread = next((t for t in threads if id(t) == thread_id and t.user_id == uid), None)
        if thread.last_action != 0:
            raise HTTPException(status_code=401, detail="there are opened position for this strategy")
        else:
            thread.stop()
            #thread.join()
            threads.remove(thread)
        return {
            "thread": "deleted"
        }
    except Exception as e:
        return {"error": str(e)}

