from constants import *
from dataclasses import dataclass, field, asdict
import json
# from ollama import Options
from models.ai.ai_options import Options

@dataclass
class AiBody:
    prompt: str                                                                                                         # Prompt para gerar a resposta ao usuário
    system_prompt: str                                                                                                  # Contexto prévio utilizado para instruir o Modelo
    options: Options = field(default_factory=lambda: Options(temperature=0.2, max_tokens=1000, top_k=0.5, top_p=0.5))   # Configurações do modelo (temperature, etc.)
    messages: list = field(default_factory=list)                                                                        # Mensagens do histórico (user/system)
    model: str = AI_MODEL                                                                                               # Nome do modelo
    stream: bool = False                                                                                                # Se o retorno deve ser em stream

    def __post_init__(self):
        if not self.messages:
            self.messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": self.prompt}
            ]

    def to_dict(self):
        return {
            "prompt": self.prompt,
            "system_prompt": self.system_prompt,
            "options": self.options.to_dict(),
            "messages": self.messages,
            "model": self.model,
            "stream": self.stream
        }

    def to_json(self):
        return json.dumps(self.to_dict(self))