import os
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'YouTube Audio Downloader'

    def ready(self):
        # Automatically inject static FFmpeg and FFprobe binaries into system PATH
        try:
            import static_ffmpeg
            static_ffmpeg.add_paths()
        except Exception:
            pass
