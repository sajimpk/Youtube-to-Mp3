"""
Backend services for YouTube audio downloading, FFmpeg integration, and database task management.
Engineered for reliable multi-process execution under Gunicorn on cloud hosts like Railway.
"""

import os
import re
import sys
import uuid
import shutil
import threading
from datetime import datetime
from typing import Dict, Any, Optional
from django.conf import settings
from django.db import connection

import yt_dlp


class FFmpegDetector:
    """Detects FFmpeg installation on Windows and Linux/Railway."""

    @staticmethod
    def get_ffmpeg_path() -> Optional[str]:
        """Check if ffmpeg executable is available in PATH or common directories."""
        # 1. Standard PATH (Linux / Railway container / Windows PATH)
        ffmpeg_bin = shutil.which("ffmpeg")
        if ffmpeg_bin:
            return ffmpeg_bin

        # 2. Local project or common Windows paths
        base_dir = str(settings.BASE_DIR)
        common_paths = [
            os.path.join(base_dir, "ffmpeg.exe"),
            os.path.join(base_dir, "ffmpeg"),
            os.path.join(base_dir, "bin", "ffmpeg.exe"),
            "/usr/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-*\bin\ffmpeg.exe"),
            os.path.expandvars(r"%USERPROFILE%\scoop\apps\ffmpeg\current\bin\ffmpeg.exe"),
            r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
        ]

        import glob
        for pattern in common_paths:
            matches = glob.glob(pattern)
            if matches:
                return matches[0]

        return None

    @classmethod
    def is_available(cls) -> bool:
        return cls.get_ffmpeg_path() is not None


class URLValidator:
    """Validates and normalizes YouTube URLs."""

    YOUTUBE_REGEX = re.compile(
        r'^(https?://)?(www\.|m\.|music\.)?'
        r'(youtube\.com/(watch\?v=|embed/|v/|shorts/)|youtu\.be/)'
        r'([a-zA-Z0-9_-]{11})',
        re.IGNORECASE
    )

    @classmethod
    def is_valid_youtube_url(cls, url: str) -> bool:
        if not url or not isinstance(url, str):
            return False
        return bool(cls.YOUTUBE_REGEX.match(url.strip()))

    @classmethod
    def extract_video_id(cls, url: str) -> Optional[str]:
        if not url:
            return None
        match = cls.YOUTUBE_REGEX.match(url.strip())
        if match:
            return match.group(5)
        return None

    @classmethod
    def clean_url(cls, url: str) -> str:
        video_id = cls.extract_video_id(url)
        if video_id:
            return f"https://www.youtube.com/watch?v={video_id}"
        return url.strip()


class VideoInfoFetcher:
    """Fetches video metadata safely without downloading media."""

    @staticmethod
    def format_duration(seconds: Optional[int]) -> str:
        if not seconds:
            return "Unknown"
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    @staticmethod
    def format_views(view_count: Optional[int]) -> str:
        if not view_count:
            return "N/A"
        if view_count >= 1_000_000_000:
            return f"{view_count / 1_000_000_000:.1f}B views"
        elif view_count >= 1_000_000:
            return f"{view_count / 1_000_000:.1f}M views"
        elif view_count >= 1_000:
            return f"{view_count / 1_000:.1f}K views"
        return f"{view_count:,} views"

    @classmethod
    def fetch_info(cls, url: str) -> Dict[str, Any]:
        if not URLValidator.is_valid_youtube_url(url):
            raise ValueError("Invalid YouTube URL. Please enter a valid YouTube video or Shorts link.")

        clean_url = URLValidator.clean_url(url)
        
        ydl_opts = {
            'extract_flat': False,
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': False,
            'noplaylist': True,
            'socket_timeout': 15,
            'geo_bypass': True,
            'nocheckcertificate': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
            },
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(clean_url, download=False)
                if not info:
                    raise ValueError("Could not retrieve video details. Video may be private or unavailable.")

                thumbnails = info.get('thumbnails', [])
                best_thumbnail = info.get('thumbnail')
                if thumbnails:
                    sorted_thumbs = sorted(
                        [t for t in thumbnails if t.get('url')],
                        key=lambda t: (t.get('preference', 0), t.get('width', 0)),
                        reverse=True
                    )
                    if sorted_thumbs:
                        best_thumbnail = sorted_thumbs[0]['url']

                duration_sec = info.get('duration')
                return {
                    'id': info.get('id', ''),
                    'title': info.get('title', 'Unknown Title'),
                    'uploader': info.get('uploader') or info.get('channel', 'Unknown Artist/Channel'),
                    'channel': info.get('channel') or info.get('uploader', 'Unknown Channel'),
                    'duration_sec': duration_sec,
                    'duration_str': cls.format_duration(duration_sec),
                    'views_str': cls.format_views(info.get('view_count')),
                    'upload_date': info.get('upload_date', ''),
                    'thumbnail_url': best_thumbnail,
                    'url': clean_url,
                    'description': (info.get('description') or '')[:200]
                }
        except yt_dlp.utils.DownloadError as e:
            err_msg = str(e)
            if "Private video" in err_msg:
                raise ValueError("This video is private and cannot be accessed.")
            elif "Sign in to confirm your age" in err_msg or "age-restricted" in err_msg.lower():
                raise ValueError("This video is age-restricted.")
            elif "Video unavailable" in err_msg:
                raise ValueError("This video is unavailable (may have been deleted or blocked).")
            elif "HTTP Error 404" in err_msg:
                raise ValueError("Video not found (404).")
            elif "Sign in" in err_msg or "bot" in err_msg.lower():
                raise ValueError("YouTube bot protection encountered. Please try again.")
            else:
                clean_err = re.sub(r'ERROR:\s*(\[.*?\])?', '', err_msg).strip()
                raise ValueError(clean_err)
        except Exception as e:
            raise Exception(f"Failed to fetch video details: {str(e)}")


