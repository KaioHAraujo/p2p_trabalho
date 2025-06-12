import socket
import threading
import json
import uuid
import time
import base64
import os
import shutil
import subprocess
import zipfile

# --- CONFIGURAÇÃO ---
peer_id = str(uuid.uuid4())
master_ip = None  # Removido IP fixo, será descoberto automaticamente
master_port = None # Será descoberto automaticamente
DISCOVERY_PORT = 50001 # Porta de descoberta (deve ser a mesma do super-peer)

my_p2p_port = 0
WORK_DIR = 'work'
P2P_RECEIVED_DIR = 'p2p_received'

os.makedirs(WORK_DIR, exist_ok=True)
os.makedirs(P2P_RECEIVED_DIR, exist_ok=True)

def discover_super_peer():
    """
    Envia um broadcast UDP para encontrar o super-peer na rede local.
    Retorna o IP e a porta do super-peer se encontrado.
    """
    global master_ip, master_port
    print("[DISCOVERY] Procurando por Super-Peer na rede...")
   
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(5.0) # Espera por 5 segundos

        discover_message = json.dumps({"action": "DISCOVER_SUPER_PEER"})
       
        try:
            sock.sendto(discover_message.encode(), ('<broadcast>', DISCOVERY_PORT))
           
            # Espera pela resposta do super-peer
            data, addr = sock.recvfrom(1024)
            response = json.loads(data.decode())

            if response.get("action") == "SUPER_PEER_ANNOUNCEMENT":
                master_ip = response["ip"]
                master_port = response["port"]
                print(f"[DISCOVERY] Super-Peer encontrado em {master_ip}:{master_port}")
                return True
        except socket.timeout:
            print("[DISCOVERY] Nenhum Super-Peer encontrado na rede. Timeout.")
            return False
        except Exception as e:
            print(f"[DISCOVERY] Erro durante a descoberta: {e}")
            return False
    return False

# --- FUNÇÕES DE COMUNICAÇÃO ---

def tcp_send_to_master(msg):
    """Envia uma mensagem TCP para o Super-Peer e retorna a resposta."""
    if not master_ip or not master_port:
        print("[ERRO MASTER] IP do Super-Peer não foi descoberto.")
        return None
       
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((master_ip, master_port))
            # Usar sendall para garantir que toda a mensagem seja enviada
            s.sendall(json.dumps(msg).encode('utf-8'))
           
            # Buffer grande para receber pacotes de tarefas
            response_data = s.recv(1048576).decode('utf-8')
            return json.loads(response_data)
    except Exception as e:
        print(f"[ERRO MASTER] Falha na comunicação com o Super-Peer: {e}")
        return None

# --- FUNÇÕES DE PROCESSAMENTO DE TAREFA ---

