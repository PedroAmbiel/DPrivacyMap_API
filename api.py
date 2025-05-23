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
from openai import OpenAI

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

def criarBodyRequestAI(userPrompt):
   
   sys_prompt = f"""
               Evite termos jurídicos técnicos e fale como se estivesse explicando para gestores de empresas que não são da área jurídica.
               Nunca responda diretamente à pergunta.
               Mantenha sempre as respostas com menos de 300 palavras.
               """

   data = AiBody(prompt=userPrompt, system=sys_prompt)

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

      select_todos_riscos = cur.execute(f" SELECT DISTINCT s.risco FROM \"DPrivacy\".secao_plano_ficha s " +
                           " LEFT JOIN \"DPrivacy\".ficha_inventario fi ON fi.id = s.fk_ficha "
                           " LEFT JOIN \"DPrivacy\".planos p ON p.titulo = s.plano " +
                           " WHERE s.fk_ficha = %s ", (idFicha, )).fetchall()

      select = cur.execute(f" SELECT s.secao, s.plano, s.risco, s.tratativa, fi.area, s.id, p.tempo_dias, p.detalhe_planos FROM \"DPrivacy\".secao_plano_ficha s " +
                           " LEFT JOIN \"DPrivacy\".ficha_inventario fi ON fi.id = s.fk_ficha "
                           " LEFT JOIN \"DPrivacy\".planos p ON p.titulo = s.plano AND s.plano = \'Resumo Geral\' " +
                           " WHERE s.fk_ficha = %s "
                           " ORDER BY s.secao", (idFicha, )).fetchall()
      
      riscos_identificados = ""

      for risco in select_todos_riscos:
         riscos_identificados += risco[0] + ", "

      user_prompt = f"""
                     Minha empresa está iniciando trabalhos com coleta de dados sensíveis.
                     Os riscos identificados são: {riscos_identificados}.
                     De acordo com a LGPD (Lei Geral de Proteção de Dados), o que devo fazer para tratar esses riscos? 
                     """
      

      data = criarBodyRequestAI(user_prompt)
      secao = 1
      for item in select:

         update_secao_data = "INSERT INTO \"DPrivacy\".secao_plano_ficha_resposta (data_inicio, fk_secao_plano_ficha) VALUES ( now(), %s ) RETURNING id"

         cur.execute(update_secao_data, (item[5], ))

         id_inserido = cur.fetchone()[0]
         
         conn.commit()

         if(secao == 1):
            user_prompt = f"""
                           Minha empresa está iniciando trabalhos com coleta de dados sensíveis.
                           Os riscos identificados são: {riscos_identificados}.
                           De acordo com a LGPD (Lei Geral de Proteção de Dados), o que devo fazer para tratar esses riscos?
                           
                           Responda com um texto corrido e sem estrutura de lista, não enumere os tópicos.
                           Descreva utilizando a tag <b></b> para identificar titulos/tópicos. 
                           Utilize HTML para gerar a estrutura de sua resposta.
                           """
         else:
            user_prompt = f"""
                           Área responsável: {item[4]}.  
                           Risco identificado: {item[2]}.  
                           Plano de mitigação em andamento: {item[1]}.

                           Explique o plano utilizando a seguinte descrição:
                           {item[7]}

                           Detalhe cada item indicando o passo a passo para implementação do plano de ação, ou seja, as etapas que a empresa precisa cumprir dentro deste plano.
                           Explique também por que essas etapas são relevantes para mitigar o risco identificado.
                           Explique com suas palavras o por que a área responsável deve se preocupar com esses riscos.
                           
                           Sua resposta deve manter o seguinte padrão de estrutura:
                              Inicie descrevendo a abordagem prevista no plano, em seguida, a sequência de ações recomendadas, utilizando elementos HTML. 
                              Ao iniciar um novo topico utilizar negrito <b></b> e em seguida dois pontos ':'.
                              Quando falar de um novo tópico da descrição do plano, inicie o tópico com '-'.
                              Não indique negrito utilizando '*'.
                              Sua resposta não deve passar de dois parágrafos. 
                              Utilize <br/> para quebra de linha.

                              Exemplo de saída esperada:

                                 <b>Objetivo:</b> 'Descreva o objetivo'
                                 
                                 <br/> <b>Etapas para Implementação:</b>

                              <ul> 
                                 <li>- 'etapa 1'</li> 
                                 <li>- 'etapa 2'</li> 
                                 <li>- 'etapa 3'</li> 
                                 ...
                                 Quantas etapas forem necessárias
                              </ul>
                     """ 
            
         data = criarBodyRequestAI(user_prompt)

         print("USER PROMPT: ", data.prompt)
         print("SYSTEM PROMPT: ", data.system)

         response = requests.post(url, headers=basicHeader, json= data.to_dict())

         print('Response:', response.json())
         update_secao_resposta = "UPDATE \"DPrivacy\".secao_plano_ficha_resposta SET resposta = %s, data_fim = now() WHERE id = %s"

         cur.execute(update_secao_resposta, (response.json()['response'], id_inserido, ))

         secao += 1
         conn.commit()



