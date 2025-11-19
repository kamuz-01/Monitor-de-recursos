#!/usr/bin/env python3
"""
Script para medir overhead do Agent de Monitoramento
Monitora: CPU e Memória
"""

import psutil
import subprocess
import time
import statistics
from datetime import datetime

def get_agent_metrics():
    """Procura por qualquer processo contendo 'agent' no comando."""
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            cmdline = " ".join(proc.info.get("cmdline") or [])
            if "agent" in cmdline.lower():
                pid = proc.info['pid']
                cpu = proc.cpu_percent(interval=0.1)
                mem_mb = proc.memory_info().rss / (1024 * 1024)

                return {
                    'pid': pid,
                    'cpu': cpu,
                    'mem_mb': mem_mb
                }
        return None
    except Exception as e:
        print("Erro ao obter métricas:", e)
        return None


def main():
    print("=" * 80)
    print("MONITOR DE OVERHEAD - AGENTE DE MEMÓRIA E DISCO")
    print("=" * 80)
    print("\nLimites Aceitáveis:")
    print("  CPU: < 2%")
    print("  Memória: < 50 MB")
    print("\n" + "=" * 80)
    
    cpu_values = []
    mem_values = []
    
    try:
        for i in range(60):  # 5 minutos de coleta (1 medição a cada 5s)
            timestamp = datetime.now().strftime('%H:%M:%S')
            
            metrics = get_agent_metrics()
            
            if metrics:
                cpu_values.append(metrics['cpu'])
                mem_values.append(metrics['mem_mb'])
                
                print(f"[{timestamp}] PID={metrics['pid']:5d} | CPU={metrics['cpu']:6.2f}% | RAM={metrics['mem_mb']:6.1f}MB", end="")

                # Validações
                if metrics['cpu'] > 2:
                    print(" ⚠️ CPU ALTA", end="")
                if metrics['mem_mb'] > 50:
                    print(" ⚠️ MEM ALTA", end="")
                
                print()
            else:
                print(f"[{timestamp}] Agente não está rodando!")
                return
            
            time.sleep(5)
        
        # -----------------------------
        # ANÁLISE FINAL
        # -----------------------------
        print("\n" + "=" * 80)
        print("ANÁLISE FINAL (60 medições):")
        print("=" * 80)
        
        print(f"\nCPU:")
        print(f"  Mínimo:  {min(cpu_values):.2f}%")
        print(f"  Máximo:  {max(cpu_values):.2f}%")
        print(f"  Médio:   {statistics.mean(cpu_values):.2f}%")
        print(f"  Mediana: {statistics.median(cpu_values):.2f}%")
        if max(cpu_values) < 2:
            print("  ✅ PASSOU - CPU < 2%")
        else:
            print("  ❌ FALHOU - CPU acima de 2%")
        
        print(f"\nMemória RAM:")
        print(f"  Mínimo:  {min(mem_values):.1f} MB")
        print(f"  Máximo:  {max(mem_values):.1f} MB")
        print(f"  Médio:   {statistics.mean(mem_values):.1f} MB")
        print(f"  Mediana: {statistics.median(mem_values):.1f} MB")
        if max(mem_values) < 50:
            print("  ✅ PASSOU - Memória < 50 MB")
        else:
            print("  ❌ FALHOU - Memória acima de 50 MB")

        # BENCHMARKS FINAIS
        print("\n\n📈 BENCHMARKS ESPERADOS")
        print("=" * 80)

        print("\nMONITOR AGENT (Sozinho)\n")
        print(f"{'Métrica':<20}{'Esperado':<15}{'Limite Máximo'}")
        print("-" * 60)
        print(f"{'CPU (%)':<20}{'0.5–1%':<15}{'< 2%'}")
        print(f"{'Memória':<20}{'30–45 MB':<15}{'< 50 MB'}")
        print(f"{'Banda':<20}{'~500 bytes/ciclo':<15}{'-'}")
        print("\nCiclo típico: 5 amostras × 10s intervalo = 50s")
        print("1 envio a cada 50s = 10 bytes/s (~0.08 KB/s) ✔️")

        print("\n\nMONITOR API (Django + PostgreSQL)\n")
        print(f"{'Métrica':<20}{'Com 1 Agent':<15}{'Com 10 Agents'}")
        print("-" * 60)
        print(f"{'CPU (%)':<20}{'3–5%':<15}{'8–12%'}")
        print(f"{'Memória':<20}{'120–150 MB':<15}{'150–200 MB'}")
        print(f"{'Requisições/s':<20}{'1 req/50s':<15}{'~0.2 req/s'}")

        print("\n\nSISTEMA TOTAL\n")
        print(f"{'Cenário':<20}{'CPU Total':<15}{'RAM Total':<15}{'Banda'}")
        print("-" * 80)
        print(f"{'1 Agent + 1 API':<20}{'< 5%':<15}{'< 200 MB':<15}{'< 1 KB/s'}")
        print(f"{'5 Agents + 1 API':<20}{'< 10%':<15}{'< 400 MB':<15}{'< 5 KB/s'}")
        print(f"{'20 Agents + 1 API':<20}{'< 30%':<15}{'< 1 GB':<15}{'< 20 KB/s'}")

        print("\n" + "=" * 80)
        print("RESUMO:")
        print("=" * 80)

        cpu_ok = max(cpu_values) < 2
        mem_ok = max(mem_values) < 50
        
        if cpu_ok and mem_ok:
            print("✅ SISTEMA COM BAIXO OVERHEAD - TUDO DENTRO DOS LIMITES!")
        else:
            print("❌ SISTEMA COM OVERHEAD ACIMA DO ESPERADO")
            if not cpu_ok:
                print(f"   - CPU máxima: {max(cpu_values):.2f}% (limite: 2%)")
            if not mem_ok:
                print(f"   - Memória máxima: {max(mem_values):.1f} MB (limite: 50 MB)")
        
        print("=" * 80)
        
    except KeyboardInterrupt:
        print("\n\nEncerrando monitoramento...")

if __name__ == '__main__':
    main()
