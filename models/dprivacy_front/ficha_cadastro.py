from pydantic import BaseModel

class FichaInventarioCadastro(BaseModel):     #Classe de modelo para a nossa API
        idFicha: int | None
        usuario: int
        area: str | None
        tipoOperacao: list[str] | None
        dadosColetados: list[str] | None
        finalidade: list[str] | None
        revisao: list[str] | None
        retencao: list[str] | None
        seguranca: str | None
        armazenamento: str | None
        exclusao: bool | None
        compartilhamentoTerceiros: bool | None
        transferenciaInternacional: bool | None