@api.post("/login")
def login(body:UserLogin):
   password = body.senha
   password_bytes = password.encode('utf-8')
   senha_hashed = hashlib.sha256(password_bytes)


   with conn.cursor() as cur:
      
      cur = conn.cursor()

      select = cur.execute(f" SELECT u.id, u.nome, u.email, u.responsavel, u.senha, u.fk_perfil FROM \"DPrivacy\".usuarios u " +
                           " WHERE u.email = %s ", [body.email]).fetchone()


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

      if(body.retencao != None):
         update += " retencao = %s, "

      if(body.revisao != None):
         update += " revisao = %s, "

      update += " finalizado = true, data_finalizado = now() "

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
         
         if(body.retencao != None):
            params.append(body.retencao)

         if(body.revisao != None):
            params.append(body.revisao)

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

      if(body.retencao != None):
         insert += " retencao, "

      if(body.revisao != None):
         insert += " revisao, "

      insert += " fk_usuario, finalizado, data_finalizado "

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

      if(body.retencao != None):
         insert += " %s, "

      if(body.revisao != None):
         insert += " %s, "
      
      insert += " %s, %s, %s "


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

         if(body.retencao != None):
            params.append(body.retencao)

         if(body.revisao != None):
            params.append(body.revisao)
            
         params.append(body.usuario)
         params.append(True)
         params.append("now()")

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

         ##----------------- Inserts nas tabelas de rl_tipo_operacao -----------------##
         if(body.tipoOperacao):
            print("Entrou RL_TIPO_OPERACAO")
            insert_dados = "INSERT INTO \"DPrivacy\".rl_ficha_tipo_operacao (fk_ficha, tipo_operacao) VALUES (%s, %s) "

            for tipoOperacao in body.tipoOperacao:
               cur.execute(insert_dados, (id_inserido, tipoOperacao))

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

      if(body.retencao != None):
         update += " retencao = %s, "

      if(body.revisao != None):
         update += " revisao = %s, "

      if(update[len(update)-2] == ','):
         print(update[len(update)-2])
         update = replacer(update, '', len(update)-2)

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

         if(body.retencao != None):
            params.append(body.retencao)

         if(body.revisao != None):
            params.append(body.revisao)
            
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

      if(body.retencao != None):
         insert += " retencao, "
      
      if(body.revisao != None):
         insert += " revisao, "

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

      if(body.retencao != None):
         insert += " %s, "
      
      if(body.revisao != None):
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

         if(body.retencao != None):
            params.append(body.retencao)

         if(body.revisao != None):
            params.append(body.revisao)
            
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

      select = cur.execute(f" SELECT fi.id, fi.area, fi.finalizado, fi.data_cadastro, fi.armazenamento, fi.exclusao, fi.compartilhamento_terceiros, fi.transferencia_internacional, fi.seguranca, fi.retencao, fi.revisao FROM \"DPrivacy\".ficha_inventario fi " +
                           " WHERE fi.id = %s ", [id_ficha]).fetchone()
      
      listaOperacoes = []
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
                                 revisao=select[10],
                                 retencao=select[9],
                                 seguranca=select[8])
         
      else:
         response = False

      return response
   

