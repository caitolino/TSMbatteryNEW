#imports
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Form, Depends
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt import PyJWTError
import hashlib
from pymongo import MongoClient
import logging
import os
from pydantic import BaseModel
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from datetime import datetime, timedelta
#from paho.mqtt import client as mqtt


templates = Jinja2Templates(directory="templates")
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

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
#mqtt_client = mqtt.Client()

BROKER = "test.mosquitto.org"
PORT = 8883
topic_for_RPI = "RPITSM2/receiver"


db = client["collected_data"]
bat_col = db["BATTERIJEN"]
tag_col = db["APRILTAGS"]   
loc_col = db["LOCATIES/AUTOS"]
assign_col = db["TAG_ASSIGNMENTS"]
user_col = db["users"]
stat_col = db["MEETDATA_STATISCH"]
wed_col = db["WEDSTRIJD"]

# app.on_event
@app.on_event("startup")
def startup_event():
    try:
        client.admin.command("ping")
        app.state.mongo_ok = True
        logger.info("Geconnecteerd met MongoDB op %s", MONGO_URI)
    except Exception as e:
        app.state.mongo_ok = False
        logger.exception("Gefaald om te connecteren met MongoDB: %s", e)



# app.get
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
def get_data():
    if not getattr(app.state, "mongo_ok", False):
        raise HTTPException(status_code=503, detail="MongoDB niet bereikbaar")
    data = list(bat_col.find({}, {"_id": 0}))
    return data

@app.get("/admin")
def get_admins():
    if not getattr(app.state, "mongo_ok", False):
        raise HTTPException(status_code=503, detail="MongoDB niet bereikbaar")
    data = list(user_col.find({"admin": True}, {"_id": 0}))
    return data

@app.get("/user")
def get_data():
    if not getattr(app.state, "mongo_ok", False):
        raise HTTPException(status_code=503, detail="MongoDB niet bereikbaar")
    data = list(user_col.find({}, {"_id": 0}))
    return data

@app.get("/bat")
def get_data():
    if not getattr(app.state, "mongo_ok", False):
        raise HTTPException(status_code=503, detail="MongoDB niet bereikbaar")
    data = list(bat_col.find({}, {"_id": 0}))

#
    for item in data:
        if "reiredAt" in item and "retiredAt" not in item:
            item["retiredAt"] = item.pop("reiredAt")

    return data

@app.get("/loc")
def get_data():
    if not getattr(app.state, "mongo_ok", False):
        raise HTTPException(status_code=503, detail="MongoDB niet bereikbaar")
    data = list(loc_col.find({}, {"_id": 0}))
    return data

@app.get("/tags")
def get_data():
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
def get_data():
    if not getattr(app.state, "mongo_ok", False):
        raise HTTPException(status_code=503, detail="MongoDB niet bereikbaar")
    data = list(assign_col.find({}, {"_id": 0}))
    return data

@app.get("/stat")
def get_data():
    if not getattr(app.state, "mongo_ok", False):
        raise HTTPException(status_code=503, detail="MongoDB niet bereikbaar")
    data = list(stat_col.find({}, {"_id": 0}))
    return data

@app.get("/wed")
def get_data():
    if not getattr(app.state, "mongo_ok", False):
        raise HTTPException(status_code=503, detail="MongoDB niet bereikbaar")
    data = list(wed_col.find({}, {"_id": 0}))
    return data


#classes
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
class Assign (BaseModel):
    tagId : int
    validFrom : str
    validTo : str
    type : str
    assignedId : str
class User (BaseModel):
    username: str
    password: str
    write: bool = False
    admin: bool = False



# login
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

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

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except PyJWTError:
        raise credentials_exception
    user = user_col.find_one({"username": username})
    if user is None:
        raise credentials_exception
    return username


# app.post
@app.post('/tags')
def add_data(tag: Tag):
    doc = tag.dict()
    tag_col.insert_one(doc)
    return {"message": "Tag toegevoegd! Sluit dit venster en refresh de pagina om de aanpassingen te zien", "tag": doc}
