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
from models.dprivacy_front.secao_ficha_request import *
from models.dprivacy_front.ficha_finalizada_response import *
from models.dprivacy_front.secao_ficha_response import *
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

def criarBodyRequestAI(userPrompt, tratativa):
   # sys_prompt = "Você é um analista de dados, focado em segurança LGPD, sempre responda com sentido de ordem, instruindo o usuário a seguir suas sugestões. Você nunca irá sugerir a criação de sistemas de informação ao usuário, somente soluções habeis de realizar de forma manual"

   # sys_prompt = f"Responda como se fosse um profissional do meio jurídico, sempre seja claro e preciso na resposta. Sempre formule respostas curtas. Utilize o contexto para complementar a resposta <context>{tratativa}</context>"

   sys_prompt = f"""
                    Atue como um especialista jurídico em proteção de dados e segurança da informação, com conhecimento aprofundado na LGPD (Lei nº 13.709/2018). Elabore respostas com linguagem objetiva, imperativa e técnica, como se estivesse redigindo uma diretriz corporativa ou instrução normativa. Nunca utilize elementos de linguagem direta ao usuário como "você", "sua empresa", ou "deve-se fazer".

                    As respostas devem apresentar instruções claras, diretas e aplicáveis à área mencionada, com base nos princípios da LGPD. Use o contexto abaixo para embasar a redação da diretriz:

                    <context>{tratativa}</context>
                 """

   data = AiBody(prompt=userPrompt, system_prompt=sys_prompt)

   return data

def replacer(s, newstring, index, nofail=False):
    if not nofail and index not in range(len(s)):
        raise ValueError("index não existe na String")

    if index < 0:
        return newstring + s
    if index > len(s):
        return s + newstring

    return s[:index] + newstring + s[index + 1:]



            

@api.post('/gerar')
def gerarResposta(idFicha:int):
   with conn.cursor() as cur:
      
      cur = conn.cursor()

      select = cur.execute(f" SELECT s.secao, s.plano, s.risco, s.tratativa, fi.area, s.id, p.tempo_dias FROM \"DPrivacy\".secao_plano_ficha s " +
                           " JOIN \"DPrivacy\".ficha_inventario fi ON fi.id = s.fk_ficha "
                           " JOIN \"DPrivacy\".planos p ON p.titulo = s.plano " +
                           " WHERE s.fk_ficha = %s ", (idFicha, )).fetchall()

      for item in select:

         update_secao_data = "INSERT INTO \"DPrivacy\".secao_plano_ficha_resposta (data_inicio, fk_secao_plano_ficha) VALUES ( now(), %s ) RETURNING id"

         cur.execute(update_secao_data, (item[5], ))

         id_inserido = cur.fetchone()[0]
         
         conn.commit()

         # user_prompt += f"<tratativas>{str(tratativas)} </tratativas> \nA partir das tratativas informadas, para *CADA TRATATIVA DIFERENTE*, informe o nome da tratativa. Em seguida, descreva como deve ser o protocolo para assegurar a integridade do dado. Sua resposta deve SEMPRE ter o seguinte padrão: <title>Tratativa com base nos dados: {area} </title> \n <body><tratativa><significado></significado><sugestões></sugestões></tratativa></body> --END dentro da tag body, descreva somente suas sugestões COM BASE NAS TRATATIVAS. Não reescreva as tratativas novamente. As suas sugestões devem ser criada a partir das tratativas + suas próprias sugestões. Sempre seja o mais claro possível e explique como cada sugestão deve ser realizada."
         # user_prompt = f"Trabalho na área de { item[4] } na minha empresa. Trabalho com informações sensíveis de meus clientes, e acabei encontrando um possível risco para \
         # para minha empresa. Esse risco é {item[2]} e já tenho o plano {item[1]} para solucinar esse risco. Como devo prosseguir, quais são os passos para tratar esse risco? \
         # <important>Sua resposta não deve ser montada com elementos html. Começe sua resposta explicando o plano e em seguida montando os passos</important>"

         user_prompt = f"""Área responsável: {item[4]}.  
                           Risco identificado: {item[2]}.  
                           Plano de mitigação em andamento: "{item[1]}".
                           Tempo entre execução desse plano: "{item[6]}".

                           Com base nessas informações, elabore uma diretriz objetiva e impessoal, descrevendo como proceder na tratativa desse risco. A linguagem deve ser imperativa, com tom normativo e institucional. A resposta não deve ser dirigida a uma pessoa ou conter instruções pessoais. Inicie descrevendo a abordagem prevista no plano e, em seguida, a sequência de ações recomendadas, sem utilizar elementos HTML ou estrutura de lista. Use texto corrido, com no máximo quebras de linha simples para separação de trechos.

                        """

         data = criarBodyRequestAI(user_prompt, item[3])

         response = requests.post(url, headers=basicHeader, json= data.to_dict())

         print('Response:', response.json())

         update_secao_resposta = "UPDATE \"DPrivacy\".secao_plano_ficha_resposta SET resposta = %s, data_fim = now() WHERE id = %s"

         cur.execute(update_secao_resposta, (response.json()['response'], id_inserido, ))

         conn.commit()

   # return response.json()['response']


