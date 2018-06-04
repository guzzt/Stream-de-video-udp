#!/usr/bin/env python
# coding: utf-8

from   socket import *
from   io     import *
from   random import shuffle
from   os     import path,stat
import struct

HOST        = 'localhost'
PORT        = 4444
SERVER      = (HOST,PORT)
TAM_BUFFER  = 50
TAM_PAYLOAD = 12288
fmt_struct  = 'i%ds' % TAM_PAYLOAD
CANALDADOS  = socket(AF_INET,SOCK_DGRAM)
CANALCONTR  = socket(AF_INET,SOCK_STREAM)
TAM_MSGS_PROTOCOL = 256

def IncializaServidor(canalDados,CanalControle,host,port):
	canalDados.bind((host,port))
	CanalControle.bind((host,port+1))

def RecebeNomeVideo(canalControle):
	canalControle.listen(1)
	conn,cliente_addr = canalControle.accept()
	resp = conn.recv(TAM_MSGS_PROTOCOL)
	return (conn,resp.decode())

def ArquivoExiste(nomeArq):
	return path.isfile(nomeArq)

def ErroArquivo(conexao):
	conexao.sendall('ERROR'.encode())
	CANALDADOS.close()
	CANALCONTR.close()
	exit(0);

def EnviaVideo(canalDados,cliente_addr,conexao,video):
	f = FileIO(video);
	buff = BufferedReader(f)
	cont = 0
	lst_pkt = []
	payload = buff.read(TAM_PAYLOAD);
	qtdpacotes = int(stat(video).st_size/TAM_PAYLOAD)
	arqDebug   = open("DebugVideo.m4v","wb")

	auxcont = qtdpacotes
	while(auxcont > 0):
		pkt  = struct.pack(fmt_struct,cont,payload);
		lst_pkt.append(pkt);
		cont += 1

		if((len(lst_pkt) == TAM_BUFFER) or (not payload)):
			msg = conexao.recv(TAM_MSGS_PROTOCOL)
			if(msg.decode() == 'MANDA_MAIS'):
				shuffle(lst_pkt)
				conexao.sendall('ENVIANDO_MAIS'.encode())
				for p in lst_pkt:
					n,aux = struct.unpack(fmt_struct,p)
					arqDebug.write(aux);
					print('[+]Enviando '+str(n)+' de '+str(qtdpacotes+1))
					canalDados.sendto(p,cliente_addr)
					auxcont -= 1
				lst_pkt = [];
		payload  = buff.read(TAM_PAYLOAD);
		

	arqDebug.close()
	print('[+]Acabou')
	msg = conexao.recv(TAM_MSGS_PROTOCOL)
	if(msg.decode() == 'MANDA_MAIS'):
		conexao.sendall('NAO_TEM'.encode());
		return

def RecebeCanalStream(canalDados):
	print("[-]Aguardando endereco do cliente")
	msg,cliente_addr = canalDados.recvfrom(TAM_MSGS_PROTOCOL)
	print(cliente_addr)
	return cliente_addr

def main():
	IncializaServidor(CANALDADOS,CANALCONTR,HOST,PORT)
	conexao,nomeArq = RecebeNomeVideo(CANALCONTR)
	if(ArquivoExiste(nomeArq)):
		conexao.sendall('OK'.encode()) #O video existe
		cliente_addr = RecebeCanalStream(CANALDADOS)
		EnviaVideo(CANALDADOS,cliente_addr,conexao,nomeArq)
	else:
		ErroArquivo(conexao) #O video nao existe
	CANALDADOS.close()
	CANALCONTR.close()

if __name__ == '__main__':
	main()