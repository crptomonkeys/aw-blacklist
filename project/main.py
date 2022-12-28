from typing import List, Union
from sqlalchemy.orm.session import Session
from fastapi import Body, FastAPI, Form, Request, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import config
from fastapi.middleware.cors import CORSMiddleware
import time,os
from sqlalchemy.future import select
from models import Blacklist
from db import commit_or_rollback, update_reason
from db import db_session,init_db
from datetime import datetime
from enum import Enum
from sqlalchemy import func

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from sqlmodel import Session, select
from db import engine
import aioredis
from pydantic import BaseModel

app = FastAPI(title="AW Botnet Archive",
        description="made with <3 and maintained by green",
        version="0.0.2")

origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def api_key_auth(api_key: str = Depends(oauth2_scheme)):
    if api_key not in config.api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Forbidden"
        )

class OrderChoose(str, Enum):
    desc = "desc"
    asc = "asc"

class BlacklistModel(BaseModel):
    wallet: str
    reason: str
    added: str

class BlacklistRequest(BaseModel):
    wallet: str
    reason: str = None

class BaseResponse(BaseModel):
    success: bool
    query_time: str
    data: Union[BlacklistModel, None] = None
    error: Union[str, None] = None

class BlacklistGetListResponse(BaseResponse):
    data: List[BlacklistModel]
    
    
@app.on_event("startup")
def on_startup():
    init_db()
    redis =  aioredis.from_url(os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379"), encoding="utf8", decode_responses=True)
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
    print("redis cache success")

@app.get("/")
def home(request: Request):
    return {"Yes this service is running fine!"}

@app.get("/healthc")
def home(request: Request):
    return {"Yes this service is running fine!"}

@app.post("/add", dependencies=[Depends(api_key_auth)], response_model=BaseResponse)
async def add_wallet(new_bl:BlacklistRequest):
    perf = time.time()

    response = {
        "success":True
    }
    with Session(engine) as session:
        
        statement = select([func.count(Blacklist.wallet)]).where(Blacklist.wallet == new_bl.wallet)
        results = session.exec(statement).one()
        if results > 0:
            response["success"] = False
            response["error"] = f"Wallet {new_bl.wallet} already Blacklisted"
        else:
            bl_to_add = Blacklist(
                wallet=new_bl.wallet,
                reason=new_bl.reason,
                added=datetime.utcnow().isoformat()
            )
            commit_or_rollback(session, bl_to_add)
            response["data"] = bl_to_add
    
    response["query_time"] = time.time()-perf

    return response

@app.put("/update", dependencies=[Depends(api_key_auth)], response_model=BaseResponse)
async def update_wallet(bl_to_update:BlacklistRequest):
    perf = time.time()

    response = {
        "success":True
    }
    with Session(engine) as session:
        
        statement = select(Blacklist).where(Blacklist.wallet == bl_to_update.wallet)
        result = session.exec(statement).one()
        if result:
            update_reason(session,bl_to_update)
            response["data"] = {
                "wallet":result.wallet,
                "added": result.added,
                "reason": bl_to_update.reason
            }
        else:
            response["success"] = False
            response["error"] = f"Wallet {bl_to_update.wallet} is not blacklisted"
    
    response["query_time"] = time.time()-perf

    return response

@app.delete("/delete", dependencies=[Depends(api_key_auth)], response_model=BaseResponse)
async def delete_wallet(wallet_to_delete:str):
    perf = time.time()

    response = {
        "success":True
    }
    try:
        delete_q = Blacklist.__table__.delete().where(
            Blacklist.wallet == wallet_to_delete
        )
        db_session.execute(delete_q)
        db_session.commit()
    except Exception as e:
            response["success"] = False
            response["error"] = e

    response["query_time"] = time.time()-perf
    
    return response

@app.get("/check", response_model=BaseResponse)
async def check_wallet(wallet:str):
    perf = time.time()

    response = {
        "success":True
    }
    with Session(engine) as session:
        try:
            statement = select(Blacklist).where(Blacklist.wallet == wallet)
            result = session.exec(statement).one()
            response["data"] = result

        except Exception as e:
            response["success"] = False
            response["error"] = f"Wallet {wallet} is not blacklisted"
    
    response["query_time"] = time.time()-perf
    
    return response

@app.get("/list", response_model=BlacklistGetListResponse)
@cache(expire=5)
async def get_list():
    perf = time.time()

    response = {
        "success":True
    }
    with Session(engine) as session:
        
        statement = select(Blacklist)
        results = session.exec(statement).all()
        response["data"] = results

    response["query_time"] = time.time()-perf
    return response
