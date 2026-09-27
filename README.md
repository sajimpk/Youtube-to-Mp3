# 🎵 AudioTube Pro - Django YouTube Audio Downloader Web Application

A full-stack **Django web application** for downloading high-fidelity audio (MP3, M4A, WAV) from YouTube videos and Shorts using `yt-dlp` and `FFmpeg`.

Featuring a glassmorphism dark theme, real-time AJAX video info preview with thumbnail extraction, multi-format bitrate options, live download progress polling (speed, percentage, size, ETA), and persistent database history logging.

---

## 🌟 Features

- **⚡ Django Backend & REST APIs**: Clean Model-View-Template architecture with asynchronous background audio downloading and real-time polling endpoints.
- **🚀 Pure Audio Extraction**: Streams audio tracks directly via `bestaudio/best` without wasting bandwidth downloading full video frames.
- **🎧 Multiple Formats & Bitrates**:
  - **MP3**: `320 kbps (Studio Quality)`, `192 kbps (Standard)`, `128 kbps (Eco)`.
  - **M4A**: AAC audio container for Apple/mobile compatibility.
  - **WAV**: Uncompressed lossless audio format.
- **🖼️ Instant Video Metadata Preview**: Fetches title, channel, duration, view count, and high-resolution thumbnail asynchronously upon pasting link.
- **📊 Real-Time Progress Bar & Metrics**:
  - Live download percentage %, speed (`MB/s`), downloaded size, and remaining ETA.
  - Multi-phase status messages (*Connecting*, *Downloading*, *Converting with FFmpeg*, *Finalizing Tags*).
- **💾 Automatic Browser Download**: Automatically delivers the processed audio file directly to the user's browser with 1-click save.
- **📜 SQLite Download History**: Persistently records past downloads in the database with instant refresh and clear options.
- **🔍 Built-in FFmpeg Detection**: Scans system paths and offers a 1-step installer guide if FFmpeg is missing.

---

## 📂 Project Structure

```
Mp3 Yt/
├── manage.py                  # Django administrative command-line utility
├── db.sqlite3                 # SQLite database for history records
├── requirements.txt           # Python dependencies (Django, yt-dlp, Pillow, requests)
├── README.md                  # Documentation and running guide
├── config/                    # Project configuration package
│   ├── __init__.py
│   ├── settings.py            # Django settings (apps, static, media, database)
│   ├── urls.py                # Main URL routing
│   └── wsgi.py                # WSGI application entry point
├── core/                      # Main Downloader Application
│   ├── __init__.py
│   ├── apps.py                # App configuration
│   ├── models.py              # DownloadRecord model
│   ├── services.py            # yt-dlp downloading engine, task manager & FFmpeg detector
│   ├── views.py               # Views and AJAX JSON API endpoints
│   ├── urls.py                # App URL patterns
│   ├── migrations/            # Database migrations
│   ├── static/core/           # Static assets
│   │   ├── css/style.css      # Vanilla CSS responsive design system & glassmorphism
│   │   └── js/app.js          # Async AJAX fetch & live progress polling
│   └── templates/core/        # HTML templates
│       ├── base.html          # Base layout with fonts, navbar & footer
│       └── index.html         # Interactive web interface
└── media/                     # Audio storage directory
    └── audio_downloads/
```

---

## 🚀 Quick Start & Installation

### 1. Navigate to Project Directory
```powershell
cd "c:\Users\Arif Academy ICT\Desktop\PRO-LIVE\Mp3 Yt"
```

### 2. Activate Virtual Environment & Install Dependencies
```powershell
# Create venv if not already created
python -m venv .venv

# Activate (PowerShell)
.\.venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt
```

### 3. Run Database Migrations
```powershell
python manage.py migrate
```

### 4. Start the Django Web Server
```powershell
python manage.py runserver
```

Open your browser and navigate to:
```
http://127.0.0.1:8000/
```

---

## 🎬 Installing FFmpeg on Windows

Audio conversion to MP3, M4A, and WAV requires FFmpeg. Choose any method:

### Option 1: 1-Click via WinGet (Recommended)
Open **PowerShell** or **Command Prompt** (Run as Administrator) and run:
```powershell
winget install Gyan.FFmpeg
```

### Option 2: Portable Direct Placement
1. Download the release build from [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/).
2. Extract `ffmpeg.exe` and `ffprobe.exe` directly into the project root folder [`c:\Users\Arif Academy ICT\Desktop\PRO-LIVE\Mp3 Yt\`](file:///c:/Users/Arif%20Academy%20ICT/Desktop/PRO-LIVE/Mp3%20Yt/). The application will detect it automatically.

---

## 📡 REST API Endpoints

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/` | `GET` | Main Web Application Interface |
| `/api/fetch-info/` | `POST` | Fetches YouTube video metadata & thumbnail |
| `/api/download/` | `POST` | Initiates asynchronous audio download task |
| `/api/progress/<task_id>/` | `GET` | Returns live progress %, speed, size, and ETA |
| `/api/get-file/<task_id>/` | `GET` | Streams the downloaded audio file to browser |
| `/api/history/` | `GET` | Returns recent download records |
| `/api/clear-history/` | `POST` | Clears all download history |

---

## 🔒 Security & Reliability

- **Safe Execution**: Does not execute arbitrary shell strings from user input.
- **Filename Sanitization**: Automatically normalizes and strips illegal operating system characters.
- **Zero Privacy Collection**: No YouTube credentials or personal cookies are stored or requested.
- **Stream Isolation**: Only requests audio streams to ensure high speed and low memory footprint.