def selectProcuraSecoes(ficha:FichaResponse):
   with conn.cursor() as cur:
      cur = conn.cursor()
      #####-----------------PROCURANDO SEÇÕES-------------------####
      select_plano_secao = """
            SELECT  STRING_AGG(DISTINCT r.riscos_dados_pessoais, ','), pl.titulo, pl.detalhes, count(pl.id) as qtd FROM \"DPrivacy\".planos pl
            JOIN \"DPrivacy\".rl_riscos_planos rp ON rp.fk_plano = pl.id
            JOIN \"DPrivacy\".rl_inventario_riscos ir ON ir.fk_risco = rp.fk_risco
            JOIN \"DPrivacy\".riscos r ON r.id = ir.fk_risco
            JOIN \"DPrivacy\".inventario_operacoes io ON io.id = ir.fk_inventario
            WHERE io.area = %s
            AND io.tipo_operacao = ANY(%s) 
            AND (	
                  io.dados_coletados = ANY(%s)
                  OR  io.finalidade = ANY(%s) 
                  OR io.revisao = %s
                  OR io.retencao = %s
                  OR io.seguranca = %s 
                  OR io.armazenamento = %s
                  OR io.exclusao = %s
                  OR io.compartilhamento_terceiros = %s
                  OR io.transferencia_internacional = %s
               )
            GROUP BY pl.id, pl.titulo
            order by qtd desc
      """

      params = []

      params.append(ficha.area)
      params.append(ficha.tipoOperacao)
      params.append(ficha.dadosColetados)
      params.append(ficha.finalidade)
      params.append(ficha.revisao)
      params.append(ficha.retencao)
      params.append(ficha.seguranca)
      params.append(ficha.armazenamento)
      params.append(ficha.exclusao)
      params.append(ficha.compartilhamentoTerceiros)
      params.append(ficha.transferenciaInternacional)

      select = cur.execute(select_plano_secao, params).fetchall()

      if(len(select) > 1):
         return select
      

      select_plano_secao = """
            SELECT STRING_AGG(DISTINCT r.riscos_dados_pessoais, ','), pl.titulo, pl.detalhes, count(pl.id) as qtd FROM \"DPrivacy\".planos pl
            JOIN \"DPrivacy\".rl_riscos_planos rp ON rp.fk_plano = pl.id
            JOIN \"DPrivacy\".rl_inventario_riscos ir ON ir.fk_risco = rp.fk_risco
            JOIN \"DPrivacy\".riscos r ON r.id = ir.fk_risco
            JOIN \"DPrivacy\".inventario_operacoes io ON io.id = ir.fk_inventario
            WHERE io.area = %s
            AND io.dados_coletados = ANY(%s) 
            AND (	
                  io.tipo_operacao = ANY(%s)
                  OR  io.finalidade = ANY(%s) 
                  OR io.revisao = %s
                  OR io.retencao = %s
                  OR io.seguranca = %s 
                  OR io.armazenamento = %s
                  OR io.exclusao = %s
                  OR io.compartilhamento_terceiros = %s
                  OR io.transferencia_internacional = %s
               )
            GROUP BY pl.id, pl.titulo
            order by qtd desc
      """

      params = []

      params.append(ficha.area)
      params.append(ficha.dadosColetados)
      params.append(ficha.tipoOperacao)
      params.append(ficha.finalidade)
      params.append(ficha.revisao)
      params.append(ficha.retencao)
      params.append(ficha.seguranca)
      params.append(ficha.armazenamento)
      params.append(ficha.exclusao)
      params.append(ficha.compartilhamentoTerceiros)
      params.append(ficha.transferenciaInternacional)

      select = cur.execute(select_plano_secao, params).fetchall()

      if(len(select) > 1):
         return select
      

      select_plano_secao = """
            SELECT STRING_AGG(DISTINCT r.riscos_dados_pessoais, ','), pl.titulo, pl.detalhes, count(pl.id) as qtd FROM \"DPrivacy\".planos pl
            JOIN \"DPrivacy\".rl_riscos_planos rp ON rp.fk_plano = pl.id
            JOIN \"DPrivacy\".rl_inventario_riscos ir ON ir.fk_risco = rp.fk_risco
            JOIN \"DPrivacy\".riscos r ON r.id = ir.fk_risco
            JOIN \"DPrivacy\".inventario_operacoes io ON io.id = ir.fk_inventario
            WHERE io.area = %s
            AND io.finalidade = ANY(%s) 
            AND (	
                  io.tipo_operacao = ANY(%s)
                  OR  io.dados_coletados = ANY(%s) 
                  OR io.revisao = %s
                  OR io.retencao = %s
                  OR io.seguranca = %s 
                  OR io.armazenamento = %s
                  OR io.exclusao = %s
                  OR io.compartilhamento_terceiros = %s
                  OR io.transferencia_internacional = %s
               )
            GROUP BY pl.id, pl.titulo
            order by qtd desc
      """

      params = []

      params.append(ficha.area)
      params.append(ficha.finalidade)
      params.append(ficha.tipoOperacao)
      params.append(ficha.dadosColetados)
      params.append(ficha.revisao)
      params.append(ficha.retencao)
      params.append(ficha.seguranca)
      params.append(ficha.armazenamento)
      params.append(ficha.exclusao)
      params.append(ficha.compartilhamentoTerceiros)
      params.append(ficha.transferenciaInternacional)

      select = cur.execute(select_plano_secao, params).fetchall()

      if(len(select) > 1):
         return select
         



