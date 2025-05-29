import socket
import threading
import json

PORTA = 9000
base_dados = {}  # { 'ip:porta': [arquivos] }

def lidar_com_nodo(conn, addr):
    try:
        dados = conn.recv(4096).decode()
        dados_json = json.loads(dados)
        tipo = dados_json['tipo']

        if tipo == 'registro':
            chave = f"{addr[0]}:{dados_json['porta']}"
            base_dados[chave] = dados_json['arquivos']
            conn.send("Registro OK".encode())

        elif tipo == 'listar':
            conn.send(json.dumps(base_dados).encode())

        elif tipo == 'buscar':
            arquivo = dados_json['arquivo']
            for no, arquivos in base_dados.items():
                if arquivo in arquivos:
                    conn.send(no.encode())
                    return
            conn.send("ARQUIVO_NAO_ENCONTRADO".encode())

        else:
            conn.send("Comando desconhecido".encode())

    except Exception as e:
        print(f"Erro com {addr}: {e}")
    finally:
        conn.close()

def servidor():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('localhost', PORTA))
    s.listen(10)
    print(f"[SuperPeer] Escutando na porta {PORTA}")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=lidar_com_nodo, args=(conn, addr)).start()

if __name__ == "__main__":
    servidor()