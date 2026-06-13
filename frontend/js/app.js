/**
 * LightVideo 主应用逻辑
 * 页面路由、状态管理、功能页面渲染
 */

// ================================================================
// 全局状态
// ================================================================
const AppState = {
    currentPage: 'home',
    currentVideo: null,
    videoMetadata: null,
    videoFileName: '',
    isProcessing: false,

    // 各功能结果缓存
    summaryResult: null,
    textResult: null,
    eventResult: null,
    sceneResult: null,
    trackResult: null,
};

// ================================================================
// 注册进度回调
// ================================================================
window.onProgress = function (data) {
    const { stage, progress, message } = data;
    Components.showProgress(stage, progress, message);
};

// ================================================================
// 导航
// ================================================================
function navigateTo(page) {
    if (AppState.isProcessing) {
        Components.showToast('正在处理中，请等待完成', 'warning');
        return;
    }

    AppState.currentPage = page;

    // 更新导航高亮
    document.querySelectorAll('.nav-item').forEach(el => {
        el.classList.toggle('active', el.dataset.page === page);
    });

    // 渲染对应页面
    const container = document.getElementById('pageContainer');
    container.className = 'page-enter';
    switch (page) {
        case 'home': renderHome(container); break;
        case 'summary': renderSummaryPage(container); break;
        case 'text': renderTextPage(container); break;
        case 'events': renderEventsPage(container); break;
        case 'scenes': renderScenesPage(container); break;
        case 'track': renderTrackPage(container); break;
        case 'settings': renderSettingsPage(container); break;
        case 'about': renderAboutPage(container); break;
        default: renderHome(container);
    }
    // 移除动画类避免重复触发
    setTimeout(() => container.classList.remove('page-enter'), 400);
}

// ================================================================
// Ollama / API 状态检测
// ================================================================
async function checkOllamaStatus() {
    const el = document.getElementById('ollamaStatus');
    const dot = el.querySelector('.status-dot');
    const label = el.querySelector('span:last-child');

    dot.className = 'status-dot checking';
    label.textContent = '检测中...';

    try {
        const result = await API.checkOllama();
        const backends = {
            'ollama': 'Ollama',
            'minicpm_api': 'MiniCPM API',
            'custom_api': '自定义 API',
        };
        const backendLabel = backends[result.backend] || 'API';

        if (result.available) {
            if (result.model_available) {
                dot.className = 'status-dot online';
                label.textContent = `${backendLabel} · ${result.model}`;
            } else {
                dot.className = 'status-dot offline';
                label.textContent = `${backendLabel} · 模型不可用`;
            }
        } else {
            dot.className = 'status-dot offline';
            label.textContent = `${backendLabel} · 未连接`;
        }
    } catch {
        dot.className = 'status-dot offline';
        label.textContent = '服务未连接';
    }
}

// ================================================================
// 视频选择
// ================================================================
async function selectVideo() {
    if (AppState.isProcessing) {
        Components.showToast('正在处理中，请等待完成', 'warning');
        return;
    }

    const result = await API.selectVideoFile();
    if (result.selected && result.path) {
        await loadVideo(result.path);
    }
}

async function loadVideo(videoPath) {
    AppState.currentVideo = videoPath;
    // 提取文件名
    const parts = videoPath.replace(/\\/g, '/').split('/');
    AppState.videoFileName = parts[parts.length - 1];

    try {
        const meta = await API.getVideoMetadata(videoPath);
        AppState.videoMetadata = meta;
    } catch {
        AppState.videoMetadata = null;
    }

    // 重新渲染当前页面
    const container = document.getElementById('pageContainer');
    navigateTo(AppState.currentPage);
}

// ================================================================
// 首页
// ================================================================
function renderHome(container) {
    const hasVideo = AppState.currentVideo !== null;
    const meta = AppState.videoMetadata;
    const name = AppState.videoFileName;

    let html = '<div class="page-title">LightVideo</div>';
    html += '<div class="page-subtitle">轻量化视频理解工具 — 基于 MiniCPM-V 4.6</div>';

    // 拖拽上传区域
    html += `
        <div class="drop-zone" id="dropZone" onclick="selectVideo()">
            <div class="drop-zone-icon">
                <span class="material-icons">video_file</span>
            </div>
            <div class="drop-zone-text">${hasVideo ? name : '点击选择视频文件'}</div>
            <div class="drop-zone-hint">支持 MP4 / MOV / AVI / MKV 格式</div>
        </div>
    `;

    // 视频信息
    if (hasVideo && meta) {
        html += `
            <div class="card" style="margin-bottom:24px;">
                <div class="section-title">${Components.escapeHtml(name)}</div>
                <div class="video-info">
                    <div class="video-info-item">
                        <div class="video-info-value">${meta.duration_seconds ? Components.formatDuration(meta.duration_seconds) : '--'}</div>
                        <div class="video-info-label">时长</div>
                    </div>
                    <div class="video-info-item">
                        <div class="video-info-value">${meta.width || '--'}×${meta.height || '--'}</div>
                        <div class="video-info-label">分辨率</div>
                    </div>
                    <div class="video-info-item">
                        <div class="video-info-value">${meta.fps || '--'}</div>
                        <div class="video-info-label">帧率 (fps)</div>
                    </div>
                    <div class="video-info-item">
                        <div class="video-info-value">${meta.total_frames || '--'}</div>
                        <div class="video-info-label">总帧数</div>
                    </div>
                </div>
                <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px;">
                    <button class="btn btn-secondary" onclick="navigateTo('summary')">
                        <span class="material-icons">description</span> 生成摘要
                    </button>
                    <button class="btn btn-secondary" onclick="navigateTo('events')">
                        <span class="material-icons">search</span> 检索事件
                    </button>
                    <button class="btn btn-secondary" onclick="navigateTo('scenes')">
                        <span class="material-icons">movie</span> 检测场景
                    </button>
                    <button class="btn btn-danger" onclick="clearVideo()" style="margin-left:auto;">
                        <span class="material-icons">close</span> 移除
                    </button>
                </div>
            </div>
        `;
    } else if (hasVideo && !meta) {
        html += `<div class="card" style="margin-bottom:24px;padding:16px;color:var(--text-secondary);">已选择: ${Components.escapeHtml(name)}（无法读取元数据）</div>`;
    }

    // 功能卡片
    html += '<div class="section-title">功能模块</div>';
    html += '<div class="feature-grid">';
    const features = [
        { icon: 'description', title: '视频摘要', desc: '内容概括与章节划分', page: 'summary' },
        { icon: 'text_snippet', title: '文字提取', desc: '画面文字结构化提取', page: 'text' },
        { icon: 'search', title: '事件检索', desc: '关键事件搜索定位', page: 'events' },
        { icon: 'movie', title: '场景检测', desc: '切换检测与关键帧', page: 'scenes' },
        { icon: 'track_changes', title: '目标追踪', desc: '对象出现时间标记', page: 'track' },
    ];
    for (const f of features) {
        html += `
            <div class="feature-card" onclick="navigateTo('${f.page}')">
                <span class="material-icons">${f.icon}</span>
                <div class="feature-card-title">${f.title}</div>
                <div class="feature-card-desc">${f.desc}</div>
            </div>
        `;
    }
    html += '</div>';

    container.innerHTML = html;
}

