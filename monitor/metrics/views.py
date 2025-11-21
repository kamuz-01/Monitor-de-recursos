import io
import openpyxl
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import timedelta
from .models import Host, Metric
from .serializers import HostSerializer, MetricSerializer

class HostViewSet(viewsets.ModelViewSet):
    queryset = Host.objects.all()
    serializer_class = HostSerializer

class MetricViewSet(viewsets.ModelViewSet):
    queryset = Metric.objects.all().order_by('-timestamp')
    serializer_class = MetricSerializer

    def get_queryset(self):
        """Filtra métricas por host, tipo e intervalo."""
        queryset = Metric.objects.all()
        host_id = self.request.query_params.get('host')
        metric_type = self.request.query_params.get('metric_type')
        range_param = self.request.query_params.get('range', '24h')
        
        if host_id:
            queryset = queryset.filter(host_id=host_id)
        if metric_type:
            queryset = queryset.filter(metric_type=metric_type)

        # Calcula o 'agora' e converte para UTC para filtrar no banco corretamente
        now = timezone.now() 
        
        if range_param == '1h':
            start_time = now - timedelta(hours=1)
        elif range_param == '6h':
            start_time = now - timedelta(hours=6)
        elif range_param == '24h':
            start_time = now - timedelta(hours=24)
        elif range_param == '7d':
            start_time = now - timedelta(days=7)
        else:
            start_time = now - timedelta(hours=24)

        return queryset.filter(timestamp__gte=start_time).select_related('host').order_by('timestamp')

    @action(detail=False, methods=['post'])
    def ingest(self, request):
        data = request.data
        items = data if isinstance(data, list) else [data]
        created = 0
        
        # Cache simples para não buscar o Host repetidamente no mesmo loop
        hosts_cache = {}

        for item in items:
            hostname = item.get("hostname")
            ip = item.get("ip")  # <--- Pega o IP enviado
            metric_type = item.get("metric_type")
            value = item.get("value")
            timestamp = item.get("timestamp")

            if not hostname or not metric_type or value is None:
                continue

            # Lógica de Atualização do Host
            if hostname not in hosts_cache:
                host, _ = Host.objects.get_or_create(hostname=hostname)
                # Se o IP veio e é diferente do que temos, ATUALIZA
                if ip and host.ip != ip:
                    host.ip = ip
                    host.save()
                hosts_cache[hostname] = host
            else:
                host = hosts_cache[hostname]

            Metric.objects.create(
                host=host,
                metric_type=metric_type,
                value=value,
                timestamp=timestamp
            )
            created += 1

        return Response({"status": "ok", "saved": created})

    @action(detail=False, methods=['get'])
    def latest(self, request):
        metrics = Metric.objects.select_related("host").order_by('-timestamp')[:20]
        data = [{
            "hostname": m.host.hostname,
            "metric_type": m.metric_type,
            "value": m.value,
            "timestamp": m.timestamp.isoformat()
        } for m in metrics]
        return Response({"metrics": data})

    @action(detail=False, methods=['get'])
    def report(self, request):
        """
        Gera JSON (padrão para gráficos) ou Arquivo (PDF/Excel) para download.
        """
        host_id = request.query_params.get('host')
        metric_type = request.query_params.get('metric_type')
        range_param = request.query_params.get('range')
        fmt = request.query_params.get('format', 'json') 
        
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        queryset = Metric.objects.select_related('host').all().order_by('-timestamp')

        if host_id:
            queryset = queryset.filter(host_id=host_id)
        if metric_type:
            queryset = queryset.filter(metric_type=metric_type)

        # --- Lógica de Filtro de Tempo ---
        now = timezone.now()
        
        if range_param == 'custom' and start_date_str and end_date_str:
            try:
                start_time = parse_datetime(start_date_str)
                end_time = parse_datetime(end_date_str)
                if start_time and end_time:
                    queryset = queryset.filter(timestamp__range=(start_time, end_time))
            except ValueError:
                pass
        else:
            if range_param == '1h': start_time = now - timedelta(hours=1)
            elif range_param == '6h': start_time = now - timedelta(hours=6)
            elif range_param == '7d': start_time = now - timedelta(days=7)
            else: start_time = now - timedelta(hours=24)
            queryset = queryset.filter(timestamp__gte=start_time)

        # Prepara a data local para exibir no cabeçalho do arquivo
        now_local = timezone.localtime(now)

        # ==========================================
        # EXPORTAÇÃO EXCEL
        # ==========================================
        if fmt == 'excel':
            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename="relatorio_{now_local.strftime("%Y%m%d_%H%M")}.xlsx"'
            
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Metricas"
            ws.append(["Data/Hora", "Host", "Tipo", "Valor (%)"])
            
            for m in queryset:
                # CONVERSÃO CRUCIAL: De UTC para Local Time
                local_ts = timezone.localtime(m.timestamp)
                # Remove info de fuso para o Excel não reclamar (tz-naive)
                ts_naive = local_ts.replace(tzinfo=None)
                
                ws.append([ts_naive, m.host.hostname, m.metric_type, m.value])
            
            wb.save(response)
            return response

        # ==========================================
        # EXPORTAÇÃO PDF
        # ==========================================
        elif fmt == 'pdf':
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=A4)
            
            p.setFont("Helvetica-Bold", 14)
            p.drawString(50, 800, "Relatório de Monitoramento")
            
            p.setFont("Helvetica", 10)
            # Usa hora local no cabeçalho
            p.drawString(50, 780, f"Gerado em: {now_local.strftime('%d/%m/%Y %H:%M')}")
            
            y = 750
            p.drawString(50, y, "Data/Hora")
            p.drawString(200, y, "Host")
            p.drawString(350, y, "Tipo")
            p.drawString(450, y, "Valor")
            y -= 20
            
            for m in queryset[:1000]: # Limite de segurança
                if y < 50:
                    p.showPage(); y = 750
                    
                # CONVERSÃO CRUCIAL: De UTC para Local Time antes de imprimir
                local_ts = timezone.localtime(m.timestamp)
                ts_str = local_ts.strftime('%d/%m %H:%M')
                
                p.drawString(50, y, ts_str)
                p.drawString(200, y, m.host.hostname[:20])
                p.drawString(350, y, m.metric_type)
                p.drawString(450, y, f"{m.value}%")
                y -= 15
                
            p.save()
            buffer.seek(0)
            return HttpResponse(buffer, content_type='application/pdf')

        # ==========================================
        # RETORNO JSON (Para o Dashboard)
        # ==========================================
        else:
            data = [{
                "hostname": m.host.hostname,
                "metric_type": m.metric_type,
                "value": m.value,
                # ISO format já carrega o fuso correto se configurado no settings, 
                # mas o JS geralmente converte para local do browser.
                "timestamp": m.timestamp.isoformat() 
            } for m in queryset]
            return Response({"report": data})
