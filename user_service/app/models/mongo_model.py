from pydantic import BaseModel, HttpUrl, Field,EmailStr
from typing import List, Dict, Optional
from bson import ObjectId
from pydantic.json_schema import JsonSchemaValue

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, schema: JsonSchemaValue) -> JsonSchemaValue:
        schema.update(type="string")
        return schema

class Content(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id")
    title: str
    description: str
    category: str
    url: HttpUrl
    image_link: HttpUrl
    interactionMetrics: Dict[str, int]

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class Interest(BaseModel):
    topic: str
    weight: float

class User(BaseModel):
    username: str
    email: EmailStr
    interests: List[Interest]
    hashed_password: str
    verified: bool

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class UserLogInterest(BaseModel):
    email: EmailStr
    interests: List[Interest]
        
class NewUser(BaseModel):
    username: str
    email: EmailStr
    password: str

class CategoryEmbedding(BaseModel):
    category: str
    vector: List[float]