from pydantic import BaseModel
from constants import *

class AiBody():
    prompt : str
    model : str = AI_MODEL
    stream : bool = False