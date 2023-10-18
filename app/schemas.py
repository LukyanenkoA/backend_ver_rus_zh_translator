import pydantic as _pydantic


class _WordBase(_pydantic.BaseModel):
    traditional: str
    simplified: str
    english: str
    pinyin: str
    hsk: int


class WordCreate(_WordBase):
    pass

    class Config:
        orm_mode = True


class Word(_WordBase):
    id: int

    class Config:
        orm_mode = True


class _WordBaseRUS(_pydantic.BaseModel):
    simplified: str
    russian: str
    pinyin: str


class WordCreateRUS(_WordBaseRUS):
    pass

    class Config:
        orm_mode = True

class WordRUS(_WordBaseRUS):
    id: int

    class Config:
        orm_mode = True