/**
 * LightVideo UI 组件库
 * Toast、Modal、进度条等
 */
const Components = (() => {
    // ---- Toast ----
    let toastId = 0;

    function showToast(message, type = 'info', duration = 3000) {
        const container = document.getElementById('toastContainer');
        if (!container) return;

        const id = ++toastId;
        const el = document.createElement('div');
        el.className = `toast toast-${type}`;
        el.id = `toast-${id}`;
        el.textContent = message;

        container.appendChild(el);

        setTimeout(() => {
            el.classList.add('toast-out');
            setTimeout(() => {
                if (el.parentNode) el.parentNode.removeChild(el);
            }, 300);
        }, duration);
    }

    // ---- Modal ----
    function showModal(title, bodyHTML) {
        document.getElementById('modalTitle').textContent = title;
        document.getElementById('modalBody').innerHTML = bodyHTML;
        document.getElementById('modalOverlay').style.display = 'flex';
    }

    function closeModal() {
        document.getElementById('modalOverlay').style.display = 'none';
    }

    // ---- Frame Preview Modal ----
    function showFrameModal(contentHTML) {
        document.getElementById('frameModalBody').innerHTML = contentHTML;
        document.getElementById('frameModal').style.display = 'flex';
    }

    function closeFrameModal() {
        document.getElementById('frameModal').style.display = 'none';
    }

    // ---- Progress ----
    function showProgress(stage, progress, message) {
        const statusBar = document.getElementById('statusBar');
        const fill = document.getElementById('progressFill');
        const msg = document.getElementById('statusMessage');

        statusBar.style.display = 'block';
        fill.style.width = `${Math.round(progress * 100)}%`;
        msg.textContent = message;

        if (stage === 'done') {
            setTimeout(() => {
                statusBar.style.display = 'none';
                fill.style.width = '0%';
            }, 1500);
        }
    }

    // ---- Copy to Clipboard ----
    function copyToClipboard(text) {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).then(() => {
                showCopiedToast();
            }).catch(() => {
                fallbackCopy(text);
            });
        } else {
            fallbackCopy(text);
        }
    }

    function fallbackCopy(text) {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        showCopiedToast();
    }

    function showCopiedToast() {
        const el = document.createElement('div');
        el.className = 'copied-toast';
        el.textContent = '已复制';
        document.body.appendChild(el);
        setTimeout(() => {
            if (el.parentNode) el.parentNode.removeChild(el);
        }, 1500);
    }

    // ---- Format Helpers ----
    function formatDuration(seconds) {
        if (!seconds || seconds <= 0) return '0s';
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = Math.floor(seconds % 60);
        let parts = [];
        if (h > 0) parts.push(`${h}h`);
        if (m > 0) parts.push(`${m}m`);
        parts.push(`${s}s`);
        return parts.join(' ');
    }

    function formatFileSize(bytes) {
        if (!bytes || bytes <= 0) return '未知';
        const units = ['B', 'KB', 'MB', 'GB'];
        let i = 0;
        let size = bytes;
        while (size >= 1024 && i < units.length - 1) {
            size /= 1024;
            i++;
        }
        return `${size.toFixed(1)} ${units[i]}`;
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function getCategoryLabel(cat) {
        const map = {
            'title': '标题',
            'subtitle': '字幕',
            'scene_text': '场景文字',
            'watermark': '水印',
        };
        return map[cat] || cat;
    }

    return {
        showToast,
        showModal,
        closeModal,
        showFrameModal,
        closeFrameModal,
        showProgress,
        copyToClipboard,
        formatDuration,
        formatFileSize,
        escapeHtml,
        getCategoryLabel,
    };
})();

// 全局关闭函数
function closeModal() { Components.closeModal(); }
function closeFrameModal() { Components.closeFrameModal(); }