function clearVideo() {
    AppState.currentVideo = null;
    AppState.videoMetadata = null;
    AppState.videoFileName = '';
    AppState.summaryResult = null;
    AppState.textResult = null;
    AppState.eventResult = null;
    AppState.sceneResult = null;
    AppState.trackResult = null;
    Components.showToast('已移除视频', 'info');
    navigateTo('home');
}

// ================================================================
// 功能一：视频摘要
// ================================================================
function renderSummaryPage(container) {
    let html = '<div class="page-title">视频摘要</div>';
    html += '<div class="page-subtitle">生成视频内容摘要与章节划分</div>';

    // 视频选择
    html += renderVideoSelector();

    if (AppState.currentVideo) {
        html += `
            <div style="margin-bottom:16px;">
                <button class="btn btn-primary" id="btnSummary" onclick="handleGenerateSummary()">
                    <span class="material-icons">auto_awesome</span> 生成摘要
                </button>
            </div>
        `;
    }

    // 结果区域
    html += '<div id="summaryResult">';
    if (AppState.summaryResult) {
        html += renderSummaryResult(AppState.summaryResult);
    } else if (AppState.currentVideo) {
        html += '<div class="empty-state"><p>点击上方按钮生成视频摘要</p></div>';
    }
    html += '</div>';

    container.innerHTML = html;
}

async function handleGenerateSummary() {
    if (!AppState.currentVideo || AppState.isProcessing) return;

    AppState.isProcessing = true;
    const btn = document.getElementById('btnSummary');
    btn.disabled = true;
    btn.innerHTML = '<span class="material-icons" style="animation:spin 1s linear infinite;">sync</span> 处理中...';

    try {
        const result = await API.generateSummary(AppState.currentVideo);
        if (result.success) {
            AppState.summaryResult = result.data;
            const resultDiv = document.getElementById('summaryResult');
            resultDiv.innerHTML = renderSummaryResult(result.data);
            Components.showToast('摘要生成完成', 'success');
        } else {
            Components.showToast(result.error || '生成失败', 'error');
        }
    } catch (err) {
        Components.showToast(err.message || '请求失败', 'error');
    } finally {
        AppState.isProcessing = false;
        btn.disabled = false;
        btn.innerHTML = '<span class="material-icons">auto_awesome</span> 生成摘要';
    }
}

function renderSummaryResult(data) {
    let html = `<div class="card" style="margin-bottom:16px;">
        <div style="font-size:20px;font-weight:700;margin-bottom:12px;">${Components.escapeHtml(data.title)}</div>
        <div class="summary-text">${Components.escapeHtml(data.summary)}</div>
    </div>`;

    if (data.chapters && data.chapters.length > 0) {
        html += '<div class="section-title">章节划分</div>';
        html += '<div class="chapter-list">';
        for (const ch of data.chapters) {
            html += `
                <div class="chapter-item">
                    <span class="chapter-timestamp">${Components.escapeHtml(ch.timestamp)}</span>
                    <div class="chapter-content">
                        <div class="chapter-title">${Components.escapeHtml(ch.title)}</div>
                        ${ch.description ? `<div class="chapter-desc">${Components.escapeHtml(ch.description)}</div>` : ''}
                    </div>
                </div>
            `;
        }
        html += '</div>';
    }

    return html;
}

// ================================================================
// 功能二：文字提取
// ================================================================
function renderTextPage(container) {
    let html = '<div class="page-title">画面文字提取</div>';
    html += '<div class="page-subtitle">提取视频中的标题、字幕、场景文字与水印</div>';

    html += renderVideoSelector();

    if (AppState.currentVideo) {
        html += `
            <div style="margin-bottom:16px;">
                <button class="btn btn-primary" id="btnText" onclick="handleExtractText()">
                    <span class="material-icons">text_snippet</span> 提取文字
                </button>
            </div>
        `;
    }

    html += '<div id="textResult">';
    if (AppState.textResult) {
        html += renderTextResult(AppState.textResult);
    } else if (AppState.currentVideo) {
        html += '<div class="empty-state"><p>点击上方按钮提取视频文字</p></div>';
    }
    html += '</div>';

    container.innerHTML = html;
}

async function handleExtractText() {
    if (!AppState.currentVideo || AppState.isProcessing) return;

    AppState.isProcessing = true;
    const btn = document.getElementById('btnText');
    btn.disabled = true;
    btn.innerHTML = '<span class="material-icons" style="animation:spin 1s linear infinite;">sync</span> 处理中...';

    try {
        const result = await API.extractText(AppState.currentVideo);
        if (result.success) {
            AppState.textResult = result.data;
            const resultDiv = document.getElementById('textResult');
            resultDiv.innerHTML = renderTextResult(result.data);
            Components.showToast('文字提取完成', 'success');
        } else {
            Components.showToast(result.error || '提取失败', 'error');
        }
    } catch (err) {
        Components.showToast(err.message || '请求失败', 'error');
    } finally {
        AppState.isProcessing = false;
        btn.disabled = false;
        btn.innerHTML = '<span class="material-icons">text_snippet</span> 提取文字';
    }
}

