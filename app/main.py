import fastapi as _fastapi
import sqlalchemy.orm as _orm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.requests import Request

import requests
import re
from pydantic import BaseModel

import app.services as _services, app.schemas as _schemas, app.model as _model

app = _fastapi.FastAPI()


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


class GoqhanziResponse(BaseModel):
    results: list[str]


@app.post("/goqhanzi")
async def goqhanzi(request: Request):
    body = await request.body()
    response = requests.post("https://www.qhanzi.com/goqhanzi/", body.decode())
    return GoqhanziResponse.model_validate_json(response.content)