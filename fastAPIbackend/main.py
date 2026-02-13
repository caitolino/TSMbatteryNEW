from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
import logging
import os
from pydantic import BaseModel
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="templates")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (or specify ["http://127.0.0.1:8000", "file://"])
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection (configurable via MONGO_URI env var)
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://Caitlin_db:vc081226@test.sht8tpb.mongodb.net/admin")

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client["collected_data"]
bat_col = db["BATTERIJEN"]
tag_col = db["APRILTAGS"]   
loc_col = db["LOCATIES/AUTOS"]


@app.on_event("startup")
def startup_event():
    try:
        client.admin.command("ping")
        app.state.mongo_ok = True
        logger.info("Connected to MongoDB at %s", MONGO_URI)
    except Exception as e:
        app.state.mongo_ok = False
        logger.exception("Failed to connect to MongoDB: %s", e)


@app.get("/health")
def health():
    return {"app": "ok", "mongo_ok": getattr(app.state, "mongo_ok", False)}


@app.get("/test-db")
def test_db():
    try:
        names = client.list_database_names()
        return {"mongo_ok": True, "databases": names}
    except Exception as e:
        logger.exception("MongoDB test failed")
        raise HTTPException(status_code=503, detail=f"MongoDB error: {e}")


@app.get("/data")
def get_data():
    if not getattr(app.state, "mongo_ok", False):
        raise HTTPException(status_code=503, detail="MongoDB not available")
    data = list(bat_col.find({}, {"_id": 0}))
    return data

@app.get("/bat")
def get_data():
    if not getattr(app.state, "mongo_ok", False):
        raise HTTPException(status_code=503, detail="MongoDB not available")
    data = list(bat_col.find({}, {"_id": 0}))
    return data

@app.get("/loc")
def get_data():
    if not getattr(app.state, "mongo_ok", False):
        raise HTTPException(status_code=503, detail="MongoDB not available")
    data = list(loc_col.find({}, {"_id": 0}))
    return data

@app.get("/tags")
def get_data():
    if not getattr(app.state, "mongo_ok", False):
        raise HTTPException(status_code=503, detail="MongoDB not available")
    data = list(tag_col.find({}, {"_id": 0}))
    return data

class Tag(BaseModel):
    tagId : int
    type : str
    active : bool
class Loc(BaseModel):
    type : str
    name : str
    comment : str
class Bat(BaseModel):
    batUID : str
    createdAt : str
    retiredAt : str

@app.post('/tags')
def add_data(tag: Tag):
    tag_col.insert_one(tag.dict())
    return tag_col
@app.post('/bat')
def add_data(bat: Bat):
    bat_col.insert_one(bat.dict())
    return bat_col
@app.post('/loc')
def add_data(loc: Loc):
    loc_col.insert_one(loc.dict())
    return loc_col


