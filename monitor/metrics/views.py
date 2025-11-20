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

    # ============================================================
    # GET /api/metrics/?host=x&metric_type=cpu_percent&range=1h
    # ============================================================
    def get_queryset(self):
        """Filtra métricas por host, tipo e intervalo."""
        queryset = Metric.objects.all()

        # Filtro por host
        host_id = self.request.query_params.get('host')
        if host_id:
            queryset = queryset.filter(host_id=host_id)

        # Filtro por tipo de métrica
        metric_type = self.request.query_params.get('metric_type')
        if metric_type:
            queryset = queryset.filter(metric_type=metric_type)

        # Filtro por intervalo de tempo
        range_param = self.request.query_params.get('range', '24h')
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

        queryset = queryset.filter(timestamp__gte=start_time)

        return queryset.select_related('host').order_by('timestamp')

    # ============================================================
    # POST /api/metrics/ingest/
    # ============================================================
    @action(detail=False, methods=['post'])
    def ingest(self, request):
        data = request.data

        # Se o payload for uma lista, processar cada item
        if isinstance(data, list):
            items = data
        else:
            items = [data]

        created = 0

        for item in items:
            hostname = item.get("hostname")
            metric_type = item.get("metric_type")
            value = item.get("value")
            timestamp = item.get("timestamp")

            if not hostname or not metric_type or value is None:
                continue

            host, _ = Host.objects.get_or_create(hostname=hostname)

            Metric.objects.create(
                host=host,
                metric_type=metric_type,
                value=value,
                timestamp=timestamp
            )

            created += 1

        return Response({"status": "ok", "saved": created})

    # ============================================================
    # GET /api/metrics/latest/
    # ============================================================
    @action(detail=False, methods=['get'])
    def latest(self, request):
        """Retorna as últimas 20 métricas."""
        metrics = Metric.objects.select_related("host").order_by('-timestamp')[:20]

        data = [
            {
                "hostname": m.host.hostname if m.host else None,
                "ip": m.host.ip if m.host else None,
                "metric_type": m.metric_type,
                "value": m.value,
                "timestamp": m.timestamp.isoformat(),
            }
            for m in metrics
        ]

        return Response({"metrics": data, "count": len(data)})

    # ============================================================
    # GET /api/metrics/report/?host=1&range=24h&metric_type=cpu_percent
    # ============================================================
    @action(detail=False, methods=['get'])
    def report(self, request):
        """Relatório filtrado de métricas."""
        host_id = request.query_params.get('host')
        metric_type = request.query_params.get('metric_type')
        range_param = request.query_params.get('range', '24h')

        queryset = Metric.objects.all()

        if host_id:
            queryset = queryset.filter(host_id=host_id)

        if metric_type:
            queryset = queryset.filter(metric_type=metric_type)

        # Intervalo
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

        queryset = queryset.filter(timestamp__gte=start_time)
        queryset = queryset.select_related('host').order_by('timestamp')

        data = [
            {
                "hostname": m.host.hostname if m.host else None,
                "metric_type": m.metric_type,
                "value": m.value,
                "timestamp": m.timestamp.isoformat(),
            }
            for m in queryset
        ]

        return Response({
            "count": len(data),
            "host_id": host_id,
            "metric_type": metric_type,
            "range": range_param,
            "report": data
        })
