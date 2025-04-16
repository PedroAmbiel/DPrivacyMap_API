from pydantic import BaseModel

class UserLoginResponse(BaseModel):
    id: int
    email: str
    responsavel: str
    nome:str
    perfil: int