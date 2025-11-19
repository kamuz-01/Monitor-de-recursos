#!/usr/bin/env python3
import psutil
import time
import requests
import socket
from datetime import datetime, timezone
import argparse
import json
import platform
import uuid
import os

AGENT_ID_FILE = "/var/lib/monitor-agent/agent_id.txt"

def load_agent_id():
    os.makedirs("/var/lib/monitor-agent", exist_ok=True)
    if os.path.exists(AGENT_ID_FILE):
        with open(AGENT_ID_FILE, "r") as f:
            return f.read().strip()
    new_id = str(uuid.uuid4())
    with open(AGENT_ID_FILE, "w") as f:
        f.write(new_id)
    return new_id

def collect_sample():
    mem = psutil.virtual_memory()
    memory = {
        'percent': mem.percent,
        'total': mem.total,
        'available': mem.available,
        'used': mem.used,
    }

    disk = psutil.disk_usage('/')
    disk_info = {
        'percent': disk.percent,
        'total': disk.total,
        'used': disk.used,
        'free': disk.free
    }

    return memory, disk_info

def consolidate(samples):
    mem_percents = [m['percent'] for m, d in samples]
    disk_percents = [d['percent'] for m, d in samples]

    return {
        'memory': {
            'min': min(mem_percents),
            'max': max(mem_percents),
            'avg': sum(mem_percents) / len(mem_percents),
            'last': mem_percents[-1],
        },
        'disk': {
            'min': min(disk_percents),
            'max': max(disk_percents),
            'avg': sum(disk_percents) / len(disk_percents),
            'last': disk_percents[-1],
        }
    }

def send_metrics(api_url, metrics):
    try:
        r = requests.post(api_url, json=metrics, timeout=10)
        if r.status_code in (200, 201):
            print("[OK] Dados enviados!")
        else:
            print("[ERRO]", r.status_code, r.text)
    except Exception as e:
        print("[FALHA] Não foi possível enviar:", e)

def run_loop(api_url, samples, interval, hostname=None):
    if hostname is None:
        hostname = socket.gethostname()

    machine_id = load_agent_id()

    print(f"[AGENTE] Iniciando agente para {hostname} (ID={machine_id})")

    while True:
        collected_samples = []

        for _ in range(samples):
            mem, disk = collect_sample()
            collected_samples.append((mem, disk))
            time.sleep(interval)

        cons = consolidate(collected_samples)
        now = datetime.now(timezone.utc).isoformat()

        payload = {
            'hostname': hostname,
            'ip': socket.gethostbyname(hostname),
            'platform': platform.platform(),
            'uuid': machine_id,
            'timestamp': now,
            'metrics': [
                {
                    'metric_type': 'memory_percent_avg',
                    'value': cons['memory']['avg'],
                    'extra': cons['memory'],
                },
                {
                    'metric_type': 'disk_percent_avg',
                    'value': cons['disk']['avg'],
                    'extra': cons['disk'],
                }
            ]
        }

        send_metrics(api_url, payload)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--api', required=True, help='URL do endpoint ingest')
    parser.add_argument('--samples', type=int, default=3)
    parser.add_argument('--interval', type=int, default=5)
    parser.add_argument('--hostname', default=None)
    args = parser.parse_args()

    run_loop(
        api_url=args.api,
        samples=args.samples,
        interval=args.interval,
        hostname=args.hostname
    )