@api.post("/login")
def login(body:UserLogin):
   #Criptografando a senha
   password = body.senha
   password_bytes = password.encode('utf-8')
   # SHA-256 hash
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
      
   return response



@api.put('/finalizar_ficha')
def finalizarFichaInventario(body:FichaInventarioCadastro):
   id_inserido = 0
   if(body.idFicha):
      update = 'UPDATE \"DPrivacy\".ficha_inventario SET '

      if(body.area):
         update += " area = %s, "

      if(body.armazenamento):
         update += " armazenamento = %s, "

      if(body.compartilhamentoTerceiros != None):
         update += " compartilhamento_terceiros = %s, "

      if(body.transferenciaInternacional != None):
         update += " transferencia_internacional = %s, "

      if(body.exclusao != None):
         update += " exclusao = %s, "
      
      if(body.seguranca != None):
         update += " seguranca = %s, "

      update += " finalizado = true "

      # if(update[len(update)-2] == ','):
      #    print(update[len(update)-2])
      #    update = replacer(update, '', len(update)-2)
         # update[len(update)-2].replace('')
         # print(update)

      update += f' WHERE id = {body.idFicha} '

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

         if(body.seguranca != None):
            params.append(body.seguranca)
            
         cur = conn.cursor()

         cur.execute(update, params)


         print(body)
         ##----------------- Inserts nas tabelas de rl_dados -----------------##
         if(body.dadosColetados):
            print("Entrou RL_DADOS")
            delete_dados = "DELETE FROM \"DPrivacy\".rl_ficha_dados_coletados WHERE fk_ficha = %s "

            cur.execute(delete_dados, (body.idFicha,))

            insert_dados = "INSERT INTO \"DPrivacy\".rl_ficha_dados_coletados (fk_ficha, dado_coletado) VALUES (%s, %s) "

            for dado in body.dadosColetados:
               cur.execute(insert_dados, (body.idFicha, dado))

         ##----------------- Inserts nas tabelas de rl_finalidade -----------------##
         if(body.finalidade):
            print("Entrou RL_FINALIDADE")
            delete_dados = "DELETE FROM \"DPrivacy\".rl_ficha_finalidade WHERE fk_ficha = %s "

            cur.execute(delete_dados, (body.idFicha,))

            insert_dados = "INSERT INTO \"DPrivacy\".rl_ficha_finalidade (fk_ficha, finalidade) VALUES (%s, %s) "

            for finalidade in body.finalidade:
               cur.execute(insert_dados, (body.idFicha, finalidade))


         ##----------------- Inserts nas tabelas de rl_retencao -----------------##
         if(body.retencao):
            print("Entrou RL_RETENCAO")
            delete_dados = "DELETE FROM \"DPrivacy\".rl_ficha_retencao WHERE fk_ficha = %s "

            cur.execute(delete_dados, (body.idFicha,))

            insert_dados = "INSERT INTO \"DPrivacy\".rl_ficha_retencao (fk_ficha, retencao) VALUES (%s, %s) "

            for retencao in body.retencao:
               cur.execute(insert_dados, (body.idFicha, retencao))


         ##----------------- Inserts nas tabelas de rl_revisao -----------------##
         if(body.revisao):
            print("Entrou RL_REVISAO")
            delete_dados = "DELETE FROM \"DPrivacy\".rl_ficha_revisao WHERE fk_ficha = %s "

            cur.execute(delete_dados, (body.idFicha,))

            insert_dados = "INSERT INTO \"DPrivacy\".rl_ficha_revisao (fk_ficha, revisao) VALUES (%s, %s) "

            for revisao in body.revisao:
               cur.execute(insert_dados, (body.idFicha, revisao))

         ##----------------- Inserts nas tabelas de rl_seguranca -----------------##
         # if(body.seguranca):
         #    print("Entrou RL_SEGURANCA")
         #    delete_dados = "DELETE FROM \"DPrivacy\".rl_ficha_seguranca WHERE fk_ficha = %s "

         #    cur.execute(delete_dados, (body.idFicha,))

         #    insert_dados = "INSERT INTO \"DPrivacy\".rl_ficha_seguranca (fk_ficha, seguranca) VALUES (%s, %s) "

         #    for seguranca in body.seguranca:
         #       cur.execute(insert_dados, (body.idFicha, seguranca))
         

         ##----------------- Inserts nas tabelas de rl_tipo_operacao -----------------##
         if(body.tipoOperacao):
            print("Entrou RL_TIPO_OPERACAO")
            delete_dados = "DELETE FROM \"DPrivacy\".rl_ficha_tipo_operacao WHERE fk_ficha = %s "

            cur.execute(delete_dados, (body.idFicha,))

            insert_dados = "INSERT INTO \"DPrivacy\".rl_ficha_tipo_operacao (fk_ficha, tipo_operacao) VALUES (%s, %s) "

            for tipoOperacao in body.tipoOperacao:
               cur.execute(insert_dados, (body.idFicha, tipoOperacao))

         conn.commit()

   else: # Caso seja um salvamento na primeira vez que abre a ficha

      insert = 'INSERT INTO \"DPrivacy\".ficha_inventario ( '

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

      if(body.seguranca != None):
         insert += " seguranca, "

      insert += " fk_usuario, finalizado "

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

      if(body.seguranca != None):
         insert += " %s, "
      
      insert += " %s, %s "


      insert += " ) RETURNING id"

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

         if(body.seguranca != None):
            params.append(body.seguranca)
            
         params.append(body.usuario)
         params.append(True)

         cur = conn.cursor()

         cur.execute(insert, params)

         id_inserido = cur.fetchone()[0]

         ##----------------- Inserts nas tabelas de rl_dados -----------------##
         if(body.dadosColetados):
            print("Entrou RL_DADOS")
            insert_dados = "INSERT INTO \"DPrivacy\".rl_ficha_dados_coletados (fk_ficha, dado_coletado) VALUES (%s, %s) "

            for dado in body.dadosColetados:
               cur.execute(insert_dados, (id_inserido, dado))

         ##----------------- Inserts nas tabelas de rl_finalidade -----------------##
         if(body.finalidade):
            print("Entrou RL_FINALIDADE")
            insert_dados = "INSERT INTO \"DPrivacy\".rl_ficha_finalidade (fk_ficha, finalidade) VALUES (%s, %s) "

            for finalidade in body.finalidade:
               cur.execute(insert_dados, (id_inserido, finalidade))


         ##----------------- Inserts nas tabelas de rl_retencao -----------------##
         if(body.retencao):
            print("Entrou RL_RETENCAO")
            insert_dados = "INSERT INTO \"DPrivacy\".rl_ficha_retencao (fk_ficha, retencao) VALUES (%s, %s) "

            for retencao in body.retencao:
               cur.execute(insert_dados, (id_inserido, retencao))


         ##----------------- Inserts nas tabelas de rl_revisao -----------------##
         if(body.revisao):
            print("Entrou RL_REVISAO")
            insert_dados = "INSERT INTO \"DPrivacy\".rl_ficha_revisao (fk_ficha, revisao) VALUES (%s, %s) "

            for revisao in body.revisao:
               cur.execute(insert_dados, (id_inserido, revisao))

         ##----------------- Inserts nas tabelas de rl_seguranca -----------------##
         # if(body.seguranca):
         #    print("Entrou RL_SEGURANCA")
         #    insert_dados = "INSERT INTO \"DPrivacy\".rl_ficha_seguranca (fk_ficha, seguranca) VALUES (%s, %s) "

         #    for seguranca in body.seguranca:
         #       cur.execute(insert_dados, (id_inserido, seguranca))
         

         ##----------------- Inserts nas tabelas de rl_tipo_operacao -----------------##
         if(body.tipoOperacao):
            print("Entrou RL_TIPO_OPERACAO")
            insert_dados = "INSERT INTO \"DPrivacy\".rl_ficha_tipo_operacao (fk_ficha, tipo_operacao) VALUES (%s, %s) "

            for tipoOperacao in body.tipoOperacao:
               cur.execute(insert_dados, (id_inserido, tipoOperacao))

         print("ACABOU")

         conn.commit()

   if(id_inserido == 0):
      response = { "idFicha" : body.idFicha }
   else:
      response = { "idFicha" : id_inserido }


   return json.dumps(response)


