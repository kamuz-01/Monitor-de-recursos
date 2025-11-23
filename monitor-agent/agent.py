#!/usr/bin/env python3
import psutil
import time
import requests
import socket
import json
import os
from datetime import datetime, timezone
import argparse
import platform
import uuid
from pathlib import Path

AGENT_ID_FILE = "/var/lib/monitor-agent/agent_id.txt"
PENDING_QUEUE_FILE = "/var/lib/monitor-agent/pending_metrics.json"  # ← NOVO

def ensure_directories():
    Path("/var/lib/monitor-agent").mkdir(parents=True, exist_ok=True)

def load_agent_id():
    ensure_directories()
    if os.path.exists(AGENT_ID_FILE):
        with open(AGENT_ID_FILE, "r") as f:
            return f.read().strip()
    new_id = str(uuid.uuid4())
    with open(AGENT_ID_FILE, "w") as f:
        f.write(new_id)
    return new_id

def get_real_ip():
    """Detecta o IP real da interface de rede principal."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0.1)
    try:
        s.connect(('10.254.254.254', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def collect_sample():
    cpu_percent = psutil.cpu_percent(interval=1)
    memory_percent = psutil.virtual_memory().percent
    return cpu_percent, memory_percent

# ===== NOVO: Gerenciar fila em disco =====

def load_pending_from_disk():
    """Carrega métricas não enviadas do arquivo no disco."""
    if os.path.exists(PENDING_QUEUE_FILE):
        try:
            with open(PENDING_QUEUE_FILE, "r") as f:
                pending = json.load(f)
                if pending:
                    print(f"[DISCO] Carregadas {len(pending)} métricas do arquivo de fila")
                return pending
        except Exception as e:
            print(f"[ERRO] Falha ao ler fila do disco: {e}")
            return []
    return []

def save_pending_to_disk(pending):
    """Persiste métricas não enviadas em disco."""
    try:
        with open(PENDING_QUEUE_FILE, "w") as f:
            json.dump(pending, f)
            if pending:
                print(f"[DISCO] {len(pending)} métricas guardadas no arquivo")
    except Exception as e:
        print(f"[ERRO] Falha ao salvar fila em disco: {e}")

def format_metric(hostname, ip, ts, cpu, mem):
    """Converte dados no formato que o Django espera."""
    return [
        {
            "hostname": hostname,
            "ip": ip,
            "metric_type": "cpu_percent",
            "timestamp": ts,
            "value": cpu
        },
        {
            "hostname": hostname,
            "ip": ip,
            "metric_type": "memory_percent",
            "timestamp": ts,
            "value": mem
        }
    ]

def send_to_api(api_url, metrics):
    try:
        resp = requests.post(api_url, json=metrics, timeout=5)
        if resp.status_code in (200, 201):
            print(f"[OK] Enviado {len(metrics)} métricas")
            return True
        print(f"[ERRO] API {resp.status_code}: {resp.text}")
        return False
    except Exception as e:
        print(f"[FALHA] {e}")
        return False

def run_loop(api_url, hostname=None, interval=60):
    if hostname is None:
        hostname = socket.gethostname()

    machine_id = load_agent_id()
    real_ip = get_real_ip()

    print(f"[AGENTE] Iniciado para {hostname}")
    print(f"[IP REAL] {real_ip}")
    print(f"[ID] {machine_id}")
    print(f"[Intervalo] {interval}s")
    print(f"[FILA DISCO] {PENDING_QUEUE_FILE}")

    # ===== NOVO: Carregar fila do disco ao iniciar =====
    pending = load_pending_from_disk()

    while True:
        current_ip = get_real_ip()
        
        cpu, mem = collect_sample()
        ts = datetime.now(timezone.utc).isoformat()

        batch = format_metric(hostname, current_ip, ts, cpu, mem)

        print(f"[{datetime.now().strftime('%H:%M:%S')}] IP={current_ip} CPU={cpu:.1f}% MEM={mem:.1f}%")

        # Junta buffer antigo + métrica nova
        to_send = pending + batch
        ok = send_to_api(api_url, to_send)

        if ok:
            pending = []  # Limpa fila em memória
            # ===== NOVO: Apagar arquivo de fila após sucesso =====
            if os.path.exists(PENDING_QUEUE_FILE):
                os.remove(PENDING_QUEUE_FILE)
                print("[DISCO] Arquivo de fila removido após sucesso")
        else:
            print("[BUFFER] Guardando métricas não enviadas")
            pending += batch
            # ===== NOVO: Persist para disco =====
            save_pending_to_disk(pending)

        time.sleep(interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", required=True)
    parser.add_argument("--hostname", default=None)
    parser.add_argument("--interval", type=int, default=60)
    a = parser.parse_args()

    run_loop(api_url=a.api, hostname=a.hostname, interval=a.interval)
