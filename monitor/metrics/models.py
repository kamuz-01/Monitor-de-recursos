from django.db import models

class Host(models.Model):
    hostname = models.CharField(max_length=150, unique=True)
    ip = models.CharField(max_length=45, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.hostname

class Metric(models.Model):
    host = models.ForeignKey(Host, on_delete=models.CASCADE, related_name='metrics')
    timestamp = models.DateTimeField(db_index=True)
    metric_type = models.CharField(max_length=50)  # e.g., 'memory', 'disk'
    value = models.FloatField()                     # value in percent or GB etc
    extra = models.JSONField(blank=True, null=True) # e.g., {'total':..., 'used':...}

    class Meta:
        indexes = [
            models.Index(fields=['host', 'timestamp']),
        ]

