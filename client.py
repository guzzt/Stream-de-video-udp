#!/usr/bin/env python
# coding: utf-8
from   socket     import *
from   optparse   import OptionParser
from   subprocess import Popen
import struct

RETRASMITIR        = 22
NAO_RETRASMITIR    = 20 
TAM_MSGS_PROTOCOL  = 256
PACOTES_RECEBIDOS  = 0
CANALDADOS         = socket(AF_INET,SOCK_DGRAM)
CANALCONTR         = socket(AF_INET,SOCK_STREAM)
PATH_PLAYER        = '/usr/bin/mpv'
ENVIAR_MAIS        = 'MANDA_MAIS'
ARQUIVO_N_EXISTE   = 'Arquivo nao encontrado'
ARQUIVO_EXISTE     = 'Iniciando trasferencia'

class Buffer():
	def __init__(self,tamPkt,canalDados):
		self.dic = {};
		self.tamBuffer   = 0
		self._canalDados = canalDados
		self._tamPkt     = tamPkt 
		self.inicio      = 0
		self.final       = 0

	def BufferCompleto(self):
		return len(self.dic) == self.tamBuffer+1

	def run(self,qtdPkt):
		self.tamBuffer = qtdPkt

		while not self.BufferCompleto():
			try:
				self._canalDados.settimeout(2)
				pkt,s       = self._canalDados.recvfrom(self._tamPkt);
				n,payload   = struct.unpack(fmt_struct,pkt)
				print("[+]Chegou: "+str(n))
				if((n >= self.inicio) and (n <= self.final)):
					self.dic[n] = payload
			except:
				return True
		return True
	
	def CriaMask(self):		
		maskBits = ''
		count    = 0
		for i in range(self.inicio,self.final):
				if(i in self.dic):
					maskBits += '0'
				else:
					maskBits += '1'
					print("[-]Pacote faltando: "+str(i))
					count    +=  1		
		return (maskBits,count)	

	def Esvazia(self):
		self.dic = {}
		self.tamBuffer = 0

	def isEmpty(self):
		return len(self.dic) == 0;


def RequisicaoVideo(canalControle,host,port,nomeVideo):
	"""Envia o nome do video e recebe uma resposta do servidor se o video existe ou nao"""
	canalControle.connect((host,port+1))
	canalControle.sendall(nomeVideo.encode())
	resp = canalControle.recv(TAM_MSGS_PROTOCOL);
	if(resp.decode() == ARQUIVO_N_EXISTE):
		print("[-]Erro na solicitacao do video!")
		exit(0);
	elif(resp.decode() == ARQUIVO_EXISTE):
		print('[+]Iniciando Tranferencia')

def SolicitaRetrasmissao(buff,canalControle):
	"""Verifica se será necessario fazer retrasmissao, e envia a resposta para o servidor, com uma mascara de bits"""
	if(len(buff.dic) < buff.tamBuffer): #se o tamanho do dicionario for menor que o tamanho esperado, pede retrasmissao
		mskBits,qtd_retrasm = buff.CriaMask()
		struct_pkt = struct.pack(fmt_struct_Retrasmissao,RETRASMITIR,mskBits.encode())
		canalControle.send(struct_pkt)
		return qtd_retrasm #Quantidade de pacotes que será necessario retrasmitir
	else:
		struct_pkt = struct.pack(fmt_struct_Retrasmissao,NAO_RETRASMITIR,'00'.encode())
		canalControle.send(struct_pkt)
		return 0

