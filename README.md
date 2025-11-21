# Monitor de Recursos 📊

Um sistema de monitoramento leve escrito em python focado na coleta, armazenamento e visualização de métricas de uso **_(CPU e Memória RAM)_**.

O sistema é composto por um Agente (que roda na máquina monitorada) que coleta as métricas a serem monitoradas, uma API REST (que recebe os dados coletados pelo Agente, os armazena no Postgresql + TimescaleDB e os serve em um dashboard interativo). A interface gráfica inclui a geração de relatórios nos formatos PDF e Excel.

## 🚀 Funcionalidades Principais

### **Monitoramento em Tempo Real**
- Coleta de uso de CPU e Memória RAM em intervalos configuráveis via código.

### **Gráficos Interativos**
- Dashboard web com:
  - Zoom (*Ctrl + Scroll*)
  - Uso de Média Móvel Exponencial (**EMA**) para suavizar tendências.

### **Agente Resiliente**
- **Buffer Local:** se a API cair, o agente armazena as métricas localmente e envia esses dados quando a conexão voltar.
- **Auto-Discovery:** detecta automaticamente o *hostname* e o IP real da máquina na rede onde está rodando.

### **Relatórios Avançados**
- Exportação em formato **PDF** e **Excel (.xlsx)**.
- Estatísticas automáticas: **Mínimo**, **Máximo** e **Média**.
- Filtros de data:
  - Pré-definidos: **1h**, **6h**, **24h**, **7 dias**
- Conversão automática de fuso horário (**UTC → Local [Fuso horário de São Paulo]**).


## 🧩🧩 Componentes
O sistema segue o padrão **Agente–Servidor**, composto por quatro camadas principais:

### **1. Monitor Agent (Python)**
- Script executado em cada VM monitorada.
- Coleta métricas usando **psutil**.
- Envia os dados para a API REST via **HTTP POST**.

### **2. Monitor API (Django)**
- Recebe as métricas enviadas pelo agente.
- Armazena as métricas recebidas no **PostgreSQL**.

### **3. Dashboard (Frontend)**
- Consome a API em formato **JSON**.
- Renderiza gráficos interativos utilizando **Chart.js**.

### **4. Exportador**
- Processa dados do banco.
- Gera relatórios para download nos formatos **PDF** e **XLSX**.

**Métricas Coletadas:**
- Memória RAM (%)
- CPU (%)

## 🏗️ Arquitetura

```
                     
┌─────────────────┐     (POST)       ┌──────────────────┐                                 ┌──────────────────┐                                        ┌──────────────────┐
│     monitor-    │      ────▶      │   monitor-api    │             ────▶               │   PostgreSQL +   │                ────▶                  │    Dashboard     │                  ────▶
│      agent      │  Envia métricas  │   Django REST    │  Recebe e envia métricas ao DB  │   TimescaleDB    │  Armazena e disponibiliza as métricas  │    (Browser)     │  Mostra as métricas via interface gráfica
└─────────────────┘                  └──────────────────┘                                 └──────────────────┘                                        └──────────────────┘
                          
```

## 📁 Estrutura do Projeto

```
monitor/
├── monitor-api/                    # Projeto Django REST
│   ├── monitor_api/               # Configurações Django
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── wsgi.py
│   ├── metrics/                   # App de métricas
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   └── migrations/
│   ├── templates/
│   │   └── dashboard.html
│   ├── static/
│   │   ├── css/dashboard.css
│   │   └── js/dashboard.js
│   ├── manage.py
│   └── requirements.txt
│
├── monitor-agent/                  # Agente de coleta
│   ├── agent.py
│   ├── requirements.txt
│   └── .env.example
│
└── README.md                        # Este arquivo
```

## 📦 Pré-requisitos

### Sistema Operacional
- Linux Xubuntu 20.04 LTS

### Dependências Globais
- **Back-end:** Python 3.8.10, Django 4.2.26, Django REST Framework 3.15.2
- **Frontend:** HTML5, CSS3, Chart.js (com plugin Zoom e Adapter Date-fns)
- **Agente:** Python, Psutil, Requests
- **Relatórios:** ReportLab (PDF), OpenPyXL (Excel)
- **Banco de Dados:** PostgreSQL + TimescaleDB
- pip

## 🚀 Instalação

### PostgreSQL 12 + TimescaleDB

#### No Xubuntu:

