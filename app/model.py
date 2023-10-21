import sqlalchemy as _sql
import sqlalchemy.ext.declarative as _declarative
import sqlalchemy.orm as _orm

import app.database as _database


class Word(_database.Base):
    __tablename__ = "words"
    id = _sql.Column(_sql.Integer, primary_key=True, index=True)
    traditional = _sql.Column(_sql.String)
    simplified = _sql.Column(_sql.String, unique=True, index=True)
    english = _sql.Column(_sql.String)
    pinyin = _sql.Column(_sql.String)


class WordRUS(_database.Base):
    __tablename__ = "words_rus"
    id = _sql.Column(_sql.Integer, primary_key=True, index=True)
    simplified = _sql.Column(_sql.String, unique=True, index=True)
    pinyin = _sql.Column(_sql.String)
    russian = _sql.Column(_sql.String)
