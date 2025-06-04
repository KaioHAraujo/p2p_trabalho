
# Projeto P2P Escalável com Heartbeat

Este projeto implementa um sistema P2P distribuído onde Peers se conectam dinamicamente a um Master para receber, executar e devolver tarefas de processamento. O sistema inclui descoberta automática, registro, monitoramento por heartbeat, e envio de tarefas em formato ZIP.

## 🔧 Estrutura do Projeto

```
heartbeat_p2p_final_v2/
├── super_peer/
│   └── super_peer.py
├── nodes/
│   ├── node1/
│   │   ├── node.py
│   │   └── arquivos/
│   │       └── exemplo.txt
│   ├── node2/
│   │   ├── node2.py
│   │   └── arquivos/
│   └── node3/
│       ├── node3.py
│       └── arquivos/
└── tasks/
    └── exemplo.zip
```

## 🚀 Como Executar

### 1. Inicie o Master

```bash
cd super_peer
python super_peer.py
```

### 2. Inicie os Peers (em terminais diferentes)

```bash
cd nodes/node1
python node.py
```

```bash
cd nodes/node2
python node2.py
```

```bash
cd nodes/node3
python node3.py
```

## 📂 Como funciona a execução de tarefas

- O Master aguarda conexões na porta TCP e escuta broadcasts na porta UDP.
- Cada Peer faz broadcast, recebe o IP do Master e se registra via TCP.
- O Peer solicita uma tarefa (`REQUEST_TASK`).
- O Master envia um ZIP com `main.py` e `input.csv`.
- O Peer extrai o ZIP, executa `main.py`, gera `stdout.txt` e `stderr.txt`, e envia de volta para o Master.

## 📁 Exemplo de tarefa (ZIP)

O ZIP da tarefa deve conter:

- `main.py` – código que processa `input.csv`
- `input.csv` – arquivo com os dados de entrada

Ao final da execução, os arquivos `stdout.txt` e `stderr.txt` são gerados e reenviados ao Master como `result.zip`.

## ✅ Dependências

Instale as dependências com:

```bash
pip install -r requirements.txt
```

## 📜 Logs

Todos os eventos são registrados em tempo real:
- Registro
- Heartbeat
- Tarefas solicitadas
- Resultados recebidos

---

**Grupo:**
- Nome: [Seu Nome Aqui]
- RA: [Seu RA Aqui]
- Email: [seuemail@dominio.com]