let textActiveTab = 'all';

function renderTextResult(data) {
    const sections = data.sections || [];
    const categories = ['all', 'title', 'subtitle', 'scene_text', 'watermark'];
    const catLabels = { all: '全部', title: '标题', subtitle: '字幕', scene_text: '场景文字', watermark: '水印' };

    // 按分类计数
    const counts = { all: sections.length };
    for (const s of sections) {
        counts[s.category] = (counts[s.category] || 0) + 1;
    }

    let html = '<div class="card">';

    // 分类标签
    html += '<div class="text-tabs">';
    for (const cat of categories) {
        const cnt = counts[cat] || 0;
        const active = cat === textActiveTab ? ' active' : '';
        html += `<button class="text-tab${active}" onclick="switchTextTab('${cat}')">${catLabels[cat]} (${cnt})</button>`;
    }
    html += '</div>';

    // 文字列表
    const filtered = textActiveTab === 'all'
        ? sections
        : sections.filter(s => s.category === textActiveTab);

    if (filtered.length === 0) {
        html += '<div class="empty-state" style="padding:24px;"><p>无文字内容</p></div>';
    } else {
        html += '<div class="text-section-list">';
        for (const s of filtered) {
            html += `
                <div class="text-section-item" onclick="Components.copyToClipboard(${JSON.stringify(s.text)})" title="点击复制">
                    <span class="timestamp">${Components.escapeHtml(s.timestamp)}</span>
                    <span class="category-tag tag-${s.category}">${Components.getCategoryLabel(s.category)}</span>
                    <span class="text-content">${Components.escapeHtml(s.text)}</span>
                </div>
            `;
        }
        html += '</div>';
    }

    // 复制全部
    if (sections.length > 0) {
        html += `
            <div style="margin-top:16px;text-align:right;">
                <button class="btn btn-secondary" onclick="Components.copyToClipboard(${JSON.stringify(data.full_text)})">
                    <span class="material-icons">content_copy</span> 复制全部
                </button>
            </div>
        `;
    }

    html += '</div>';
    return html;
}

function switchTextTab(cat) {
    textActiveTab = cat;
    if (AppState.textResult) {
        const resultDiv = document.getElementById('textResult');
        if (resultDiv) resultDiv.innerHTML = renderTextResult(AppState.textResult);
    }
}

// ================================================================
// 功能三：事件检索
// ================================================================
function renderEventsPage(container) {
    let html = '<div class="page-title">关键事件检索</div>';
    html += '<div class="page-subtitle">在长视频中搜索特定事件或对象出现的时间点</div>';

    html += renderVideoSelector();

    if (AppState.currentVideo) {
        html += `
            <div class="search-bar">
                <input type="text" id="eventQuery" placeholder="输入查询关键词，如：行人、汽车、人物对话..." />
            </div>
            <div class="control-group">
                <div class="control-item">
                    <label>检索灵敏度</label>
                    <div style="display:flex;align-items:center;gap:8px;">
                        <input type="range" id="eventSensitivity" min="0" max="1" step="0.1" value="0.5" oninput="updateSliderValue(this)" />
                        <span class="slider-value" id="eventSensitivityVal">0.5</span>
                    </div>
                </div>
                <button class="btn btn-primary" id="btnEvents" onclick="handleRetrieveEvents()">
                    <span class="material-icons">search</span> 检索
                </button>
            </div>
        `;
    }

    html += '<div id="eventsResult">';
    if (AppState.eventResult) {
        html += renderEventsResult(AppState.eventResult);
    } else if (AppState.currentVideo) {
        html += '<div class="empty-state"><p>输入关键词并点击检索</p></div>';
    }
    html += '</div>';

    container.innerHTML = html;
}

function updateSliderValue(el) {
    const valEl = document.getElementById(el.id + 'Val');
    if (valEl) valEl.textContent = el.value;
}

async function handleRetrieveEvents() {
    if (!AppState.currentVideo || AppState.isProcessing) return;

    const query = document.getElementById('eventQuery').value.trim();
    if (!query) {
        Components.showToast('请输入检索关键词', 'warning');
        return;
    }

    const sensitivity = parseFloat(document.getElementById('eventSensitivity').value);

    AppState.isProcessing = true;
    const btn = document.getElementById('btnEvents');
    btn.disabled = true;
    btn.innerHTML = '<span class="material-icons" style="animation:spin 1s linear infinite;">sync</span> 检索中...';

    try {
        const result = await API.retrieveEvents(AppState.currentVideo, query, sensitivity);
        if (result.success) {
            AppState.eventResult = result.data;
            const resultDiv = document.getElementById('eventsResult');
            resultDiv.innerHTML = renderEventsResult(result.data);
            Components.showToast(`检索完成，共 ${result.data.total_events} 个事件`, 'success');
        } else {
            Components.showToast(result.error || '检索失败', 'error');
        }
    } catch (err) {
        Components.showToast(err.message || '请求失败', 'error');
    } finally {
        AppState.isProcessing = false;
        btn.disabled = false;
        btn.innerHTML = '<span class="material-icons">search</span> 检索';
    }
}

