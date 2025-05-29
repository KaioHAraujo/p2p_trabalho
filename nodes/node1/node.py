import socket
import threading
import os
import json
import time
import hashlib

PASTA_ARQUIVOS = "arquivos"
SUPER_PEER = ('localhost', 9000)
porta_local = int(input("Porta deste nó: "))
os.makedirs(PASTA_ARQUIVOS, exist_ok=True)

def calcular_checksum(caminho):
    hash_md5 = hashlib.md5()
    with open(caminho, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def listar_arquivos():
    return os.listdir(PASTA_ARQUIVOS)

def servidor():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("localhost", porta_local))
    s.listen(5)
    print(f"[Servidor {porta_local}] Escutando...")

    while True:
        conn, addr = s.accept()
        threading.Thread(target=lidar_com_pedido, args=(conn, addr)).start()

def lidar_com_pedido(conn, addr):
    try:
        nome_arquivo = conn.recv(1024).decode()
        caminho = os.path.join(PASTA_ARQUIVOS, nome_arquivo)
        if os.path.exists(caminho):
            with open(caminho, "rb") as f:
                conn.sendall(f.read())
        else:
            conn.send(b"ARQUIVO_NAO_ENCONTRADO")
    except Exception as e:
        print(f"Erro ao enviar arquivo: {e}")
    finally:
        conn.close()

def registrar():
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(SUPER_PEER)
            msg = {
                'tipo': 'registro',
                'porta': porta_local,
                'arquivos': listar_arquivos()
            }
            s.send(json.dumps(msg).encode())
            print("[Registro]", s.recv(1024).decode())
            s.close()
            break
        except:
            print("[Registro] Falha, tentando novamente em 5s...")
            time.sleep(5)

def buscar_lista():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(SUPER_PEER)
        s.send(json.dumps({'tipo': 'listar'}).encode())
        resposta = json.loads(s.recv(4096).decode())
        print("[LISTA GLOBAL]")
        for no, arquivos in resposta.items():
            print(f"{no} -> {arquivos}")
        s.close()
    except Exception as e:
        print("[Erro listagem]", e)

def buscar_arquivo(arquivo):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(SUPER_PEER)
        s.send(json.dumps({'tipo': 'buscar', 'arquivo': arquivo}).encode())
        destino = s.recv(1024).decode()
        s.close()
        if destino == "ARQUIVO_NAO_ENCONTRADO":
            print("Arquivo não encontrado na rede.")
            return

        ip, porta = destino.split(":")
        porta = int(porta)

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, porta))
        s.send(arquivo.encode())
        dados = s.recv(1024*1024)
        if dados == b"ARQUIVO_NAO_ENCONTRADO":
            print("O nó remoto não tem mais o arquivo.")
        else:
            with open(f"{PASTA_ARQUIVOS}/baixado_{arquivo}", "wb") as f:
                f.write(dados)
            checksum = calcular_checksum(f"{PASTA_ARQUIVOS}/baixado_{arquivo}")
            print(f"Arquivo '{arquivo}' baixado com sucesso.")
            print(f"Checksum: {checksum}")
        s.close()
    except Exception as e:
        print("[Erro ao buscar arquivo]", e)

if __name__ == "__main__":
    threading.Thread(target=servidor, daemon=True).start()
    time.sleep(1)
    registrar()

    while True:
        print("\nOpções:")
        print("1 - Ver lista global")
        print("2 - Baixar arquivo")
        print("3 - Sair")
        op = input("Escolha: ")
        if op == "1":
            buscar_lista()
        elif op == "2":
            nome = input("Nome do arquivo: ")
            buscar_arquivo(nome)
        else:
            break