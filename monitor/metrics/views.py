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

        # CORRIGIDO: Usar timezone.now() que retorna UTC aware
        now = timezone.now()
        
        print(f"\n{'='*80}")
        print(f"[FILTRO] Intervalo solicitado: {range_param}")
        print(f"[FILTRO] NOW (UTC): {now}")
        
        # Calcula start_time baseado em NOW
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

        print(f"[FILTRO] START_TIME: {start_time}")
        print(f"[FILTRO] END_TIME: {now}")
        print(f"[FILTRO] Diferença: {(now - start_time).total_seconds() / 3600:.1f} horas")
        print(f"{'='*80}\n")

        # Filtro com range inclusivo
        filtered = queryset.filter(
            timestamp__gte=start_time,
            timestamp__lte=now
        ).select_related('host').order_by('timestamp')
        
        count = filtered.count()
        print(f"[RESULTADO] Total de registros encontrados: {count}")
        
        if count > 0:
            first = filtered.first()
            last = filtered.last()
            print(f"[RESULTADO] Primeiro: {first.timestamp}")
            print(f"[RESULTADO] Último: {last.timestamp}")
        
        return filtered

    @action(detail=False, methods=['post'])
    def ingest(self, request):
        data = request.data
        items = data if isinstance(data, list) else [data]
        created = 0
        
        hosts_cache = {}

        for item in items:
            hostname = item.get("hostname")
            ip = item.get("ip")
            metric_type = item.get("metric_type")
            value = item.get("value")
            timestamp = item.get("timestamp")

            if not hostname or not metric_type or value is None:
                continue

            if hostname not in hosts_cache:
                host, _ = Host.objects.get_or_create(hostname=hostname)
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
        CRÍTICO: Usar NOW como referência final e calcular intervalo exato
        """
        host_id = request.query_params.get('host')
        metric_type = request.query_params.get('metric_type')
        range_param = request.query_params.get('range', '24h')
        fmt = request.query_params.get('format', 'json') 
        
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        queryset = Metric.objects.select_related('host').all().order_by('timestamp')

        if host_id:
            queryset = queryset.filter(host_id=host_id)
        if metric_type:
            queryset = queryset.filter(metric_type=metric_type)

        # CRÍTICO: NOW como referência de FIM do intervalo
        now = timezone.now()
        
        print(f"\n{'='*80}")
        print(f"[REPORT] Range: {range_param}")
        print(f"[REPORT] NOW: {now}")
        
        if range_param == 'custom' and start_date_str and end_date_str:
            try:
                start_time = parse_datetime(start_date_str)
                end_time = parse_datetime(end_date_str)
                if start_time and end_time:
                    queryset = queryset.filter(timestamp__range=(start_time, end_time))
                    print(f"[REPORT] CUSTOM: {start_time} até {end_time}")
            except ValueError:
                pass
        else:
            # Calcula intervalo EXATO
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
            
            print(f"[REPORT] START: {start_time}")
            print(f"[REPORT] END: {now}")
            print(f"[REPORT] Diferença: {(now - start_time).total_seconds() / 3600:.1f} horas")
            
            # Filtro com range inclusivo em AMBAS as extremidades
            queryset = queryset.filter(
                timestamp__gte=start_time,
                timestamp__lte=now
            )

        queryset = queryset.order_by('timestamp')
        print(f"[REPORT] Total encontrado: {queryset.count()}")
        print(f"{'='*80}\n")

        now_local = timezone.localtime(now)

        # EXPORTAÇÃO EXCEL
        if fmt == 'excel':
            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename="relatorio_{now_local.strftime("%Y%m%d_%H%M")}.xlsx"'
            
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Metricas"
            ws.append(["Data/Hora", "Host", "Tipo", "Valor (%)"])
            
            for m in queryset:
                local_ts = timezone.localtime(m.timestamp)
                ts_naive = local_ts.replace(tzinfo=None)
                ws.append([ts_naive, m.host.hostname, m.metric_type, m.value])
            
            wb.save(response)
            return response

        # EXPORTAÇÃO PDF
        elif fmt == 'pdf':
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=A4)
            
            p.setFont("Helvetica-Bold", 14)
            p.drawString(50, 800, "Relatório de Monitoramento")
            
            p.setFont("Helvetica", 10)
            p.drawString(50, 780, f"Gerado em: {now_local.strftime('%d/%m/%Y %H:%M')}")
            
            y = 750
            p.drawString(50, y, "Data/Hora")
            p.drawString(200, y, "Host")
            p.drawString(350, y, "Tipo")
            p.drawString(450, y, "Valor")
            y -= 20
            
            for m in queryset[:1000]:
                if y < 50:
                    p.showPage()
                    y = 750
                    
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

        # RETORNO JSON (Para o Dashboard)
        else:
            items = list(queryset)
            
            data = [{
                "hostname": m.host.hostname,
                "metric_type": m.metric_type,
                "value": m.value,
                "timestamp": m.timestamp.isoformat() 
            } for m in items]
            
            return Response({"report": data})