function renderEventsResult(data) {
    const events = data.events || [];
    if (events.length === 0) {
        return '<div class="empty-state"><span class="material-icons">search_off</span><p>未检索到相关事件</p></div>';
    }

    let html = `<div style="margin-bottom:8px;font-size:13px;color:var(--text-secondary);">共 ${data.total_events} 个事件</div>`;
    html += '<div class="event-list">';
    for (const evt of events) {
        const confidenceColor = evt.confidence >= 0.7 ? 'var(--success)' : evt.confidence >= 0.4 ? 'var(--warning)' : 'var(--error)';
        html += `
            <div class="event-item" onclick="showEventDetail(${JSON.stringify(evt).replace(/"/g, '&quot;')})">
                <div class="event-header">
                    <span class="event-timestamp">${Components.escapeHtml(evt.timestamp)}</span>
                    <span class="event-confidence">置信度 ${Math.round(evt.confidence * 100)}%</span>
                </div>
                <div class="event-desc">${Components.escapeHtml(evt.description)}</div>
                <div class="event-meta">
                    <span>类型: ${Components.escapeHtml(evt.event_type)}</span>
                    <span>持续: ${Components.formatDuration(evt.duration_seconds)}</span>
                </div>
                <div class="confidence-bar">
                    <div class="confidence-fill" style="width:${evt.confidence * 100}%;background:${confidenceColor};"></div>
                </div>
            </div>
        `;
    }
    html += '</div>';
    return html;
}

function showEventDetail(evt) {
    const html = `
        <p><strong>时间：</strong>${Components.escapeHtml(evt.timestamp)}</p>
        <p><strong>描述：</strong>${Components.escapeHtml(evt.description)}</p>
        <p><strong>类型：</strong>${Components.escapeHtml(evt.event_type)}</p>
        <p><strong>置信度：</strong>${Math.round(evt.confidence * 100)}%</p>
        <p><strong>持续时长：</strong>${Components.formatDuration(evt.duration_seconds)}</p>
        <p><strong>关键帧索引：</strong>${evt.key_frame_index}</p>
    `;
    Components.showModal('事件详情', html);
}

// ================================================================
// 功能四：场景检测
// ================================================================
function renderScenesPage(container) {
    let html = '<div class="page-title">场景检测</div>';
    html += '<div class="page-subtitle">检测视频场景切换点，生成关键帧描述</div>';

    html += renderVideoSelector();

    if (AppState.currentVideo) {
        html += `
            <div style="margin-bottom:16px;">
                <button class="btn btn-primary" id="btnScenes" onclick="handleDetectScenes()">
                    <span class="material-icons">movie</span> 检测场景
                </button>
            </div>
        `;
    }

    html += '<div id="scenesResult">';
    if (AppState.sceneResult) {
        html += renderScenesResult(AppState.sceneResult);
    } else if (AppState.currentVideo) {
        html += '<div class="empty-state"><p>点击上方按钮检测场景</p></div>';
    }
    html += '</div>';

    container.innerHTML = html;
}

async function handleDetectScenes() {
    if (!AppState.currentVideo || AppState.isProcessing) return;

    AppState.isProcessing = true;
    const btn = document.getElementById('btnScenes');
    btn.disabled = true;
    btn.innerHTML = '<span class="material-icons" style="animation:spin 1s linear infinite;">sync</span> 检测中...';

    try {
        const result = await API.detectScenes(AppState.currentVideo);
        if (result.success) {
            AppState.sceneResult = result.data;
            const resultDiv = document.getElementById('scenesResult');
            resultDiv.innerHTML = renderScenesResult(result.data);
            Components.showToast(`检测完成，共 ${result.data.total_scenes} 个场景`, 'success');
        } else {
            Components.showToast(result.error || '检测失败', 'error');
        }
    } catch (err) {
        Components.showToast(err.message || '请求失败', 'error');
    } finally {
        AppState.isProcessing = false;
        btn.disabled = false;
        btn.innerHTML = '<span class="material-icons">movie</span> 检测场景';
    }
}

function renderScenesResult(data) {
    const scenes = data.scenes || [];
    if (scenes.length === 0) {
        return '<div class="empty-state"><span class="material-icons">broken_image</span><p>未检测到场景切换</p></div>';
    }

    let html = `<div style="margin-bottom:12px;font-size:13px;color:var(--text-secondary);">共 ${data.total_scenes} 个场景</div>`;
    html += '<div class="scene-gallery">';
    for (const scene of scenes) {
        const thumbSrc = scene.thumbnail
            ? `data:image/jpeg;base64,${scene.thumbnail}`
            : '';
        html += `
            <div class="scene-item" onclick="showSceneDetail(${JSON.stringify(scene).replace(/"/g, '&quot;')})">
                ${thumbSrc ? `<img class="scene-thumb" src="${thumbSrc}" alt="场景缩略图" />` : '<div class="scene-thumb" style="display:flex;align-items:center;justify-content:center;color:var(--text-secondary);"><span class="material-icons" style="font-size:36px;">image</span></div>'}
                <div class="scene-info">
                    <div class="scene-timestamps">${Components.escapeHtml(scene.start_timestamp)} → ${Components.escapeHtml(scene.end_timestamp)}</div>
                    <div class="scene-desc">${Components.escapeHtml(scene.description || '无描述')}</div>
                </div>
            </div>
        `;
    }
    html += '</div>';
    return html;
}

function showSceneDetail(scene) {
    const thumbSrc = scene.thumbnail
        ? `<img src="data:image/jpeg;base64,${scene.thumbnail}" style="max-width:100%;max-height:400px;border-radius:8px;margin-bottom:12px;" />`
        : '';
    const html = `
        ${thumbSrc}
        <p><strong>开始：</strong>${Components.escapeHtml(scene.start_timestamp)}</p>
        <p><strong>结束：</strong>${Components.escapeHtml(scene.end_timestamp)}</p>
        <p><strong>时长：</strong>${Components.formatDuration(scene.duration_seconds)}</p>
        <p><strong>描述：</strong>${Components.escapeHtml(scene.description || '无')}</p>
        <p><strong>关键帧索引：</strong>${scene.frame_index}</p>
    `;
    Components.showModal('场景详情', html);
}

