from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Form
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
assign_col = db["TAG_ASSIGNMENTS"]


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
    #data = list(tag_col.find({}, {"_id": 0}))
    pipeline = [
        {
            "$lookup": {
                "from": "TAG_ASSIGNMENTS",
                "localField": "tagId",
                "foreignField": "tagId",
                "as": "assignments"
            }
        }
    ]
    data = list(tag_col.aggregate(pipeline))
    for tag in data:
        tag.pop("_id", None)  # remove tag _id
        for assign in tag.get("assignments", []):
            assign.pop("_id", None)      # remove assignment _id
            assign.pop("tagId", None)    # remove assignment tagId if you don't want it

    return data

@app.get("/assign")
def get_data():
    if not getattr(app.state, "mongo_ok", False):
        raise HTTPException(status_code=503, detail="MongoDB not available")
    data = list(assign_col.find({}, {"_id": 0}))
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
    createdAt : str
    retiredAt : str
    batUID : str
    comment : str
class Assign (BaseModel):
    tagId : int
    validFrom : str
    validTo : str
    type : str
    assignedId : str


@app.post('/tags')
def add_data(tag: Tag):
    tag_col.insert_one(tag.dict())
    return tag_col
@app.post('/bat')
def add_data(createdAt: str = Form(...), retiredAt: str = Form(...),batUID: str = Form(...), comment: str = Form(...)):
    bat_col.insert_one({"createdAt": createdAt, "reiredAt": retiredAt, "batUID": batUID, "comment": comment})
    return {"message": "Batterij toegevoegd!Sluit dit venster en refresh de pagina om de aanpassingen te zien"}
@app.post('/loc')
def add_data(type: str = Form(...), name: str = Form(...), comment: str = Form(...)):
    loc_col.insert_one({"type": type, "name": name, "comment": comment})
    return {"message": "Locatie toegevoeg! Sluit dit venster en refresh de pagina om de aanpassingen te zien"}
@app.post('/assign')
def add_data(assign: Assign):
    assign_col.insert_one(assign.dict())
    return assign_col