```bash
# 1. Adicionar repositórios
sudo apt update
sudo apt install -y postgresql-12 postgresql-contrib-12

# 2. Instalar TimescaleDB
sudo sh -c "echo 'deb https://packagecloud.io/timescale/timescaledb/ubuntu/ focal main' > /etc/apt/sources.list.d/timescaledb.list"
wget --quiet -O - https://packagecloud.io/timescaledb/timescaledb/gpgkey | sudo apt-key add -
sudo apt update
sudo apt install -y timescaledb-postgresql-12

# 3. Ativar TimescaleDB
sudo timescaledb-tune --quiet --yes

# 4. Reiniciar PostgreSQL
sudo systemctl restart postgresql

# 5. Verificar status
sudo systemctl status postgresql
```

### Criação do Banco de Dados

```bash
# 1. Conectar como superuser
sudo -u postgres psql

# Dentro do psql, execute:
CREATE DATABASE monitor_de_recursos;
CREATE USER monitor_user WITH PASSWORD 'sua_senha_aqui';
ALTER ROLE monitor_user SET client_encoding TO 'utf8';
ALTER ROLE monitor_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE monitor_user SET default_transaction_deferrable TO on;
GRANT ALL PRIVILEGES ON DATABASE monitor_de_recursos TO monitor_user;

# Conectar ao banco
\c monitor_de_recursos

# Ativar TimescaleDB
CREATE EXTENSION IF NOT EXISTS timescaledb;

# Sair
\q
```

### Monitor API

#### 1. Instale as dependências

```bash
cd monitor-api
python3 -m venv venv

pip install --upgrade pip
pip install -r requirements.txt
```

#### 2. Configure o banco de dados

Edite `monitor-api/monitor_api/settings.py` ou use variáveis de ambiente:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'monitor_de_recursos',
        'USER': 'monitor_user',
        'PASSWORD': 'sua_senha_aqui',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

#### 3. Execute as migrações

```bash
python manage.py makemigrations
python manage.py migrate
```

#### 4. Crie um superusuário (admin)

```bash
python manage.py createsuperuser
```

### Monitor Agent

#### 1. Instale as dependências

```bash
cd ../monitor-agent
python3 -m venv venv

# Xubuntu
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

#### 2. Teste o agente

```bash
python agent.py --api http://localhost:8000/api/metrics/ingest/ --samples 3 --interval 5
```

## ⚙️ Configuração

### Monitor API

#### Variáveis de Ambiente (Opcional)

Crie um arquivo `.env` na raiz de `monitor-api/`:

```bash
DEBUG=False
SECRET_KEY=sua-chave-secreta-super-segura
DATABASE_ENGINE=django.db.backends.postgresql
DATABASE_NAME=monitor_de_recursos
DATABASE_USER=monitor_user
DATABASE_PASSWORD=sua_senha_aqui
DATABASE_HOST=localhost
DATABASE_PORT=5432
ALLOWED_HOSTS=localhost,127.0.0.1,seu-dominio.com
```

#### Dados de Teste (Opcional)

```bash
cd monitor-api
python manage.py shell
```

```python
from metrics.models import Host

Host.objects.create(
    hostname='servidor-producao',
    ip='192.168.1.100',
    description='Servidor de produção'
)

Host.objects.create(
    hostname='servidor-desenvolvimento',
    ip='192.168.1.101',
    description='Servidor de desenvolvimento'
)

exit()
```

### Monitor Agent

#### Variáveis de Configuração

Crie um arquivo `.env` na raiz de `monitor-agent/`:

```bash
AGENT_API_URL=http://192.168.1.10:8000/api/metrics/ingest/
AGENT_SAMPLES=5
AGENT_INTERVAL=10
AGENT_HOSTNAME=servidor-producao
```

## 🏃 Execução

### Desenvolvimento Local

#### Terminal 1 - Iniciar API:

```bash
cd monitor-api
source venv/bin/activate  # Xubuntu
python manage.py runserver 0.0.0.0:8000
```

Acesse:
- **API**: http://localhost:8000/api/
- **Dashboard**: http://localhost:8000/dashboard/
- **Admin**: http://localhost:8000/admin/

#### Terminal 2 - Iniciar Agente:

```bash
cd monitor-agent
source venv/bin/activate  # Xubuntu
python agent.py --api http://localhost:8000/api/metrics/ingest/ --samples 3 --interval 5
```

### Produção

#### Monitor API com Gunicorn

```bash
cd monitor-api
source venv/bin/activate
pip install gunicorn

gunicorn --bind 0.0.0.0:8000 --workers 4 monitor_api.wsgi:application
```

#### Monitor Agent como Serviço Systemd

Crie `/etc/systemd/system/monitor-agent.service`:

```ini
[Unit]
Description=Monitor Agent - Coleta de Métricas
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=monitor-agent
WorkingDirectory=/opt/monitor-agent
Environment="PATH=/opt/monitor-agent/venv/bin"
ExecStart=/opt/monitor-agent/venv/bin/python /opt/monitor-agent/agent.py \
  --api http://192.168.1.10:8000/api/metrics/ingest/ \
  --samples 5 \
  --interval 10 \
  --hostname producao-01

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Ative:

