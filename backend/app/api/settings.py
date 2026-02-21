# -*- coding: utf-8 -*-
"""
系统设置 API
"""

import requests
from flask import Blueprint, request, jsonify
from loguru import logger
from urllib.parse import SplitResult, urlsplit, urlunsplit
from app.models.settings import Settings
from app.utils.auth import login_required

bp = Blueprint('settings', __name__, url_prefix='/api/settings')
LOCAL_UDPXY_HOSTS = {'localhost', '127.0.0.1', '::1'}


def _normalize_udpxy_url(raw_url: str):
    """规范化 UDPxy 地址并做基础校验。"""
    if not raw_url:
        return None, '请提供 UDPxy 服务器地址'

    raw_url = raw_url.strip()
    if '://' not in raw_url:
        raw_url = f"http://{raw_url}"

    parsed = urlsplit(raw_url)
    if parsed.scheme not in ('http', 'https'):
        return None, 'UDPxy 地址必须使用 http:// 或 https://'
    if not parsed.hostname:
        return None, 'UDPxy 地址格式无效'

    try:
        _ = parsed.port
    except ValueError:
        return None, 'UDPxy 端口格式无效'

    normalized = parsed._replace(path=parsed.path.rstrip('/'))
    return normalized, None


def _extract_host(host_with_port: str):
    """从 host:port 中提取 host（兼容 IPv6）。"""
    if not host_with_port:
        return None
    if host_with_port.startswith('['):
        end = host_with_port.find(']')
        if end > 0:
            return host_with_port[1:end]
    if ':' in host_with_port:
        return host_with_port.rsplit(':', 1)[0]
    return host_with_port


def _build_netloc(parsed: SplitResult, host: str):
    """按原 URL 的认证信息和端口重建 netloc。"""
    if ':' in host and not host.startswith('['):
        host = f"[{host}]"

    credentials = ''
    if parsed.username:
        credentials = parsed.username
        if parsed.password:
            credentials = f"{credentials}:{parsed.password}"
        credentials = f"{credentials}@"

    if parsed.port is not None:
        return f"{credentials}{host}:{parsed.port}"
    return f"{credentials}{host}"


def _build_udpxy_candidates(parsed: SplitResult, request_host: str, remote_addr: str):
    """构建 UDPxy 探测候选地址列表。"""
    original_host = parsed.hostname or ''
    hosts = [original_host]

    if original_host.lower() in LOCAL_UDPXY_HOSTS:
        hosts.extend(['localhost', '127.0.0.1', '::1', 'host.docker.internal', 'host.containers.internal'])
        incoming_host = _extract_host(request_host)
        if incoming_host:
            hosts.append(incoming_host)
        if remote_addr:
            hosts.append(remote_addr)

    deduped_hosts = []
    seen = set()
    for host in hosts:
        if not host:
            continue
        lower_host = host.lower()
        if lower_host in seen:
            continue
        seen.add(lower_host)
        deduped_hosts.append(host)

    candidates = []
    for host in deduped_hosts:
        netloc = _build_netloc(parsed, host)
        base_url = urlunsplit((parsed.scheme, netloc, parsed.path, '', '')).rstrip('/')
        if base_url:
            candidates.append(base_url)
    return candidates


def _probe_udpxy(base_url: str, timeout: int = 5):
    """探测单个 UDPxy 地址，优先 /status，失败时回退到根路径。"""
    probe_urls = [f"{base_url}/status", f"{base_url}/"]
    attempts = []

    for target_url in probe_urls:
        try:
            response = requests.get(target_url, timeout=timeout, allow_redirects=True)
            attempts.append({'url': target_url, 'status_code': response.status_code})
            if 200 <= response.status_code < 400:
                return True, target_url, response.status_code, attempts
        except requests.exceptions.RequestException as exc:
            attempts.append({'url': target_url, 'error': str(exc)})

    return False, None, None, attempts


@bp.route('', methods=['GET'])
@login_required
def get_settings():
    """获取所有设置"""
    settings = Settings.get_all()
    return jsonify(settings)


@bp.route('/<key>', methods=['GET'])
@login_required
def get_setting(key):
    """获取单个设置"""
    value = Settings.get(key)
    return jsonify({
        'key': key,
        'value': value
    })


@bp.route('', methods=['POST'])
@login_required
def update_settings():
    """批量更新设置"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': '请提供设置信息'}), 400
    
    for key, value in data.items():
        Settings.set(key, value)
    
    return jsonify({
        'message': '设置更新成功',
        'settings': Settings.get_all()
    })


@bp.route('/<key>', methods=['PUT'])
@login_required
def update_setting(key):
    """更新单个设置"""
    data = request.get_json()
    
    if data is None:
        return jsonify({'error': '请提供设置值'}), 400
    
    value = data.get('value')
    Settings.set(key, value)
    
    return jsonify({
        'message': '设置更新成功',
        'key': key,
        'value': value
    })


@bp.route('/reload', methods=['POST'])
@login_required
def reload_settings():
    """重新加载运行时配置"""
    try:
        from app.config import load_runtime_config_from_db
        success = load_runtime_config_from_db()

        if success:
            return jsonify({'message': '配置已重新加载'})
        else:
            return jsonify({'error': '配置重载失败'}), 500
    except Exception as e:
        logger.error(f"重载配置失败: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/test-udpxy', methods=['POST'])
@login_required
def test_udpxy():
    """测试 UDPxy 服务器连接性"""
    data = request.get_json(silent=True) or {}
    parsed_url, error_message = _normalize_udpxy_url(data.get('url', ''))
    if error_message:
        return jsonify({'error': error_message}), 400

    candidates = _build_udpxy_candidates(parsed_url, request.host, request.remote_addr)
    attempted_urls = []

    for base_url in candidates:
        ok, success_url, status_code, attempts = _probe_udpxy(base_url)
        attempted_urls.extend([a['url'] for a in attempts])
        if ok:
            logger.info(f"UDPxy 服务器连接成功: {success_url}")
            return jsonify({
                'success': True,
                'message': 'UDPxy 服务器连接成功',
                'status_code': status_code,
                'tested_url': success_url,
                'resolved_base_url': base_url
            })

    logger.warning(f"UDPxy 服务器连接失败，已尝试: {attempted_urls}")
    return jsonify({
        'success': False,
        'message': '无法连接到 UDPxy 服务器，请检查地址、端口和网络连通性',
        'attempted_urls': attempted_urls
    })