@api.put('/atualizar_ficha')
def atualizarFicha(body:FichaInventarioCadastro):
   print(body.idFicha)
   if(body.idFicha):
      update = 'UPDATE \"DPrivacy\".ficha_inventario SET '

      if(body.area):
         update += " area = %s, "

      if(body.armazenamento):
         update += " armazenamento = %s, "

      if(body.compartilhamentoTerceiros != None):
         update += " compartilhamento_terceiros = %s, "

      if(body.transferenciaInternacional != None):
         update += " transferencia_internacional = %s, "

      if(body.exclusao != None):
         update += " exclusao = %s, "

      if(body.seguranca != None):
         update += " seguranca = %s, "

      if(update[len(update)-2] == ','):
         print(update[len(update)-2])
         update = replacer(update, '', len(update)-2)
         # update[len(update)-2].replace('')
         # print(update)

      update += f' WHERE id = {body.idFicha} '

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

         if(body.seguranca != None):
            params.append(body.seguranca)
            
         cur = conn.cursor()

         cur.execute(update, params)


         print(body)
         ##----------------- Inserts nas tabelas de rl_dados -----------------##
         if(body.dadosColetados):
            print("Entrou RL_DADOS")
            delete_dados = "DELETE FROM \"DPrivacy\".rl_ficha_dados_coletados WHERE fk_ficha = %s "

            cur.execute(delete_dados, (body.idFicha,))

            insert_dados = "INSERT INTO \"DPrivacy\".rl_ficha_dados_coletados (fk_ficha, dado_coletado) VALUES (%s, %s) "

            for dado in body.dadosColetados:
               cur.execute(insert_dados, (body.idFicha, dado))

         ##----------------- Inserts nas tabelas de rl_finalidade -----------------##
         if(body.finalidade):
            print("Entrou RL_FINALIDADE")
            delete_dados = "DELETE FROM \"DPrivacy\".rl_ficha_finalidade WHERE fk_ficha = %s "

            cur.execute(delete_dados, (body.idFicha,))

            insert_dados = "INSERT INTO \"DPrivacy\".rl_ficha_finalidade (fk_ficha, finalidade) VALUES (%s, %s) "

            for finalidade in body.finalidade:
               cur.execute(insert_dados, (body.idFicha, finalidade))


         ##----------------- Inserts nas tabelas de rl_retencao -----------------##
         if(body.retencao):
            print("Entrou RL_RETENCAO")
            delete_dados = "DELETE FROM \"DPrivacy\".rl_ficha_retencao WHERE fk_ficha = %s "

            cur.execute(delete_dados, (body.idFicha,))

            insert_dados = "INSERT INTO \"DPrivacy\".rl_ficha_retencao (fk_ficha, retencao) VALUES (%s, %s) "

            for retencao in body.retencao:
               cur.execute(insert_dados, (body.idFicha, retencao))


         ##----------------- Inserts nas tabelas de rl_revisao -----------------##
         if(body.revisao):
            print("Entrou RL_REVISAO")
            delete_dados = "DELETE FROM \"DPrivacy\".rl_ficha_revisao WHERE fk_ficha = %s "

            cur.execute(delete_dados, (body.idFicha,))

            insert_dados = "INSERT INTO \"DPrivacy\".rl_ficha_revisao (fk_ficha, revisao) VALUES (%s, %s) "

            for revisao in body.revisao:
               cur.execute(insert_dados, (body.idFicha, revisao))

         ##----------------- Inserts nas tabelas de rl_seguranca -----------------##
         # if(body.seguranca):
         #    print("Entrou RL_SEGURANCA")
         #    delete_dados = "DELETE FROM \"DPrivacy\".rl_ficha_seguranca WHERE fk_ficha = %s "

         #    cur.execute(delete_dados, (body.idFicha,))

         #    insert_dados = "INSERT INTO \"DPrivacy\".rl_ficha_seguranca (fk_ficha, seguranca) VALUES (%s, %s) "

         #    for seguranca in body.seguranca:
         #       cur.execute(insert_dados, (body.idFicha, seguranca))
         

         ##----------------- Inserts nas tabelas de rl_tipo_operacao -----------------##
         if(body.tipoOperacao):
            print("Entrou RL_TIPO_OPERACAO")
            delete_dados = "DELETE FROM \"DPrivacy\".rl_ficha_tipo_operacao WHERE fk_ficha = %s "

            cur.execute(delete_dados, (body.idFicha,))

            insert_dados = "INSERT INTO \"DPrivacy\".rl_ficha_tipo_operacao (fk_ficha, tipo_operacao) VALUES (%s, %s) "

            for tipoOperacao in body.tipoOperacao:
               cur.execute(insert_dados, (body.idFicha, tipoOperacao))
         

         conn.commit()

   else:

      insert = 'INSERT INTO \"DPrivacy\".ficha_inventario ( '

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
      
      if(body.seguranca != None):
         insert += " seguranca, "

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

      if(body.seguranca != None):
         insert += " %s, "
      
      insert += " %s "


      insert += " ) RETURNING id"

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

         if(body.seguranca != None):
            params.append(body.seguranca)
            
         params.append(body.usuario)

         cur = conn.cursor()

         cur.execute(insert, params)

         id_inserido = cur.fetchone()[0]

         ##----------------- Inserts nas tabelas de rl_dados -----------------##
         if(body.dadosColetados):
            print("Entrou RL_DADOS")
            insert_dados = "INSERT INTO \"DPrivacy\".rl_ficha_dados_coletados (fk_ficha, dado_coletado) VALUES (%s, %s) "

            for dado in body.dadosColetados:
               cur.execute(insert_dados, (id_inserido, dado))

         ##----------------- Inserts nas tabelas de rl_finalidade -----------------##
         if(body.finalidade):
            print("Entrou RL_FINALIDADE")
            insert_dados = "INSERT INTO \"DPrivacy\".rl_ficha_finalidade (fk_ficha, finalidade) VALUES (%s, %s) "

            for finalidade in body.finalidade:
               cur.execute(insert_dados, (id_inserido, finalidade))


         ##----------------- Inserts nas tabelas de rl_retencao -----------------##
         if(body.retencao):
            print("Entrou RL_RETENCAO")
            insert_dados = "INSERT INTO \"DPrivacy\".rl_ficha_retencao (fk_ficha, retencao) VALUES (%s, %s) "

            for retencao in body.retencao:
               cur.execute(insert_dados, (id_inserido, retencao))


         ##----------------- Inserts nas tabelas de rl_revisao -----------------##
         if(body.revisao):
            print("Entrou RL_REVISAO")
            insert_dados = "INSERT INTO \"DPrivacy\".rl_ficha_revisao (fk_ficha, revisao) VALUES (%s, %s) "

            for revisao in body.revisao:
               cur.execute(insert_dados, (id_inserido, revisao))

         ##----------------- Inserts nas tabelas de rl_seguranca -----------------##
         # if(body.seguranca):
         #    print("Entrou RL_SEGURANCA")
         #    insert_dados = "INSERT INTO \"DPrivacy\".rl_ficha_seguranca (fk_ficha, seguranca) VALUES (%s, %s) "

         #    for seguranca in body.seguranca:
         #       cur.execute(insert_dados, (id_inserido, seguranca))
         

         ##----------------- Inserts nas tabelas de rl_tipo_operacao -----------------##
         if(body.tipoOperacao):
            print("Entrou RL_TIPO_OPERACAO")
            insert_dados = "INSERT INTO \"DPrivacy\".rl_ficha_tipo_operacao (fk_ficha, tipo_operacao) VALUES (%s, %s) "

            for tipoOperacao in body.tipoOperacao:
               cur.execute(insert_dados, (id_inserido, tipoOperacao))

         print("ACABOU")

         conn.commit()
      

   return True


