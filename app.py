from crypt import methods
from gc import DEBUG_COLLECTABLE
from flask import Flask, jsonify, request
import logging, time, psycopg2, jwt, json
from datetime import datetime, timedelta
from functools import wraps
import os

app = Flask(__name__)   

app.config['SECRET_KEY'] = 'it\xb5u\xc3\xaf\xc1Q\xb9\n\x92W\tB\xe4\xfe__\x87\x8c}\xe9\x1e\xb8\x0f'

NOT_FOUND_CODE = 400
OK_CODE = 200
SUCCESS_CODE = 201
BAD_REQUEST_CODE = 400
UNAUTHORIZED_CODE = 401
FORBIDDEN_CODE = 403
NOT_FOUND = 404
SERVER_ERROR = 500
  
@app.route('/', methods = ["GET"])
def home():
    return "Bem vindo à API!"


##########################################################
## VERIFICAÇÃO TOKEN
##########################################################
def auth_user(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        content = request.headers.get('Authorization')
        #verificar se o token tem conteúdo ou não
        if content is None or "token" not in content or not content["token"]:
            return jsonify({'Erro': 'Token está em falta!', 'Code': UNAUTHORIZED_CODE})

        try:
            token = content["token"]
            data = jwt.decode(token, app.config['SECRET_KEY'])    
            #verificar a data de expiração do token
            if(data["expiration"] < str(datetime.utcnow())):
                return jsonify({"Erro": "O Token expirou!", "Code": NOT_FOUND_CODE})

        except Exception as e:
            return jsonify({'Erro': 'Token inválido', 'Code': FORBIDDEN_CODE})
        return func(*args, **kwargs)
    return decorated



################################
##  UTILIZADORES
################################

## LOGIN

@app.route("/user/login", methods=['POST'])
def login():
    content = request.get_json()

    if "nome_user" not in content or "password" not in content:
        return jsonify({"Code": BAD_REQUEST_CODE, "Erro": "Parâmetros inválidos"})

    #obter conteúdo do utilizador
    get_user_info = """
                SELECT *
                FROM users
                WHERE nome = %s AND pass = %s;
                """
    #descrever os parâmetros da query
    values = [content["nome_user"], content["password"]]
    
    try:
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(get_user_info, values)
                rows = cursor.fetchall()
                token = jwt.encode({
                    'id': rows[0][0],
                    #renovar a data de expiração do token
                    'expiration': str(datetime.utcnow() + timedelta(hours=1))
                }, app.config['SECRET_KEY'])
        conn.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
        return jsonify({"Code": NOT_FOUND_CODE, "Erro": "Utilizador não encontrado"})
    
    return {"Utilizador logado com sucesso! Code": OK_CODE, 'Token': token.decode('utf-8')}
  



## REGISTO

@app.route("/user/registo", methods=['POST'])
def registo():
    content = request.get_json()

    if "nome_user" not in content or "password" not in content: 
        return jsonify({"Code": BAD_REQUEST_CODE, "Erro": "Parâmetros inválidos"})

    insert_user_info = """
                INSERT INTO users(id, nome, pass) 
                VALUES(0, %s, %s);
                """

    values = [content["nome_user"], content["password"]]

    try:
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(insert_user_info, values)
        conn.close()
    except (Exception, psycopg2.DatabaseError) as error:
        return jsonify({"Code": NOT_FOUND_CODE, "Erro": str(error)})
    return {"Utilizador registado com sucesso! Code": OK_CODE}



## RETORNAR DADOS 

#@app.route("/user/consultar", methods=['GET'])
#@auth_user
#def consultarUser():
#    content = request.get_json()
#
#    conn = db_connection()
#    cur = conn.cursor()
#
#    decoded_token = jwt.decode(content['token'], app.config['SECRET_KEY'])
#
#    cur.execute("SELECT * FROM users WHERE id = %s;", (decoded_token["id"],))
#    rows = cur.fetchall()
#
#    conn.close()
#    return jsonify({"Id": rows[0][1], "nome": rows[0][2]})



################################
##  LISTAS
################################

## INSERIR

@app.route("/lista/inserir", methods=['POST'])
#@auth_user
def inserirLista():
    content = request.get_json()

    if "titulo" not in content or "users_id" not in content: 
        return jsonify({"Code": BAD_REQUEST_CODE, "Erro": "Parâmetros inválidos"})

    insert_lista_info = """
                INSERT INTO lista(id, titulo, users_id) 
                VALUES(0, %s, %s);
                """

    values = [content["titulo"], content["users_id"]]

    try:
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(insert_lista_info, values)
        conn.close()
    except (Exception, psycopg2.DatabaseError) as error:
        return jsonify({"Code": NOT_FOUND_CODE, "Erro": str(error)})
    return {"Lista inserida com sucesso! Code": OK_CODE}



## RETORNAR DADOS

@app.route("/lista/consultar", methods=['GET'])
@auth_user
def retornarLista():
    content = request.get_json()

    if "id" not in content: 
        return jsonify({"Code": BAD_REQUEST_CODE, "Erro": "Parâmetros inválidos"})
    conn = db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM lista WHERE id = %s;", content["id"])
    rows = cur.fetchall()
    conn.close()
    return jsonify({"Id": rows[0][0], "Título": rows[0][1], "Utilizador": rows[0][2]}), OK_CODE



## ATUALIZAR DADOS

@app.route("/lista/atualizar", methods=['PUT'])
#@auth_user
def atualizaLista():
    content = request.get_json()

    if "titulo" not in content and "id" not in content: 
        return jsonify({"Code": BAD_REQUEST_CODE, "Erro": "Parâmetros inválidos"})
 
    update_lista_info = """
        UPDATE lista SET titulo = %s WHERE id = %s;
         """
  
#    decoded_token = jwt.decode(content['token'], app.config['SECRET_KEY'])
    values = [content["titulo"], content["id"]]

    try:
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(update_lista_info, values)
        conn.close()
    except (Exception, psycopg2.DatabaseError) as error:
        return jsonify({"Code": NOT_FOUND_CODE, "Erro": "Lista não atualizada!"})
    return {"Lista atualizada com sucesso! Code": OK_CODE}


## LISTAGEM 

@app.route("/lista/listagem", methods=['GET'])
#@auth_user
def listaLista():
    arrayList = []
    content = request.get_json()

    if "users_id" not in content:
        return jsonify({"Code": NOT_FOUND_CODE, "Erro": "O id não existe!"})
    
    conn = db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM lista WHERE users_id = %s", content["users_id"])
    rows = cur.fetchall()
    for i in rows:
        arrayList.append({"id":i[0], "titulo":i[1], "users_id":i[2]})
    conn.close()
    return json.dumps(arrayList)



## REMOVER

@app.route("/lista/remover", methods=['DELETE'])
#@auth_user
def removerLista():
    content = request.get_json()

    remove_lista = """
                DELETE FROM lista WHERE id = %s;
                """
#    decoded_token = jwt.decode(content['token'], app.config['SECRET_KEY'])
    values = [content["id"]]

    try:
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(remove_lista, values)
        conn.close()
    except (Exception, psycopg2.DatabaseError) as error:
        return jsonify({"Code": NOT_FOUND_CODE, "Erro": "A Lista não foi removida!"})
    return {"Lista removida com sucesso! Code": OK_CODE}




################################
##  TAREFAS
################################

## INSERIR

@app.route("/tarefa/inserir", methods=['POST'])
#@auth_user
def inserirTarefa():
    content = request.get_json()

    if "titulo" not in content or "descricao" not in content or "data" not in content or "hora" not in content or "estado" not in content or "lista_id" not in content: 
        return jsonify({"Code": BAD_REQUEST_CODE, "Erro": "Parâmetros inválidos"})

    insert_tarefa_info = """
                INSERT INTO tarefa(id, titulo, descricao, data, hora, estado, lista_id) 
                VALUES(0, %s, %s, %s, %s, %s, %s);
                """

    values = [content["titulo"], content["descricao"], content["data"], content["hora"], content["estado"], content["lista_id"]]

    try:
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(insert_tarefa_info, values)
        conn.close()
    except (Exception, psycopg2.DatabaseError) as error:
        return jsonify({"Code": NOT_FOUND_CODE, "Erro": str(error)})
    return {"Tarefa inserida com sucesso! Code": OK_CODE}



## RETORNAR DADOS

@app.route("/tarefa/consultar", methods=['GET'])
#@auth_user
def retornarTarefa():
    content = request.get_json()

    if "id" not in content: 
        return jsonify({"Code": BAD_REQUEST_CODE, "Erro": "Parâmetros inválidos"})
    conn = db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM tarefa WHERE id = %s;", content["id"])
    rows = cur.fetchall()
    conn.close()
    return jsonify({"Id": rows[0][0], "Título": rows[0][1], "Descrição": rows[0][2], "Data": rows[0][3], "Hora": rows[0][4], "Estado": rows[0][5], "Lista": rows[0][6]}), OK_CODE



## ATUALIZAR DADOS

@app.route("/tarefa/atualizar", methods=['PUT'])
#@auth_user
def atualizaTarefa():
    content = request.get_json()

    if "contexto" not in content and "dados" not in content and "id" not in content: 
        return jsonify({"Code": BAD_REQUEST_CODE, "Erro": "Parâmetros inválidos"})

    if content["contexto"] == "titulo":
        update_tarefa_info = """
                UPDATE tarefa SET titulo = %s WHERE id = %s;
                """
    if content["contexto"] == "descricao":
        update_tarefa_info = """
                UPDATE tarefa SET descricao = %s WHERE id = %s;
                """
    if content["contexto"] == "data":
        update_tarefa_info = """
                UPDATE tarefa SET data = %s WHERE id = %s;
                """
    if content["contexto"] == "hora":
        update_tarefa_info = """
                UPDATE tarefa SET hora = %s WHERE id = %s;
                """
    if content["contexto"] == "estado":
        update_tarefa_info = """
                UPDATE tarefa SET estado = %s WHERE id = %s;
                """

#    decoded_token = jwt.decode(content['token'], app.config['SECRET_KEY'])
    values = [content["dados"], content["id"]]

    try:
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(update_tarefa_info, values)
        conn.close()
    except (Exception, psycopg2.DatabaseError) as error:
        return jsonify({"Code": NOT_FOUND_CODE, "Erro": "Tarefa não atualizada!"})
    return {"Tarefa atualizada com sucesso! Code": OK_CODE}



## REMOVER

@app.route("/tarefa/remover", methods=['DELETE'])
#@auth_user
def removerTarefa():
    content = request.get_json()

    remove_tarefa = """
                DELETE FROM tarefa WHERE id = %s;
                """
#    decoded_token = jwt.decode(content['token'], app.config['SECRET_KEY'])
    values = [content["id"]]

    try:
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(remove_tarefa, values)
        conn.close()
    except (Exception, psycopg2.DatabaseError) as error:
        return jsonify({"Code": NOT_FOUND_CODE, "Erro": "A Tarefa não foi removida!"})
    return {"Tarefa removida com sucesso! Code": OK_CODE}



## LISTAGEM 

@app.route("/tarefa/listagem", methods=['GET'])
#@auth_user
def listaTarefas():
    arrayList = []
    content = request.get_json()

    if "lista_id" not in content:
        return jsonify({"Code": NOT_FOUND_CODE, "Erro": "O id não existe!"})
    
    conn = db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM tarefa WHERE lista_id = %s", content["lista_id"])
    rows = cur.fetchall()
    for i in rows:
        arrayList.append({"id":i[0], "titulo":i[1], "descricao":i[2], "data":i[3], "hora":i[4], "estado":i[5], "lista_id":i[6]})
    conn.close()
    return json.dumps(arrayList)




##########################################################
## CONSULTAR SALDO
##########################################################
@app.route("/consultar_saldo", methods=['POST'])
@auth_user
def consultar_saldo():

    content = request.get_json()

    conn = db_connection()
    cur = conn.cursor()

    decoded_token = jwt.decode(content['token'], app.config['SECRET_KEY'])

    cur.execute("SELECT CAST(CAST(saldo AS NUMERIC(8,2)) AS VARCHAR) FROM utilizadores WHERE id = %s;", (decoded_token["id"],))
    rows = cur.fetchall()
    conn.close()
    return {"Saldo": rows[0][0]}



##########################################################
## CONSULTAR UTILIZADOR
##########################################################
@app.route("/consultar_utilizador", methods=['POST'])
@auth_user
def consultar_utilizador():
    content = request.get_json()

    conn = db_connection()
    cur = conn.cursor()

    decoded_token = jwt.decode(content['token'], app.config['SECRET_KEY'])

    cur.execute("SELECT * FROM utilizadores WHERE id = %s;", (decoded_token["id"],))
    rows = cur.fetchall()

    conn.close()
    return jsonify({"Id": rows[0][1], "nome": rows[0][2], "e-mail": rows[0][4], "cargo": rows[0][6]})




##########################################################
## LISTAR SE E ADMIN
##########################################################
@app.route("/isAdmin", methods=['POST'])
@auth_user
def isAdmin():

    conn = db_connection()
    cur = conn.cursor()
    content = request.get_json()

    decoded_token = jwt.decode(content['token'], app.config['SECRET_KEY'])

    cur.execute("SELECT administrador FROM utilizadores WHERE id = %s;", (decoded_token["id"],))
    rows = cur.fetchall()
    conn.close()
    return {"admin": rows[0][0]}



##########################################################
## ACTUALIZAR UTILIZADOR
##########################################################
@app.route("/actualizar_utilizador", methods=['POST'])
@auth_user
def actualizar_utilizador():
    content = request.get_json()

    if "nome" not in content or "email" not in content: 
        return jsonify({"Code": BAD_REQUEST_CODE, "Erro": "Parâmetros inválidos"})

    get_user_info = """
                UPDATE utilizadores SET nome = %s, email = %s WHERE id = %s;
                """
    decoded_token = jwt.decode(content['token'], app.config['SECRET_KEY'])
    values = [content["nome"], content["email"], decoded_token["id"]]

    try:
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(get_user_info, values)
        conn.close()
    except (Exception, psycopg2.DatabaseError) as error:
        return jsonify({"Code": NOT_FOUND_CODE, "Erro": "Utilizador não actualizado!"})
    return {"Code": OK_CODE}


##########################################################
## CARREGAR SALDO
##########################################################
@app.route("/carregar_saldo", methods=['POST'])
@auth_user
def carregar_saldo():
    content = request.get_json()

    if "n_identificacao" not in content or "saldo" not in content:
        return jsonify({"Code": BAD_REQUEST_CODE, "Erro": "Parâmetros inválidos"})

    get_user_info = """
                UPDATE utilizadores SET saldo = saldo + %s WHERE n_identificacao = %s;
                """

    values = [content["saldo"], content["n_identificacao"]]

    decoded_token = jwt.decode(content['token'], app.config['SECRET_KEY'])
    if(not decoded_token['administrador']):
        return jsonify({"Erro": "O utilizador não tem esses privilégios", "Code": FORBIDDEN_CODE})

    try:
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(get_user_info, values)
        conn.close()
    except (Exception, psycopg2.DatabaseError) as error:
        return jsonify({"Code": NOT_FOUND_CODE, "Erro": "Saldo não carregado"})
    return {"Code": OK_CODE}

##########################################################
## ENVIAR REPORTS
##########################################################
@app.route("/enviar_report", methods=['POST'])
@auth_user
def enviar_report():
    content = request.get_json()

    if "assunto" not in content or "mensagem" not in content or "info" not in content or "anonimo" not in content:
        return jsonify({"Code": BAD_REQUEST_CODE, "Erro": "Parâmetros inválidos"})

    insert_report = """
                INSERT INTO report(assunto, mensagem, utilizador_id, info_dispositivo, data_envio) VALUES(%s, %s, %s, %s, now());
                """

    decoded_token = jwt.decode(content['token'], app.config['SECRET_KEY'])
    
    if content["anonimo"] == "True":
        user = None
    else:
        user = decoded_token["id"]

    values = [content["assunto"], content["mensagem"], user, content["info"]]

    try:
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(insert_report, values)
        conn.close()
    except (Exception, psycopg2.DatabaseError) as error:
        return jsonify({"Code": NOT_FOUND_CODE, "Erro": "Report não registado"})
    return {"Code": OK_CODE}



##########################################################
## DATABASE ACCESS
##########################################################
def db_connection():
    
    DATABASE_URL = os.environ.get('DATABASE_URL')
    db = psycopg2.connect(DATABASE_URL)
    return db


if __name__ == "__main__":

    app.run(port=8080, debug=True, threaded=True)