// ================================================================
// 功能五：目标追踪
// ================================================================
function renderTrackPage(container) {
    let html = '<div class="page-title">目标追踪</div>';
    html += '<div class="page-subtitle">标记目标对象在视频中出现的时间段</div>';

    html += renderVideoSelector();

    if (AppState.currentVideo) {
        html += `
            <div class="search-bar">
                <input type="text" id="trackTarget" placeholder="输入目标描述，如：红色的汽车、戴帽子的人..." />
                <button class="btn btn-primary" id="btnTrack" onclick="handleTrackObject()">
                    <span class="material-icons">track_changes</span> 追踪
                </button>
            </div>
        `;
    }

    html += '<div id="trackResult">';
    if (AppState.trackResult) {
        html += renderTrackResult(AppState.trackResult);
    } else if (AppState.currentVideo) {
        html += '<div class="empty-state"><p>输入目标描述并点击追踪</p></div>';
    }
    html += '</div>';

    container.innerHTML = html;
}

async function handleTrackObject() {
    if (!AppState.currentVideo || AppState.isProcessing) return;

    const target = document.getElementById('trackTarget').value.trim();
    if (!target) {
        Components.showToast('请输入目标描述', 'warning');
        return;
    }

    AppState.isProcessing = true;
    const btn = document.getElementById('btnTrack');
    btn.disabled = true;
    btn.innerHTML = '<span class="material-icons" style="animation:spin 1s linear infinite;">sync</span> 追踪中...';

    try {
        const result = await API.trackObject(AppState.currentVideo, target);
        if (result.success) {
            AppState.trackResult = result.data;
            const resultDiv = document.getElementById('trackResult');
            resultDiv.innerHTML = renderTrackResult(result.data);
            Components.showToast(`追踪完成，共 ${result.data.total_appearances} 个出现时段`, 'success');
        } else {
            Components.showToast(result.error || '追踪失败', 'error');
        }
    } catch (err) {
        Components.showToast(err.message || '请求失败', 'error');
    } finally {
        AppState.isProcessing = false;
        btn.disabled = false;
        btn.innerHTML = '<span class="material-icons">track_changes</span> 追踪';
    }
}

function renderTrackResult(data) {
    const appearances = data.appearances || [];
    if (appearances.length === 0) {
        return '<div class="empty-state"><span class="material-icons">visibility_off</span><p>未检测到目标出现</p></div>';
    }

    let html = `<div style="margin-bottom:12px;font-size:13px;color:var(--text-secondary);">共 ${data.total_appearances} 个出现时段</div>`;
    html += '<div class="appearance-list">';
    for (const app of appearances) {
        const framesStr = (app.frames_with_object || []).join(', ');
        html += `
            <div class="appearance-item">
                <div class="appearance-range">
                    <span class="appearance-time">${Components.escapeHtml(app.start_timestamp)}</span>
                    <span class="material-icons">arrow_forward</span>
                    <span class="appearance-time">${Components.escapeHtml(app.end_timestamp)}</span>
                </div>
                <div class="appearance-desc">${Components.escapeHtml(app.description)}</div>
                ${framesStr ? `<div class="appearance-frames">${framesStr.split(', ').map(f => `<span class="frame-chip">帧 ${f}</span>`).join('')}</div>` : ''}
            </div>
        `;
    }
    html += '</div>';
    return html;
}

// ================================================================
// 通用：带超时的异步调用
// ================================================================
async function timeoutFetch(promise, ms) {
    let timer;
    const timeout = new Promise((_, reject) => {
        timer = setTimeout(() => reject(new Error('请求超时')), ms);
    });
    return Promise.race([promise, timeout]).finally(() => clearTimeout(timer));
}

