/**
 * AITranscriber - 前端应用
 */
(function () {
    'use strict';

    // ---- State ----
    const state = {
        engines: [],
        selectedFile: null,
        currentTaskId: null,
        tasks: [],
        pollingTimers: {},
        audio: null,
        isPlaying: false,
        activeSegmentIndex: -1,
        editingSegmentIndex: -1,
        _rafId: null,
    };

    // ---- DOM refs ----
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    const dom = {
        engineStatus: $('#engineStatus'),
        uploadZone: $('#uploadZone'),
        fileInput: $('#fileInput'),
        selectedFile: $('#selectedFile'),
        fileName: $('#fileName'),
        fileSize: $('#fileSize'),
        removeFile: $('#removeFile'),
        engineSelect: $('#engineSelect'),
        modelSelect: $('#modelSelect'),
        languageSelect: $('#languageSelect'),
        startBtn: $('#startBtn'),
        taskList: $('#taskList'),
        welcomeScreen: $('#welcomeScreen'),
        resultView: $('#resultView'),
        audioElement: $('#audioElement'),
        playPauseBtn: $('#playPauseBtn'),
        playIcon: $('#playIcon'),
        pauseIcon: $('#pauseIcon'),
        stopBtn: $('#stopBtn'),
        currentTime: $('#currentTime'),
        totalTime: $('#totalTime'),
        speedSelect: $('#speedSelect'),
        volumeSlider: $('#volumeSlider'),
        waveformBar: $('#waveformBar'),
        waveformProgress: $('#waveformProgress'),
        waveformCursor: $('#waveformCursor'),
        playerFilename: $('#playerFilename'),
        playerEngine: $('#playerEngine'),
        exportBtn: $('#exportBtn'),
        exportMenu: $('#exportMenu'),
        segmentsList: $('#segmentsList'),
        segmentCount: $('#segmentCount'),
        detectedLang: $('#detectedLang'),
        retranscribeBtn: $('#retranscribeBtn'),
        retranscribeModal: $('#retranscribeModal'),
        retranscribeModalClose: $('#retranscribeModalClose'),
        retranscribeEngine: $('#retranscribeEngine'),
        retranscribeModel: $('#retranscribeModel'),
        retranscribeLanguage: $('#retranscribeLanguage'),
        retranscribeFilename: $('#retranscribeFilename'),
        retranscribeCancel: $('#retranscribeCancel'),
        retranscribeConfirm: $('#retranscribeConfirm'),
    };

    // ---- Init ----
    async function init() {
        setupUpload();
        setupPlayer();
        setupExport();
        setupRetranscribe();
        await loadEngines();
        await loadHistory();
        updateStartBtn();
    }

    // ---- API helpers ----
    async function api(url, options = {}) {
        const resp = await fetch(url, options);
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ detail: resp.statusText }));
            throw new Error(err.detail || 'Request failed');
        }
        return resp.json();
    }

    // ---- Toast ----
    function showToast(message, type = 'info') {
        let container = $('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        container.appendChild(toast);
        setTimeout(() => { toast.remove(); }, 4000);
    }

    // ---- Engines ----
    async function loadEngines() {
        try {
            const data = await api('/api/engines');
            state.engines = data.engines;

            dom.engineSelect.innerHTML = '';
            let hasAvailable = false;

            for (const engine of state.engines) {
                const opt = document.createElement('option');
                opt.value = engine.name;
                opt.textContent = engine.display_name + (engine.available ? '' : ' (未安装)');
                opt.disabled = !engine.available;
                dom.engineSelect.appendChild(opt);
                if (engine.available) hasAvailable = true;
            }

            if (hasAvailable) {
                const first = state.engines.find(e => e.available);
                if (first) {
                    dom.engineSelect.value = first.name;
                    updateModels(first.name);
                }
                dom.engineStatus.textContent = `${state.engines.filter(e => e.available).length} 个引擎可用`;
                dom.engineStatus.style.color = 'var(--success)';
            } else {
                dom.engineStatus.textContent = '无可用引擎';
                dom.engineStatus.style.color = 'var(--danger)';
            }

            dom.engineSelect.addEventListener('change', () => {
                updateModels(dom.engineSelect.value);
                updateStartBtn();
            });
        } catch (e) {
            dom.engineStatus.textContent = '引擎加载失败';
            dom.engineStatus.style.color = 'var(--danger)';
            console.error(e);
        }
    }

    function updateModels(engineName) {
        const engine = state.engines.find(e => e.name === engineName);
        dom.modelSelect.innerHTML = '';
        if (!engine || !engine.models.length) {
            dom.modelSelect.innerHTML = '<option value="">无可用模型</option>';
            return;
        }
        for (const model of engine.models) {
            const opt = document.createElement('option');
            opt.value = model.id;
            opt.textContent = `${model.name} - ${model.description}`;
            dom.modelSelect.appendChild(opt);
        }
    }

    // ---- History ----
    async function loadHistory() {
        try {
            const data = await api('/api/tasks');
            const tasks = data.tasks || [];
            for (const task of tasks) {
                const idx = state.tasks.findIndex(t => t.id === task.id);
                if (idx < 0) {
                    state.tasks.push(task);
                }
            }
            renderTaskList();
        } catch (e) {
            console.error('Failed to load history:', e);
        }
    }

    // ---- Upload ----
    function setupUpload() {
        dom.uploadZone.addEventListener('click', () => dom.fileInput.click());

        dom.uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dom.uploadZone.classList.add('dragover');
        });

        dom.uploadZone.addEventListener('dragleave', () => {
            dom.uploadZone.classList.remove('dragover');
        });

        dom.uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dom.uploadZone.classList.remove('dragover');
            if (e.dataTransfer.files.length) selectFile(e.dataTransfer.files[0]);
        });

        dom.fileInput.addEventListener('change', () => {
            if (dom.fileInput.files.length) selectFile(dom.fileInput.files[0]);
        });

        dom.removeFile.addEventListener('click', () => {
            state.selectedFile = null;
            dom.selectedFile.style.display = 'none';
            dom.uploadZone.style.display = '';
            dom.fileInput.value = '';
            updateStartBtn();
        });

        dom.startBtn.addEventListener('click', startTranscription);
    }

    function selectFile(file) {
        state.selectedFile = file;
        dom.fileName.textContent = file.name;
        dom.fileSize.textContent = formatFileSize(file.size);
        dom.selectedFile.style.display = 'flex';
        dom.uploadZone.style.display = 'none';
        updateStartBtn();
    }

    function updateStartBtn() {
        const engine = state.engines.find(e => e.name === dom.engineSelect.value);
        dom.startBtn.disabled = !state.selectedFile || !engine || !engine.available;
    }

    function formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }

    // ---- Transcription ----
    async function startTranscription() {
        if (!state.selectedFile) return;

        const formData = new FormData();
        formData.append('file', state.selectedFile);
        formData.append('engine', dom.engineSelect.value);
        formData.append('model', dom.modelSelect.value);
        formData.append('language', dom.languageSelect.value);

        dom.startBtn.disabled = true;
        dom.startBtn.innerHTML = '<span class="spinner" style="width:16px;height:16px;border-width:2px;margin:0;"></span> 上传中...';

        try {
            const data = await api('/api/upload', {
                method: 'POST',
                body: formData,
            });

            showToast('文件已上传，开始转录', 'success');
            startPolling(data.task_id);

            // Reset upload
            state.selectedFile = null;
            dom.selectedFile.style.display = 'none';
            dom.uploadZone.style.display = '';
            dom.fileInput.value = '';
        } catch (e) {
            showToast('上传失败: ' + e.message, 'error');
        } finally {
            dom.startBtn.disabled = false;
            dom.startBtn.innerHTML = `
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polygon points="5 3 19 12 5 21 5 3"/>
                </svg>
                开始转录`;
            updateStartBtn();
        }
    }

    // ---- Polling ----
    function startPolling(taskId) {
        if (state.pollingTimers[taskId]) return;

        const poll = async () => {
            try {
                const data = await api(`/api/task/${taskId}`);
                const task = data.task;
                updateTaskList(task);

                if (task.status === 'completed') {
                    clearInterval(state.pollingTimers[taskId]);
                    delete state.pollingTimers[taskId];
                    showToast(`"${task.filename}" 转录完成`, 'success');
                    showResult(task);
                } else if (task.status === 'failed') {
                    clearInterval(state.pollingTimers[taskId]);
                    delete state.pollingTimers[taskId];
                    showToast(`转录失败: ${task.error}`, 'error');
                }
            } catch (e) {
                console.error('Polling error:', e);
            }
        };

        poll();
        state.pollingTimers[taskId] = setInterval(poll, 1500);
    }

    // ---- Task List ----
    function updateTaskList(task) {
        const idx = state.tasks.findIndex(t => t.id === task.id);
        if (idx >= 0) {
            // Don't overwrite result data with a task that lacks it
            if (!task.result && state.tasks[idx].result) {
                task.result = state.tasks[idx].result;
            }
            state.tasks[idx] = task;
        } else {
            state.tasks.unshift(task);
        }
        renderTaskList();
    }

    function renderTaskList() {
        if (state.tasks.length === 0) {
            dom.taskList.innerHTML = '<div class="empty-state">暂无任务</div>';
            return;
        }

        const statusLabels = { pending: '等待中', processing: '处理中', completed: '已完成', failed: '失败' };

        dom.taskList.innerHTML = state.tasks.map(task => {
            const timeStr = task.created_at ? formatDate(task.created_at) : '';
            return `
            <div class="task-item ${task.id === state.currentTaskId ? 'active' : ''}"
                 data-task-id="${task.id}">
                <div class="task-item-header">
                    <span class="task-item-name" title="${task.filename}">${task.filename}</span>
                    <div class="task-item-right">
                        <span class="task-item-status ${task.status}">${statusLabels[task.status] || task.status}</span>
                        ${(task.status === 'completed' || task.status === 'failed') ? `
                        <button class="task-retranscribe-btn" data-task-id="${task.id}" title="重新转录">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="23 4 23 10 17 10"/>
                                <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
                            </svg>
                        </button>` : ''}
                        <button class="task-delete-btn" data-task-id="${task.id}" title="删除任务">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                            </svg>
                        </button>
                    </div>
                </div>
                ${task.status === 'processing' ? `
                    <div class="task-progress">
                        <div class="task-progress-bar" style="width:${Math.round(task.progress * 100)}%"></div>
                    </div>
                ` : ''}
                <div class="task-item-meta">${task.engine || ''} ${task.model ? '/ ' + task.model : ''}${timeStr ? ' · ' + timeStr : ''}</div>
            </div>`;
        }).join('');

        // Click task to view
        dom.taskList.querySelectorAll('.task-item').forEach(el => {
            el.addEventListener('click', async (e) => {
                if (e.target.closest('.task-delete-btn')) return;
                const taskId = el.dataset.taskId;
                const task = state.tasks.find(t => t.id === taskId);
                if (task && (task.status === 'completed' || task.has_result)) {
                    try {
                        const data = await api(`/api/task/${taskId}`);
                        showResult(data.task);
                    } catch (err) {
                        showToast('加载任务失败: ' + err.message, 'error');
                    }
                }
            });
        });

        // Delete buttons
        dom.taskList.querySelectorAll('.task-delete-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const taskId = btn.dataset.taskId;
                if (!confirm('确定删除此任务？关联的文件和转录结果将一并删除。')) return;
                try {
                    await api(`/api/task/${taskId}`, { method: 'DELETE' });
                    state.tasks = state.tasks.filter(t => t.id !== taskId);
                    if (state.currentTaskId === taskId) {
                        state.currentTaskId = null;
                        dom.resultView.style.display = 'none';
                        dom.welcomeScreen.style.display = '';
                    }
                    renderTaskList();
                    showToast('任务已删除', 'success');
                } catch (err) {
                    showToast('删除失败: ' + err.message, 'error');
                }
            });
        });

        // Retranscribe buttons in task list
        dom.taskList.querySelectorAll('.task-retranscribe-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const taskId = btn.dataset.taskId;
                // Set as current task and open modal
                state.currentTaskId = taskId;
                const task = state.tasks.find(t => t.id === taskId);
                if (!task) return;

                // Load full task data if needed, then show result view first
                try {
                    const data = await api(`/api/task/${taskId}`);
                    showResult(data.task);
                } catch (err) {
                    // Even if this fails, still open the modal
                }

                // Trigger the retranscribe button click
                dom.retranscribeBtn.click();
            });
        });
    }

    // ---- Show Result ----
    function showResult(task) {
        state.currentTaskId = task.id;

        // Store the full task data (with result) in state.tasks
        const idx = state.tasks.findIndex(t => t.id === task.id);
        if (idx >= 0) {
            // Preserve result if the incoming task has it
            if (task.result) {
                state.tasks[idx] = task;
            }
        } else {
            state.tasks.unshift(task);
        }

        renderTaskList();

        dom.welcomeScreen.style.display = 'none';
        dom.resultView.style.display = 'flex';

        dom.playerFilename.textContent = task.filename;
        dom.playerEngine.textContent = task.engine + ' / ' + task.model;

        // Setup audio
        dom.audioElement.src = `/api/audio/${task.id}`;
        dom.audioElement.load();

        const result = task.result;
        if (!result) {
            console.warn('showResult: task.result is empty', task);
            dom.segmentsList.innerHTML = '<div class="empty-state">暂无转录结果</div>';
            return;
        }

        const segments = result.segments || [];
        const langNames = { zh: '中文', en: 'English', ja: '日本語', ko: '한국어', fr: 'Français', de: 'Deutsch', es: 'Español', ru: 'Русский' };
        dom.segmentCount.textContent = `${segments.length} 个片段`;
        dom.detectedLang.textContent = langNames[result.language] || result.language || '';

        if (segments.length === 0) {
            dom.segmentsList.innerHTML = '<div class="empty-state">转录完成但未识别到内容</div>';
            return;
        }

        renderSegments(segments);
    }

    // ---- Segments ----
    const SPEAKER_COLORS = [
        '#6c5ce7', '#00cec9', '#e17055', '#00b894', '#fdcb6e',
        '#e84393', '#0984e3', '#d63031', '#6ab04c', '#f0932b',
    ];

    function getSpeakerColor(speaker, speakerMap) {
        if (!speaker) return '';
        if (!speakerMap.has(speaker)) {
            speakerMap.set(speaker, SPEAKER_COLORS[speakerMap.size % SPEAKER_COLORS.length]);
        }
        return speakerMap.get(speaker);
    }

    /**
     * Group consecutive segments by speaker.
     * Returns array of { speaker, color, segments: [{index, start, end, text}, ...] }
     */
    function groupSegmentsBySpeaker(segments, speakerMap) {
        const groups = [];
        let current = null;

        segments.forEach((seg, i) => {
            const speaker = seg.speaker || '';
            if (!current || current.speaker !== speaker) {
                current = {
                    speaker,
                    color: speaker ? getSpeakerColor(speaker, speakerMap) : '',
                    segments: [],
                };
                groups.push(current);
            }
            current.segments.push({ index: i, start: seg.start, end: seg.end, text: (seg.text || '').trim() });
        });

        return groups;
    }

    function renderSegments(segments) {
        if (!segments || segments.length === 0) {
            dom.segmentsList.innerHTML = '<div class="empty-state">转录完成但未识别到内容</div>';
            return;
        }

        // Detect if conversation mode (has speaker info)
        const hasSpeakers = segments.some(s => s.speaker);
        const speakerMap = new Map();

        if (hasSpeakers) {
            // Pre-assign colors
            segments.forEach(s => { if (s.speaker) getSpeakerColor(s.speaker, speakerMap); });

            // Group consecutive segments by speaker
            const groups = groupSegmentsBySpeaker(segments, speakerMap);

            dom.segmentsList.innerHTML = groups.map(group => {
                const firstSeg = group.segments[0];
                const lastSeg = group.segments[group.segments.length - 1];
                const totalDuration = lastSeg.end - firstSeg.start;

                let html = '';
                // Speaker label
                if (group.speaker) {
                    html += `<div class="speaker-divider" style="--speaker-color:${group.color}">
                        <span class="speaker-label" style="background:${group.color}">${escapeHtml(group.speaker)}</span>
                    </div>`;
                }

                // Merged block
                const subSegmentsHtml = group.segments.map(s => {
                    const displayText = s.text ? escapeHtml(s.text) : '<span style="color:var(--text-muted);font-style:italic">(无文字)</span>';
                    return `<span class="segment-phrase" data-index="${s.index}" data-start="${s.start}" data-end="${s.end}">${displayText}</span>`;
                }).join('');

                html += `
                <div class="segment-item has-speaker segment-group" data-start="${firstSeg.start}" data-end="${lastSeg.end}"
                     style="--speaker-color:${group.color}">
                    <div class="segment-time">
                        <span class="segment-time-badge" title="跳转到 ${formatTime(firstSeg.start)}">${formatTime(firstSeg.start)}</span>
                        <span class="segment-duration">${totalDuration.toFixed(1)}s</span>
                    </div>
                    <div class="segment-content">
                        <div class="segment-text segment-text-merged">${subSegmentsHtml}</div>
                    </div>
                </div>`;
                return html;
            }).join('');

            dom.segmentCount.textContent = `${segments.length} 个片段 · ${speakerMap.size} 位说话人`;
        } else {
            // Non-speaker mode: render as before
            dom.segmentsList.innerHTML = segments.map((seg, i) => {
                const text = (seg.text || '').trim();
                const displayText = text ? escapeHtml(text) : '<span style="color:var(--text-muted);font-style:italic">(无文字)</span>';
                return `
                <div class="segment-item" data-index="${i}" data-start="${seg.start}" data-end="${seg.end}">
                    <div class="segment-time">
                        <span class="segment-time-badge" title="跳转到 ${formatTime(seg.start)}">${formatTime(seg.start)}</span>
                        <span class="segment-duration">${(seg.end - seg.start).toFixed(1)}s</span>
                    </div>
                    <div class="segment-content">
                        <div class="segment-text" data-index="${i}">${displayText}</div>
                    </div>
                    <div class="segment-actions">
                        <button class="segment-edit-btn" data-index="${i}">编辑</button>
                    </div>
                </div>`;
            }).join('');
        }

        // Click time badge to seek
        dom.segmentsList.querySelectorAll('.segment-time-badge').forEach(badge => {
            badge.addEventListener('click', (e) => {
                e.stopPropagation();
                const item = badge.closest('.segment-item');
                const start = parseFloat(item.dataset.start);
                seekTo(start);
            });
        });

        // Click segment to seek & play
        dom.segmentsList.querySelectorAll('.segment-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (e.target.closest('.segment-edit-btn') || e.target.closest('.segment-save-btn') ||
                    e.target.closest('.segment-cancel-btn') || e.target.closest('.segment-time-badge') ||
                    e.target.getAttribute('contenteditable') === 'true') return;
                // If clicked on a phrase, seek to that phrase's start
                const phrase = e.target.closest('.segment-phrase');
                const start = phrase ? parseFloat(phrase.dataset.start) : parseFloat(item.dataset.start);
                seekTo(start);
                play();
            });
        });

        // Edit buttons (non-speaker mode only)
        dom.segmentsList.querySelectorAll('.segment-edit-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const index = parseInt(btn.dataset.index);
                startEditSegment(index);
            });
        });

        // Build cache for fast highlight lookup
        buildHighlightCache();
    }

    function startEditSegment(index) {
        if (state.editingSegmentIndex >= 0) cancelEditSegment();
        state.editingSegmentIndex = index;

        const textEl = dom.segmentsList.querySelector(`.segment-text[data-index="${index}"]`);
        const actionsEl = textEl.closest('.segment-item').querySelector('.segment-actions');

        textEl.contentEditable = 'true';
        textEl.focus();

        // Select all text
        const range = document.createRange();
        range.selectNodeContents(textEl);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);

        actionsEl.innerHTML = `
            <button class="segment-save-btn" data-index="${index}">保存</button>
            <button class="segment-cancel-btn" data-index="${index}">取消</button>
        `;
        actionsEl.style.opacity = '1';

        actionsEl.querySelector('.segment-save-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            saveEditSegment(index, textEl.textContent.trim());
        });

        actionsEl.querySelector('.segment-cancel-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            cancelEditSegment();
        });

        textEl.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                saveEditSegment(index, textEl.textContent.trim());
            }
            if (e.key === 'Escape') {
                cancelEditSegment();
            }
        });
    }

    async function saveEditSegment(index, text) {
        const formData = new FormData();
        formData.append('segment_index', index);
        formData.append('text', text);

        try {
            await api(`/api/result/${state.currentTaskId}/edit`, {
                method: 'POST',
                body: formData,
            });
            showToast('已保存修改', 'success');
        } catch (e) {
            showToast('保存失败: ' + e.message, 'error');
        }

        state.editingSegmentIndex = -1;
        const textEl = dom.segmentsList.querySelector(`.segment-text[data-index="${index}"]`);
        textEl.contentEditable = 'false';
        const actionsEl = textEl.closest('.segment-item').querySelector('.segment-actions');
        actionsEl.innerHTML = `<button class="segment-edit-btn" data-index="${index}">编辑</button>`;
        actionsEl.style.opacity = '';

        actionsEl.querySelector('.segment-edit-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            startEditSegment(index);
        });
    }

    function cancelEditSegment() {
        if (state.editingSegmentIndex < 0) return;
        const index = state.editingSegmentIndex;
        state.editingSegmentIndex = -1;

        const textEl = dom.segmentsList.querySelector(`.segment-text[data-index="${index}"]`);
        if (!textEl) return;
        textEl.contentEditable = 'false';

        // Restore from task data
        const task = state.tasks.find(t => t.id === state.currentTaskId);
        if (task && task.result && task.result.segments[index]) {
            textEl.textContent = task.result.segments[index].text;
        }

        const actionsEl = textEl.closest('.segment-item').querySelector('.segment-actions');
        actionsEl.innerHTML = `<button class="segment-edit-btn" data-index="${index}">编辑</button>`;
        actionsEl.style.opacity = '';

        actionsEl.querySelector('.segment-edit-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            startEditSegment(index);
        });
    }

    // ---- Retranscribe ----
    function setupRetranscribe() {
        dom.retranscribeBtn.addEventListener('click', () => {
            if (!state.currentTaskId) return;
            const task = state.tasks.find(t => t.id === state.currentTaskId);
            if (!task) return;

            dom.retranscribeFilename.textContent = task.filename;

            // Populate engine select from loaded engines
            dom.retranscribeEngine.innerHTML = '';
            for (const engine of state.engines) {
                const opt = document.createElement('option');
                opt.value = engine.name;
                opt.textContent = engine.display_name + (engine.available ? '' : ' (未安装)');
                opt.disabled = !engine.available;
                dom.retranscribeEngine.appendChild(opt);
            }
            // Pre-select current task's engine
            const curEngine = state.engines.find(e => e.name === task.engine && e.available);
            if (curEngine) {
                dom.retranscribeEngine.value = curEngine.name;
            } else {
                const firstAvail = state.engines.find(e => e.available);
                if (firstAvail) dom.retranscribeEngine.value = firstAvail.name;
            }
            updateRetranscribeModels();

            // Pre-select language
            dom.retranscribeLanguage.value = task.language || 'auto';

            dom.retranscribeEngine.onchange = updateRetranscribeModels;
            dom.retranscribeModal.style.display = '';
        });

        dom.retranscribeModalClose.addEventListener('click', closeRetranscribeModal);
        dom.retranscribeCancel.addEventListener('click', closeRetranscribeModal);
        dom.retranscribeModal.addEventListener('click', (e) => {
            if (e.target === dom.retranscribeModal) closeRetranscribeModal();
        });

        dom.retranscribeConfirm.addEventListener('click', doRetranscribe);
    }

    function updateRetranscribeModels() {
        const engineName = dom.retranscribeEngine.value;
        const engine = state.engines.find(e => e.name === engineName);
        dom.retranscribeModel.innerHTML = '';
        if (!engine || !engine.models.length) {
            dom.retranscribeModel.innerHTML = '<option value="">无可用模型</option>';
            return;
        }
        for (const model of engine.models) {
            const opt = document.createElement('option');
            opt.value = model.id;
            opt.textContent = `${model.name} - ${model.description}`;
            dom.retranscribeModel.appendChild(opt);
        }
        // Try to pre-select current task's model
        const task = state.tasks.find(t => t.id === state.currentTaskId);
        if (task && task.engine === engineName) {
            const hasModel = engine.models.some(m => m.id === task.model);
            if (hasModel) dom.retranscribeModel.value = task.model;
        }
    }

    function closeRetranscribeModal() {
        dom.retranscribeModal.style.display = 'none';
    }

    async function doRetranscribe() {
        if (!state.currentTaskId) return;

        const engine = dom.retranscribeEngine.value;
        const model = dom.retranscribeModel.value;
        const language = dom.retranscribeLanguage.value;

        dom.retranscribeConfirm.disabled = true;
        dom.retranscribeConfirm.innerHTML = '<span class="spinner" style="width:14px;height:14px;border-width:2px;margin:0;"></span> 提交中...';

        try {
            const formData = new FormData();
            formData.append('engine', engine);
            formData.append('model', model);
            formData.append('language', language);

            await api(`/api/task/${state.currentTaskId}/retranscribe`, {
                method: 'POST',
                body: formData,
            });

            closeRetranscribeModal();
            showToast('已开始重新转录', 'success');

            // Update local task state to processing
            const task = state.tasks.find(t => t.id === state.currentTaskId);
            if (task) {
                task.status = 'processing';
                task.engine = engine;
                task.model = model;
                task.language = language;
                task.result = null;
                task.progress = 0;
            }
            renderTaskList();

            // Show processing state in result view
            dom.segmentsList.innerHTML = '<div class="empty-state"><div class="spinner" style="margin:0 auto 12px"></div>正在重新转录...</div>';
            dom.playerEngine.textContent = engine + ' / ' + model;
            dom.segmentCount.textContent = '';
            dom.detectedLang.textContent = '';

            // Start polling for the retranscription
            startPolling(state.currentTaskId);
        } catch (e) {
            showToast('重新转录失败: ' + e.message, 'error');
        } finally {
            dom.retranscribeConfirm.disabled = false;
            dom.retranscribeConfirm.innerHTML = `
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="23 4 23 10 17 10"/>
                    <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
                </svg>
                开始转录`;
        }
    }

    // ---- Audio Player ----
    function setupPlayer() {
        const audio = dom.audioElement;

        dom.playPauseBtn.addEventListener('click', () => {
            if (state.isPlaying) pause();
            else play();
        });

        dom.stopBtn.addEventListener('click', () => {
            pause();
            audio.currentTime = 0;
            updatePlayerUI();
        });

        dom.speedSelect.addEventListener('change', () => {
            audio.playbackRate = parseFloat(dom.speedSelect.value);
        });

        dom.volumeSlider.addEventListener('input', () => {
            audio.volume = dom.volumeSlider.value / 100;
        });

        audio.addEventListener('loadedmetadata', () => {
            dom.totalTime.textContent = formatTime(audio.duration);
            audio.volume = dom.volumeSlider.value / 100;
        });

        audio.addEventListener('timeupdate', () => {
            updatePlayerUI();
        });

        audio.addEventListener('ended', () => {
            state.isPlaying = false;
            dom.playIcon.style.display = '';
            dom.pauseIcon.style.display = 'none';
            stopHighlightLoop();
        });

        // Waveform click to seek
        dom.waveformBar.addEventListener('click', (e) => {
            const rect = dom.waveformBar.getBoundingClientRect();
            const pct = (e.clientX - rect.left) / rect.width;
            audio.currentTime = pct * audio.duration;
            updatePlayerUI();
        });
    }

    function play() {
        dom.audioElement.play();
        state.isPlaying = true;
        dom.playIcon.style.display = 'none';
        dom.pauseIcon.style.display = '';
        startHighlightLoop();
    }

    function pause() {
        dom.audioElement.pause();
        state.isPlaying = false;
        dom.playIcon.style.display = '';
        dom.pauseIcon.style.display = 'none';
        stopHighlightLoop();
    }

    function startHighlightLoop() {
        stopHighlightLoop();
        function loop() {
            highlightActiveSegment();
            state._rafId = requestAnimationFrame(loop);
        }
        state._rafId = requestAnimationFrame(loop);
    }

    function stopHighlightLoop() {
        if (state._rafId) {
            cancelAnimationFrame(state._rafId);
            state._rafId = null;
        }
    }

    function seekTo(time) {
        dom.audioElement.currentTime = time;
        updatePlayerUI();
    }

    function updatePlayerUI() {
        const audio = dom.audioElement;
        if (!audio.duration) return;
        const pct = (audio.currentTime / audio.duration) * 100;
        dom.waveformProgress.style.width = pct + '%';
        dom.waveformCursor.style.left = pct + '%';
        dom.currentTime.textContent = formatTime(audio.currentTime);
    }

    // Cached segment data for fast highlight lookup (rebuilt on each renderSegments)
    let _cachedPhrases = null;  // [{el, start, end, group}]
    let _cachedItems = null;    // [{el, start, end, textEl}]
    let _highlightMode = '';    // 'phrases' | 'items'

    function buildHighlightCache() {
        const phrases = dom.segmentsList.querySelectorAll('.segment-phrase');
        if (phrases.length > 0) {
            _highlightMode = 'phrases';
            _cachedPhrases = [];
            phrases.forEach(ph => {
                _cachedPhrases.push({
                    el: ph,
                    start: parseFloat(ph.dataset.start),
                    end: parseFloat(ph.dataset.end),
                    group: ph.closest('.segment-item'),
                });
            });
            _cachedItems = null;
        } else {
            _highlightMode = 'items';
            _cachedPhrases = null;
            const items = dom.segmentsList.querySelectorAll('.segment-item');
            _cachedItems = [];
            items.forEach(item => {
                _cachedItems.push({
                    el: item,
                    start: parseFloat(item.dataset.start),
                    end: parseFloat(item.dataset.end),
                    textEl: item.querySelector('.segment-text'),
                });
            });
        }
    }

    function highlightActiveSegment() {
        const current = dom.audioElement.currentTime;

        if (_highlightMode === 'phrases' && _cachedPhrases) {
            let activeGroup = null;
            for (const p of _cachedPhrases) {
                if (current >= p.start && current < p.end) {
                    p.el.classList.add('phrase-playing');
                    activeGroup = p.group;
                } else {
                    p.el.classList.remove('phrase-playing');
                }
            }

            // Highlight the parent group
            const groups = dom.segmentsList.querySelectorAll('.segment-item');
            for (const g of groups) {
                if (g === activeGroup) g.classList.add('playing');
                else g.classList.remove('playing');
            }

            if (activeGroup && activeGroup !== state._lastActiveGroup) {
                state._lastActiveGroup = activeGroup;
                activeGroup.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
            return;
        }

        if (_cachedItems) {
            let newActive = -1;
            for (let i = 0; i < _cachedItems.length; i++) {
                const c = _cachedItems[i];
                if (current >= c.start && current < c.end) {
                    newActive = i;
                    c.el.classList.add('playing');
                    if (c.textEl) c.textEl.classList.add('text-playing');
                } else {
                    c.el.classList.remove('playing');
                    if (c.textEl) c.textEl.classList.remove('text-playing');
                }
            }

            if (newActive !== state.activeSegmentIndex && newActive >= 0) {
                state.activeSegmentIndex = newActive;
                _cachedItems[newActive].el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }
    }

    // ---- Export ----
    function setupExport() {
        dom.exportBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            dom.exportMenu.classList.toggle('show');
        });

        document.addEventListener('click', () => {
            dom.exportMenu.classList.remove('show');
        });

        dom.exportMenu.querySelectorAll('button').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const format = btn.dataset.format;
                dom.exportMenu.classList.remove('show');
                await exportResult(format);
            });
        });
    }

    async function exportResult(format) {
        if (!state.currentTaskId) return;
        try {
            const data = await api(`/api/export/${state.currentTaskId}?format=${format}`);
            downloadText(data.content, data.filename);
            showToast(`已导出 ${data.filename}`, 'success');
        } catch (e) {
            showToast('导出失败: ' + e.message, 'error');
        }
    }

    function downloadText(content, filename) {
        const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    }

    // ---- Helpers ----
    function formatTime(seconds) {
        if (!seconds || isNaN(seconds)) return '00:00';
        const m = Math.floor(seconds / 60);
        const s = Math.floor(seconds % 60);
        return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    }

    function formatDate(timestamp) {
        if (!timestamp) return '';
        const d = new Date(timestamp * 1000);
        const now = new Date();
        const isToday = d.toDateString() === now.toDateString();
        const yesterday = new Date(now);
        yesterday.setDate(yesterday.getDate() - 1);
        const isYesterday = d.toDateString() === yesterday.toDateString();

        const timeStr = `${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`;

        if (isToday) return `今天 ${timeStr}`;
        if (isYesterday) return `昨天 ${timeStr}`;
        return `${(d.getMonth()+1).toString().padStart(2,'0')}/${d.getDate().toString().padStart(2,'0')} ${timeStr}`;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // ---- Start ----
    document.addEventListener('DOMContentLoaded', init);
})();
