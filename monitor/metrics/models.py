from django.db import models


class Host(models.Model):
    """
    Representa um servidor/host monitorado.
    """
    hostname = models.CharField(
        max_length=150,
        unique=True,
        help_text="Nome do host monitorado"
    )

    # GenericIPAddressField (melhor validação)
    ip = models.GenericIPAddressField(
        protocol="both",
        unpack_ipv4=True,
        blank=True,
        null=True,
        help_text="Endereço IP do host"
    )

    description = models.TextField(
        blank=True,
        null=True,
        help_text="Descrição opcional do host"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.hostname

    class Meta:
        ordering = ['hostname']
        verbose_name_plural = 'Hosts'


class Metric(models.Model):
    """
    Métricas monitoradas (CPU e Memória RAM).

    metric_type:
    - cpu_percent: uso de CPU (%)
    - memory_percent: uso de Memória RAM (%)
    """

    METRIC_TYPES = (
        ('cpu_percent', 'CPU (%)'),
        ('memory_percent', 'Memória RAM (%)'),
    )

    host = models.ForeignKey(
        Host,
        on_delete=models.CASCADE,
        related_name='metrics'
    )

    timestamp = models.DateTimeField(
        db_index=True,
        help_text="Timestamp da coleta"
    )

    metric_type = models.CharField(
        max_length=20,
        choices=METRIC_TYPES,
        db_index=True,
        help_text="Tipo da métrica (cpu_percent ou memory_percent)"
    )

    value = models.FloatField(
        help_text="Valor da métrica em percentual"
    )

    extra = models.JSONField(
        blank=True,
        null=True,
        help_text="JSON com metadados adicionais"
    )

    def __str__(self):
        host = self.host.hostname if self.host else "SEM-HOST"
        return f"{host} | {self.metric_type}: {self.value}%"

    class Meta:
        indexes = [
            models.Index(fields=['host', 'timestamp']),
            models.Index(fields=['metric_type', 'timestamp']),
            models.Index(fields=['host', 'metric_type', 'timestamp']),
        ]
        ordering = ['-timestamp']
        verbose_name_plural = 'Metrics'
