from django.db import models
from django.utils import timezone


class DownloadTask(models.Model):
    """Tracks active and recent audio download tasks across all Gunicorn worker processes."""
    task_id = models.CharField(max_length=64, unique=True, db_index=True)
    url = models.URLField(max_length=500)
    audio_format = models.CharField(max_length=10, default='mp3')
    quality = models.CharField(max_length=50, default='320')
    status = models.CharField(max_length=50, default='starting')  # starting, downloading, converting, finalizing, completed, error
    progress = models.FloatField(default=0.0)
    speed = models.CharField(max_length=50, default='0 MB/s')
    size = models.CharField(max_length=50, default='0 MB')
    eta = models.CharField(max_length=50, default='--:--')
    message = models.CharField(max_length=500, default='Connecting to YouTube...')
    file_path = models.CharField(max_length=1000, blank=True, null=True)
    file_name = models.CharField(max_length=500, blank=True, null=True)
    file_size = models.CharField(max_length=50, blank=True, null=True)
    title = models.CharField(max_length=500, blank=True, null=True)
    channel = models.CharField(max_length=255, blank=True, null=True)
    thumbnail_url = models.URLField(max_length=1000, blank=True, null=True)
    duration_str = models.CharField(max_length=50, blank=True, null=True)
    error = models.TextField(blank=True, null=True)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Task {self.task_id} - {self.status}"


class DownloadRecord(models.Model):
    """Stores metadata of downloaded audio tracks for the history feed."""
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
