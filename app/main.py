import os
from typing import Dict

import fastapi as _fastapi
import sqlalchemy.orm as _orm
from fastapi import Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.requests import Request

import requests
import re

from gtts import gTTS
from pydantic import BaseModel
from starlette.responses import FileResponse

import app.services as _services, app.schemas as _schemas, app.model as _model

from googletrans import Translator

app = _fastapi.FastAPI()


tasks: Dict[str, str] = {}


# Define a Pydantic model for the TTS request
class TTSRequest(BaseModel):
    text: str
    voice_id: int
    language: int
    gender: int
    age: int

language_codes = {
    1: 'ru',  # Russian
    2: 'zh',  # Chinese
}
@app.post("/tts/")
async def generate_speech(request: TTSRequest):
    # Simulate speech generation
    task_id = str(len(tasks) + 1)  # Simple task ID generation
    audio_file = f"speech_{task_id}.mp3"
    lang_code = language_codes.get(request.language)
    if not lang_code:
        lang_code = 'en'
    # Generate speech using gTTS
    tts = gTTS(text=request.text, lang=lang_code)  # Change 'en' to the appropriate language code if needed
    tts.save(audio_file)  # Save the audio file

    # Store the file path in tasks
    tasks[task_id] = audio_file
    return {"task_id": task_id}


@app.get("/tts/status/{task_id}")
async def get_speech(task_id: str):
    if task_id in tasks:
        return {"task_id": task_id, "audio_file": tasks[task_id]}
    else:
        raise HTTPException(status_code=404, detail="Task not found")


@app.get("/tts/play/{task_id}")
async def play_speech(task_id: str):
    if task_id in tasks:
        audio_file = tasks[task_id]
        if os.path.exists(audio_file):
            return FileResponse(audio_file)
        else:
            raise HTTPException(status_code=404, detail="Audio file not found")
    else:
        raise HTTPException(status_code=404, detail="Task not found")


@app.post("/words")
async def create_word(
        word: _schemas.WordCreate, db: _orm.Session = _fastapi.Depends(_services.get_db)
):
    db_word = await _services.get_word_by_simplified(word.simplified, db)
    if db_word:
        raise _fastapi.HTTPException(status_code=400, detail="Word is already in use")

    return await _services.create_word(word, db)


@app.post("/words_rus")
async def create_word(
        word: _schemas.WordCreateRUS, db: _orm.Session = _fastapi.Depends(_services.get_db)
):
    db_word = await _services.get_word_by_simplified_rus(word.simplified, db)
    if db_word:
        raise _fastapi.HTTPException(status_code=400, detail="Word is already in use")

    return await _services.create_word_rus(word, db)


@app.get("/")
def hello_world():
    return {"hello": "world"}


@app.get("/words")
def get_words(db: _orm.Session = _fastapi.Depends(_services.get_db)):
    return db.query(_model.Word).all()


@app.get("/words_rus")
def get_words(db: _orm.Session = _fastapi.Depends(_services.get_db)):
    return db.query(_model.WordRUS).all()


origins = [
    "https://lukyanenkoa.github.io/web_ver_rus_zh_translator/",
    "http://localhost:8000",
    "http://127.0.0.1:8000/api/words/",
    "http://130.193.46.137:8000",
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/words/{word}", response_model=_schemas.Word)
async def get_word(word, db: _orm.Session = _fastapi.Depends(_services.get_db)):
    # get translated word by simplified version
    db_word = db.query(_model.Word).filter(_model.Word.simplified == word).first()
    if db_word is None:
        return _fastapi.responses.JSONResponse(
            status_code=404, content={"message": "No such word found"}
        )
    return db_word


@app.get("/words_rus/{word}", response_model=_schemas.WordRUS)
async def get_word(word, db: _orm.Session = _fastapi.Depends(_services.get_db)):
    # get translated word by simplified version
    db_word = db.query(_model.WordRUS).filter(_model.WordRUS.simplified == word).first()
    if db_word is None:
        return _fastapi.responses.JSONResponse(
            status_code=404, content={"message": "No such word found"}
        )
    return db_word


@app.get("/stroke-order")
async def stroke_order(q: str):
    response = requests.get("http://www.strokeorder.info/mandarin.php?q=" + q)
    imgsrc = re.findall(
        'src="(http://bishun.strokeorder.info/characters/.+gif)"',
        response.content.decode(),
    )[0]

    response = requests.get(imgsrc)
    headers = response.headers
    content = response.content
    return Response(
        content=content, headers={"Content-Type": headers.get("Content-Type")}
    )


# отдельно для библиотеки googletrans
translator = Translator()


@app.get("/translate/", response_model=dict)
async def translate_text(
        text: str = Query(..., description="Text to be translated")
):
    try:
        translation = translator.translate(text, src='zh-CN', dest='ru')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation error: {str(e)}")

    return {"translated_text": translation.text}


class GoqhanziResponse(BaseModel):
    results: list[str]


@app.post("/goqhanzi")
async def goqhanzi(request: Request):
    body = await request.body()
    response = requests.post("https://www.qhanzi.com/goqhanzi/", body.decode())
    return GoqhanziResponse.model_validate_json(response.content)
