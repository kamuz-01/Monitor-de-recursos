from django.http import HttpResponse
from django.http import JsonResponse, HttpResponse
from .models import Metric
from django.utils.dateparse import parse_datetime
from django.shortcuts import render


def home(request):
    return HttpResponse("<h1>API de Monitoramento — OK</h1><p>Use /api/</p>")
    
def dashboard(request):
     return render(request, "dashboard.html")

def report(request):

    host = request.GET.get("host")
    start = request.GET.get("start")
    end = request.GET.get("end")

    qs = Metric.objects.all()

    if host:
        qs = qs.filter(host_id=host)

    if start:
        start_dt = parse_datetime(start)
        qs = qs.filter(timestamp__gte=start_dt)

    if end:
        end_dt = parse_datetime(end)
        qs = qs.filter(timestamp__lte=end_dt)

    qs = qs.order_by("timestamp")

    data = [
        {
            "timestamp": m.timestamp,
            "metric_type": m.metric_type,
            "value": m.value
        } for m in qs
    ]

    return JsonResponse({"report": data}, safe=False)
