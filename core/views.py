"""
Views and API endpoints for YouTube Audio Downloader Web Application.
"""

import os
import mimetypes
from django.shortcuts import render
from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET

from core.models import DownloadRecord
from core.services import (
    FFmpegDetector,
    URLValidator,
    VideoInfoFetcher,
    DownloadTaskManager,
)


def index_view(request):
    """Renders the main single-page modern web application."""
    recent_downloads = DownloadRecord.objects.all()[:15]
    ffmpeg_available = FFmpegDetector.is_available()
    ffmpeg_path = FFmpegDetector.get_ffmpeg_path()

    context = {
        'recent_downloads': recent_downloads,
        'ffmpeg_available': ffmpeg_available,
        'ffmpeg_path': ffmpeg_path,
    }
    return render(request, 'core/index.html', context)


@require_POST
@csrf_exempt
def api_fetch_info(request):
    """API endpoint to fetch YouTube video metadata and thumbnail."""
    url = request.POST.get('url', '').strip()
    if not url:
        return JsonResponse({'success': False, 'error': 'Please provide a YouTube URL.'}, status=400)

    if not URLValidator.is_valid_youtube_url(url):
        return JsonResponse({'success': False, 'error': 'Invalid YouTube URL format. Please check the link.'}, status=400)

    try:
        info = VideoInfoFetcher.fetch_info(url)
        return JsonResponse({'success': True, 'data': info})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_POST
@csrf_exempt
def api_start_download(request):
    """API endpoint to initialize background audio download."""
    url = request.POST.get('url', '').strip()
    audio_format = request.POST.get('format', 'mp3').strip().lower()
    quality = request.POST.get('quality', '320').strip()

    if not url or not URLValidator.is_valid_youtube_url(url):
        return JsonResponse({'success': False, 'error': 'Valid YouTube URL required.'}, status=400)

    if audio_format not in ['mp3', 'm4a', 'wav']:
        audio_format = 'mp3'

    if quality not in ['128', '192', '320']:
        quality = '320'

    # Create task and launch asynchronous downloader
    task_id = DownloadTaskManager.create_task(url, audio_format, quality)
    DownloadTaskManager.run_download_async(task_id)

    return JsonResponse({
        'success': True,
        'task_id': task_id,
        'message': 'Download task started'
    })


@require_GET
def api_check_progress(request, task_id):
    """API endpoint to poll download progress in real-time."""
    task = DownloadTaskManager.get_task(task_id)
    if not task:
        return JsonResponse({'success': False, 'error': 'Task not found'}, status=404)

    # Format response
    response_data = {
        'success': True,
        'status': task.get('status'),
        'progress': task.get('progress', 0),
        'speed': task.get('speed', '0 MB/s'),
        'size': task.get('size', '0 MB'),
        'eta': task.get('eta', '--:--'),
        'message': task.get('message', ''),
        'completed': task.get('completed', False),
        'error': task.get('error'),
        'title': task.get('title'),
        'channel': task.get('channel'),
        'file_name': task.get('file_name'),
        'file_size': task.get('file_size'),
        'thumbnail_url': task.get('thumbnail_url'),
    }

    if task.get('completed'):
        response_data['download_url'] = f"/api/get-file/{task_id}/"

    return JsonResponse(response_data)


@require_GET
def api_download_file(request, task_id):
    """Serves the generated audio file to the user's browser for download."""
    task = DownloadTaskManager.get_task(task_id)
    if not task or not task.get('completed') or not task.get('file_path'):
        raise Http404("Audio file not ready or expired.")

    file_path = task['file_path']
    if not os.path.exists(file_path):
        raise Http404("File not found on server.")

    # Guess MIME type
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = 'audio/mpeg' if file_path.endswith('.mp3') else 'application/octet-stream'

    clean_filename = task.get('file_name') or os.path.basename(file_path)
    
    response = FileResponse(open(file_path, 'rb'), content_type=mime_type)
    response['Content-Disposition'] = f'attachment; filename="{clean_filename}"'
    return response


@require_GET
def api_get_history(request):
    """Returns the list of recent downloads as JSON."""
    records = DownloadRecord.objects.all()[:20]
    data = []
    for r in records:
        data.append({
            'id': r.id,
            'title': r.title,
            'channel': r.channel,
            'format': r.audio_format,
            'quality': r.quality,
            'file_size': r.file_size,
            'duration_str': r.duration_str,
            'created_at': r.created_at.strftime("%Y-%m-%d %H:%M"),
            'file_name': r.file_name,
            'thumbnail_url': r.thumbnail_url or '',
        })
    return JsonResponse({'success': True, 'history': data})


@require_POST
@csrf_exempt
def api_clear_history(request):
    """Clears download history from database."""
    DownloadRecord.objects.all().delete()
    return JsonResponse({'success': True, 'message': 'History cleared'})
