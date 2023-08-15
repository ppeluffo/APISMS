#!/home/pablo/Spymovil/python/proyectos/APISMSV1/venv/bin/python3
'''
API flask de recepcion de datos para envio de SMS.
Version 1.0:
- Utiliza un SQLITE para almacenar los mensajes enviados
- No aplica autenticación.

- Creacion de la BD


https://www.digitalocean.com/community/tutorials/how-to-use-an-sqlite-database-in-a-flask-application

Pendiente:
- Control de errores de abrir BD

'''
import os
import logging
import datetime
import random
import string
import pickle
import sqlite3
from flask import Flask
from flask import request
from flask_restful import Resource
from flask_restful import Api

app = Flask(__name__)
api = Api(app)

DBNAME = os.environ.get('DBNAME', '/dbase/sms.db')

class Sms(Resource):
    '''
    Implementa la recepcion de nuevos SMS, la consulta del status y la modificacion del estado
    '''  
    def post(self):
        '''
        Crea un nuevo registro para envio de un SMS. 
        Recibe un json con los datos del SMS
        {'sms_numero': '099123456', 'sms_mensaje':'Este es un texto de prueba'}
        Devuelve un json con el tag asignado y el status:
        { 'tag': 'AB324RTvw', 'estado':'PENDIENTE'}
        '''
        d_params = request.get_json()
        if not isinstance(d_params, dict):
            d_rsp = {'rsp':'ERROR', 'msg': 'No es una instancia de dict.'}
            return d_rsp, 406
        #
        if 'sms_numero' not in d_params:
            app.logger.info('(001) ApiSMS_ERR001: No sms_numero in request_json_data')
            d_rsp = {'rsp':'ERROR', 'msg':'ApiSMS_ERR001: No sms_numero in request_json_data'}
            return d_rsp, 406
        #
        sms_numero = d_params.get('sms_numero','000000000')
        #                         
        if 'sms_mensaje' not in d_params:
            app.logger.info('(002) ApiSMS_ERR002: No sms_mensaje in request_json_data')
            d_rsp = {'rsp':'ERROR', 'msg':'ApiSMS_ERR002: No sms_mensaje in request_json_data'}
            return d_rsp, 406
        #
        sms_mensaje = d_params.get('sms_mensaje','')
        #
        # Genero el token unico de la operación
        # El token es de 20 bytes alfanumericos, basado en el timestamp, sms, mensaje.
        mydict={'timestamp':datetime.datetime.now(),'sms_numero':sms_numero,'sms_mensaje':sms_mensaje}
        random.seed( pickle.dumps(mydict))
        tag = ''.join(random.choices(string.ascii_uppercase + string.digits, k=20))
        #
        # Guardo los datos en la SQLITE
        conn = sqlite3.connect(DBNAME)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO sms_table (sms_numero,sms_mensaje,estado,tag) VALUES (?,?,?,?)',
                       (sms_numero,sms_mensaje,'PENDIENTE',tag))
        conn.commit()
        conn.close()
        #
        # Log
        app.logger.info(f'ApiSMS: NEW_SMS,sms_nro={sms_numero},sms_msg={sms_mensaje},status=PENDIENTE')
        #
        # Respuesta
        d_rsp = {'tag':tag, 'estado':'PENDIENTE'}
        return d_rsp, 201
    
    def put(self):
        '''
        Modifica un registro.
        Solo se actualiza el send_timestamp y el estado
        Recibe un json { 'id': bd_id, 'estado': nuevo_estado}
        Localmente le agrega el send_timestamp.
        '''
        d_params = request.get_json()
        if not isinstance(d_params, dict):
            d_rsp = {'rsp':'ERROR', 'msg': 'No es una instancia de dict.'}
            return d_rsp, 406
        #
        if 'id' not in d_params:
            app.logger.info('(003) ApiSMS_ERR003: No id in request_json_data')
            d_rsp = {'rsp':'ERROR', 'msg':'ApiSMS_ERR003: No id in request_json_data'}
            return d_rsp, 406
        #
        id = d_params.get('id','0')
        #                         
        if 'estado' not in d_params:
            app.logger.info('(004) ApiSMS_ERR004: No estado in request_json_data')
            d_rsp = {'rsp':'ERROR', 'msg':'ApiSMS_ERR004: No estado in request_json_data'}
            return d_rsp, 406
        #
        estado = d_params.get('estado','ERROR')
        now = datetime.datetime.now()
        # Actualizo los datos en la SQLITE
        conn = sqlite3.connect(DBNAME)
        cursor = conn.cursor()
        _ = cursor.execute("UPDATE sms_table SET estado = ?, send_timestamp = ? WHERE id = ?", (estado, now, id))
        conn.commit()
        conn.close()
        #
        # Log
        app.logger.info(f'ApiSMS: CAMBIO_STATUS,id:{id}, status={estado}')
        #
        d_rsp = { 'rsp': 'OK'}
        return d_rsp, 200

    def get(self):
        '''
        Consulta del estado del envio de un SMS. Recibe un json con el tag.
        {'tag': 'AB324RTvw'}
        Devuelve lo mismo que el put:
        { 'tag': 'AB324RTvw', 'estado':'PENDIENTE'}
        '''
        # Leo los datos del JSON
        d_params = request.get_json()
        if not isinstance(d_params, dict):
            d_rsp = {'rsp':'ERROR', 'msg': 'No es una instancia de dict.'}
            return d_rsp, 406
        #
        if 'tag' not in d_params:
            app.logger.info('(005) ApiSMS_ERR005: No tag in request_json_data')
            d_rsp = {'rsp':'ERROR', 'msg':'ApiSMS_ERR005: No tag in request_json_data'}
            return d_rsp, 406
        #
        tag = d_params.get('tag','000000000')
        # Leo los datos de la SQLITE.
        conn = sqlite3.connect(DBNAME)
        cursor = conn.cursor()
        rsp = cursor.execute("SELECT * FROM sms_table WHERE tag = ?" , [tag]).fetchone()
        conn.commit()
        conn.close()
        #
        if rsp is None:
            d_rsp = {'rsp':'ERROR', 'msg': f'tag {tag} no existe.'}
            return d_rsp, 406
        #
        d_rcd = {'id':rsp[0],
                 'received_timestamp': rsp[1],
                 'send_timestamp': rsp[2],
                 'sms_numero': rsp[3],
                 'sms_mensaje': rsp[4],
                 'estado': rsp[5],
                 'tag': rsp[6]}
        #
        d_rsp = { 'tag': d_rcd.get('tag','000000'), 'estado': d_rcd.get('estado','Err')}
        return d_rsp, 200

