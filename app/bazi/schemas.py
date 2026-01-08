from pydantic import BaseModel, Field
from typing import Optional, Literal

class BaziRequest(BaseModel):
    date: str = Field(..., example="1966-10-09")
    time: Optional[str] = Field(None, example="07:00")
    location: str = Field(..., example="Asia/Hong_Kong")
    gender: Literal["Male", "Female"]
    year: str = Field(..., example="2026")
    llm: Literal["openai", "qianwen", "hunyuan"] = "openai"
    lang: Literal["en", "cn"] = "en"
