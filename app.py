from asyncio.windows_events import NULL
from base64 import decode
from crypt import methods
from curses.ascii import NUL
from gc import DEBUG_COLLECTABLE
from flask import Flask, jsonify, request
import logging, time, psycopg2, jwt, json
from datetime import datetime, timedelta
from functools import wraps
import os

app = Flask(__name__)   

app.config['SECRET_KEY'] = 'it\xb5u\xc3\xaf\xc1Q\xb9\n\x92W\tB\xe4\xfe__\x87\x8c}\xe9\x1e\xb8\x0f'

NOT_FOUND_CODE = 404
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
        token = request.headers.get('Token')

        # Verificar se a mensagem contem token
        if not token:
            return jsonify({"message": "Token está em falta!"}), UNAUTHORIZED_CODE

        try:
            # Verificar se o token é válido
            data = jwt.decode(token, app.config['SECRET_KEY'])
            # Verificar a validade (tempo) do token
            if(data['expiration'] < str(datetime.utcnow())):
                return jsonify({"message": "O Token expirou!"}), NOT_FOUND_CODE

        except Exception as e:
            return jsonify({"message": "Token inválido"}), FORBIDDEN_CODE
        return func(*args, **kwargs)
    return decorated

################################
##  UTILIZADORES
################################

## LOGIN
@app.route("/login", methods=['POST'])
def login():
    content = request.get_json()

    # Verificar se o json contem var nome e pass
    if "nome" not in content or "pass" not in content:
        return jsonify({"message": "Parametros invalidos!"}), BAD_REQUEST_CODE

    # SQL Querry
    query = """SELECT * FROM users WHERE nome = %s AND pass = %s;"""

    # Array com parametros a atribuir à querry (nome e pass dados pelo json)
    values = [content['nome'], content['pass']]
    
    try:
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, values)
                row = cursor.fetchone()
                # Criação do token com id do user e o tempo de expiração do token
                token = jwt.encode({
                    'id': row[0], 
                    'expiration': str(datetime.utcnow() + timedelta(hours=1))}, 
                    app.config['SECRET_KEY'])
        conn.close()
    except (Exception, psycopg2.DatabaseError):
        return jsonify({"message": "Utilizador nao encontrado"}), NOT_FOUND_CODE
    
    return jsonify({"message": "Login realizado com sucesso!", "token": token.decode('utf-8')}), OK_CODE


## REGISTO
@app.route("/registo", methods=['POST'])
def registo():
    content = request.get_json()

    if "nome" not in content or "pass" not in content: 
        return jsonify({"message": "Parâmetros inválidos"}), BAD_REQUEST_CODE

    query = """INSERT INTO users(nome, pass) VALUES(%s, %s);"""

    values = [content['nome'], content['pass']]

    try:
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, values)
        conn.close()
    except (Exception, psycopg2.DatabaseError) as error:
        return jsonify({"message": str(error)}), NOT_FOUND_CODE

    return jsonify({"message": "Utilizador registado com sucesso!"}), OK_CODE


################################
##  LISTAS
################################

## INSERIR
@app.route("/lista", methods=['POST'])
@auth_user
def inserirLista():
    content = request.get_json()
    token = request.headers.get('Token')

    decoded_token = jwt.decode(token, app.config['SECRET_KEY'])

    if "titulo" not in content or "id" not in decoded_token: 
        return jsonify({"message": "Parâmetros inválidos"}), BAD_REQUEST_CODE

    query = """INSERT INTO lista(titulo, user_id) VALUES(%s, %s);"""

    values = [content['titulo'], decoded_token['id']]

    try:
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, values)
        conn.close()
    except (Exception, psycopg2.DatabaseError) as error:
        return jsonify({"message": str(error)}), NOT_FOUND_CODE

    return jsonify({"message": "Lista inserida com sucesso!"}), OK_CODE


## RETORNAR DADOS
@app.route("/lista", methods=['GET'])
@auth_user
def retornarLista():
    content = request.get_json()

    if "id" not in content: 
        return jsonify({"message": "Parâmetros inválidos"}), BAD_REQUEST_CODE

    conn = db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM lista WHERE id = %s;", content["id"])
    row = cur.fetchone()

    conn.close()

    return jsonify({"id": row[0], "titulo": row[1], "user_id": row[2]}), OK_CODE


## ATUALIZAR DADOS
@app.route("/lista", methods=['PUT'])
@auth_user
def atualizaLista():
    content = request.get_json()

    if "titulo" not in content and "id" not in content: 
        return jsonify({"message": "Parâmetros inválidos"}), BAD_REQUEST_CODE
 
    query = """UPDATE lista SET titulo = %s WHERE id = %s;"""
  
    values = [content['titulo'], content['id']]

    try:
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, values)
        conn.close()
    except (Exception, psycopg2.DatabaseError):
        return jsonify({"message": "Lista não atualizada!"}), NOT_FOUND_CODE

    return jsonify({"message": "Lista atualizada com sucesso!"}), OK_CODE