def EscreveBuffer(canalDados,host,port,arq,buff,canalControle):
	"""Escreve os pacotes que estão armazenados no buffer em um arquivo, em seguida solicita ao servidor mais pacotes"""
	global PACOTES_RECEBIDOS
	
	retrasmitir = SolicitaRetrasmissao(buff,canalControle)
	while retrasmitir != 0: #Solicita retrasmissao até que todos os pacotes da rajada chegue
		buff.run(buff.tamBuffer)
		retrasmitir = SolicitaRetrasmissao(buff,canalControle)

	for n in range(buff.inicio,buff.final+1): #Escreve no arquivo o payload de cada pacote na ordem do numero de sequencia dos pacotes
		try:
			payload = buff.dic.pop(n)  #remove o payload do buffer
			PACOTES_RECEBIDOS += 1 
		except Exception as e:
			print("[-]Erro ao remover: "+str(e))
		arq.write(payload) #escreve o payload do pacote no arquivo

	canalControle.sendall(ENVIAR_MAIS.encode()) 
	resp = canalControle.recv(8); #Retorna uma tupla que contem o numero do pacote inicial e final da rajada, ou 0 se o arquivo foi enviado
	if(resp == b'\x00\x00\x00\x00\x00\x00\x00\x00'): #(0,0)
		return 0;
	else:
		return resp; 

def InicializaPlayer(nomeVideo):
	Popen([PATH_PLAYER,nomeVideo])

def InicializaStream(canalDados,host,port):
	"""Envia uma mensagem no canal de strem, para o servidor obter o endereço e o porto do canal de dados"""
	canalDados.sendto('Enviando_Endereco'.encode(),(host,port))
	print("[+]Endereço enviado")

def main():

	parser = OptionParser(usage="usage: [options] -h <Endereço servidor> -f <video>",conflict_handler="resolve")
	parser.add_option("-h","--host",type='string',dest='host_addr',help='Especifique o IP do servidor.')
	parser.add_option('-f','--file',type='string',dest='video',help='Especifique o nome do video.')
	parser.add_option('--port',type='int',dest='port',default=4444)
	parser.add_option('--buffer_len', type='int',dest='tam_buffer', default=50)
	parser.add_option('--payload_len',type='int',dest='tam_payload',default=12288)
	(options,args) = parser.parse_args()

	if((not options.host_addr) or (not options.video)):
		print(parser.usage)
		exit(0)

	#Inicializo as variaveis  globais
	global HOST,PORT,TAM_BUFFER,TAM_PAYLOAD,SERVER,fmt_struct,fmt_struct_Retrasmissao,TAM_PACOTE,TAM_PACOTE_RETRASMISSAO
	HOST = options.host_addr
	PORT = options.port
	TAM_BUFFER  = options.tam_buffer
	TAM_PAYLOAD = options.tam_payload
	fmt_struct  = 'i%ds' % TAM_PAYLOAD  
	fmt_struct_Retrasmissao = 'i%ds' % TAM_BUFFER
	TAM_PACOTE = len(struct.pack(fmt_struct,55,'a'.encode()))
	TAM_PACOTE_RETRASMISSAO = len(struct.pack(fmt_struct_Retrasmissao,55,'a'.encode()))

	video   = options.video 
	nomeArq = "Received-"+video
	arq     = open(nomeArq,"wb");
	buff    = Buffer(TAM_PACOTE,CANALDADOS);

	RequisicaoVideo(CANALCONTR,HOST,PORT,video)
	InicializaStream(CANALDADOS,HOST,PORT)

	CANALCONTR.sendall(ENVIAR_MAIS.encode())
	resp = CANALCONTR.recv(8)
	inicio,final = struct.unpack('ii',resp)
	buff.inicio  = inicio
	buff.final   = final
	tam = (final - inicio)

	flag = 0
	while buff.run(tam):
		resp = EscreveBuffer(CANALDADOS,HOST,PORT,arq,buff,CANALCONTR)
		if(flag == 1):
			InicializaPlayer(nomeArq)
		flag += 1
		if(resp == 0):
			break;	
		inicio,final = struct.unpack('ii',resp)
		tam = (final - inicio)
		buff.inicio  = inicio
		buff.final   = final

	print("[+]Quantidade de pacotes recebidos: "+str(PACOTES_RECEBIDOS-1))
	CANALDADOS.close()
	CANALCONTR.close()
	arq.close()

if __name__ == '__main__':
	main()
