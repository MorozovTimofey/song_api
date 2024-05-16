from typing import List, Optional
from fastapi import FastAPI, HTTPException, Form, Depends
from pydantic import Field, BaseModel
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
from fastapi.middleware.cors import CORSMiddleware

# Создаем экземпляр FastAPI
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Можете изменить "*" на список доверенных доменов
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Подключение к MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["music_db"]
songs_collection = db["songs"]

# Модель данных для песни
class Song(BaseModel):
    id: str = Field(default_factory=ObjectId, alias="_id")
    name: str
    lyrics: str
    last_performed_date: Optional[datetime] = None
    performances: List[datetime] = []

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str
        }

# Роут для создания новой песни через форму
@app.post("/songs/", response_model=dict)
async def create_song(name: str = Form(...), lyrics: str = Form(...), last_performed_date: str = Form(None)):
    last_performed_datetime = None
    if last_performed_date:
        last_performed_datetime = datetime.strptime(last_performed_date, "%d-%m-%Y")
    song_data = {"name": name, "lyrics": lyrics, "last_performed_date": last_performed_datetime}
    result = songs_collection.insert_one(song_data)
    return {"song_id": str(result.inserted_id)}

# Роут для получения информации о песне по ее ID
@app.get("/songs/{song_id}", response_model=Song)
def read_song(song_id: str):
    song_data = songs_collection.find_one({"_id": ObjectId(song_id)})
    if not song_data:
        raise HTTPException(status_code=404, detail="Song not found")
    song_data["_id"] = str(song_data["_id"])  # Преобразование ObjectId в строку
    return Song(**song_data)

# Роут для обновления информации о песне (например, при исполнении)
@app.put("/songs/{song_id}", response_model=dict)
def update_song(song_id: str, last_performed_date: datetime):
    song_data = songs_collection.find_one({"_id": ObjectId(song_id)})
    if not song_data:
        raise HTTPException(status_code=404, detail="Song not found")
    songs_collection.update_one(
        {"_id": ObjectId(song_id)},
        {"$set": {"last_performed_date": last_performed_date}}
    )
    return {"message": "Song updated successfully"}

# Роут для вывода всех песен
@app.get("/songs/", response_model=List[Song])
def get_all_songs():
    all_songs = songs_collection.find({})
    songs = []
    for song in all_songs:
        song["_id"] = str(song["_id"])  # Преобразование ObjectId в строку
        songs.append(Song(**song))
    return songs

# Подключаем Swagger UI
from fastapi.openapi.docs import get_swagger_ui_html

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="API docs")

@app.get("/openapi.json", include_in_schema=False)
async def get_openapi_schema():
    return app.openapi()

# Запуск приложения
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
