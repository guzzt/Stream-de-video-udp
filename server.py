#!/usr/bin/env python
# coding: utf-8
from   socket   import *
from   io       import *
from   os       import path,stat
from   optparse import OptionParser
import struct

CANALDADOS  = socket(AF_INET,SOCK_DGRAM)
CANALCONTR  = socket(AF_INET,SOCK_STREAM)

TAM_MSGS_PROTOCOL  = 256
RETRASMITIR        = 22
NAO_RETRASMITIR    = 20
ENVIAR_MAIS        = 'MANDA_MAIS'
ARQUIVO_N_EXISTE   = 'Arquivo nao encontrado'
ARQUIVO_EXISTE     = 'Iniciando trasferencia'

def IncializaServidor(canalDados,CanalControle,host,port):
	"""Inicialização dos canais de dados (UDP) e de controle (TCP)"""
	canalDados.bind((host,port))
	CanalControle.bind((host,port+1)) #O canal de controle executará em um porto acima do porto do canal de dados 

def RecebeNomeVideo(canalControle):
	"""Espera um cliente solicitar um video para dar inicio a conexao"""
	canalControle.listen(1)
	conn,cliente_addr = canalControle.accept()
	resp = conn.recv(TAM_MSGS_PROTOCOL)
	return (conn,resp.decode())

def ArquivoExiste(nomeArq):
	return path.isfile(nomeArq)

def ErroArquivo(conexao):
	"""Envia mensagem de erro para o cliente caso o video não exista"""
	conexao.sendall(ARQUIVO_N_EXISTE.encode())
	CANALDADOS.close()
	CANALCONTR.close()
	exit(0);

def Retrasmitir(canalDados,cliente_addr,conexao,dic_pkt):
	"""
	   Aguarda o cliente informar se será necessario retrasmitir algum pacote, se for necessario os pacotes que serão 
	   retrasmitidos serão informados atráves de uma máscara de bits,
	"""
	while True: #só sai do laço quando não for necessario retrasmissão
		pkt_retrasm = conexao.recv(TAM_PACOTE_RETRASMISSAO)
		msg_Prot,maskBits = struct.unpack(fmt_struct_Retrasmissao,pkt_retrasm);
		maskBits = maskBits.decode()

		if(msg_Prot == RETRASMITIR):
			bit = 0
			print("[!]RETRASMITIR: " + maskBits)
			for pkt in dic_pkt.items(): #perrcorre a máscara de bits e reenvia os pacotes necessários
				if((maskBits[bit] == '1') or (bit == TAM_BUFFER-1)):  
					canalDados.sendto(dic_pkt[pkt[0]],cliente_addr)
					print("[+]Pacote Retrasmitido: "+str(pkt[0]))
				bit += 1
		else:
			break

def EnviaVideo(canalDados,cliente_addr,conexao,video):
	"""
		Lê o arquivo e constroi os pacotes inserindo um numero de sequencia, em seguida armazena N pacotes em um dicionario
		e aguarda o cliente solicitar o envio, caso seja necessario é feita a retrasmissão.
	"""
	f          = FileIO(video);
	buff       = BufferedReader(f)
	pkt_env    = 0 #Quantidade de pacotes enviados
	cont       = 0 #contador do numero de sequencia de cada pacote
	dic_pkt    = {} #dicionario de pacotes a chave é o numero do pacote e o valor é o proprio pacote
	payload    = buff.read(TAM_PAYLOAD); #bytes do arquivo que será enviado
	qtdpacotes = int(stat(video).st_size/TAM_PAYLOAD) #Quantidade total de pacotes da trasmissão

	auxcont = qtdpacotes
	while(auxcont > 0): #Só sai do laço após todos os bytes do arquivo serem enviados
		pkt  = struct.pack(fmt_struct,cont,payload)
		dic_pkt[cont] = pkt
		cont += 1

		if((len(dic_pkt) == TAM_BUFFER) or (not payload)): #O servidor estará pronto para enviar os pacotes quando o dicionario estiver com o tamanho max ou quando os bytes do arquivo acabarem
			msg = conexao.recv(TAM_MSGS_PROTOCOL) #So envia quando o cliente solicitar
			if(msg.decode() == ENVIAR_MAIS):

				lst_aux = []
				keys = dic_pkt.keys() #Pega do dicionario a menor chave e a maior
				for k in keys:
					lst_aux.append(k)
				lst_aux.sort()
				inicio = lst_aux[0]  #menor
				final  = lst_aux[-1] #maior

				strct_pkt  = struct.pack('ii',inicio,final) #envia o primeiro e o ultimo elemento do dicionario
				conexao.sendall(strct_pkt)

				for p in dic_pkt.values(): #envia os pacotes que estao no dicionario
					print('[+]Enviando '+str(pkt_env)+' de '+str(qtdpacotes+1))
					canalDados.sendto(p,cliente_addr)
					pkt_env += 1
					auxcont -= 1

				Retrasmitir(canalDados,cliente_addr,conexao,dic_pkt) #Pra cada rajada de pacotes, pergunta o cliente se será necessario retrasmissao
				dic_pkt = {} 
		payload = buff.read(TAM_PAYLOAD)

	print('[+]Acabou')
	msg = conexao.recv(TAM_MSGS_PROTOCOL) #Quando todos os bytes forem enviados, o servidor manda uma tupla de 0s para o cliente para encerrar a conexão
	if(msg.decode() == ENVIAR_MAIS):
		strct_pkt = struct.pack('ii',0,0)
		conexao.sendall(strct_pkt);
		return

def RecebeCanalStream(canalDados):
	"""Recebe o endereço e o porto para o fluxo de pacotes UDP"""
	msg,cliente_addr = canalDados.recvfrom(TAM_MSGS_PROTOCOL)
	return cliente_addr

def main():

	parser = OptionParser(usage="usage: [options] -h <Endereço servidor> ",conflict_handler="resolve")
	parser.add_option("-h","--host",type='string',dest='host_addr',default='0.0.0.0')
	parser.add_option('--port',type='int',dest='port',default=4444)
	parser.add_option('--buffer_len', type='int',dest='tam_buffer', default=50)
	parser.add_option('--payload_len',type='int',dest='tam_payload',default=12288)
	(options,args) = parser.parse_args()


	global HOST,PORT,TAM_BUFFER,TAM_PAYLOAD,SERVER,fmt_struct,fmt_struct_Retrasmissao,TAM_PACOTE_RETRASMISSAO
	HOST = options.host_addr
	PORT = options.port
	TAM_BUFFER  = options.tam_buffer
	TAM_PAYLOAD = options.tam_payload
	fmt_struct  = 'i%ds' % TAM_PAYLOAD  
	fmt_struct_Retrasmissao = 'i%ds' % TAM_BUFFER
	TAM_PACOTE_RETRASMISSAO = len(struct.pack(fmt_struct_Retrasmissao,55,'a'.encode()))

	IncializaServidor(CANALDADOS,CANALCONTR,HOST,PORT)
	conexao,nomeArq = RecebeNomeVideo(CANALCONTR)
	if(ArquivoExiste(nomeArq)):
		conexao.sendall(ARQUIVO_EXISTE.encode()) #O video existe
		cliente_addr = RecebeCanalStream(CANALDADOS)
		EnviaVideo(CANALDADOS,cliente_addr,conexao,nomeArq)
	else:
		ErroArquivo(conexao) #O video nao existe
	CANALDADOS.close()
	CANALCONTR.close()

if __name__ == '__main__':
	main()