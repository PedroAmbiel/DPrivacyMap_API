from pydantic import BaseModel
from pydantic_extra_types.pendulum_dt import DateTime

class FichaResponse(BaseModel):
    id: int
    area: str | None
    finalizado: bool
    dataCadastro: DateTime
    compartilhamentoTerceiros: bool | None
    transferenciaInternacional: bool | None
    exclusao: bool | None
    armazenamento: str | None