class SmsPendientes(Resource):
    '''
    Implementa el envio de la lista de SMS pendientes
    '''
    def get(self):
        '''
        Metodo para enviar la lista de pendientes. Se le manda cuantos elementos se quieren
        Si el valor es 0, entoces se mandan todos.
        '''
        # Leo los datos del JSON
        d_params = request.get_json()
        if not isinstance(d_params, dict):
            d_rsp = {'rsp':'ERROR', 'msg': 'No es una instancia de dict.'}
            return d_rsp, 406
        #
        if 'count' not in d_params:
            app.logger.info('(006) ApiSMS_ERR006: No count in request_json_data')
            d_rsp = {'rsp':'ERROR', 'msg':'ApiSMS_ERR006: No count in request_json_data'}
            return d_rsp, 406
        #
        count = int(d_params.get('count','0'))
        #
        # Leo los datos de la SQLITE.
        conn = sqlite3.connect(DBNAME)
        cursor = conn.cursor()
        results = cursor.execute("SELECT * FROM sms_table WHERE estado = 'PENDIENTE'").fetchall()
        conn.commit()
        conn.close()
        #
        sms_pendientes = []
        if results is None:
            return sms_pendientes
        
        for rcd in results:
            d_rcd = {'id':rcd[0],
                    'received_timestamp': rcd[1],
                    'send_timestamp': rcd[2],
                    'sms_numero': rcd[3],
                    'sms_mensaje': rcd[4],
                    'estado': rcd[5],
                    'tag': rcd[6]}
            sms_pendientes.append(d_rcd)
        #
        d_rsp = { 'count': len(sms_pendientes), 'sms_pendientes': sms_pendientes }
        return d_rsp, 200

class Ping(Resource):
    '''
    Clase que usamos solo para poder detectar que la API esta arriba y corriendo
    '''
    def get(self):
        '''
        Solo accedemos por GET sin parámetros.
        '''
        d_rsp = {'rsp': 'PONG' }
        return d_rsp, 200

api.add_resource( Sms, '/apisms/sms')
api.add_resource( SmsPendientes, '/apisms/sms_pendientes')
api.add_resource( Ping, '/apisms/ping')

# Lineas para que cuando corre desde gunicorn utilize el log handle de este
# https://trstringer.com/logging-flask-gunicorn-the-manageable-way/

if __name__ != '__main__':
    # SOLO PARA TESTING !!!
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    app.logger.info('Starting APISMS...')


# Lineas para cuando corre en modo independiente
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6000, debug=True)