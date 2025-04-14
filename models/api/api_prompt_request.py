from pydantic import BaseModel

class PromptRequest(BaseModel):     #Classe de modelo para a nossa API
    prompt : str