@app.post('/bat')
def add_data(batUID: str = Form(...), current_user: str = Depends(get_current_user), comment: str = Form(...)):
    bat_col.insert_one({"createdAt": str((datetime.utcnow() + timedelta(hours=1)).isoformat()), "retiredAt": "/", "batUID": batUID, "user" : current_user, "comment": comment})
    return {"message": "Batterij toegevoegd!Sluit dit venster en refresh de pagina om de aanpassingen te zien"}
@app.post('/loc')
def add_data(type: str = Form(...), name: str = Form(...), current_user: str = Depends(get_current_user), comment: str = Form(...)):
    loc_col.insert_one({"type": type, "name": name, "user": current_user, "comment": comment})
    return {"message": "Locatie toegevoeg! Sluit dit venster en refresh de pagina om de aanpassingen te zien"}
@app.post('/assign')
def add_data(tagId: int = Form(...), type: str = Form(...), assignedId: str = Form(...)):
    assign_col.insert_one({"tagId": tagId, "validFrom": str((datetime.utcnow() + timedelta(hours=1)).isoformat()), "validTo": "/", "type": type, "assignedId": assignedId})
    return {"message": "Assignment toegevoegd!Sluit dit venster en refresh de pagina om de aanpassingen te zien"}

@app.post('/stat')
def add_data(batUID: str = Form(...),rawData: str = Form(...),estimation : int = Form(...), current_user: str = Depends(get_current_user), comment: str = Form(...)):
    stat_col.insert_one({"batUID": batUID, "timestamp": str((datetime.utcnow() + timedelta(hours=1)).isoformat()), "rawData": rawData, "estimation" : estimation, "user": current_user, "comment": comment})
    return {"message": "Meetdata toegevoegd!Sluit dit venster en refresh de pagina om de aanpassingen te zien"}

@app.post('/user')
def add_data(username: str = Form(...), password: str = Form(...)):
    if len(username) > 20:
        raise HTTPException(
            status_code=400,
            detail="Gebruikersnaam mag niet langer zijn dan 20 tekens!",
        )
    if user_col.find_one({"username": username}):
        raise HTTPException(
            status_code=400,
            detail="Gebruikersnaam bestaat al!",
        )

    user_col.insert_one({
        "username": username,
        "password": hash_password(password),
        "write": False,
        "admin": False,
    })
    return {"message": "Gebruiker toegevoegd! Sluit dit venster en refresh de pagina om de aanpassingen te zien"}

@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    if not verify_user(username, password):

        raise HTTPException(status_code=401, detail="Invalide gebruikersnaam of paswoord")
    
    user = user_col.find_one({"username": username}, {"_id": 0})
    write_flag = bool(user.get("write", False))
    admin_flag = verify_admin(username)
    
    access_token = create_access_token({"sub": username})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "write": write_flag,
        "admin": admin_flag,
    }

@app.post('/admin/set-write')
def admin_set_write(target_username: str = Form(...), write: bool = Form(...), current_user: str = Depends(get_current_user)):
    if not verify_admin(current_user):
        raise HTTPException(status_code=403, detail="Niet geautoriseerd")
    result = user_col.update_one({"username": target_username}, {"$set": {"write": write}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    mqtt_client.publish("topic_for_RPI", )
    return {"message": f"User {target_username} write set to {write}"}

@app.post('/admin/set-admin')
def admin_set_admin(target_username: str = Form(...), admin: bool = Form(...), current_user: str = Depends(get_current_user)):
    if not verify_admin(current_user):
        raise HTTPException(status_code=403, detail="Niet geautoriseerd")
    if target_username == "caitlinvandenblock" and not admin:
        raise HTTPException(status_code=403, detail="Kan geen leerkracht status van deze gebruiker verwijderen")
    result = user_col.update_one({"username": target_username}, {"$set": {"admin": admin}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Gebruiker niet gevonden")
    return {"message": f"User {target_username} admin set to {admin}"}


from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory="..", html=True), name="static")

