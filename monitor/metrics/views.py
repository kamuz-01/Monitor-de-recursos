from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Host, Metric
from .serializers import HostSerializer, MetricSerializer
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
import json

class HostViewSet(viewsets.ModelViewSet):
    queryset = Host.objects.all()
    serializer_class = HostSerializer

class MetricViewSet(viewsets.ModelViewSet):
    queryset = Metric.objects.all().order_by('-timestamp')
    serializer_class = MetricSerializer

    def get_queryset(self):
        """Filtra métricas por host, tipo e intervalo de tempo"""
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

    @action(detail=False, methods=['post'])
    def ingest(self, request):
        """Ingestão de métricas: POST /api/metrics/ingest/"""
        data = request.data
        hostname = data.get('hostname')
        ip = data.get('ip')
        metrics = data.get('metrics', [])

        host, _ = Host.objects.get_or_create(hostname=hostname, defaults={'ip': ip})
        saved = []
        
        for m in metrics:
            ts = m.get('timestamp')
            if ts:
                try:
                    ts = parse_datetime(ts)
                    if ts is None:
                        ts = timezone.now()
                except:
                    ts = timezone.now()
            else:
                ts = timezone.now()

            metric = Metric.objects.create(
                host=host,
                timestamp=ts,
                metric_type=m.get('metric_type'),
                value=m.get('value'),
                extra=m.get('extra', {})
            )
            saved.append(MetricSerializer(metric).data)
        
        return Response({'saved': saved}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def latest(self, request):
        """Últimas 10 métricas: GET /api/metrics/latest/"""
        metrics = Metric.objects.select_related("host").order_by('-timestamp')[:10]

        data = [
            {
                "hostname": m.host.hostname if m.host else None,
                "ip": m.host.ip if m.host else None,
                "metric_type": m.metric_type,
                "value": m.value,
                "timestamp": m.timestamp.isoformat(),
                "extra": m.extra,
            }
            for m in metrics
        ]

        return Response({"metrics": data})

    @action(detail=False, methods=['get'])
    def report(self, request):
        """Gera relatório filtrado: GET /api/metrics/report/?host=1&range=24h"""
        host_id = request.query_params.get('host')
        range_param = request.query_params.get('range', '24h')
        
        queryset = Metric.objects.all()
        
        if host_id:
            queryset = queryset.filter(host_id=host_id)
        
        # Aplicar filtro de tempo
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
        
        queryset = queryset.filter(timestamp__gte=start_time).select_related('host').order_by('timestamp')
        
        data = [
            {
                "hostname": m.host.hostname if m.host else None,
                "metric_type": m.metric_type,
                "value": m.value,
                "timestamp": m.timestamp.isoformat(),
                "extra": m.extra,
            }
            for m in queryset
        ]
        
        return Response({
            "count": len(data),
            "host_id": host_id,
            "range": range_param,
            "report": data
        })
