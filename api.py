import requests
from fastapi import FastAPI, status, HTTPException
from models.api.api_prompt_request import PromptRequest
import psycopg
from constants import *
from models.ai.ai_request_body import *
from models.api.user_login import *
from models.api.user_login_response import *
from models.dprivacy_front.ficha_cadastro import *
from models.dprivacy_front.fichas_redigindo_response import *
from models.dprivacy_front.ficha_inventario_response import *
import hashlib
from fastapi.middleware.cors import CORSMiddleware
from typing import List

api = FastAPI()
conn = psycopg.connect(BD_CONN)

origins = [
    "http://localhost:3000",
    "http://localhost:8080",
    "http://localhost",
]

api.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

basicHeader = {
   'Content-Type': 'application/json'
}

url = 'http://localhost:11434/api/generate'

def buscarIdsOperacoes(area):
   with conn.cursor() as cur:
      pattern = f"%{area}%"

      cur = conn.cursor()

      select = cur.execute(f"SELECT id FROM \"DPrivacy\".inventario_operacoes WHERE area ILIKE %s ", (pattern,)).fetchall()

      lista_ids = []
      for row in select:
         lista_ids.append(row[0])

   return lista_ids
   
def buscarIdsRiscosPorOperacao(listaIds):
   with conn.cursor() as cur:
      
      cur = conn.cursor()

      select = cur.execute(f" SELECT DISTINCT a.id FROM \"DPrivacy\".riscos a " +
                           " JOIN \"DPrivacy\".rl_inventario_riscos b ON b.fk_risco = a.id " + 
                           " WHERE b.fk_inventario = ANY(%s) ", (listaIds,)).fetchall()

      lista_ids = []
      for row in select:
         lista_ids.append(row[0])

   return lista_ids
   
def buscarPlanosComBaseRiscos(listaIds):
      with conn.cursor() as cur:
      
         cur = conn.cursor()

         select = cur.execute(f" SELECT DISTINCT a.detalhes FROM \"DPrivacy\".planos a " +
                              " JOIN \"DPrivacy\".rl_riscos_planos b ON b.fk_risco = a.id " + 
                              " WHERE b.fk_risco = ANY(%s) ", (listaIds,)).fetchall()

         lista_ids = []
         for row in select:
            lista_ids.append(row[0])

      return lista_ids


def criarBodyRequestAI(userPrompt, tratativas):
   sys_prompt = "Você é um analista de dados, focado em segurança LGPD, sempre responda com sentido de ordem, instruindo o usuário a seguir suas sugestões. Você nunca irá sugerir a criação de sistemas de informação ao usuário, somente soluções habeis de realizar de forma manual"

   data = AiBody(prompt=userPrompt, system_prompt=sys_prompt)

   return data

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



#--------------------------EXEMPLO DE SELECT USANDO PSYCOPG
# with conn.cursor() as cur:
#         search_term = "example"
#         pattern = f"%{'Financeiro'}%"

# cur = conn.cursor()

# select = cur.execute(f"SELECT id FROM \"DPrivacy\".inventario_operacoes WHERE area ILIKE %s ", (pattern,)).fetchall()

# print(select)


@api.post("/login")
def login(body:UserLogin):
   #Criptografando a senha
   password = body.senha
   password_bytes = password.encode('utf-8')
   # Create SHA-256 hash
   senha_hashed = hashlib.sha256(password_bytes)


   with conn.cursor() as cur:
      
      cur = conn.cursor()

      select = cur.execute(f" SELECT u.id, u.nome, u.email, u.responsavel, u.senha, u.fk_perfil FROM \"DPrivacy\".usuarios u " +
                           " WHERE u.email = %s ", [body.email]).fetchone()


      # try:
      if(select == None):
         raise HTTPException(status_code=400, detail="Usuário não encontrado")
      
      print('Senha Banco: ', str(select[4]), "senha post: ", senha_hashed.hexdigest())

      if(str(select[4]) != senha_hashed.hexdigest()):
         raise HTTPException(status_code=400, detail="Senha inválida")
      
      response = UserLoginResponse(id=select[0], nome=select[1], email=select[2], responsavel=select[3], perfil=select[5])
      
      # except HTTPException as erro:
         # response = {"code": erro.status_code, "detalhe": erro.detail}
      

   return response
            