@api.post('/criar_secoes')
def criarSecoesFicha(body:SecaoFichaRequest):


   select_dados_coletados = f"SELECT dado_coletado FROM \"DPrivacy\".rl_ficha_dados_coletados WHERE fk_ficha = {body.idFicha} "
   select_finalidade = f"SELECT finalidade FROM \"DPrivacy\".rl_ficha_finalidade WHERE fk_ficha = {body.idFicha} "
   select_tipo_operacao = f"SELECT tipo_operacao FROM \"DPrivacy\".rl_ficha_tipo_operacao WHERE fk_ficha = {body.idFicha} "

   listDadosColetados = []
   listFinalidade = []
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

      #TIPO OPERAÇÃO#
      select = cur.execute(select_tipo_operacao).fetchall()

      for item in select:
         listTipoOperacao.append(item[0])

      #####-----------------PREENCHENDO A FICHA-------------------####
      select_ficha = f"SELECT id, armazenamento, exclusao, compartilhamento_terceiros, transferencia_internacional, area, seguranca, retencao, revisao FROM \"DPrivacy\".ficha_inventario WHERE id = {body.idFicha} "
      
      select = cur.execute(select_ficha).fetchone()
      print(select)
      ficha = FichaResponse(id=select[0], armazenamento=select[1], exclusao=select[2], compartilhamentoTerceiros=select[3], transferenciaInternacional=select[4], 
                            area=select[5], seguranca=select[6], dadosColetados=listDadosColetados, dataCadastro=None, finalidade=listFinalidade, finalizado=None, retencao=select[7],
                            revisao=select[8], tipoOperacao=listTipoOperacao)
      
      
   select = selectProcuraSecoes(ficha)

   with conn.cursor() as cur:
      cur = conn.cursor()

      insert_secao = "INSERT INTO \"DPrivacy\".secao_plano_ficha(secao, fk_ficha, plano, risco, tratativa) VALUES (%s, %s, %s, %s, %s)"

      cur.execute(insert_secao, (1, ficha.id, 'Resumo Geral', '', 'Explicação Geral', ))

      secao = 2
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
                              ORDER BY fi.data_finalizado DESC, fi.id DESC"""
      



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


      