## LISTAGEM 
@app.route("/lista/listagem", methods=['GET'])
@auth_user
def listaLista():
    token = request.headers.get('Token')

    decoded_token = jwt.decode(token, app.config['SECRET_KEY'])

    if "id" not in decoded_token:
        return jsonify({"message": "O id não existe!"}), NOT_FOUND_CODE

    values = [decoded_token['id']]

    arrayList = []
    
    conn = db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM lista WHERE user_id = %s", values)
    rows = cur.fetchall()

    for row in rows:
        arrayList.append({"id":row[0], "titulo":row[1], "user_id":row[2]})
    conn.close()

    return jsonify({"listas":arrayList, "message":"listas utilizador"}), OK_CODE


## REMOVER
@app.route("/lista", methods=['DELETE'])
@auth_user
def removerLista():
    content = request.get_json()

    if "id" not in content:
        return jsonify({"message": "O id não existe!"}), NOT_FOUND_CODE

    query = """DELETE FROM lista WHERE id = %s;"""

    valeus = [content['id']]

    try:
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, valeus)
        conn.close()
    except (Exception, psycopg2.DatabaseError):
        return jsonify({"message": "A Lista não foi removida!"}), NOT_FOUND_CODE

    return jsonify({"message": "Lista removida com sucesso!"}), OK_CODE


################################
##  TAREFAS
################################

## INSERIR
@app.route("/tarefa", methods=['POST'])
@auth_user
def inserirTarefa():
    content = request.get_json()

    if "titulo" not in content or "descricao" not in content or "data" not in content or "hora" not in content or "estado" not in content or "lista_id" not in content: 
        return jsonify({"message": "Parâmetros inválidos"}), BAD_REQUEST_CODE

    query = """INSERT INTO tarefa(titulo, descricao, data, hora, estado, lista_id) VALUES(%s, %s, %s, %s, %s, %s);"""

    values = [content['titulo'], content['descricao'], content['data'], content['hora'], content['estado'], content['lista_id']]

    try:
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, values)
        conn.close()
    except (Exception, psycopg2.DatabaseError) as error:
        return jsonify({"message": str(error)}), NOT_FOUND_CODE
        
    return jsonify({"message": "Tarefa inserida com sucesso!"}), OK_CODE


## RETORNAR DADOS
@app.route("/tarefa", methods=['GET'])
@auth_user
def retornarTarefa():
    content = request.get_json()

    if "id" not in content: 
        return jsonify({"message": "Parâmetros inválidos"}), BAD_REQUEST_CODE
    
    conn = db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM tarefa WHERE id = %s;", content['id'])
    row = cur.fetchone()

    conn.close()

    return jsonify({"id": row[0], "titulo": row[1], "decricao": row[2], "data": row[3], "hora": row[4], "estado": row[5], "lista_id": row[6]}), OK_CODE



## ATUALIZAR DADOS
@app.route("/tarefa", methods=['PUT'])
@auth_user
def atualizaTarefa():
    content = request.get_json()

    if "id" not in content and "titulo" not in content and "descricao" not in content and "data" not in content and "hora" not in content and "estado" not in content:
        return jsonify({"message": "Parâmetros inválidos"}), BAD_REQUEST_CODE
    
    query = """UPDATE tarefa SET titulo = %s, descricao = %s, data = %s, hora = %s, estado = %s WHERE id = %s;"""

    values = [content['titulo'], content['descricao'], content['data'], content['hora'], content['estado'], content['id']]

    try:
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, values)
        conn.close()
    except (Exception, psycopg2.DatabaseError):
        return jsonify({"message": "Tarefa não atualizada!"}), NOT_FOUND_CODE

    return jsonify({"message": "Tarefa atualizada com sucesso!"}), OK_CODE


## REMOVER
@app.route("/tarefa", methods=['DELETE'])
@auth_user
def removerTarefa():
    content = request.get_json()

    query = """DELETE FROM tarefa WHERE id = %s;"""

    try:
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, content['id'])
        conn.close()
    except (Exception, psycopg2.DatabaseError):
        return jsonify({"message": "A Tarefa não foi removida!"}), NOT_FOUND_CODE
    
    return jsonify({"message": "Tarefa removida com sucesso!"}), OK_CODE


## LISTAGEM 
@app.route("/tarefa/listagem/{lista_id}", methods=['GET'])
@auth_user
def listaTarefas(lista_id):

    if lista_id is NULL:
        return jsonify({"message": "O id não existe!"}), NOT_FOUND_CODE

    arrayList = []
    
    conn = db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM tarefa WHERE lista_id = %s", lista_id)
    rows = cur.fetchall()
    for row in rows:
        arrayList.append({"id":row[0], "titulo":row[1], "descricao":row[2], "data":row[3], "hora":row[4], "estado":row[5], "lista_id":row[6]})

    conn.close()
    return jsonify({"tarefas":arrayList}), OK_CODE


##########################################################
## DATABASE ACCESS
##########################################################
def db_connection():
    
    DATABASE_URL = os.environ.get('DATABASE_URL')
    db = psycopg2.connect(DATABASE_URL)
    return db


if __name__ == "__main__":

    app.run(port=8080, debug=True, threaded=True)