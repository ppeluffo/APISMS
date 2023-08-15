#!/usr/bin/python3 -u
'''
Script que corre permanentemente leyendo la BD sqlite en busca de mensajes para enviar.
PENDIENTE:
- Mensajes multilinea
https://stackoverflow.com/questions/25761202/sending-multi-part-sms-with-gsm-using-at-commands

https://techsofar.com/combining-sms-messages/

https://stackoverflow.com/questions/29663459/python-app-does-not-print-anything-when-running-detached-in-docker

'''

import os
import requests
import time
import serial

SERIALPORT = os.environ.get('SERIALPORT','/dev/ttyUSB0')
SLEEPTIME = int(os.environ.get('SLEEPTIME', 30))
APISMS_HOST = os.environ.get('APISMS_HOST','127.0.0.1')
APISMS_PORT = os.environ.get('APISMS_PORT','6000')

class SmsEngine():
    '''
    Metodos para conectarme y enviar SMS
    ''' 
    def __init__(self):
        self.modem = None
        self.modem_prendido = False

    def open_device(self, serial_port = SERIALPORT):
        '''
        Abre el puerto serial al que esta conectado el modem.
        '''
        try:
            self.modem = serial.Serial(serial_port, baudrate=9600, timeout=1)
        except Exception as e:
            print(f'ERROR al abrir modem. Exception {e}.')

    def close_device(self):
        '''
        Cierra el handle
        '''
        self.modem_prendido = False
        try:
            self.modem.close()
        except Exception as e:
            print('close_device: modem not opened !!')
        
    def test_responses(self, verbose=True):
        '''
        Enviamos un comando AT y espero 1s por su respuesta. Si es OK asumo que está prendido
        Retorna True/False
        '''
        time.sleep(2)
        if not self.modem.is_open:
            print('Modem is closed. !!')
            return False
        
        self.modem.reset_input_buffer()
        self.modem.flush()
        #
        if verbose:
            print('Testing AT...',end='')
        self.modem.write('AT\r'.encode())
        time.sleep(1)
        response = self.modem.read(100).decode()
        if 'OK' not in response:
            print(f'No responde AT. RSP={response}\rExit.')
            self.modem_prendido = False
            return False
        #
        self.modem_prendido = True
        if verbose:
            print('Modem responde.')
        return True
    
    def prender_modem(self, verbose=True):
        '''
        Manda el comando AT*PWRON y espera 15 secs. No chequea la respuesta.
        '''
        if verbose:
            print('Prendiendo Modem (30s)...')

        if self.modem.is_open:
            try:
                self.modem.write('AT*PWRON\r'.encode())
            except Exception as e:
                print(f'SMSdaemon: ERROR al enviar AT*PWRON. Exception {e}.')
                return
            #
            for i in range(30):
                time.sleep(1)
                response = self.modem.read(200).decode()
                if 'PB DONE' in response:
                    break
            if verbose:
                print(response)
        else:
            print('Modem is closed. !!')
 
    def apagar_modem(self, verbose=True):
        '''
        Manda el comando AT*PWROFF y espera 5s
        '''
        if verbose:
            print('Apagando Modem...')

        if self.modem.is_open:
            try:
                self.modem.write('AT*PWROFF\r'.encode())
            except Exception as e:
                print(f'\rSMSdaemon: ERROR al enviar AT*PWROFF. Exception {e}.')
                return
            #
            time.sleep(5)
        else:
            print('Modem is closed. !!')

    def send(self, l_sms_pendientes):
        '''
        Recibe una lista de mensajes y envia los mensajes de la lista, y actualiza el estado en la BD.
        '''
        # print(f'SMSdaemon: {len(l_sms_pendientes)} queued sms.')
        for sms in l_sms_pendientes:
            time.sleep(5)
            sms_id = sms.get('id',0)
            sms_numero = sms.get('sms_numero','00000')
            sms_mensaje = sms.get('sms_mensaje','Err')
            print(f'NUMERO={sms_numero}')
            print(f'MSJ={sms_mensaje}')
            # Envio por el modem.
            if self.send_sms( sms_number=sms_numero, sms_message=sms_mensaje):
                # Actualizo el status del mensaje a ENVIADO
                try:
                    d_params = {'id':sms_id,'estado':'ENVIADO'}
                    print(f'DEBUG={d_params}')
                    r_conf = requests.put(f"http://{APISMS_HOST}:{APISMS_PORT}/apisms/sms", json=d_params, timeout=10 )
                    if r_conf.status_code == 200:
                        print(f'SMSdaemon: SMS {sms_id} sent OK')
                #
                except requests.exceptions.RequestException as err: 
                    print( f'SMSdaemon: ApiSMS request exception, HOST:{APISMS_HOST}:{APISMS_PORT}, Err:{err}')
                    return
            else:
                print(f'Error al enviar SMS {sms_id}.')
            
    def send_sms(self, serial_port=SERIALPORT, sms_number='0123456789', sms_message='', verbose=True):
        '''
        Funcion que se conecta al modem por el puerto serial y envia los mensajes
        '''
        self.open_device()
        time.sleep(2)
        if self.modem.is_open:
            print('Modem open.')
        else:
            print('Modem open Error !!!.')
            return False
        
        for i in range(3):
            # Si responde el AT, sigo.
            if self.test_responses():
                break
            #
            # Apago e intento prenderlo
            self.apagar_modem()
            self.prender_modem()
            time.sleep(10)
        #
        # Vemos si sali porque esta prendido o porque no puede prenderlo
        if not self.modem_prendido:
            print('SMSdaemon: ERROR modem no prendió !!')
            self.close_device()
            return False
        #
        # El modem está prendido: mando mensaje
        if verbose:
            print('Envio numero...')
        self.modem.write(f'AT*SMSNBR={sms_number}\r'.encode())
        time.sleep(1)
        if verbose:
            print('Envio mensaje...')
        self.modem.write(f'AT*SMSMSG={sms_message}\r'.encode())
        time.sleep(1)
        self.modem.reset_input_buffer()
        self.modem.flush()
        if verbose:    
            print('Envio SMS...')
        self.modem.write(f'AT*SMSSEND\r'.encode())
        sms_sent = False
        if verbose:
            print('Espero hasta 20s...')
        for i in range(20):
            time.sleep(1)
            response = self.modem.read(200).decode()
            if "SMS: Sent OK" in response:
                sms_sent = True
                print(f'Sent OK to {sms_number}')
                if verbose:
                    print(response)
                break
        #
        if not sms_sent:
            print(f'TIMEOUT:{response}')
            self.close_device()
            return False
        #
        self.close_device()
        return True

