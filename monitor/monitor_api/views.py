from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from datetime import timedelta
from metrics.models import Metric, Host
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from io import BytesIO
from datetime import datetime


def home(request):
    return HttpResponse("<h1>API de Monitoramento — OK</h1><p>Use /api/</p>")
    

def dashboard(request):
    return render(request, "dashboard.html")


def generate_report(request):
    """
    Gera relatórios em PDF ou XLSX baseado nos query params
    """
    host_id = request.GET.get("host")
    range_param = request.GET.get("range", "24h")
    format_param = request.GET.get("format", "xlsx")

    if not host_id:
        return HttpResponse("Host ID é obrigatório", status=400)

    # Buscar dados do banco
    try:
        host = Host.objects.get(id=host_id)
    except Host.DoesNotExist:
        return HttpResponse("Host não encontrado", status=404)

    # Filtro de tempo
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

    # Buscar métricas usando o modelo correto (metrics.models.Metric)
    metrics = Metric.objects.filter(
        host=host,
        timestamp__gte=start_time
    ).order_by('timestamp')

    # Separar CPU e Memória
    cpu_data = [(m.timestamp, m.value) for m in metrics if m.metric_type == 'cpu_percent']
    memory_data = [(m.timestamp, m.value) for m in metrics if m.metric_type == 'memory_percent']

    # Gerar relatório baseado no formato
    if format_param == 'pdf':
        return generate_pdf_report(host, cpu_data, memory_data, range_param)
    else:  # xlsx
        return generate_xlsx_report(host, cpu_data, memory_data, range_param)


def generate_xlsx_report(host, cpu_data, memory_data, range_param):
    """Gera relatório em XLSX (Excel)"""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Relatório"

    # Estilos
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12)
    title_font = Font(bold=True, size=14)
    center_align = Alignment(horizontal="center", vertical="center")
    border_style = openpyxl.styles.Border(
        left=openpyxl.styles.Side(style='thin'),
        right=openpyxl.styles.Side(style='thin'),
        top=openpyxl.styles.Side(style='thin'),
        bottom=openpyxl.styles.Side(style='thin')
    )

    # Cabeçalho do relatório
    ws.merge_cells('A1:D1')
    title_cell = ws['A1']
    title_cell.value = f"Relatório de Monitoramento - {host.hostname}"
    title_cell.font = title_font
    title_cell.alignment = center_align

    # Informações gerais
    ws['A3'].value = f"Host: {host.hostname}"
    ws['A4'].value = f"IP: {host.ip if host.ip else 'N/A'}"
    ws['A5'].value = f"Período: {range_param}"
    ws['A6'].value = f"Data do Relatório: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"

    # Seção CPU
    ws['A8'].value = "DADOS DE CPU (%)"
    ws['A8'].font = Font(bold=True, size=11, color="FFFFFF")
    ws['A8'].fill = PatternFill(start_color="C55A11", end_color="C55A11", fill_type="solid")

    ws['A9'].value = "Timestamp"
    ws['B9'].value = "Valor (%)"

    for col in ['A9', 'B9']:
        ws[col].font = header_font
        ws[col].fill = header_fill
        ws[col].alignment = center_align
        ws[col].border = border_style

    row = 10
    for timestamp, value in cpu_data:
        ws[f'A{row}'].value = timestamp.strftime('%d/%m/%Y %H:%M:%S')
        ws[f'B{row}'].value = round(value, 2)
        ws[f'A{row}'].border = border_style
        ws[f'B{row}'].border = border_style
        row += 1

    # Estatísticas CPU
    cpu_row = row + 1
    if cpu_data:
        cpu_values = [v for _, v in cpu_data]
        ws[f'A{cpu_row}'].value = "Mínimo:"
        ws[f'B{cpu_row}'].value = round(min(cpu_values), 2)
        ws[f'A{cpu_row}'].font = Font(bold=True)

        ws[f'A{cpu_row + 1}'].value = "Máximo:"
        ws[f'B{cpu_row + 1}'].value = round(max(cpu_values), 2)
        ws[f'A{cpu_row + 1}'].font = Font(bold=True)

        ws[f'A{cpu_row + 2}'].value = "Média:"
        ws[f'B{cpu_row + 2}'].value = round(sum(cpu_values) / len(cpu_values), 2)
        ws[f'A{cpu_row + 2}'].font = Font(bold=True)

    # Seção Memória
    mem_section_row = cpu_row + 5
    ws[f'A{mem_section_row}'].value = "DADOS DE MEMÓRIA RAM (%)"
    ws[f'A{mem_section_row}'].font = Font(bold=True, size=11, color="FFFFFF")
    ws[f'A{mem_section_row}'].fill = PatternFill(start_color="0070C0", end_color="0070C0", fill_type="solid")

    mem_header_row = mem_section_row + 1
    ws[f'A{mem_header_row}'].value = "Timestamp"
    ws[f'B{mem_header_row}'].value = "Valor (%)"

    for col in [f'A{mem_header_row}', f'B{mem_header_row}']:
        ws[col].font = header_font
        ws[col].fill = header_fill
        ws[col].alignment = center_align
        ws[col].border = border_style

    row = mem_header_row + 1
    for timestamp, value in memory_data:
        ws[f'A{row}'].value = timestamp.strftime('%d/%m/%Y %H:%M:%S')
        ws[f'B{row}'].value = round(value, 2)
        ws[f'A{row}'].border = border_style
        ws[f'B{row}'].border = border_style
        row += 1

    # Estatísticas Memória
    mem_row = row + 1
    if memory_data:
        mem_values = [v for _, v in memory_data]
        ws[f'A{mem_row}'].value = "Mínimo:"
        ws[f'B{mem_row}'].value = round(min(mem_values), 2)
        ws[f'A{mem_row}'].font = Font(bold=True)

        ws[f'A{mem_row + 1}'].value = "Máximo:"
        ws[f'B{mem_row + 1}'].value = round(max(mem_values), 2)
        ws[f'A{mem_row + 1}'].font = Font(bold=True)

        ws[f'A{mem_row + 2}'].value = "Média:"
        ws[f'B{mem_row + 2}'].value = round(sum(mem_values) / len(mem_values), 2)
        ws[f'A{mem_row + 2}'].font = Font(bold=True)

    # Ajustar largura das colunas
    ws.column_dimensions['A'].width = 25
    ws.column_dimensions['B'].width = 20

    # Salvar em memória
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="relatorio_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'

    return response