@api.get('/listar_planos_redigindo/{id_usuario}')
def listarPlanosRedigindo(id_usuario):
   with conn.cursor() as cur:
      cur = conn.cursor()

      select = cur.execute(f" SELECT fi.id, fi.area, fi.finalizado, fi.data_cadastro FROM \"DPrivacy\".ficha_inventario fi " +
                           " WHERE fi.fk_usuario = %s ORDER BY fi.finalizado, fi.data_cadastro DESC", [id_usuario]).fetchall()
      

      response : List[FichasRedigindoResponse] = []

      for row in select:
         response.append(FichasRedigindoResponse(id=row[0], area=row[1], finalizado=row[2], dataCadastro=row[3]))

      # print(len(response))
      if(len(response) != 0):
         return response
      else:
         return 'E'
      
@api.get('/buscar_ficha/{id_ficha}')
def listarPlanosRedigindo(id_ficha):
   with conn.cursor() as cur:
      cur = conn.cursor()

      select = cur.execute(f" SELECT fi.id, fi.area, fi.finalizado, fi.data_cadastro, fi.armazenamento, fi.exclusao, fi.compartilhamento_terceiros, fi.transferencia_internacional, seguranca FROM \"DPrivacy\".ficha_inventario fi " +
                           " WHERE fi.id = %s ", [id_ficha]).fetchone()
      
      listaOperacoes = []
      # listaSeguranca = []
      listaRevisao = []
      listaRetencao = []
      listaFinalidade = []
      listaDadoColetado = []
      
      selectdado = cur.execute(f" SELECT dado_coletado FROM \"DPrivacy\".rl_ficha_dados_coletados " +
                           " WHERE fk_ficha = %s ", [id_ficha]).fetchall()
      for row in selectdado:
         listaDadoColetado.append(row[0])

      
      selectfinalidade = cur.execute(f" SELECT finalidade FROM \"DPrivacy\".rl_ficha_finalidade " +
                           " WHERE fk_ficha = %s ", [id_ficha]).fetchall()
      for row in selectfinalidade:
         listaFinalidade.append(row[0])
         
      
      selectretencao = cur.execute(f" SELECT retencao FROM \"DPrivacy\".rl_ficha_retencao " +
                           " WHERE fk_ficha = %s ", [id_ficha]).fetchall()
      for row in selectretencao:
         listaRetencao.append(row[0])
      


      selectrevisao = cur.execute(f" SELECT revisao FROM \"DPrivacy\".rl_ficha_revisao " +
                           " WHERE fk_ficha = %s ", [id_ficha]).fetchall()
      for row in selectrevisao:
         listaRevisao.append(row[0])
      


      # selectseguranca = cur.execute(f" SELECT seguranca FROM \"DPrivacy\".rl_ficha_seguranca " +
      #                      " WHERE fk_ficha = %s ", [id_ficha]).fetchall()
      # for row in selectseguranca:
      #    listaSeguranca.append(row[0])
      


      selecttipoperacao = cur.execute(f" SELECT tipo_operacao FROM \"DPrivacy\".rl_ficha_tipo_operacao " +
                           " WHERE fk_ficha = %s ", [id_ficha]).fetchall()
      for row in selecttipoperacao:
         listaOperacoes.append(row[0])
      

      if(select != None):
         response = FichaResponse(id=select[0], 
                                 area=select[1], 
                                 finalizado=select[2], 
                                 dataCadastro=select[3], 
                                 armazenamento=select[4], 
                                 exclusao=select[5], 
                                 compartilhamentoTerceiros=select[6], 
                                 transferenciaInternacional=select[7],
                                 tipoOperacao=listaOperacoes,
                                 dadosColetados=listaDadoColetado,
                                 finalidade=listaFinalidade,
                                 revisao=listaRevisao,
                                 retencao=listaRetencao,
                                 seguranca=select[8])
         
      else:
         response = False


      return response
   


