from pydantic import BaseModel

class insert_user(BaseModel):
    name: str
    username: str
    password: str

class user_login_schema(BaseModel):
    username: str
    password: str


