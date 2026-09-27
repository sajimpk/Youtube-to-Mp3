from django.db import models
from django.utils import timezone


class DownloadRecord(models.Model):
    """Stores metadata of downloaded audio tracks."""
    title = models.CharField(max_length=500)
    channel = models.CharField(max_length=255, default='Unknown Artist')
    url = models.URLField(max_length=500)
    duration_str = models.CharField(max_length=50, default='00:00')
    audio_format = models.CharField(max_length=10, default='MP3')
    quality = models.CharField(max_length=50, default='320 kbps')
    file_name = models.CharField(max_length=500)
    file_path = models.CharField(max_length=1000)
    file_size = models.CharField(max_length=50, default='0 MB')
    file_size_bytes = models.BigIntegerField(default=0)
    thumbnail_url = models.URLField(max_length=1000, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Download Record'
        verbose_name_plural = 'Download Records'

    def __str__(self):
        return f"{self.title} ({self.audio_format} - {self.quality})"