def generate_pdf_report(host, cpu_data, memory_data, range_param):
    """Gera relatório em PDF"""
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=letter)
    story = []

    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#333333'),
        spaceAfter=12,
        alignment=1  # center
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#FFFFFF'),
        spaceAfter=10
    )

    # Título
    title = Paragraph(f"Relatório de Monitoramento - {host.hostname}", title_style)
    story.append(title)
    story.append(Spacer(1, 0.3 * inch))

    # Informações gerais
    info_text = f"""
    <b>Host:</b> {host.hostname}<br/>
    <b>IP:</b> {host.ip if host.ip else 'N/A'}<br/>
    <b>Período:</b> {range_param}<br/>
    <b>Data do Relatório:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
    """
    story.append(Paragraph(info_text, styles['Normal']))
    story.append(Spacer(1, 0.2 * inch))

    # Tabela CPU
    cpu_heading = Paragraph("DADOS DE CPU (%)", heading_style)
    cpu_heading.style.backColor = colors.HexColor('#C55A11')
    story.append(cpu_heading)
    
    cpu_table_data = [['Timestamp', 'Valor (%)']]
    for timestamp, value in cpu_data[-20:]:  # Últimas 20 medições
        cpu_table_data.append([
            timestamp.strftime('%d/%m/%Y %H:%M'),
            f"{value:.2f}"
        ])

    if cpu_data:
        cpu_values = [v for _, v in cpu_data]
        cpu_table_data.append(['Mínimo', f"{min(cpu_values):.2f}"])
        cpu_table_data.append(['Máximo', f"{max(cpu_values):.2f}"])
        cpu_table_data.append(['Média', f"{sum(cpu_values)/len(cpu_values):.2f}"])

    cpu_table = Table(cpu_table_data, colWidths=[3*inch, 2*inch])
    cpu_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F2F2F2')]),
    ]))
    story.append(cpu_table)
    story.append(Spacer(1, 0.3 * inch))

    # Tabela Memória
    mem_heading = Paragraph("DADOS DE MEMÓRIA RAM (%)", heading_style)
    mem_heading.style.backColor = colors.HexColor('#0070C0')
    story.append(mem_heading)
    
    mem_table_data = [['Timestamp', 'Valor (%)']]
    for timestamp, value in memory_data[-20:]:  # Últimas 20 medições
        mem_table_data.append([
            timestamp.strftime('%d/%m/%Y %H:%M'),
            f"{value:.2f}"
        ])

    if memory_data:
        mem_values = [v for _, v in memory_data]
        mem_table_data.append(['Mínimo', f"{min(mem_values):.2f}"])
        mem_table_data.append(['Máximo', f"{max(mem_values):.2f}"])
        mem_table_data.append(['Média', f"{sum(mem_values)/len(mem_values):.2f}"])

    mem_table = Table(mem_table_data, colWidths=[3*inch, 2*inch])
    mem_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0070C0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F2F2F2')]),
    ]))
    story.append(mem_table)

    # Gerar PDF
    doc.build(story)
    output.seek(0)

    response = HttpResponse(
        output.getvalue(),
        content_type='application/pdf'
    )
    response['Content-Disposition'] = f'attachment; filename="relatorio_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'

    return response


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
