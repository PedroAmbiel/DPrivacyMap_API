from pydantic import BaseModel
from pydantic_extra_types.pendulum_dt import DateTime

class FichasRedigindoResponse(BaseModel):
    id: int
    area: str | None
    finalizado: bool
    dataCadastro: DateTime 