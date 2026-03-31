#imports
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Form, Depends
import hashlib
from pymongo import MongoClient
import logging
import os
from pydantic import BaseModel
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from datetime import datetime, timedelta
import jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles

templates = Jinja2Templates(directory="templates")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI()

#CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MONGO_URI = os.getenv("MONGO_URI")

logger.info("startup: MONGO_URI = %r", MONGO_URI)

if not MONGO_URI:
    raise RuntimeError("MONGO_URI environment variable must be set")

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)

db = client["collected_data"]
bat_col = db["BATTERIJEN"]
tag_col = db["APRILTAGS"]   
loc_col = db["LOCATIES/AUTOS"]
assign_col = db["TAG_ASSIGNMENTS"]
user_col = db["users"]
stat_col = db["MEETDATA_STATISCH"]
wed_col = db["WEDSTRIJD"]

bearer_scheme = HTTPBearer()

# ==================== TOKEN FUNCTIONS ====================

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user_from_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return {
            "username": payload.get("sub"),
            "write": payload.get("write", False),
            "admin": payload.get("admin", False)
        }
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        raise HTTPException(status_code=401, detail="Invalid token", headers={"WWW-Authenticate": "Bearer"})

def check_write_permission(current_user_data: dict):
    """Check if user has write permissions"""
    if not current_user_data.get("write", False) and not current_user_data.get("admin", False):
        raise HTTPException(status_code=403, detail="Geen schrijfmachtigingen")
    return current_user_data

def check_admin_permission(current_user_data: dict):
    """Check if user has admin permissions"""
    if not current_user_data.get("admin", False):
        raise HTTPException(status_code=403, detail="Niet geautoriseerd")
    return current_user_data



def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def verify_user(username: str, password: str) -> bool:
    user = user_col.find_one({"username": username})
    if not user:
        return False
    return user["password"] == hash_password(password)

def verify_admin(username: str) -> bool:
    user = user_col.find_one({"username": username})
    if not user:
        return False
    return bool(user.get("admin", False))



@app.on_event("startup")
def startup_event():
    try:
        client.admin.command("ping")
        app.state.mongo_ok = True
        logger.info("Geconnecteerd met MongoDB op %s", MONGO_URI)
    except Exception as e:
        app.state.mongo_ok = False
        logger.exception("Gefaald om te connecteren met MongoDB: %s", e)


@app.get("/health")
def health():
    return {"app": "ok", "mongo_ok": getattr(app.state, "mongo_ok", False)}

@app.get("/test-db")
def test_db():
    try:
        names = client.list_database_names()
        info = {
            "mongo_ok": True,
            "databases": names,
            "client_address": getattr(client, "address", None),
            "mongo_uri": MONGO_URI,
        }
        return info
    except Exception as e:
        logger.exception("MongoDB test gefaald")
        raise HTTPException(status_code=503, detail=f"MongoDB error: {e}")



@app.get("/data")
def get_data(current_user_data = Depends(get_current_user_from_token)):
    if not getattr(app.state, "mongo_ok", False):
        raise HTTPException(status_code=503, detail="MongoDB niet bereikbaar")
    data = list(bat_col.find({}, {"_id": 0}))
    return data

@app.get("/admin")
def get_admins(current_user_data = Depends(get_current_user_from_token)):
    check_admin_permission(current_user_data)
    if not getattr(app.state, "mongo_ok", False):
        raise HTTPException(status_code=503, detail="MongoDB niet bereikbaar")
    data = list(user_col.find({"admin": True}, {"_id": 0}))
    return data

@app.get("/user")
def get_users(current_user_data = Depends(get_current_user_from_token)):
    check_admin_permission(current_user_data)
    if not getattr(app.state, "mongo_ok", False):
        raise HTTPException(status_code=503, detail="MongoDB niet bereikbaar")
    data = list(user_col.find({}, {"_id": 0}))
    return data

@app.get("/bat")
def get_batteries(current_user_data = Depends(get_current_user_from_token)):
    if not getattr(app.state, "mongo_ok", False):
        raise HTTPException(status_code=503, detail="MongoDB niet bereikbaar")
    data = list(bat_col.find({}, {"_id": 0}))
    for item in data:
        if "reiredAt" in item and "retiredAt" not in item:
            item["retiredAt"] = item.pop("reiredAt")
    return data

@app.get("/loc")
def get_locations(current_user_data = Depends(get_current_user_from_token)):
    if not getattr(app.state, "mongo_ok", False):
        raise HTTPException(status_code=503, detail="MongoDB niet bereikbaar")
    data = list(loc_col.find({}, {"_id": 0}))
    return data

@app.get("/tags")
def get_tags(current_user_data = Depends(get_current_user_from_token)):
    if not getattr(app.state, "mongo_ok", False):
        raise HTTPException(status_code=503, detail="MongoDB niet bereikbaar")
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
        tag.pop("_id", None) 
        for assign in tag.get("assignments", []):
            assign.pop("_id", None)    
            assign.pop("tagId", None)    
    return data

@app.get("/assign")
def get_assignments(current_user_data = Depends(get_current_user_from_token)):
    if not getattr(app.state, "mongo_ok", False):
        raise HTTPException(status_code=503, detail="MongoDB niet bereikbaar")
    data = list(assign_col.find({}, {"_id": 0}))
    return data

@app.get("/stat")
def get_stats(current_user_data = Depends(get_current_user_from_token)):
    if not getattr(app.state, "mongo_ok", False):
        raise HTTPException(status_code=503, detail="MongoDB niet bereikbaar")
    data = list(stat_col.find({}, {"_id": 0}))
    return data