if __name__ == '__main__':
    
    print('Starting SMSdaemon:')
    print(f'Serial port: {SERIALPORT}')
    print(f'Sleeptime: {SLEEPTIME}')
    print(f'APIsms: {APISMS_HOST}:{APISMS_PORT}')
    print('running...')

    sms_engine = SmsEngine()
   
    while True:
        try:
             # Leemos si hay datos para enviar
            params={'count':0}
            r_conf = requests.get(f"http://{APISMS_HOST}:{APISMS_PORT}/apisms/sms_pendientes",json=params, timeout=10 )
            if r_conf.status_code == 200:
                d_rsp = r_conf.json()
                nro_sms_pendientes = d_rsp.get('count',0)
                l_sms_pendientes = d_rsp.get('sms_pendientes',[])
                print(f'SMSdaemon: Hay {nro_sms_pendientes} sms pendiente.')
                # Hay datos: los envio
                if len(l_sms_pendientes) > 0:
                     sms_engine.send(l_sms_pendientes) 
                #               
            else:
                print(f'status={r_conf.status_code}')
        except requests.exceptions.RequestException as err: 
            print( f'SMSdaemon: ApiSMS request exception, HOST:{APISMS_HOST}:{APISMS_PORT}, Err:{err}')

        print('Sleeping...')
        time.sleep(SLEEPTIME)