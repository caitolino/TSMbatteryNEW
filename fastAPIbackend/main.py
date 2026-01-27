from fastapi import FastAPI, HTTPException
from pymongo import MongoClient
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# MongoDB connection (configurable via MONGO_URI env var)
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://Caitlin_db:vc081226@test.sht8tpb.mongodb.net/admin")

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client["collected_data"]
bat_col = db["batterijen"]
auto_col = db["autos"]
tag_col = db["apriltags"]   
loc_col = db["locaties"]


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

@app.get("/autos")
def get_data():
    if not getattr(app.state, "mongo_ok", False):
        raise HTTPException(status_code=503, detail="MongoDB not available")
    data = list(auto_col.find({}, {"_id": 0}))
    return data

@app.get("/tags")
def get_data():
    if not getattr(app.state, "mongo_ok", False):
        raise HTTPException(status_code=503, detail="MongoDB not available")
    data = list(tag_col.find({}, {"_id": 0}))
    return data

@app.get("/loc")
def get_data():
    if not getattr(app.state, "mongo_ok", False):
        raise HTTPException(status_code=503, detail="MongoDB not available")
    data = list(loc_col.find({}, {"_id": 0}))
    return data