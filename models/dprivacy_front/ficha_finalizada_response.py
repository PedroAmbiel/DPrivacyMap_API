from pydantic import BaseModel
from pydantic_extra_types.pendulum_dt import DateTime

class FichasFinalizadasResponse(BaseModel):
    id: int
    area: str | None
    finalizado: bool
    dataCadastro: DateTime
    totalSecoes: int | None