from pydantic import BaseModel
from pydantic_extra_types.pendulum_dt import DateTime

class FichaResponse(BaseModel):
    id: int | None
    area: str | None
    finalizado: bool | None
    dataCadastro: DateTime | None
    compartilhamentoTerceiros: bool | None
    transferenciaInternacional: bool | None
    exclusao: bool | None
    armazenamento: str | None
    tipoOperacao: list[str] | None
    dadosColetados: list[str] | None
    finalidade: list[str] | None
    revisao: str | None
    retencao: str | None
    seguranca: str | None