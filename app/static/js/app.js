/**
 * DispatchingSystem 前端统一管理
 * ================================
 * 所有 API 请求通过这里的封装方法发起，统一携带 Authorization Header。
 * Token 存储在 localStorage，不使用 Cookie。
 * 内置自定义模态框，替代 alert/confirm。
 */
(function () {
    'use strict';

    var TOKEN_KEY = 'token';
    var PUBLIC_PAGES = ['/login', '/register'];

    // ========== Token 管理 ==========
    window.App = {

        getToken: function () { return localStorage.getItem(TOKEN_KEY); },
        setToken: function (t) { localStorage.setItem(TOKEN_KEY, t); },
        removeToken: function () { localStorage.removeItem(TOKEN_KEY); },
        isLoggedIn: function () { return !!localStorage.getItem(TOKEN_KEY); },
        logout: function () { localStorage.removeItem(TOKEN_KEY); window.location.href = '/login'; },

        // ========== 鉴权请求头 ==========
        _authHeaders: function () {
            var token = App.getToken();
            return token ? { 'Authorization': 'Bearer ' + token } : {};
        },

        // ========== fetch 封装 ==========
        get: function (url) { return fetch(url, { headers: App._authHeaders() }).then(App._handle); },
        post: function (url, data) {
            var h = App._authHeaders(); h['Content-Type'] = 'application/json';
            return fetch(url, { method: 'POST', headers: h, body: JSON.stringify(data) }).then(App._handle);
        },
        postForm: function (url, fd) {
            return fetch(url, { method: 'POST', headers: App._authHeaders(), body: fd }).then(App._handle);
        },
        put: function (url, data) {
            var h = App._authHeaders(); h['Content-Type'] = 'application/json';
            return fetch(url, { method: 'PUT', headers: h, body: JSON.stringify(data) }).then(App._handle);
        },
        del: function (url) {
            return fetch(url, { method: 'DELETE', headers: App._authHeaders() }).then(App._handle);
        },

        // ========== 统一响应处理 ==========
        _handle: function (resp) {
            if (resp.status === 401) { App.removeToken(); window.location.href = '/login'; throw new Error('未登录'); }
            return resp.json();
        },

        // ========== 文件上传 ==========
        upload: function (file, callback) {
            var fd = new FormData();
            fd.append('file', file);
            return fetch('/api/v1/files/upload', {
                method: 'POST',
                headers: App._authHeaders(),
                body: fd
            }).then(App._handle).then(function (data) {
                if (data.code === 0 && callback) callback(data.data.file_path);
                return data;
            });
        },

        // ========== 页面导航（仅替换 body 内容） ==========
        navigate: function (url) {
            return fetch(url, { headers: App._authHeaders() })
                .then(function (resp) {
                    if (resp.status === 401 || resp.status === 302) {
                        App.removeToken();
                        window.location.href = '/login';
                        return;
                    }
                    return resp.text();
                })
                .then(function (html) {
                    if (!html) return;
                    var parser = new DOMParser();
                    var doc = parser.parseFromString(html, 'text/html');
                    document.title = doc.title;
                    // 替换 body 内容
                    var newBody = doc.body;
                    document.body.innerHTML = newBody.innerHTML;
                    // 手动执行新内容中的 script 标签
                    var scripts = document.body.querySelectorAll('script');
                    scripts.forEach(function (s) {
                        // 跳过已在 head 中加载的 CDN 脚本，避免重复加载警告
                        if (s.src && (s.src.includes('tailwindcss') || s.src.includes('alpinejs'))) return;
                        var ns = document.createElement('script');
                        if (s.src) { ns.src = s.src; }
                        else { ns.textContent = s.textContent; }
                        document.body.appendChild(ns);
                    });
                    history.pushState({}, '', url);
                    // 重新绑定全局点击拦截
                    window.__PAGE_RENDERED = true;
                });
        },

        // ========== 自定义模态框（替代 alert / confirm） ==========
        modal: {
            _el: null,

            /** 确保 DOM 中有模态框容器 */
            _ensure: function () {
                if (document.getElementById('app-modal')) return;
                var div = document.createElement('div');
                div.id = 'app-modal';
                div.innerHTML =
                    '<div class="modal-overlay" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:9999;overflow-y:auto;padding:40px 0">' +
                    '<div class="modal-box" style="background:#fff;border-radius:12px;padding:24px;width:90vw;max-width:420px;margin:0 auto;box-shadow:0 20px 60px rgba(0,0,0,0.3);max-height:85vh;overflow-y:auto;position:relative">' +
                    '<div class="modal-title" style="font-size:18px;font-weight:700;margin-bottom:16px;position:sticky;top:0;background:#fff;z-index:1;padding-bottom:8px"></div>' +
                    '<div class="modal-body" style="font-size:14px;color:#4b5563;margin-bottom:20px"></div>' +
                    '<div class="modal-footer" style="display:flex;justify-content:flex-end;gap:8px;position:sticky;bottom:0;background:#fff;padding-top:12px;z-index:1"></div>' +
                    '</div></div>';
                document.body.appendChild(div);
                App.modal._el = div.querySelector('.modal-overlay');
            },

            /** 显示确认框 */
            confirm: function (title, message, onOk) {
                App.modal._ensure();
                var el = App.modal._el;
                el.querySelector('.modal-box').style.maxWidth = '420px';
                el.querySelector('.modal-title').textContent = title;
                el.querySelector('.modal-body').textContent = message;
                var footer = el.querySelector('.modal-footer');
                footer.innerHTML =
                    '<button class="modal-btn-cancel" style="padding:8px 20px;border:1px solid #d1d5db;border-radius:8px;background:#fff;cursor:pointer">取消</button>' +
                    '<button class="modal-btn-ok" style="padding:8px 20px;border:none;border-radius:8px;background:#4f46e5;color:#fff;cursor:pointer">确认</button>';
                footer.querySelector('.modal-btn-cancel').onclick = App.modal.hide;
                footer.querySelector('.modal-btn-ok').onclick = function () { App.modal.hide(); if (onOk) onOk(); };
                el.style.display = 'flex';
            },

            /** 显示提示框（支持 HTML） */
            alert: function (title, message) {
                App.modal._ensure();
                var el = App.modal._el;
                el.querySelector('.modal-box').style.maxWidth = '420px';
                el.querySelector('.modal-title').textContent = title;
                el.querySelector('.modal-body').innerHTML = message;
                var footer = el.querySelector('.modal-footer');
                footer.innerHTML =
                    '<button class="modal-btn-ok" style="padding:8px 28px;border:none;border-radius:8px;background:#4f46e5;color:#fff;cursor:pointer">确定</button>';
                footer.querySelector('.modal-btn-ok').onclick = App.modal.hide;
                el.style.display = 'flex';
            },

            /** 显示自定义表单弹窗 */
            form: function (title, bodyHTML, onSubmit) {
                App.modal._ensure();
                var el = App.modal._el;
                el.querySelector('.modal-title').textContent = title;
                el.querySelector('.modal-body').innerHTML = bodyHTML;
                el.querySelector('.modal-box').style.maxWidth = '700px';
                var footer = el.querySelector('.modal-footer');
                footer.innerHTML =
                    '<button class="modal-btn-cancel" style="padding:8px 20px;border:1px solid #d1d5db;border-radius:8px;background:#fff;cursor:pointer">取消</button>' +
                    '<button class="modal-btn-ok" style="padding:8px 20px;border:none;border-radius:8px;background:#4f46e5;color:#fff;cursor:pointer">确认</button>';
                footer.querySelector('.modal-btn-cancel').onclick = App.modal.hide;
                footer.querySelector('.modal-btn-ok').onclick = function () {
                    if (onSubmit) onSubmit();
                };
                el.style.display = 'flex';
            },

            /** 关闭模态框并延迟回调 */
            close: function (fn) {
                App.modal._el.style.display = 'none';
                if (fn) setTimeout(fn, 200);
            },

            hide: function () {
                if (document.getElementById('app-modal')) {
                    var el = document.querySelector('#app-modal .modal-overlay');
                    if (el) el.style.display = 'none';
                }
            }
        }
    };

    // ========== 全局点击拦截 ==========
    document.addEventListener('DOMContentLoaded', function () {
        document.body.addEventListener('click', function (e) {
            var link = e.target.closest('a');
            if (!link) return;
            var href = link.getAttribute('href');
            if (!href || href.startsWith('#') || href.startsWith('http') || href.startsWith('//')) return;
            if (link.getAttribute('target') === '_blank') return;
            if (link.hasAttribute('data-no-nav')) return;
            if (PUBLIC_PAGES.indexOf(href) !== -1) return;
            e.preventDefault();
            App.navigate(href);
        });
    });
})();

// 通用分页渲染（最多显示 7 个页码）
App.pagination = function(total, page, pageSize, containerId, onClick) {
    var tp = Math.ceil(total / pageSize);
    var pages = [];
    if (tp <= 7) {
        for (var i = 1; i <= tp; i++) pages.push(i);
    } else {
        pages.push(1);
        if (page > 3) pages.push('...');
        for (var i = Math.max(2, page - 1); i <= Math.min(tp - 1, page + 1); i++) pages.push(i);
        if (page < tp - 2) pages.push('...');
        pages.push(tp);
    }
    var html = '<div class="flex items-center space-x-1 text-sm"><span class="text-gray-500 mr-2">共 ' + total + ' 条</span>';
    pages.forEach(function(p) {
        if (p === '...') html += '<span class="px-2 text-gray-400">...</span>';
        else html += '<button onclick="' + onClick + '(' + p + ')" class="px-3 py-1 rounded ' + (p === page ? 'bg-indigo-600 text-white' : 'bg-gray-200') + '">' + p + '</button>';
    });
    html += '</div>';
    document.getElementById(containerId).innerHTML = html;
};