```bash
sudo systemctl daemon-reload
sudo systemctl enable monitor-agent
sudo systemctl start monitor-agent
sudo systemctl status monitor-agent
```

## 📡 Endpoints da API

### Hosts

```bash
# Listar todos
GET /api/hosts/

# Criar
POST /api/hosts/
{
  "hostname": "novo-servidor",
  "ip": "192.168.1.200",
  "description": "Descrição"
}

# Detalhes
GET /api/hosts/{id}/

# Atualizar
PUT /api/hosts/{id}/

# Deletar
DELETE /api/hosts/{id}/
```

### Métricas

```bash
# Listar com filtros
GET /api/metrics/?host=1&metric_type=memory_percent_avg&range=24h
# Parâmetros:
# - host: ID do host
# - metric_type: memory_percent_avg, disk_percent_avg
# - range: 1h, 6h, 24h, 7d (padrão: 24h)

# Últimas 10 métricas
GET /api/metrics/latest/

# Gerar relatório
GET /api/metrics/report/?host=1&range=24h

# Ingerir métricas (usado pelo agente)
POST /api/metrics/ingest/
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
      "extra": {"min": 40.1, "max": 50.3, "avg": 45.2, "last": 45.2}
    },
    {
      "metric_type": "disk_percent_avg",
      "value": 65.8,
      "extra": {"min": 65.0, "max": 66.5, "avg": 65.8, "last": 65.8}
    }
  ]
}
```

## 🔍 Troubleshooting

### Erro: "psycopg2.OperationalError"

```bash
# Verifique se PostgreSQL está rodando
sudo systemctl status postgresql

# Teste a conexão
psql -U monitor_user -d monitor_de_recursos -h localhost
```

### Erro: "relation 'metrics_metric' does not exist"

```bash
cd monitor-api
python manage.py migrate
```

### Erro: "Connection refused" no agente

```bash
# Verifique se a API está rodando
curl http://localhost:8000/api/

# Teste a URL correta
python agent.py --api http://seu-ip:8000/api/metrics/ingest/ --samples 1 --interval 1
```

### Dashboard em branco

1. Abra o console do navegador (F12)
2. Verifique se há erros
3. Certifique-se de que há dados:

```bash
cd monitor-api
python manage.py shell
from metrics.models import Metric
print(Metric.objects.count())  # Deve retornar > 0
```

### Agente para de enviar dados

```bash
# Reinicie o serviço
sudo systemctl restart monitor-agent

# Verifique os logs
sudo journalctl -u monitor-agent -f

# Veja últimas linhas
sudo journalctl -u monitor-agent -n 50
```

## 📊 Dashboard

Acesse http://localhost:8000/dashboard/ para visualizar:

- **Gráfico de Memória**: Uso em tempo real
- **Gráfico de Disco**: Espaço em uso
- **Filtros**: Por host e intervalo de tempo
- **Download**: Relatórios em JSON ou CSV

## 🔧 Desenvolvimento

### Estrutura de Dados - Host

```python
class Host(models.Model):
    hostname = CharField(max_length=150, unique=True)
    ip = CharField(max_length=45)
    description = TextField(blank=True)
    created_at = DateTimeField(auto_now_add=True)
```

### Estrutura de Dados - Metric

```python
class Metric(models.Model):
    host = ForeignKey(Host, on_delete=CASCADE)
    timestamp = DateTimeField(db_index=True)
    metric_type = CharField(max_length=50)
    value = FloatField()
    extra = JSONField(blank=True, null=True)
```

## 📈 Performance

### Recursos do Agente
- CPU: < 1%
- Memória: ~30-50 MB
- Banda: ~500 bytes por envio

### Ciclos Recomendados
- **Pequeno**: 3 amostras × 5s = 15s
- **Médio**: 5 amostras × 10s = 50s
- **Grande**: 10 amostras × 30s = 300s

### Armazenamento
```
Dados por ciclo: ~500 bytes
Por dia: ~40-130 MB
Por mês: ~1-4 GB
```

## 📝 Licença

MIT License - veja LICENSE.md

## 🤝 Contribuindo

1. Fork o repositório
2. Crie uma branch (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 🆘 Suporte

Para reportar bugs ou sugerir features, abra uma issue no GitHub.

---

**Desenvolvido com ❤️ para a disciplina Tópicos Especiais do Instituto Federal Catarinense - Campus Fraiburgo**

Versão: 1.0.0  
Última atualização: 2024-11-17