@api.post('/criar_secoes')
def criarSecoesFicha(body:SecaoFichaRequest):


   select_dados_coletados = f"SELECT dado_coletado FROM \"DPrivacy\".rl_ficha_dados_coletados WHERE fk_ficha = {body.idFicha} "
   select_finalidade = f"SELECT finalidade FROM \"DPrivacy\".rl_ficha_finalidade WHERE fk_ficha = {body.idFicha} "
   select_retencao = f"SELECT retencao FROM \"DPrivacy\".rl_ficha_retencao WHERE fk_ficha = {body.idFicha} "
   select_revisao = f"SELECT revisao FROM \"DPrivacy\".rl_ficha_revisao WHERE fk_ficha = {body.idFicha} "
   select_tipo_operacao = f"SELECT tipo_operacao FROM \"DPrivacy\".rl_ficha_tipo_operacao WHERE fk_ficha = {body.idFicha} "

   listDadosColetados = []
   listFinalidade = []
   listRetencao = []
   listRevisao = []
   listTipoOperacao = []

   with conn.cursor() as cur:
      cur = conn.cursor()


      #####-----------------PREENCHENDO AS LISTAS-------------------####
      #DADOS COLETADOS#
      select = cur.execute(select_dados_coletados).fetchall()

      for item in select:
         listDadosColetados.append(item[0])

      #FINALIDADE#
      select = cur.execute(select_finalidade).fetchall()

      for item in select:
         listFinalidade.append(item[0])

      #RETENÇÃO#
      select = cur.execute(select_retencao).fetchall()

      for item in select:
         listRetencao.append(item[0])

      #REVISÃO#
      select = cur.execute(select_revisao).fetchall()

      for item in select:
         listRevisao.append(item[0])

      #TIPO OPERAÇÃO#
      select = cur.execute(select_tipo_operacao).fetchall()

      for item in select:
         listTipoOperacao.append(item[0])

      #####---------------------------------------------------------------####


      #####-----------------PREENCHENDO A FICHA-------------------####
      select_ficha = f"SELECT id, armazenamento, exclusao, compartilhamento_terceiros, transferencia_internacional, area, seguranca FROM \"DPrivacy\".ficha_inventario WHERE id = {body.idFicha} "
      
      select = cur.execute(select_ficha).fetchone()
      print(select)
      ficha = FichaResponse(id=select[0], armazenamento=select[1], exclusao=select[2], compartilhamentoTerceiros=select[3], transferenciaInternacional=select[4], 
                            area=select[5], seguranca=select[6], dadosColetados=None, dataCadastro=None, finalidade=None, finalizado=None, retencao=None,
                            revisao=None, tipoOperacao=None)
      #####--------------------------------------------------------####
      



      #####-----------------CRIANDO SEÇÕES-------------------####
      select_plano_secao = """
            SELECT DISTINCT r.riscos_dados_pessoais, pl.titulo, pl.detalhes, count(pl.id) as qtd FROM \"DPrivacy\".planos pl
            JOIN \"DPrivacy\".rl_riscos_planos rp ON rp.fk_plano = pl.id
            JOIN \"DPrivacy\".rl_inventario_riscos ir ON ir.fk_risco = rp.fk_risco
            JOIN \"DPrivacy\".riscos r ON r.id = ir.fk_risco
            JOIN \"DPrivacy\".inventario_operacoes io ON io.id = ir.fk_inventario
            WHERE io.area = %s
            AND io.tipo_operacao = ANY(%s) 
            AND (	
                  io.dados_coletados = ANY(%s)
                  OR  io.finalidade = ANY(%s) 
                  OR io.revisao = ANY(%s)
                  OR io.retencao = ANY(%s)
                  OR io.seguranca = %s 
                  OR io.armazenamento = %s
                  OR io.exclusao = %s
                  OR io.compartilhamento_terceiros = %s
                  OR io.transferencia_internacional = %s
               )
            GROUP BY pl.id, r.riscos_dados_pessoais
            order by qtd desc
      """

      params = []

      params.append(ficha.area)
      params.append(listTipoOperacao)
      params.append(listDadosColetados)
      params.append(listFinalidade)
      params.append(listRevisao)
      params.append(listRetencao)
      params.append(ficha.seguranca)
      params.append(ficha.armazenamento)
      params.append(ficha.exclusao)
      params.append(ficha.compartilhamentoTerceiros)
      params.append(ficha.transferenciaInternacional)

      select = cur.execute(select_plano_secao, params).fetchall()


      insert_secao = "INSERT INTO \"DPrivacy\".secao_plano_ficha(secao, fk_ficha, plano, risco, tratativa) VALUES (%s, %s, %s, %s, %s)"

      secao = 1
      for item in select:
         cur.execute(insert_secao, (secao, ficha.id, item[1], item[0], item[2], ))
         secao += 1

      conn.commit()

   gerarResposta(ficha.id)

   return None