// ================================================================
// 设置页面（支持 Ollama / MiniCPM API / 自定义 API）
// ================================================================
function renderSettingsPage(container) {
    container.innerHTML = `
        <div class="page-title">设置</div>
        <div class="page-subtitle">配置后端模型服务与生成参数</div>

        <div class="card settings-card">
            <div class="section-title">后端模式</div>
            <div class="settings-group">
                <div class="settings-item">
                    <label>模型服务</label>
                    <div class="backend-selector">
                        <label class="backend-option" id="optOllama" onclick="onBackendOptionClick(this)">
                            <input type="radio" name="apiBackend" value="ollama" onchange="onBackendChange()" />
                            <div class="backend-option-text">
                                <span class="backend-label">Ollama（本地）</span>
                                <span class="backend-desc">通过本地 Ollama 调用模型</span>
                            </div>
                        </label>
                        <label class="backend-option" id="optMinicpm" onclick="onBackendOptionClick(this)">
                            <input type="radio" name="apiBackend" value="minicpm_api" onchange="onBackendChange()" />
                            <div class="backend-option-text">
                                <span class="backend-label">MiniCPM 官方 API</span>
                                <span class="backend-desc">使用 MiniCPM 免费在线 API（自动填充配置）</span>
                            </div>
                        </label>
                        <label class="backend-option" id="optCustom" onclick="onBackendOptionClick(this)">
                            <input type="radio" name="apiBackend" value="custom_api" onchange="onBackendChange()" />
                            <div class="backend-option-text">
                                <span class="backend-label">自定义 API</span>
                                <span class="backend-desc">自定义 OpenAI 兼容 API 服务</span>
                            </div>
                        </label>
                    </div>
                </div>
            </div>
        </div>

        <!-- Ollama 设置区 -->
        <div class="card settings-card" id="ollamaSettings">
            <div class="section-title">Ollama 服务</div>
            <div class="settings-group">
                <div class="settings-item">
                    <label>服务地址</label>
                    <input type="text" id="cfgOllamaUrl" placeholder="http://localhost:11434" />
                    <span class="settings-hint">Ollama 服务的 HTTP 地址，默认 http://localhost:11434</span>
                </div>
                <div class="settings-item">
                    <label>模型名称</label>
                    <input type="text" id="cfgModelName" placeholder="minicpm-v4.6" />
                    <span class="settings-hint">使用的多模态视觉模型，如 minicpm-v4.6、llava:7b</span>
                </div>
                <div class="settings-item">
                    <label>请求超时（秒）</label>
                    <input type="number" id="cfgTimeout" min="10" max="600" />
                    <span class="settings-hint">单次 Ollama 请求的超时时间，视频较长时可适当增大</span>
                </div>
            </div>
            <div style="display:flex;gap:12px;margin-top:8px;">
                <button class="btn btn-secondary" id="btnTestConnection" onclick="handleTestConnection()">
                    <span class="material-icons">wifi_find</span> 测试连接
                </button>
                <div id="connectionResult" style="display:none;align-self:center;font-size:13px;"></div>
            </div>
        </div>

        <!-- API 设置区 -->
        <div class="card settings-card" id="apiSettings" style="display:none;">
            <div class="section-title">API 配置</div>
            <div class="settings-group">
                <div class="settings-item">
                    <label>API 地址</label>
                    <input type="text" id="cfgApiBaseUrl" placeholder="https://api.modelbest.cn/v1" />
                    <span class="settings-hint">OpenAI 兼容 API 的基础地址，末尾不加 /chat/completions</span>
                </div>
                <div class="settings-item">
                    <label>API Key</label>
                    <input type="password" id="cfgApiKey" placeholder="sk-..." />
                    <span class="settings-hint">API 认证密钥。MiniCPM 官方 API 有免费测试 Key 可用</span>
                </div>
                <div class="settings-item">
                    <label>模型名称</label>
                    <input type="text" id="cfgApiModelName" placeholder="MiniCPM-V-4.6-Instruct" />
                    <span class="settings-hint">使用的模型 ID，如 MiniCPM-V-4.6-Instruct、MiniCPM-o-4.5</span>
                </div>
                <div class="settings-item" id="minicpmModelHint" style="display:none;">
                    <span class="settings-hint" style="color:var(--accent);">
                        💡 MiniCPM 可用模型：MiniCPM-V-4.6-Instruct、MiniCPM-V-4.6-Thinking、MiniCPM-o-4.5
                    </span>
                </div>
            </div>
            <div style="display:flex;gap:12px;margin-top:8px;">
                <button class="btn btn-secondary" id="btnTestApiConnection" onclick="handleTestApiConnection()">
                    <span class="material-icons">wifi_find</span> 测试 API 连接
                </button>
                <div id="apiConnectionResult" style="display:none;align-self:center;font-size:13px;"></div>
            </div>
        </div>

        <div class="card settings-card">
            <div class="section-title">模型参数</div>
            <div class="settings-group">
                <div class="settings-item">
                    <label>生成温度 (Temperature)</label>
                    <div style="display:flex;align-items:center;gap:8px;">
                        <input type="range" id="cfgTemperature" min="0" max="1" step="0.05" value="0.1" oninput="updateSliderValue(this)" />
                        <span class="slider-value" id="cfgTemperatureVal">0.1</span>
                    </div>
                    <span class="settings-hint">值越低回答越确定，值越高越有创造力。推荐 0.1~0.3</span>
                </div>
                <div class="settings-item">
                    <label>最大采样帧数</label>
                    <input type="number" id="cfgMaxFrames" min="1" max="128" />
                    <span class="settings-hint">分析视频时最多抽取的帧数，数值越大结果越精确但耗时更长</span>
                </div>
                <div class="settings-item">
                    <label>上下文窗口大小（tokens）</label>
                    <input type="number" id="cfgContextSize" min="2048" max="131072" step="1024" />
                    <span class="settings-hint">模型的 context length，自动据此控制发送帧数防超限。如 MiniCPM-V 4.6 为 4096、MiniCPM-o 4.5 为 16384</span>
                </div>
                <div class="settings-item">
                    <label>每帧估算 Token</label>
                    <input type="number" id="cfgTokensPerFrame" min="100" max="5000" step="50" />
                    <span class="settings-hint">每帧消耗的 token 估算值（含 base64 + 描述）。值越小允许发送越多帧，但可能导致上下文溢出</span>
                </div>
            </div>
        </div>

        <div style="display:flex;gap:12px;margin-top:24px;">
            <button class="btn btn-primary" id="btnSaveConfig" onclick="handleSaveConfig()">
                <span class="material-icons">save</span> 保存设置
            </button>
            <button class="btn btn-secondary" onclick="handleResetConfig()">
                <span class="material-icons">restart_alt</span> 恢复默认
            </button>
        </div>
    `;

    // 加载当前配置
    loadConfigToForm();
}

function onBackendOptionClick(el) {
    const radio = el.querySelector('input[type="radio"]');
    if (radio) radio.checked = true;
    onBackendChange();
}

function onBackendChange() {
    // 更新选中高亮
    document.querySelectorAll('.backend-option').forEach(opt => {
        const radio = opt.querySelector('input[type="radio"]');
        opt.classList.toggle('checked', radio && radio.checked);
    });

    const backend = document.querySelector('input[name="apiBackend"]:checked')?.value;
    document.getElementById('ollamaSettings').style.display = backend === 'ollama' ? '' : 'none';
    document.getElementById('apiSettings').style.display = backend !== 'ollama' ? '' : 'none';
    document.getElementById('minicpmModelHint').style.display = backend === 'minicpm_api' ? '' : 'none';

    // MiniCPM API 模式：自动填充
    if (backend === 'minicpm_api') {
        const keyInput = document.getElementById('cfgApiKey');
        if (!keyInput.value) {
            keyInput.value = 'sk-pQ8L2zF3XmR5kY9wV4jB7hN1tC6vM0xG3aD5sH2bJ9lK4cZ8';
        }
        const urlInput = document.getElementById('cfgApiBaseUrl');
        if (!urlInput.value) {
            urlInput.value = 'https://api.modelbest.cn/v1';
        }
    }
}

