import requests
from fastapi import FastAPI
from models.api.api_prompt_request import PromptRequest
import psycopg
from constants import *
from models.ai.ai_request_body import *
import json
from cryptography.fernet import Fernet
import hashlib

api = FastAPI()
conn = psycopg.connect(BD_CONN)


def inserirNovoUsuario():
    with conn.cursor() as cur:
        password = 'admin'
        password_bytes = password.encode('utf-8')
        # Create SHA-256 hash
        hash_object = hashlib.sha256(password_bytes)
        print(hash_object)
        cur = conn.cursor()

        cur.execute(f"INSERT INTO \"DPrivacy\".usuarios (nome, senha, responsavel, fk_perfil, email) values (%s, %s, %s, %s, %s)", ('pedroam', hash_object.hexdigest(), 'PEDRO AMBIEL MASCHIETTO', 1, 'teste@teste.com'))

        conn.commit()

inserirNovoUsuario()