@api.post("/generate")
def gerarResposta(body:PromptRequest):

   area = 'Financeiro'
   tipo_operacao = ''
   dados_coletados = ''
   finalidade = ''
   revisao = ''

   
   user_prompt = body.prompt

   lista_IDS = buscarIdsOperacoes(area)
   listariscos = buscarIdsRiscosPorOperacao(lista_IDS)
   tratativas = buscarPlanosComBaseRiscos(listariscos)

   for a in tratativas:
      print(a, '\n')

   user_prompt += f"<tratativas>{str(tratativas)} </tratativas> \nA partir das tratativas informadas, para *CADA TRATATIVA DIFERENTE*, informe o nome da tratativa. Em seguida, descreva como deve ser o protocolo para assegurar a integridade do dado. Sua resposta deve SEMPRE ter o seguinte padrão: <title>Tratativa com base nos dados: {area} </title> \n <body><tratativa><significado></significado><sugestões></sugestões></tratativa></body> --END dentro da tag body, descreva somente suas sugestões COM BASE NAS TRATATIVAS. Não reescreva as tratativas novamente. As suas sugestões devem ser criada a partir das tratativas + suas próprias sugestões. Sempre seja o mais claro possível e explique como cada sugestão deve ser realizada."

   data = criarBodyRequestAI(user_prompt, tratativas)

   # print(data.to_dict())

   response = requests.post(url, headers=basicHeader, json= data.to_dict())

   # if response.status_code == 200:
   print('Response:', response.json())
   # else:
   #    print('Error:', response.status_code, response.text)

   return response.json()['response']
   # return ''

def salvarAtualizarFichaInventario(isFinalizada:bool, body:FichaInventarioCadastro):
   insert = "INSERT INTO \"DPrivacy\".ficha_inventario ( "

   if(body.area):
      insert += " area, "

   if(body.armazenamento):
      insert += " armazenamento, "

   if(body.compartilhamentoTerceiros != None):
      insert += " compartilhamento_terceiros, "

   if(body.transferenciaInternacional != None):
      insert += " transferencia_internacional, "

   if(body.exclusao != None):
      insert += " exclusao, "

   if(isFinalizada):
      insert += " finalizado, "

   insert += " fk_usuario "

   insert += " ) VALUES ( "

   if(body.area):
      insert += " %s, "

   if(body.armazenamento):
      insert += " %s, "

   if(body.compartilhamentoTerceiros != None):
      insert += " %s, "

   if(body.transferenciaInternacional != None):
      insert += " %s, "

   if(body.exclusao != None):
      insert += " %s, "

   if(isFinalizada):
      insert += " %s, "
   
   insert += " %s "




   insert += " ) "
   
   with conn.cursor() as cur:

      params = []

      if(body.area):
         params.append(body.area)

      if(body.armazenamento):
         params.append(body.armazenamento)

      if(body.compartilhamentoTerceiros != None):
         params.append(body.compartilhamentoTerceiros)

      if(body.transferenciaInternacional != None):
         params.append(body.transferenciaInternacional)

      if(body.exclusao != None):
         params.append(body.exclusao)
         
      params.append(body.usuario)

      if(isFinalizada):
         params.append(True)

      cur = conn.cursor()

      cur.execute(insert, params)

      conn.commit()

      return True

  
@api.post('/finalizar_ficha')
def finalizarFicha(body:FichaInventarioCadastro):

   salvarAtualizarFichaInventario(True, body)

   return True


@api.put('/salvar_ficha')
def salvarFicha(body:FichaInventarioCadastro):

   salvarAtualizarFichaInventario(False, body)

   return True

@api.get('/listar_planos_redigindo/{id_usuario}')
def listarPlanosRedigindo(id_usuario):
   with conn.cursor() as cur:
      cur = conn.cursor()

      select = cur.execute(f" SELECT fi.id, fi.area, fi.finalizado, fi.data_cadastro FROM \"DPrivacy\".ficha_inventario fi " +
                           " WHERE fi.finalizado IS FALSE AND fi.fk_usuario = %s ", [id_usuario]).fetchall()
      

      response : List[FichasRedigindoResponse] = []

      for row in select:
         response.append(FichasRedigindoResponse(id=row[0], area=row[1], finalizado=row[2], dataCadastro=row[3]))

      print(len(response))
      if(len(response) != 0):
         return response
      else:
         return 'E'
      
@api.get('/buscar_ficha/{id_ficha}')
def listarPlanosRedigindo(id_ficha):
   with conn.cursor() as cur:
      cur = conn.cursor()

      select = cur.execute(f" SELECT fi.id, fi.area, fi.finalizado, fi.data_cadastro, fi.armazenamento, fi.exclusao, fi.compartilhamento_terceiros, fi.transferencia_internacional FROM \"DPrivacy\".ficha_inventario fi " +
                           " WHERE fi.finalizado IS FALSE AND fi.id = %s ", [id_ficha]).fetchone()
      

      
      response = FichaResponse(id=select[0], area=select[1], finalizado=select[2], dataCadastro=select[3], armazenamento=select[4], exclusao=select[5], compartilhamentoTerceiros=select[6], transferenciaInternacional=select[7])


      return response

         
