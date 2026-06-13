/**
 * LightVideo API 通信封装
 * 所有后端接口通过 window.pywebview.api 调用
 */
const API = (() => {
    // 判断是否在 pywebview 环境中
    const isPyWebView = () => {
        return typeof window.pywebview !== 'undefined' && window.pywebview.api;
    };

    // 获取 api 对象
    const _api = () => window.pywebview.api;

    // 通用调用包装：将 JSON 字符串结果解析为对象
    const _call = async (method, ...args) => {
        if (!isPyWebView()) {
            console.warn(`[API] pywebview 未就绪，模拟调用: ${method}`);
            return { success: false, error: 'pywebview 未就绪' };
        }
        try {
            const result = await _api()[method](...args);
            // 字符串响应需要 JSON.parse
            if (typeof result === 'string') {
                return JSON.parse(result);
            }
            return result;
        } catch (err) {
            console.error(`[API] ${method} 调用失败:`, err);
            return { success: false, error: err.message || '调用失败' };
        }
    };

    return {
        // ---- 基础 ----
        checkOllama: async () => {
            if (!isPyWebView()) return { available: false, model: 'minicpm-v4.6' };
            return _api().check_ollama();
        },

        getVideoMetadata: async (videoPath) => {
            if (!isPyWebView()) return {};
            return _api().get_video_metadata(videoPath);
        },

        selectVideoFile: async () => {
            if (!isPyWebView()) return { selected: false, path: '' };
            return _api().select_video_file();
        },

        // ---- 配置 ----
        getConfig: async () => {
            if (!isPyWebView()) return {
                ollama_url: 'http://localhost:11434',
                model_name: 'minicpm-v4.6',
                ollama_timeout: 120,
                temperature: 0.1,
                max_num_frames: 32,
                context_size: 8192,
            };
            return _api().get_config();
        },

        saveConfig: async (config) => {
            return _call('save_config', JSON.stringify(config));
        },

        // ---- 功能一：视频摘要 ----
        generateSummary: async (videoPath) => {
            return _call('generate_summary', videoPath);
        },

        // ---- 功能二：文字提取 ----
        extractText: async (videoPath) => {
            return _call('extract_text', videoPath);
        },

        // ---- 功能三：事件检索 ----
        retrieveEvents: async (videoPath, query, sensitivity = 0.5) => {
            return _call('retrieve_events', videoPath, query, sensitivity);
        },

        // ---- 功能四：场景检测 ----
        detectScenes: async (videoPath) => {
            return _call('detect_scenes', videoPath);
        },

        // ---- 功能五：目标追踪 ----
        trackObject: async (videoPath, target) => {
            return _call('track_object', videoPath, target);
        },

        isReady: isPyWebView,
    };
})();
