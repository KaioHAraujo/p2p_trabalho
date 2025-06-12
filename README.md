# Projeto P2P com Envio de Arquivos

Este projeto implementa um sistema peer-to-peer (P2P) com um nó central (Super Peer) responsável por distribuir tarefas, receber arquivos e monitorar a atividade dos peers conectados.

## FUNCIONALIDADES

- Descoberta do Super Peer via UDP Broadcast
- Registro de Peers via conexão TCP
- Heartbeat para verificação de atividade dos peers
- Envio de arquivos dos peers para o Super Peer
- Armazenamento local dos arquivos recebidos

## COMO EXECUTAR

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/KaioHAraujo/p2p_trabalho.git
   cd p2p_trabalho
   ```

2. **Instale os requisitos (opcional):**
   ```bash
   pip install -r requirements.txt
   ```

3. **Execute o Super Peer:**
   ```bash
   python super_peer/super_peer.py
   ```

4. **Execute os Peers (em terminais separados):**
   ```bash
   python nodes/peer.py
   ```

## ESTRUTURA DO PROJETO

```
p2p_trabalho-main/
├── .gitignore
├── README.md
├── requirements.txt
├── nodes/
│   ├── exemplo.txt
│   ├── peer.py
├── super_peer/
│   ├── super_peer.py
```

## AUTORES

- Projeto desenvolvido por estudantes para fins acadêmicos.
- Alunos: Kaio Araujo e equipe.
