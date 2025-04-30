from pydantic import BaseModel
from pydantic_extra_types.pendulum_dt import DateTime

class SecaoFichaResponse(BaseModel):
    idFicha: int
    secao: int | None
    plano: str | None 
    risco : str | None
    tratativa : str | None
    resposta : str | None
    dataInicio : DateTime | None
    dataFim : DateTime | None