def process_task(task_name, task_data_b64):
    """Lógica completa para processar uma tarefa recebida."""
    print(f"\n[TAREFA] Iniciando processamento da tarefa: {task_name}")
    task_work_dir = os.path.join(WORK_DIR, task_name.replace('.zip', ''))
    os.makedirs(task_work_dir, exist_ok=True)
    task_zip_path = os.path.join(WORK_DIR, task_name)

    try:
        # 1. Decodificar e salvar o ZIP da tarefa
        with open(task_zip_path, 'wb') as f:
            f.write(base64.b64decode(task_data_b64))

        # 2. Extrair o conteúdo do ZIP
        with zipfile.ZipFile(task_zip_path, 'r') as zip_ref:
            zip_ref.extractall(task_work_dir)
        print(f"[TAREFA] Arquivos extraídos em: {task_work_dir}")

        # 3. Executar o script main.py e capturar saídas
        main_script_path = os.path.join(task_work_dir, 'main.py')
        stdout_path = os.path.join(task_work_dir, 'stdout.txt')
        stderr_path = os.path.join(task_work_dir, 'stderr.txt')

        print("[TAREFA] Executando main.py...")
        with open(stdout_path, 'w') as f_out, open(stderr_path, 'w') as f_err:
            subprocess.run(
                ['python', main_script_path],
                cwd=task_work_dir,
                stdout=f_out,
                stderr=f_err,
                check=False # Não lança exceção se o script falhar
            )
        print("[TAREFA] Execução concluída. Saídas salvas.")

        # 4. Compactar os resultados em um novo ZIP
        result_zip_path = os.path.join(WORK_DIR, f"result_{task_name}")
        with zipfile.ZipFile(result_zip_path, 'w') as zip_ref:
            zip_ref.write(stdout_path, arcname='stdout.txt')
            zip_ref.write(stderr_path, arcname='stderr.txt')
        print("[TAREFA] Resultados compactados.")

        # 5. Ler o ZIP de resultado e codificar em Base64
        with open(result_zip_path, 'rb') as f:
            result_data_b64 = base64.b64encode(f.read()).decode('utf-8')

        # 6. Enviar o resultado para o Super-Peer
        print("[TAREFA] Enviando resultados para o Super-Peer...")
        submit_msg = {
            "action": "SUBMIT_RESULT",
            "peer_id": peer_id,
            "result_name": task_name, # Envia o nome da tarefa original
            "result_data": result_data_b64
        }
        response = tcp_send_to_master(submit_msg)
        if response and response.get("status") == "OK":
            print("[TAREFA] Resultado enviado com sucesso!")
        else:
            print(f"[TAREFA] Falha ao enviar resultado: {response}")

    except Exception as e:
        print(f"[ERRO TAREFA] Falha ao processar {task_name}: {e}")
    finally:
        # 7. Limpar o diretório de trabalho
        shutil.rmtree(task_work_dir, ignore_errors=True)
        if os.path.exists(task_zip_path):
            os.remove(task_zip_path)
        if 'result_zip_path' in locals() and os.path.exists(result_zip_path):
            os.remove(result_zip_path)
        print(f"[TAREFA] Limpeza concluída para {task_name}.")


# --- LOOP PRINCIPAL E THREADS ---

def register(p2p_port_to_register):
    print(f"Registrando no Super-Peer {master_ip}:{master_port}...")
    msg = {"action": "REGISTER", "peer_id": peer_id, "p2p_port": p2p_port_to_register}
    res = tcp_send_to_master(msg)
    if res and res.get("status") == "REGISTERED":
        print("[MASTER] Registro bem-sucedido!")
        return True
    print(f"[MASTER] Falha no registro: {res}")
    return False

def heartbeat():
    while True:
        time.sleep(30)
        tcp_send_to_master({"action": "HEARTBEAT", "peer_id": peer_id})
        print("(Heartbeat enviado)")

def main_task_loop():
    """Loop principal que solicita e processa tarefas de forma autônoma."""
    while True:
        print("\n--- Solicitando nova tarefa ---")
        req_msg = {"action": "REQUEST_TASK", "peer_id": peer_id}
        response = tcp_send_to_master(req_msg)

        if response and response.get("task_name"):
            task_name = response["task_name"]
            task_data = response["task_data"]
            process_task(task_name, task_data)
        else:
            print("Nenhuma tarefa disponível no momento. Aguardando...")
            time.sleep(15) # Aguarda antes de pedir novamente

if __name__ == "__main__":
    # 1. Descobre o Super-Peer na rede
    if not discover_super_peer():
        print("Encerrando programa por não encontrar um Super-Peer.")
        os._exit(1)

    # 2. Registra no Super-Peer descoberto
    if not register(my_p2p_port): # Envia 0 se o P2P não for usado
        print("Encerrando programa por falha no registro.")
        os._exit(1)

    # 3. Inicia o heartbeat em uma thread separada
    heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
    heartbeat_thread.start()

    # 4. Inicia o loop de processamento de tarefas
    main_task_loop()