@app.get("/wed")
def get_wedstrijden(current_user_data = Depends(get_current_user_from_token)):
    if not getattr(app.state, "mongo_ok", False):
        raise HTTPException(status_code=503, detail="MongoDB niet bereikbaar")
    data = list(wed_col.find({}, {"_id": 0}))
    return data



class Stat(BaseModel):
    batUID : str
    timestamp : str
    rawData : str
    estimation : int
    user : str
    comment : str

class Tag(BaseModel):
    tagId : int
    type : str
    active : bool

class Loc(BaseModel):
    type : str
    name : str
    user : str
    comment : str

class Bat(BaseModel):
    createdAt : str
    retiredAt : str
    batUID : str
    user : str
    comment : str

class Assign(BaseModel):
    tagId : int
    validFrom : str
    validTo : str
    type : str
    assignedId : str

class User(BaseModel):
    username: str
    password: str
    write: bool = False
    admin: bool = False


@app.post('/tags')
def add_tag(tag: Tag, current_user_data = Depends(get_current_user_from_token)):
    check_write_permission(current_user_data)
    doc = tag.dict()
    tag_col.insert_one(doc)
    return {"message": "Tag toegevoegd! Sluit dit venster en refresh de pagina om de aanpassingen te zien", "tag": doc}

@app.post('/bat')
def add_battery(batUID: str = Form(...), current_user_data = Depends(get_current_user_from_token), comment: str = Form(...)):
    check_write_permission(current_user_data)
    current_user = current_user_data["username"]
    bat_col.insert_one({"createdAt": str((datetime.utcnow() + timedelta(hours=1)).isoformat()), "retiredAt": "/", "batUID": batUID, "user" : current_user, "comment": comment})
    return {"message": "Batterij toegevoegd!Sluit dit venster en refresh de pagina om de aanpassingen te zien"}

@app.post('/loc')
def add_location(type: str = Form(...), name: str = Form(...), current_user_data = Depends(get_current_user_from_token), comment: str = Form(...)):
    check_write_permission(current_user_data)
    current_user = current_user_data["username"]
    loc_col.insert_one({"type": type, "name": name, "user": current_user, "comment": comment})
    return {"message": "Locatie toegevoeg! Sluit dit venster en refresh de pagina om de aanpassingen te zien"}

@app.post('/assign')
def add_assignment(tagId: int = Form(...), type: str = Form(...), assignedId: str = Form(...), current_user_data = Depends(get_current_user_from_token)):
    check_write_permission(current_user_data)
    assign_col.insert_one({"tagId": tagId, "validFrom": str((datetime.utcnow() + timedelta(hours=1)).isoformat()), "validTo": "/", "type": type, "assignedId": assignedId})
    return {"message": "Assignment toegevoegd!Sluit dit venster en refresh de pagina om de aanpassingen te zien"}

@app.post('/stat')
def add_stat(batUID: str = Form(...), rawData: str = Form(...), estimation : int = Form(...), current_user_data = Depends(get_current_user_from_token), comment: str = Form(...)):
    check_write_permission(current_user_data)
    current_user = current_user_data["username"]
    stat_col.insert_one({"batUID": batUID, "timestamp": str((datetime.utcnow() + timedelta(hours=1)).isoformat()), "rawData": rawData, "estimation" : estimation, "user": current_user, "comment": comment})
    return {"message": "Meetdata toegevoegd!Sluit dit venster en refresh de pagina om de aanpassingen te zien"}

@app.post('/user')
def add_user(username: str = Form(...), password: str = Form(...), current_user_data = Depends(get_current_user_from_token)):
    check_admin_permission(current_user_data)
    if user_col.find_one({"username": username}):
        raise HTTPException(status_code=400, detail="Gebruikersnaam bestaat al!")
    user_col.insert_one({
        "username": username,
        "password": hash_password(password),
        "write": False,
        "admin": False,
    })
    return {"message": "Gebruiker toegevoegd! Sluit dit venster en refresh de pagina om de aanpassingen te zien"}



@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    if verify_user(username, password):
        user = user_col.find_one({"username": username}, {"_id": 0})
        write_flag = bool(user.get("write", False))
        admin_flag = verify_admin(username)
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": username, "write": write_flag, "admin": admin_flag}, expires_delta=access_token_expires
        )
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "write": write_flag,
            "admin": admin_flag
        }
    raise HTTPException(status_code=401, detail="Invalide gebruikersnaam of paswoord")

@app.post("/register")
def register(username: str = Form(...), password: str = Form(...)):
    if user_col.find_one({"username": username}):
        raise HTTPException(status_code=400, detail="Gebruikersnaam bestaat al!")
    user_col.insert_one({
        "username": username,
        "password": hash_password(password),
        "write": True,
        "admin": False
    })
    return {"message": "User registered successfully"}



@app.post('/admin/set-write')
def admin_set_write(target_username: str = Form(...), write: bool = Form(...), current_user_data = Depends(get_current_user_from_token)):
    check_admin_permission(current_user_data)
    result = user_col.update_one({"username": target_username}, {"$set": {"write": write}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": f"User {target_username} write set to {write}"}

@app.post('/admin/set-admin')
def admin_set_admin(target_username: str = Form(...), admin: bool = Form(...), current_user_data = Depends(get_current_user_from_token)):
    check_admin_permission(current_user_data)
    if target_username == "caitlinvandenblock" and not admin:
        raise HTTPException(status_code=403, detail="Kan geen leerkracht status van deze gebruiker verwijderen")
    result = user_col.update_one({"username": target_username}, {"$set": {"admin": admin}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Gebruiker niet gevonden")
    return {"message": f"User {target_username} admin set to {admin}"}


app.mount("/", StaticFiles(directory="..", html=True), name="static")

