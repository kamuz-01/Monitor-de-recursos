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

def collect_sample():
    cpu_percent = psutil.cpu_percent(interval=1)
    memory_percent = psutil.virtual_memory().percent
    return cpu_percent, memory_percent

# buffer para guardar métricas caso a API falhe
pending = []

def format_metric(hostname, ts, cpu, mem):
    """Converte duas métricas no formato que o Django espera."""
    return [
        {
            "hostname": hostname,
            "metric_type": "cpu_percent",
            "timestamp": ts,
            "value": cpu
        },
        {
            "hostname": hostname,
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

    print(f"[AGENTE] Iniciado para {hostname}")
    print(f"[ID] {machine_id}")
    print(f"[Intervalo] {interval}s")

    global pending

    while True:
        cpu, mem = collect_sample()
        ts = datetime.now(timezone.utc).isoformat()

        batch = format_metric(hostname, ts, cpu, mem)

        print(f"[{datetime.now().strftime('%H:%M:%S')}] CPU={cpu:.1f}%  MEM={mem:.1f}%")

        # junta buffer antigo + métrica nova
        to_send = pending + batch
        ok = send_to_api(api_url, to_send)

        if ok:
            pending = []  # limpamos buffer
        else:
            print("[BUFFER] Guardando métricas não enviadas")
            pending += batch

        time.sleep(interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", required=True)
    parser.add_argument("--hostname", default=None)
    parser.add_argument("--interval", type=int, default=60)
    a = parser.parse_args()

    run_loop(api_url=a.api, hostname=a.hostname, interval=a.interval)
