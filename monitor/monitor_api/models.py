from django.db import models

class Metric(models.Model):
    hostname = models.CharField(max_length=255)
    cpu_percent = models.FloatField()
    ram_percent = models.FloatField()
    disk_percent = models.FloatField()
    created_at = models.DateTimeField()

    def __str__(self):
        return f"{self.hostname} - {self.created_at}"