@api.get('/buscar_planos_concluidos/{id_usuario}')
def buscarPlanosConcluidos(id_usuario):
   with conn.cursor() as cur:
      cur = conn.cursor()

      selectPlanoFicha = """SELECT fi.id, fi.area, fi.finalizado, fi.data_cadastro, count(sfp.id) FROM \"DPrivacy\".ficha_inventario fi 
                              JOIN \"DPrivacy\".secao_plano_ficha sfp ON sfp.fk_ficha = fi.id
                              WHERE fi.finalizado IS TRUE AND fi.fk_usuario = %s 
                              GROUP BY 1,2,3,4
                              ORDER BY fi.data_cadastro DESC"""
      



      select = cur.execute(selectPlanoFicha, (id_usuario, )).fetchall()
      

      response : List[FichasFinalizadasResponse] = []

      for row in select:
         response.append(FichasFinalizadasResponse(id=row[0], area=row[1], finalizado=row[2], dataCadastro=row[3], totalSecoes=row[4]))

      # print(len(response))
      if(len(response) != 0):
         return response
      else:
         return 'E'


@api.get('/buscar_secoes/{id_ficha}')
def buscarSecoes(id_ficha):

   selectSecaoPlanoFicha = """SELECT spf.secao, spf.fk_ficha, spf.plano, spf.risco, spf.tratativa, spfr.resposta, spfr.data_inicio, spfr.data_fim FROM \"DPrivacy\".secao_plano_ficha spf 
                                 LEFT JOIN \"DPrivacy\".secao_plano_ficha_resposta spfr ON spfr.fk_secao_plano_ficha = spf.id
                                 WHERE spf.fk_ficha = %s
                                 ORDER BY spf.secao ASC
                                   """

   response : List[SecaoFichaResponse] = []
      
   with conn.cursor() as cur:
      cur = conn.cursor()

      select = cur.execute(selectSecaoPlanoFicha, (id_ficha, ))


      for row in select:
         response.append(SecaoFichaResponse(idFicha=row[1], secao=row[0], plano=row[2], risco=row[3], 
                                            tratativa=row[4], resposta=row[5], dataInicio=row[6], dataFim=row[7]))
         
      
   if(len(response) != 0):
      return response
   else:
      return 'E'


      

