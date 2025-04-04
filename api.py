import requests
from fastapi import FastAPI
from promptrequest import PromptRequest
import psycopg
from constants import *
from airequestbody import *
import json

api = FastAPI()
conn = psycopg.connect(BD_CONN)


basicHeader = {
   'Content-Type': 'application/json'
}

url = 'http://localhost:11434/api/generate'


# data = {
#    'prompt': 'make a small song lyric',
#    'model': 'llama3.2:3b',
#    'stream': False
# }

# response = requests.post(url, headers=basicHeader, json=data)

# if response.status_code == 200:
#    print('Response:', response.json()['response'])
# else:
#    print('Error:', response.status_code, response.text)

# @api.post("/insert")
# def inserirNoBanco(body:Teste):
#   cur = conn.cursor()

#   cur.execute("INSERT INTO teste(teste) VALUES (%s)", 
#                 [body.teste])

#   conn.commit()

@api.post("/generate")
def gerarResposta(body:PromptRequest):
   url = 'http://localhost:11434/api/generate'
  
   data = {
      'prompt': body.prompt,
      'model': AI_MODEL,
      'stream': False
   }

   print(data)

   response = requests.post(url, headers=basicHeader, json= data)

   # if response.status_code == 200:
   print('Response:', response.json())
   # else:
   #    print('Error:', response.status_code, response.text)

   return response.json()['response']
  