async function loadConfigToForm() {
    try {
        const cfg = await API.getConfig();

        // 后端模式
        const backendRadio = document.querySelector(`input[name="apiBackend"][value="${cfg.api_backend || 'ollama'}"]`);
        if (backendRadio) backendRadio.checked = true;
        onBackendChange();

        // Ollama 字段
        document.getElementById('cfgOllamaUrl').value = cfg.ollama_url || 'http://localhost:11434';
        document.getElementById('cfgModelName').value = cfg.model_name || 'minicpm-v4.6';
        document.getElementById('cfgTimeout').value = cfg.ollama_timeout || 120;

        // API 字段
        document.getElementById('cfgApiBaseUrl').value = cfg.api_base_url || 'https://api.modelbest.cn/v1';
        document.getElementById('cfgApiKey').value = cfg.api_key || '';
        document.getElementById('cfgApiModelName').value = cfg.api_model_name || 'MiniCPM-V-4.6-Instruct';

        // 模型参数
        const tempInput = document.getElementById('cfgTemperature');
        tempInput.value = cfg.temperature ?? 0.1;
        document.getElementById('cfgTemperatureVal').textContent = cfg.temperature ?? 0.1;

        document.getElementById('cfgMaxFrames').value = cfg.max_num_frames || 12;
        document.getElementById('cfgContextSize').value = cfg.context_size || 8192;
        document.getElementById('cfgTokensPerFrame').value = cfg.tokens_per_frame || 600;
    } catch (err) {
        Components.showToast('加载配置失败: ' + err.message, 'error');
    }
}

function getConfigFromForm() {
    return {
        API_BACKEND: document.querySelector('input[name="apiBackend"]:checked')?.value || 'ollama',
        OLLAMA_URL: document.getElementById('cfgOllamaUrl').value.trim(),
        MODEL_NAME: document.getElementById('cfgModelName').value.trim(),
        OLLAMA_TIMEOUT: parseInt(document.getElementById('cfgTimeout').value) || 120,
        API_BASE_URL: document.getElementById('cfgApiBaseUrl').value.trim(),
        API_KEY: document.getElementById('cfgApiKey').value.trim(),
        API_MODEL_NAME: document.getElementById('cfgApiModelName').value.trim(),
        TEMPERATURE: parseFloat(document.getElementById('cfgTemperature').value) || 0.1,
        MAX_NUM_FRAMES: parseInt(document.getElementById('cfgMaxFrames').value) || 12,
        CONTEXT_SIZE: parseInt(document.getElementById('cfgContextSize').value) || 8192,
        TOKENS_PER_FRAME: parseInt(document.getElementById('cfgTokensPerFrame').value) || 600,
    };
}

async function handleTestConnection() {
    const backend = document.querySelector('input[name="apiBackend"]:checked')?.value;

    if (backend === 'ollama') {
        await handleTestOllamaConnection();
    } else {
        await handleTestApiConnection();
    }
}

async function handleTestOllamaConnection() {
    const btn = document.getElementById('btnTestConnection');
    const resultEl = document.getElementById('connectionResult');

    btn.disabled = true;
    btn.innerHTML = '<span class="material-icons" style="animation:spin 1s linear infinite;">sync</span> 连接中...';
    resultEl.style.display = 'none';

    const cfg = getConfigFromForm();
    await API.saveConfig(cfg);

    try {
        const res = await timeoutFetch(API.checkOllama(), 8000);
        resultEl.style.display = 'flex';
        if (res.available && res.model_available) {
            resultEl.innerHTML = `<span class="material-icons" style="color:var(--success);font-size:18px;">check_circle</span> 连接成功 — ${res.model} 已就绪`;
            resultEl.style.color = 'var(--success)';
        } else if (res.available && !res.model_available) {
            resultEl.innerHTML = `<span class="material-icons" style="color:var(--warning);font-size:18px;">warning</span> Ollama 已连接，但模型 <strong>${res.model}</strong> 不可用`;
            resultEl.style.color = 'var(--warning)';
        } else {
            resultEl.innerHTML = `<span class="material-icons" style="color:var(--error);font-size:18px;">error</span> 连接失败，请检查 Ollama 是否已启动`;
            resultEl.style.color = 'var(--error)';
        }
    } catch {
        resultEl.style.display = 'flex';
        resultEl.innerHTML = `<span class="material-icons" style="color:var(--error);font-size:18px;">error</span> 连接失败，请检查 Ollama 是否已启动`;
        resultEl.style.color = 'var(--error)';
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span class="material-icons">wifi_find</span> 测试连接';
    }

    checkOllamaStatus();
}

async function handleTestApiConnection() {
    const btn = document.getElementById('btnTestApiConnection');
    const resultEl = document.getElementById('apiConnectionResult');

    if (!btn) return;

    btn.disabled = true;
    btn.innerHTML = '<span class="material-icons" style="animation:spin 1s linear infinite;">sync</span> 连接中...';
    resultEl.style.display = 'none';

    const cfg = getConfigFromForm();
    await API.saveConfig(cfg);

    try {
        const res = await timeoutFetch(API.checkOllama(), 10000);
        resultEl.style.display = 'flex';
        if (res.available) {
            resultEl.innerHTML = `<span class="material-icons" style="color:var(--success);font-size:18px;">check_circle</span> API 连接成功 — ${res.model}`;
            resultEl.style.color = 'var(--success)';
        } else {
            resultEl.innerHTML = `<span class="material-icons" style="color:var(--error);font-size:18px;">error</span> API 连接失败，请检查地址和密钥`;
            resultEl.style.color = 'var(--error)';
        }
    } catch {
        resultEl.style.display = 'flex';
        resultEl.innerHTML = `<span class="material-icons" style="color:var(--error);font-size:18px;">error</span> API 连接失败（请求超时），请检查地址和密钥是否正确`;
        resultEl.style.color = 'var(--error)';
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span class="material-icons">wifi_find</span> 测试 API 连接';
    }

    checkOllamaStatus();
}