class DownloadTaskManager:
    """Manages active tasks backed by the database for shared Gunicorn multi-worker access."""

    @classmethod
    def create_task(cls, url: str, audio_format: str, quality: str) -> str:
        from core.models import DownloadTask
        task_id = str(uuid.uuid4())
        DownloadTask.objects.create(
            task_id=task_id,
            url=url,
            audio_format=audio_format.lower(),
            quality=quality,
            status='starting',
            progress=0.0,
            message='Connecting to YouTube...'
        )
        return task_id

    @classmethod
    def get_task(cls, task_id: str) -> Optional[Dict[str, Any]]:
        from core.models import DownloadTask
        task = DownloadTask.objects.filter(task_id=task_id).first()
        if not task:
            return None
        return {
            'id': task.task_id,
            'url': task.url,
            'format': task.audio_format,
            'quality': task.quality,
            'status': task.status,
            'progress': task.progress,
            'speed': task.speed,
            'size': task.size,
            'eta': task.eta,
            'message': task.message,
            'file_path': task.file_path,
            'file_name': task.file_name,
            'file_size': task.file_size,
            'title': task.title,
            'channel': task.channel,
            'thumbnail_url': task.thumbnail_url,
            'duration_str': task.duration_str,
            'error': task.error,
            'completed': task.completed,
        }

    @classmethod
    def update_task(cls, task_id: str, **kwargs):
        from core.models import DownloadTask
        try:
            DownloadTask.objects.filter(task_id=task_id).update(**kwargs)
        except Exception:
            pass

    @classmethod
    def run_download_async(cls, task_id: str):
        thread = threading.Thread(target=cls._execute_download, args=(task_id,), daemon=True)
        thread.start()

    @classmethod
    def _execute_download(cls, task_id: str):
        connection.close()  # Ensure clean connection in new thread
        from core.models import DownloadTask, DownloadRecord

        task = DownloadTask.objects.filter(task_id=task_id).first()
        if not task:
            return

        url = task.url
        audio_format = task.audio_format
        audio_quality = task.quality
        output_dir = os.path.join(settings.MEDIA_ROOT, 'audio_downloads')
        os.makedirs(output_dir, exist_ok=True)

        downloaded_file = {'path': None}

        def progress_hook(d: Dict[str, Any]):
            status = d.get('status')
            if status == 'downloading':
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                downloaded_bytes = d.get('downloaded_bytes') or 0
                
                percent = 0.0
                if total_bytes > 0:
                    percent = round((downloaded_bytes / total_bytes) * 100, 1)
                elif '_percent_str' in d:
                    raw_pct = re.sub(r'[^\d.]', '', d['_percent_str'])
                    if raw_pct:
                        try:
                            percent = float(raw_pct)
                        except ValueError:
                            percent = 0.0

                speed_bytes = d.get('speed') or 0
                eta_seconds = d.get('eta') or 0

                if speed_bytes > 1_048_576:
                    speed_str = f"{speed_bytes / 1_048_576:.2f} MB/s"
                elif speed_bytes > 1024:
                    speed_str = f"{speed_bytes / 1024:.1f} KB/s"
                else:
                    speed_str = f"{speed_bytes:.0f} B/s"

                def format_b(b: float) -> str:
                    if b > 1_048_576:
                        return f"{b / 1_048_576:.1f} MB"
                    elif b > 1024:
                        return f"{b / 1024:.1f} KB"
                    return f"{b:.0f} B"

                size_str = f"{format_b(downloaded_bytes)} / {format_b(total_bytes) if total_bytes else 'Unknown'}"
                
                if eta_seconds and eta_seconds > 0:
                    mins = int(eta_seconds // 60)
                    secs = int(eta_seconds % 60)
                    eta_str = f"{mins:02d}:{secs:02d}"
                else:
                    eta_str = "--:--"

                cls.update_task(
                    task_id,
                    status='downloading',
                    progress=min(percent, 95.0),
                    speed=speed_str,
                    size=size_str,
                    eta=eta_str,
                    message=f"Downloading audio stream ({percent}%)..."
                )

            elif status == 'finished':
                fn = d.get('filename')
                if fn:
                    downloaded_file['path'] = fn
                cls.update_task(
                    task_id,
                    status='converting',
                    progress=96.0,
                    message=f"Converting audio to {audio_format.upper()} via FFmpeg..."
                )

        def postprocessor_hook(d: Dict[str, Any]):
            status = d.get('status')
            if status == 'started':
                cls.update_task(
                    task_id,
                    status='converting',
                    progress=97.0,
                    message=f"Extracting & encoding {audio_format.upper()}..."
                )
            elif status == 'finished':
                info_dict = d.get('info_dict', {})
                fp = info_dict.get('filepath') or info_dict.get('_filename')
                if fp:
                    downloaded_file['path'] = fp
                cls.update_task(
                    task_id,
                    status='finalizing',
                    progress=99.0,
                    message="Finalizing audio tags & metadata..."
                )

        # Build yt-dlp options
        postprocessors = [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': audio_format,
                'preferredquality': audio_quality if audio_format == 'mp3' else None,
                'nopostoverwrites': False,
            },
            {
                'key': 'FFmpegMetadata',
                'add_metadata': True,
            }
        ]

        ffmpeg_bin = FFmpegDetector.get_ffmpeg_path()
        ffmpeg_location = os.path.dirname(ffmpeg_bin) if ffmpeg_bin else None

        out_template = os.path.join(output_dir, f"%(title)s_{task_id[:8]}.%(ext)s")

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': out_template,
            'postprocessors': postprocessors,
            'progress_hooks': [progress_hook],
            'postprocessor_hooks': [postprocessor_hook],
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'windowsfilenames': True,
            'overwrites': True,
            'socket_timeout': 30,
            'geo_bypass': True,
            'nocheckcertificate': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
            },
        }

        if ffmpeg_location:
            ydl_opts['ffmpeg_location'] = ffmpeg_location

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if not info:
                    raise Exception("Failed to retrieve audio stream from YouTube.")

                title = info.get('title', 'Audio Track')
                channel = info.get('uploader') or info.get('channel', 'Unknown Artist')
                duration_sec = info.get('duration', 0)
                duration_str = VideoInfoFetcher.format_duration(duration_sec)
                thumbnail_url = info.get('thumbnail', '')

                final_path = downloaded_file['path']
                if not final_path or not os.path.exists(final_path):
                    matches = [
                        os.path.join(output_dir, f)
                        for f in os.listdir(output_dir)
                        if task_id[:8] in f
                    ]
                    if matches:
                        final_path = max(matches, key=os.path.getmtime)
                    else:
                        raise Exception("Output audio file was not generated.")

                file_size_bytes = os.path.getsize(final_path)
                def format_sz(b: int) -> str:
                    if b > 1_048_576:
                        return f"{b / 1_048_576:.2f} MB"
                    elif b > 1024:
                        return f"{b / 1024:.1f} KB"
                    return f"{b} B"

                file_name = os.path.basename(final_path)
                file_size_str = format_sz(file_size_bytes)

                try:
                    DownloadRecord.objects.create(
                        title=title,
                        channel=channel,
                        url=url,
                        duration_str=duration_str,
                        audio_format=audio_format.upper(),
                        quality=f"{audio_quality} kbps" if audio_format == 'mp3' else 'Default',
                        file_name=file_name,
                        file_path=final_path,
                        file_size=file_size_str,
                        file_size_bytes=file_size_bytes,
                        thumbnail_url=thumbnail_url
                    )
                except Exception as db_err:
                    print(f"Warning: Database record save error: {db_err}", file=sys.stderr)

                cls.update_task(
                    task_id,
                    status='completed',
                    progress=100.0,
                    completed=True,
                    message="Download and conversion complete!",
                    file_path=final_path,
                    file_name=file_name,
                    file_size=file_size_str,
                    title=title,
                    channel=channel,
                    thumbnail_url=thumbnail_url,
                    duration_str=duration_str
                )

        except yt_dlp.utils.DownloadError as e:
            err_str = str(e)
            if "ffmpeg not found" in err_str.lower() or "ffprobe not found" in err_str.lower():
                msg = "FFmpeg is missing on the server. Required for MP3/WAV conversion."
            elif "Sign in" in err_str or "bot" in err_str.lower():
                msg = "YouTube temporarily rate-limited the cloud IP. Please try again in a moment."
            else:
                clean_err = re.sub(r'ERROR:\s*(\[.*?\])?', '', err_str).strip()
                msg = clean_err
            cls.update_task(task_id, status='error', error=msg, message=f"Error: {msg}")
        except Exception as e:
            cls.update_task(task_id, status='error', error=str(e), message=f"Error: {str(e)}")
        finally:
            connection.close()
