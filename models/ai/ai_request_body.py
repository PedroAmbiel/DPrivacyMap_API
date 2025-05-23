from constants import *
from dataclasses import dataclass, field, asdict
import json
from models.ai.ai_options import Options

@dataclass
class AiBody:
    prompt: str                                                                                                         # Prompt para gerar a resposta ao usuário
    system: str                                                                                                         # Contexto prévio utilizado para instruir o Modelo
    options: Options = field(default_factory=lambda: Options(temperature=0.6, top_k=20, top_p=0.9))                     # Configurações do modelo (temperature, etc.)
    messages: list = field(default_factory=list)                                                                        # Mensagens do histórico (user/system)
    model: str = AI_MODEL                                                                                               # Nome do modelo
    stream: bool = False                                                                                                # Se o retorno deve ser em stream

    def __post_init__(self):
        if not self.messages:
            self.messages = [
                {"role": "system", "content": self.system},
                {"role": "user", "content": self.prompt}
            ]

    def to_dict(self):
        return {
            "prompt": self.prompt,
            "system": self.system,
            "options": self.options.to_dict(),
            "messages": self.messages,
            "model": self.model,
            "stream": self.stream
        }

    def to_json(self):
        return json.dumps(self.to_dict(self))