async function handleSaveConfig() {
    const cfg = getConfigFromForm();

    if (cfg.API_BACKEND === 'ollama') {
        if (!cfg.OLLAMA_URL) {
            Components.showToast('请填写 Ollama 服务地址', 'warning');
            return;
        }
        if (!cfg.MODEL_NAME) {
            Components.showToast('请填写模型名称', 'warning');
            return;
        }
    } else {
        if (!cfg.API_BASE_URL) {
            Components.showToast('请填写 API 地址', 'warning');
            return;
        }
        if (!cfg.API_MODEL_NAME) {
            Components.showToast('请填写模型名称', 'warning');
            return;
        }
    }

    try {
        const result = await API.saveConfig(cfg);
        if (result.success) {
            Components.showToast('设置已保存', 'success');
            checkOllamaStatus();
        } else {
            Components.showToast(result.error || '保存失败', 'error');
        }
    } catch (err) {
        Components.showToast(err.message || '保存失败', 'error');
    }
}

async function handleResetConfig() {
    const defaults = {
        API_BACKEND: 'ollama',
        OLLAMA_URL: 'http://localhost:11434',
        MODEL_NAME: 'minicpm-v4.6',
        OLLAMA_TIMEOUT: 120,
        API_BASE_URL: 'https://api.modelbest.cn/v1',
        API_KEY: 'sk-pQ8L2zF3XmR5kY9wV4jB7hN1tC6vM0xG3aD5sH2bJ9lK4cZ8',
        API_MODEL_NAME: 'MiniCPM-V-4.6-Instruct',
        TEMPERATURE: 0.1,
        MAX_NUM_FRAMES: 12,
        CONTEXT_SIZE: 8192,
        TOKENS_PER_FRAME: 600,
    };

    try {
        const result = await API.saveConfig(defaults);
        if (result.success) {
            await loadConfigToForm();
            Components.showToast('已恢复默认设置', 'info');
            checkOllamaStatus();
        } else {
            Components.showToast(result.error || '恢复失败', 'error');
        }
    } catch (err) {
        Components.showToast(err.message || '恢复失败', 'error');
    }
}

// ================================================================
// 关于页面
// ================================================================
function renderAboutPage(container) {
    container.innerHTML = `
        <div class="page-title">关于 LightVideo</div>
        <div class="page-subtitle">轻量化视频理解工具</div>

        <div class="card" style="max-width:600px;">
            <div style="text-align:center;margin-bottom:20px;">
                <div style="width:64px;height:64px;background:var(--accent);border-radius:16px;display:flex;align-items:center;justify-content:center;margin:0 auto 12px;">
                    <span class="material-icons" style="font-size:36px;color:#FFFFFF;">smart_display</span>
                </div>
                <div style="font-size:20px;font-weight:700;">LightVideo</div>
                <div style="font-size:12px;color:var(--text-secondary);">v0.1.0</div>
            </div>

            <div style="font-size:14px;line-height:1.8;color:var(--text-secondary);">
                <p>基于 <strong>MiniCPM-V 4.6</strong> 的轻量化视频理解桌面工具。</p>
                <p>支持五大核心功能：</p>
                <ul style="padding-left:20px;margin:8px 0;">
                    <li>视频内容摘要与章节划分</li>
                    <li>画面文字提取与结构化解析</li>
                    <li>长时监控视频关键事件检索</li>
                    <li>场景切换检测与关键帧描述</li>
                    <li>目标对象出现时间点标记</li>
                </ul>
                <p style="margin-top:12px;">技术栈：Python 3.10+ · pywebview · Ollama · MiniCPM-V 4.6</p>
            </div>

            <div style="margin-top:20px;padding:12px;background:var(--bg-card);border-radius:var(--radius-sm);">
                <div style="font-size:12px;color:var(--text-secondary);">Ollama 状态：</div>
                <div id="aboutOllamaStatus" style="font-size:13px;margin-top:4px;">检测中...</div>
            </div>
        </div>
    `;

    // 检测状态
    API.checkOllama().then(r => {
        const el = document.getElementById('aboutOllamaStatus');
        if (el) {
            if (r.available && r.model_available) {
                el.textContent = `已连接 (${r.model})`;
                el.style.color = 'var(--success)';
            } else if (r.available && !r.model_available) {
                el.textContent = `Ollama 已连接，但模型 ${r.model} 未拉取`;
                el.style.color = 'var(--warning)';
            } else {
                el.textContent = '未连接';
                el.style.color = 'var(--error)';
            }
        }
    });
}

// ================================================================
// 通用：视频选择器组件
// ================================================================
function renderVideoSelector() {
    if (!AppState.currentVideo) {
        return `
            <div style="margin-bottom:20px;">
                <button class="btn btn-primary" onclick="selectVideo()">
                    <span class="material-icons">folder_open</span> 选择视频文件
                </button>
            </div>
        `;
    }

    const meta = AppState.videoMetadata;
    let info = '';
    if (meta) {
        info = `${Components.formatDuration(meta.duration_seconds)} · ${meta.width}×${meta.height} · ${meta.fps}fps`;
    } else {
        info = '无法读取元数据';
    }

    return `
        <div class="card" style="margin-bottom:20px;padding:14px 20px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
            <div style="display:flex;align-items:center;gap:10px;">
                <span class="material-icons" style="color:var(--accent);">check_circle</span>
                <div>
                    <div style="font-weight:600;font-size:14px;">${Components.escapeHtml(AppState.videoFileName)}</div>
                    <div style="font-size:11px;color:var(--text-secondary);">${info}</div>
                </div>
            </div>
            <div style="display:flex;gap:8px;">
                <button class="btn btn-secondary" onclick="selectVideo()" style="padding:6px 14px;font-size:12px;">更换</button>
            </div>
        </div>
    `;
}

// ================================================================
// 初始化
// ================================================================
document.addEventListener('DOMContentLoaded', () => {
    // 渲染首页
    navigateTo('home');

    // 添加 spin 动画
    const style = document.createElement('style');
    style.textContent = `@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`;
    document.head.appendChild(style);
});

// pywebview 就绪后自动检测 Ollama 连接与模型状态
window.addEventListener('pywebviewready', () => {
    checkOllamaStatus();
});
