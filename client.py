#!/usr/bin/env python
# coding: utf-8

from   socket import *
from   io     import *
from   random import randint
import struct
import time

HOST        = 'localhost'
PORT        = 4444
SERVER      = (HOST,PORT)
TAM_BUFFER  = 50
TAM_PAYLOAD = 12288
fmt_struct  = 'i%ds' % TAM_PAYLOAD
CANALDADOS  = socket(AF_INET,SOCK_DGRAM)
CANALCONTR  = socket(AF_INET,SOCK_STREAM)
TAM_PACOTE  = len(struct.pack(fmt_struct,55,'a'.encode()))
TAM_MSGS_PROTOCOL = 256

PACOTES_RECEBIDOS = 0

class Buffer():
	def __init__(self):
		self.lst = [];
		#threading.Thread.__init__(self)
	def BuffCheio(self):
		return len(self.lst) == TAM_BUFFER

	def run(self):
		while not self.BuffCheio():
			try:
				global CONTADOR_SUPREMO
				CANALDADOS.settimeout(5)
				pkt,s = CANALDADOS.recvfrom(TAM_PACOTE);
				self.lst.append(pkt)
			except: 
				return True
		return True

	def isEmpty(self):
		return len(self.lst) == 0;


def RequisicaoVideo(canalControle,host,port,nomeVideo):
	"""Envia o nome do video e recebe uma resposta do servidor se o video existe ou nao"""
	canalControle.connect((host,port+1))
	canalControle.sendall(nomeVideo.encode())
	resp = canalControle.recv(TAM_MSGS_PROTOCOL);
	print(resp.decode())
	if(resp.decode() == 'ERROR'):
		print("[-]Erro na solicitacao do video!")
		exit(0);
	elif(resp.decode() == 'OK'):
		print('[+]Iniciando Tranferencia')

def EscreveBuffer(canalDados,host,port,arq,buff,canalControle):
	global PACOTES_RECEBIDOS
	PACOTES_RECEBIDOS += len(buff.lst)
	print("[+]Quantidade de pacotes recebidos: "+str(PACOTES_RECEBIDOS))
	buff.lst.sort() #Ordeno a lista antes de percorrela

	while not buff.isEmpty():
		pkt = buff.lst[0] #pega o primeiro pacote da fila
		n,payload = struct.unpack(fmt_struct,pkt) #descompacta
		print("[?]Escrevendo pacote: "+str(n))
		buff.lst.remove(pkt) #remove o primeiro pacote da fila
		arq.write(payload) #escreve o payload do pacote no arquivo

	canalControle.sendall('MANDA_MAIS'.encode())
	resp = canalControle.recv(TAM_MSGS_PROTOCOL);
	if(resp.decode() == 'NAO_TEM'):
		return False;
	elif(resp.decode() == 'ENVIANDO_MAIS'):
		print('[+]Recebendo mais')
		return True; 

def InicializaStream(canalDados,host,port):
	canalDados.sendto('Vamo_Vamo'.encode(),(host,port))
	print("[-]Enderco enviado")

def main():
	video = input("Informe o nome do video: "); 
	nomeArq = "Eitam"
	arq  = open(nomeArq,"wb");
	buff = Buffer();

	RequisicaoVideo(CANALCONTR,HOST,PORT,video)
	InicializaStream(CANALDADOS,HOST,PORT)

	time.sleep(1)
	CANALCONTR.sendall('MANDA_MAIS'.encode())
	while buff.run():
		if(not EscreveBuffer(CANALDADOS,HOST,PORT,arq,buff,CANALCONTR)):
			break;

	CANALDADOS.close()
	CANALCONTR.close()
	arq.close()
if __name__ == '__main__':
	main()