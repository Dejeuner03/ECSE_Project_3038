from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, BeforeValidator, Field
from typing import List, Annotated
from fastapi.encoders import jsonable_encoder
from datetime import datetime, timedelta, timezone
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from bson import ObjectId
import motor.motor_asyncio
import requests
import os
import re
import pytz  

load_dotenv()

app = FastAPI()

regex = re.compile(r'((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?')

def parse_time(time_str):
    parts = regex.match(time_str)
    if not parts:
        return
    parts = parts.groupdict()
    time_params = {}
    for name, param in parts.items():
        if param:
            time_params[name] = int(param)
    return timedelta(**time_params)


connection = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("My_Key"))
settings_db = connection.control
readings_db = connection.sensor


origins = ["https://simple-smart-hub-client.netlify.app"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_url = "https://api.sunrise-sunset.org/json"
latitude = "17.97787"
longitude = "-76.77339"

PyObjectId = Annotated[str, BeforeValidator(str)]

class Settings(BaseModel):
    id: PyObjectId = Field(default=None, alias="_id")
    user_temp: float
    user_light: str
    light_duration: str
    light_time_off: str | None = None
    
class SensorValues(BaseModel):
    id: PyObjectId = Field(default=None, alias="_id")
    temperature: float
    presence: bool
    datetime: datetime

class SettingCollection(BaseModel):
    controls: List[Settings]
    
class SenorCollection(BaseModel):
    sensors: List[SensorValues]


def get_sunset_time():
    params = {
        "lat": latitude,
        "lng": longitude,
        "formatted": 0
    }

    response = requests.get(api_url, params=params)

    if response.status_code == 200:
        data = response.json()
        
        
        sunrise_utc = datetime.strptime(data['results']['sunrise'], '%Y-%m-%dT%H:%M:%S+00:00').replace(tzinfo=timezone.utc)
        sunset_utc = datetime.strptime(data['results']['sunset'], '%Y-%m-%dT%H:%M:%S+00:00').replace(tzinfo=timezone.utc)

        
        jamaica_tz = pytz.timezone("America/Jamaica")
        sunrise_local = sunrise_utc.astimezone(jamaica_tz)
        sunset_local = sunset_utc.astimezone(jamaica_tz)

        print(f"Sunrise: {sunrise_local.strftime('%H:%M:%S')}")
        print(f"Sunset: {sunset_local.strftime('%H:%M:%S')}")
    else:
        print(f"Error fetching sunrise/sunset: {response.status_code}")
        
async def calculate_light_off_time(start_time_str, duration_str):
    start_time = datetime.strptime(start_time_str, "%H:%M")
    duration = parse_time(duration_str)
    if not duration:
        raise HTTPException(status_code=400, detail="Invalid duration format")
    off_time = (datetime.combine(datetime.today(), start_time.time()) + duration).time()
    return off_time.strftime("%H:%M")

@app.put("/settings", response_model=Settings)
async def update_settings(settings: Settings):
    if settings.user_light.lower() == "sunset":
        settings.user_light = await get_sunset_time()

    settings.light_time_off = await calculate_light_off_time(settings.user_light, settings.light_duration)

    settings_dict = jsonable_encoder(settings, exclude={"id"})
    result = await settings_db["controls"].update_one(
        {},
        {"$set": settings_dict},
        upsert=True
    )

    if result.upserted_id:
        settings.id = result.upserted_id
    else:
        existing = await settings_db["controls"].find_one({})
        settings.id = existing["_id"]

    return settings

@app.get("/settings")
async def get_settings():
    setting_collection = await settings_db["controls"].find().to_list(1000)
    return SettingCollection(controls=setting_collection).controls

@app.post("/reading", response_model=SensorValues)
async def create_reading(reading: SensorValues):
    reading.datetime = datetime.now(pytz.timezone('America/Jamaica'))
    reading_dict = jsonable_encoder(reading, exclude={"id"})  
    new_reading = await readings_db["sensors"].insert_one(reading_dict)
    created_reading = await readings_db["sensors"].find_one({"_id": new_reading.inserted_id})
    return SensorValues(**created_reading)

@app.get("/graph", response_model=List[SensorValues])
async def get_graph():
    sensor_collection = await readings_db["sensors"].find().sort("datetime", -1).to_list(1000)
    return sensor_collection

@app.get("/control")
async def get_control_commands():
    settings = await settings_db["controls"].find_one({})
    if not settings:
        return {"fan": False, "light": False}
    
    reading = await readings_db["sensors"].find_one(sort=[("datetime", -1)])
    if not reading:
        return {"fan": False, "light": False}

    current_time = datetime.now(pytz.timezone('America/Jamaica')).time()
    light_on_time = datetime.strptime(settings["user_light"], "%H:%M:%S").time()
    light_off_time = datetime.strptime(settings["light_time_off"], "%H:%M:%S").time()
    
    light_on = reading["presence"] and light_on_time <= current_time <= light_off_time
    fan_on = reading["presence"] and reading["temperature"] > settings["user_temp"]
    
    return {
        "fan": fan_on,
        "light": light_on,
        "current_temp": reading["temperature"],
        "presence": reading["presence"]
    }