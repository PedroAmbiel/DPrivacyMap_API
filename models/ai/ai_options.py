from dataclasses import dataclass

@dataclass
class Options:
    temperature: float
    max_tokens: int
    top_p:float
    top_k:float

    def to_dict(self):
        return {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_k":self.top_k,
            "top_p":self.top_p
        }