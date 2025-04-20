import io
import json
import logging
import os
from typing import Dict, Generator, Tuple

from botocore.config import Config
import fastapi as _fastapi
import pyaudio as pyaudio
import sqlalchemy.orm as _orm
from botocore.exceptions import ClientError
from fastapi import Query, HTTPException, WebSocket, WebSocketDisconnect
from fastapi import Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.requests import Request

import requests
import re

from gtts import gTTS
from pydantic import BaseModel
from starlette.responses import FileResponse, StreamingResponse

from pydub import AudioSegment
from vosk import Model, KaldiRecognizer

import boto3

import app.services as _services, app.schemas as _schemas, app.model as _model

from googletrans import Translator

app = _fastapi.FastAPI()

tasks: Dict[str, str] = {}

s3 = boto3.client(
    's3',
    endpoint_url='https://s3.twcstorage.ru',  # Укажи свой кастомный endpoint
    aws_access_key_id='9BFGKZB03BFJTWPKHS1G',
    aws_secret_access_key='hQ9ekLVCdRowNV2hd6DaBnHrmQbaRKB8A1AKoXIQ',
    region_name='ru-1',  # Укажи нужный регион, если требуется
    config=Config(signature_version='s3')
)
bucket_name = '3206f698-44fe1357-cc20-4d9d-8ed9-19d864b63752'


def get_s3_metadata(bucket: str, key: str) -> Tuple[bool, str]:
    """
    Проверяет существование объекта и возвращает Content-Type.
    Возвращает: (exists: bool, content_type: str)
    """
    try:
        response = s3.head_object(Bucket=bucket, Key=key)
        return True, response.get("ContentType", "application/octet-stream")
    except ClientError as e:
        if e.response['Error']['Code'] == "404":
            return False, ""
        else:
            raise


def stream_s3_object(bucket: str, key: str) -> Generator[bytes, None, None]:
    s3_object = s3.get_object(Bucket=bucket, Key=key)
    body = s3_object['Body']
    for chunk in iter(lambda: body.read(8192), b''):
        yield chunk


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
    with open(audio_file, 'rb') as f:
        s3.upload_fileobj(f, bucket_name, "tts/" + audio_file)

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
        audio_file_key = 'tts/' + audio_file
        exists, content_type = get_s3_metadata(bucket_name, audio_file_key)
        if exists:
            return StreamingResponse(
                stream_s3_object(bucket_name, audio_file_key),
                media_type=content_type,
                headers={"Content-Disposition": f"attachment; filename={audio_file_key.split('/')[-1]}"}
            )
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
    "https://translate.shoky.ru",
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


# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация модели Vosk
model = Model("./ai-models/vosk-model-cn-0.22")  # Укажите путь к вашей модели
recognizer = KaldiRecognizer(model, 16000)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logging.info("Соединение установлено, начало распознавания...")

    try:
        while True:
            # Получение аудиоданных из WebSocket
            data = await websocket.receive_bytes()  # Получаем бинарные данные

            # Перекодировка аудиоданных из формата webm в PCM
            audio_segment = AudioSegment.from_file(io.BytesIO(data), format="webm")
            audio_segment = audio_segment.set_frame_rate(16000).set_channels(1).set_sample_width(2)

            # Получаем байты в формате PCM
            pcm_data = audio_segment.raw_data

            # Передаем данные в распознаватель
            if recognizer.AcceptWaveform(pcm_data):
                result = recognizer.Result()
                result_json = json.loads(result)
                recognized_text = result_json.get("text", "").replace(" ", "")
                if recognized_text:
                    logging.info(f"Распознанный текст: {recognized_text}")
                    await websocket.send_text(recognized_text)  # Отправляем распознанный текст клиенту
            else:
                partial_result = recognizer.PartialResult()
                partial_json = json.loads(partial_result)
                partial_text = partial_json.get("partial", "").replace(" ", "")
                if partial_text:
                    logging.info(f"Частичный результат: {partial_text}")
                    await websocket.send_text(partial_text)  # Отправляем частичный результат клиенту
            recognizer.Reset()

    except WebSocketDisconnect:
        logging.info("Соединение закрыто клиентом")
    except Exception as e:
        logging.error(f"Произошла ошибка: {e}")
    finally:
        logging.info("Завершение работы WebSocket.")
