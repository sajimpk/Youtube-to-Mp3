/**
 * AudioTube Pro - Client-side AJAX interactions and real-time progress polling
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const urlInput = document.getElementById('youtube-url-input');
    const btnPaste = document.getElementById('btn-paste');
    const btnClearUrl = document.getElementById('btn-clear-url');
    const btnFetchInfo = document.getElementById('btn-fetch-info');
    const urlFeedback = document.getElementById('url-feedback');

    const previewCard = document.getElementById('video-preview-card');
    const videoThumb = document.getElementById('video-thumb');
    const videoDuration = document.getElementById('video-duration');
    const videoTitle = document.getElementById('video-title');
    const videoChannel = document.getElementById('video-channel');
    const videoViews = document.getElementById('video-views');
    const videoDate = document.getElementById('video-date');

    const formatSelector = document.getElementById('format-selector');
    const qualitySelector = document.getElementById('quality-selector');
    const qualityOptionGroup = document.getElementById('quality-option-group');

    const btnStartDownload = document.getElementById('btn-start-download');
    const progressBox = document.getElementById('progress-box');
    const progressStatusMsg = document.getElementById('progress-status-msg');
    const progressPercentage = document.getElementById('progress-percentage');
    const progressBarFill = document.getElementById('progress-bar-fill');
    const metricSpeed = document.getElementById('metric-speed');
    const metricSize = document.getElementById('metric-size');
    const metricEta = document.getElementById('metric-eta');

    const downloadSuccessCard = document.getElementById('download-success-card');
    const successTitle = document.getElementById('success-title');
    const successMeta = document.getElementById('success-meta');
    const btnDirectDownload = document.getElementById('btn-direct-download');
    const btnConvertAnother = document.getElementById('btn-convert-another');

    const historyList = document.getElementById('history-list');
    const btnRefreshHistory = document.getElementById('btn-refresh-history');
    const btnClearHistory = document.getElementById('btn-clear-history');

    const ffmpegModal = document.getElementById('ffmpeg-modal');
    const btnOpenFfmpegModal = document.getElementById('btn-open-ffmpeg-modal');
    const btnCloseFfmpegModal = document.getElementById('btn-close-ffmpeg-modal');
    const btnDismissModal = document.getElementById('btn-dismiss-modal');

    // State Variables
    let selectedFormat = 'mp3';
    let selectedQuality = '320';
    let activePollInterval = null;
    let isDownloading = false;

    // --- URL Regex Validator ---
    const YT_REGEX = /^(https?:\/\/)?(www\.|m\.|music\.)?(youtube\.com\/(watch\?v=|embed\/|v\/|shorts\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/i;

    function isValidYoutubeUrl(url) {
        return YT_REGEX.test(url.trim());
    }

    // --- URL Input Event Listeners ---
    urlInput.addEventListener('input', () => {
        const val = urlInput.value.trim();
        btnClearUrl.style.display = val ? 'block' : 'none';

        if (!val) {
            urlFeedback.textContent = '';
            urlFeedback.className = 'url-feedback';
            return;
        }

        if (isValidYoutubeUrl(val)) {
            urlFeedback.textContent = '✓ Valid YouTube link detected';
            urlFeedback.className = 'url-feedback success';
        } else {
            urlFeedback.textContent = '⚠️ Invalid link. Please enter a valid YouTube video or Shorts URL.';
            urlFeedback.className = 'url-feedback error';
        }
    });

    urlInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            fetchVideoMetadata();
        }
    });

    btnClearUrl.addEventListener('click', () => {
        urlInput.value = '';
        btnClearUrl.style.display = 'none';
        urlFeedback.textContent = '';
        previewCard.style.display = 'none';
    });

    btnPaste.addEventListener('click', async () => {
        try {
            const text = await navigator.clipboard.readText();
            if (text) {
                urlInput.value = text.trim();
                urlInput.dispatchEvent(new Event('input'));
                if (isValidYoutubeUrl(text)) {
                    fetchVideoMetadata();
                }
            }
        } catch (err) {
            showToast('Unable to read from clipboard. Please paste manually.', 'error');
        }
    });

    btnFetchInfo.addEventListener('click', fetchVideoMetadata);

    const qualityLabel = document.getElementById('quality-label');
    const audioQualitySelector = document.getElementById('audio-quality-selector');
    const videoQualitySelector = document.getElementById('video-quality-selector');
    const btnDownloadText = document.querySelector('.btn-download-content span');

    // --- Format & Bitrate Selectors ---
    formatSelector.querySelectorAll('.pill-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            formatSelector.querySelectorAll('.pill-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedFormat = btn.getAttribute('data-format');

            if (selectedFormat === 'mp4') {
                qualityOptionGroup.style.opacity = '1';
                qualityOptionGroup.style.pointerEvents = 'auto';
                qualityLabel.innerHTML = '<i class="fa-solid fa-video"></i> MP4 Video Resolution';
                audioQualitySelector.style.display = 'none';
                videoQualitySelector.style.display = 'flex';
                
                // Get active video quality
                const activeVideoBtn = videoQualitySelector.querySelector('.pill-btn.active');
                selectedQuality = activeVideoBtn ? activeVideoBtn.getAttribute('data-quality') : '1080';
                if (btnDownloadText) btnDownloadText.textContent = 'Start Video Download (MP4)';
            } else if (selectedFormat === 'mp3') {
                qualityOptionGroup.style.opacity = '1';
                qualityOptionGroup.style.pointerEvents = 'auto';
                qualityLabel.innerHTML = '<i class="fa-solid fa-gauge-high"></i> MP3 Audio Bitrate';
                audioQualitySelector.style.display = 'flex';
                videoQualitySelector.style.display = 'none';
                
                // Get active audio quality
                const activeAudioBtn = audioQualitySelector.querySelector('.pill-btn.active');
                selectedQuality = activeAudioBtn ? activeAudioBtn.getAttribute('data-quality') : '320';
                if (btnDownloadText) btnDownloadText.textContent = 'Start Audio Download (MP3)';
            } else {
                qualityOptionGroup.style.opacity = '0.4';
                qualityOptionGroup.style.pointerEvents = 'none';
                qualityLabel.innerHTML = `<i class="fa-solid fa-sliders"></i> ${selectedFormat.toUpperCase()} Quality`;
                selectedQuality = '320';
                if (btnDownloadText) btnDownloadText.textContent = `Start Audio Download (${selectedFormat.toUpperCase()})`;
            }
        });
    });

    audioQualitySelector.querySelectorAll('.pill-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            audioQualitySelector.querySelectorAll('.pill-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedQuality = btn.getAttribute('data-quality');
        });
    });

    videoQualitySelector.querySelectorAll('.pill-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            videoQualitySelector.querySelectorAll('.pill-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedQuality = btn.getAttribute('data-quality');
        });
    });

    // --- Fetch Video Info AJAX ---
    async function fetchVideoMetadata() {
        const url = urlInput.value.trim();
        if (!url) {
            showToast('Please enter a YouTube link first.', 'error');
            return;
        }

        if (!isValidYoutubeUrl(url)) {
            showToast('Please enter a valid YouTube URL.', 'error');
            return;
        }

        const origBtnText = btnFetchInfo.innerHTML;
        btnFetchInfo.disabled = true;
        btnFetchInfo.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Loading...';

        try {
            const formData = new FormData();
            formData.append('url', url);

            const res = await fetch('/api/fetch-info/', {
                method: 'POST',
                body: formData
            });

            const data = await res.json();
            if (data.success) {
                const info = data.data;
                videoTitle.textContent = info.title;
                videoChannel.textContent = info.uploader || info.channel;
                videoDuration.textContent = info.duration_str;
                videoViews.textContent = info.views_str;
                videoDate.textContent = info.upload_date ? info.upload_date : 'Uploaded';
                if (info.thumbnail_url) {
                    videoThumb.src = info.thumbnail_url;
                }
                previewCard.style.display = 'flex';
                showToast('Video information loaded!', 'success');
            } else {
                showToast(data.error || 'Failed to fetch video details.', 'error');
            }
        } catch (err) {
            showToast('Network error while fetching video info.', 'error');
        } finally {
            btnFetchInfo.disabled = false;
            btnFetchInfo.innerHTML = origBtnText;
        }
    }

    // --- Start Audio Download ---
    btnStartDownload.addEventListener('click', async () => {
        if (isDownloading) return;

        const url = urlInput.value.trim();
        if (!url || !isValidYoutubeUrl(url)) {
            showToast('Please provide a valid YouTube URL.', 'error');
            return;
        }

        isDownloading = true;
        btnStartDownload.disabled = true;
        btnStartDownload.style.opacity = '0.6';
        progressBox.style.display = 'block';
        downloadSuccessCard.style.display = 'none';

        progressBarFill.style.width = '0%';
        progressPercentage.textContent = '0%';
        metricSpeed.textContent = '0 MB/s';
        metricSize.textContent = 'Calculating...';
        metricEta.textContent = '--:--';
        progressStatusMsg.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Connecting to YouTube...';

        try {
            const formData = new FormData();
            formData.append('url', url);
            formData.append('format', selectedFormat);
            formData.append('quality', selectedQuality);

            const res = await fetch('/api/download/', {
                method: 'POST',
                body: formData
            });

            const data = await res.json();
            if (data.success && data.task_id) {
                // Begin progress polling
                pollProgress(data.task_id);
            } else {
                throw new Error(data.error || 'Failed to initialize download task.');
            }
        } catch (err) {
            handleDownloadError(err.message);
        }
    });

    // --- Real-time Progress Poller ---
    function pollProgress(taskId) {
        if (activePollInterval) clearInterval(activePollInterval);

        let consecutiveErrors = 0;

        activePollInterval = setInterval(async () => {
            try {
                const res = await fetch(`/api/progress/${taskId}/`);
                const data = await res.json().catch(() => ({}));

                if (!res.ok) {
                    consecutiveErrors++;
                    if (consecutiveErrors >= 3) {
                        throw new Error(data.error || 'Task error or connection timeout');
                    }
                    return; // Retry on next tick
                }

                consecutiveErrors = 0; // Reset error counter on success

                if (!data.success) {
                    throw new Error(data.error || 'Download failed');
                }

                const pct = Math.min(Math.max(data.progress || 0, 0), 100);
                progressBarFill.style.width = `${pct}%`;
                progressPercentage.textContent = `${Math.round(pct)}%`;
                metricSpeed.textContent = data.speed || '-- MB/s';
                metricSize.textContent = data.size || '-- / --';
                metricEta.textContent = data.eta || '--:--';
                progressStatusMsg.innerHTML = `<i class="fa-solid fa-arrows-rotate fa-spin"></i> ${data.message || 'Processing audio stream...'}`;

                if (data.completed) {
                    clearInterval(activePollInterval);
                    handleDownloadSuccess(data);
                } else if (data.status === 'error') {
                    clearInterval(activePollInterval);
                    handleDownloadError(data.error || 'Audio extraction encountered an error.');
                }
            } catch (err) {
                clearInterval(activePollInterval);
                handleDownloadError(err.message);
            }
        }, 800);
    }

    function handleDownloadSuccess(data) {
        isDownloading = false;
        btnStartDownload.disabled = false;
        btnStartDownload.style.opacity = '1';
        progressBox.style.display = 'none';

        successTitle.textContent = data.title || 'Audio File Ready';
        successMeta.textContent = `${selectedFormat.toUpperCase()} (${selectedQuality}kbps) • ${data.file_size || 'Ready'}`;
        btnDirectDownload.href = data.download_url;
        btnDirectDownload.setAttribute('download', data.file_name || 'audio.mp3');

        downloadSuccessCard.style.display = 'block';
        showToast('Audio extracted successfully! Click below to download.', 'success');

        // Automatically trigger browser download
        setTimeout(() => {
            btnDirectDownload.click();
        }, 600);

        // Refresh history
        refreshHistory();
    }

    function handleDownloadError(msg) {
        isDownloading = false;
        btnStartDownload.disabled = false;
        btnStartDownload.style.opacity = '1';
        progressBox.style.display = 'none';
        showToast(msg || 'An error occurred during audio download.', 'error');
    }

    btnConvertAnother.addEventListener('click', () => {
        downloadSuccessCard.style.display = 'none';
        urlInput.value = '';
        btnClearUrl.style.display = 'none';
        previewCard.style.display = 'none';
        urlFeedback.textContent = '';
        urlInput.focus();
    });

    // --- History Operations ---
    async function refreshHistory() {
        try {
            const res = await fetch('/api/history/');
            const data = await res.json();
            if (data.success && data.history) {
                renderHistory(data.history);
            }
        } catch (err) {
            console.error('Failed to load history:', err);
        }
    }

    function renderHistory(items) {
        if (!items || items.length === 0) {
            historyList.innerHTML = `
                <div class="empty-history" id="empty-history-placeholder">
                    <i class="fa-solid fa-music empty-icon"></i>
                    <p>No downloads recorded yet. Paste a link above to get started!</p>
                </div>
            `;
            return;
        }

        let html = '';
        items.forEach(item => {
            const fmt = (item.format || 'MP3').toLowerCase();
            html += `
                <div class="history-item">
                    <div class="history-badge badge-${fmt}">
                        ${item.format}
                    </div>
                    <div class="history-info">
                        <h4 class="history-title">${escapeHtml(item.title)}</h4>
                        <div class="history-sub">
                            <span><i class="fa-regular fa-user"></i> ${escapeHtml(item.channel)}</span>
                            <span>• ${item.quality}</span>
                            <span>• ${item.file_size}</span>
                            <span>• ${item.created_at}</span>
                        </div>
                    </div>
                    <div class="history-actions">
                        <span class="history-file-name" title="${escapeHtml(item.file_name)}">${escapeHtml(item.file_name)}</span>
                    </div>
                </div>
            `;
        });
        historyList.innerHTML = html;
    }

    btnRefreshHistory.addEventListener('click', () => {
        refreshHistory();
        showToast('History refreshed', 'success');
    });

    btnClearHistory.addEventListener('click', async () => {
        if (!confirm('Are you sure you want to clear all download history records?')) return;
        try {
            const res = await fetch('/api/clear-history/', { method: 'POST' });
            const data = await res.json();
            if (data.success) {
                refreshHistory();
                showToast('History records cleared', 'success');
            }
        } catch (err) {
            showToast('Failed to clear history', 'error');
        }
    });

    // --- Modal Controls ---
    if (btnOpenFfmpegModal) {
        btnOpenFfmpegModal.addEventListener('click', () => {
            ffmpegModal.style.display = 'flex';
        });
    }

    if (btnCloseFfmpegModal) {
        btnCloseFfmpegModal.addEventListener('click', () => {
            ffmpegModal.style.display = 'none';
        });
    }

    if (btnDismissModal) {
        btnDismissModal.addEventListener('click', () => {
            ffmpegModal.style.display = 'none';
        });
    }

    window.addEventListener('click', (e) => {
        if (e.target === ffmpegModal) {
            ffmpegModal.style.display = 'none';
        }
    });

    // --- Toast Alert Helper ---
    function showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icon = type === 'error' ? 'fa-triangle-exclamation' : (type === 'success' ? 'fa-circle-check' : 'fa-info-circle');
        toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${escapeHtml(message)}</span>`;
        
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    function escapeHtml(str) {
        if (!str) return '';
        return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
    }
});
