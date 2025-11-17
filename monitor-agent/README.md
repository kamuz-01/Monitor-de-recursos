# Monitor Agent

Agente de coleta de métricas de sistema que envia dados para a API de Monitoramento.

## Características

- ✅ Coleta de CPU, Memória e Disco
- ✅ Consolidação de amostras (min, max, avg)
- ✅ Envio automático para API REST
- ✅ Identificação única do agente (UUID)
- ✅ Suporte a múltiplos hosts
- ✅ Configurável via argumentos CLI

## Instalação

### Pré-requisitos

- Python 3.7+
- pip

### Setup

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/monitor-agent.git
cd monitor-agent

# Crie um ambiente virtual
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instale as dependências
pip install -r requirements.txt
```

## Uso

### Execução básica

```bash
python agent.py --api http://localhost:8000/api/metrics/ingest/
```

### Com parâmetros customizados

```bash
python agent.py \
  --api http://api.example.com/api/metrics/ingest/ \
  --samples 5 \
  --interval 10 \
  --hostname meu-servidor
```

### Parâmetros

- `--api`: URL do endpoint ingest da API (**obrigatório**)
- `--samples`: Número de amostras a coletar (padrão: 3)
- `--interval`: Intervalo entre amostras em segundos (padrão: 5)
- `--hostname`: Nome do host (padrão: hostname do sistema)

## Exemplos

**Monitorar com 5 amostras de 10 segundos cada (50 segundos totais):**
```bash
python agent.py \
  --api http://localhost:8000/api/metrics/ingest/ \
  --samples 5 \
  --interval 10
```

**Monitorar servidor remoto:**
```bash
python agent.py \
  --api http://api-server.com/api/metrics/ingest/ \
  --hostname servidor-producao
```

## Como Serviço Systemd (Linux)

Crie `/etc/systemd/system/monitor-agent.service`:

```ini
[Unit]
Description=Monitor Agent - Coleta de Métricas
After=network.target

[Service]
Type=simple
User=monitor-agent
WorkingDirectory=/opt/monitor-agent
ExecStart=/opt/monitor-agent/venv/bin/python /opt/monitor-agent/agent.py \
  --api http://localhost:8000/api/metrics/ingest/ \
  --samples 5 \
  --interval 10 \
  --hostname meu-servidor

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Então ative:
```bash
sudo systemctl daemon-reload
sudo systemctl enable monitor-agent
sudo systemctl start monitor-agent
sudo systemctl status monitor-agent
```

## Monitoramento de Logs

```bash
# Ver logs em tempo real
sudo journalctl -u monitor-agent -f

# Ver últimos 50 logs
sudo journalctl -u monitor-agent -n 50
```

## Estrutura de Dados Enviados

```json
{
  "hostname": "meu-servidor",
  "ip": "192.168.1.100",
  "platform": "Linux-5.10.0",
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-11-17T10:30:45.123456+00:00",
  "metrics": [
    {
      "metric_type": "memory_percent_avg",
      "value": 45.2,
      "extra": {
        "min": 40.1,
        "max": 50.3,
        "avg": 45.2,
        "last": 45.2,
        "total": 16000000000,
        "available": 8800000000,
        "used": 7200000000
      }
    },
    {
      "metric_type": "disk_percent_avg",
      "value": 65.8,
      "extra": {
        "min": 65.0,
        "max": 66.5,
        "avg": 65.8,
        "last": 65.8,
        "total": 1099511627776,
        "used": 724324917248,
        "free": 375186710528
      }
    }
  ]
}
```

## Troubleshooting

### Erro de conexão com a API

```
[FALHA] Não foi possível enviar: Connection refused
```

Verifique se:
- A API está rodando: `curl http://localhost:8000/api/`
- A URL está correta
- Firewall não está bloqueando

### Permissão negada no diretório

```
PermissionError: [Errno 13] Permission denied: '/var/lib/monitor-agent'
```

Execute como root ou ajuste permissões:
```bash
sudo mkdir -p /var/lib/monitor-agent
sudo chown $USER:$USER /var/lib/monitor-agent
```

## Desenvolvimento

Para contribuir:

1. Fork o repositório
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## Licença

MIT License - veja LICENSE.md para detalhes

## Suporte

Para reportar bugs ou sugerir features, abra uma issue no GitHub.
