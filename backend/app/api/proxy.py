# -*- coding: utf-8 -*-
"""
流代理 API
"""

import requests
from datetime import datetime
from flask import Blueprint, request, jsonify, Response, stream_with_context
from loguru import logger
from app import db
from app.models.user import User
from app.models.channel import Channel
from app.models.watch_history import WatchHistory
from app.config import config
from app.utils.auth import login_required

bp = Blueprint('proxy', __name__, url_prefix='/api/proxy')

# 存储当前活跃的代理连接
active_connections = {}


def get_udpxy_url(original_url):
    """将组播地址转换为 UDPxy 地址"""
    from app.config import get_udpxy_enabled, get_udpxy_url as get_udpxy_url_config

    if not get_udpxy_enabled():
        return None

    udpxy_base = get_udpxy_url_config().rstrip('/')
    
    # 解析 rtp:// 或 udp:// 地址
    # 格式: rtp://239.0.0.1:5000 或 udp://@239.0.0.1:5000
    if original_url.startswith('rtp://'):
        addr = original_url[6:]  # 移除 rtp://
    elif original_url.startswith('udp://'):
        addr = original_url[6:]  # 移除 udp://
        if addr.startswith('@'):
            addr = addr[1:]  # 移除 @
    else:
        return None
    
    # UDPxy URL 格式: http://udpxy:port/udp/239.0.0.1:5000
    return f"{udpxy_base}/udp/{addr}"


@bp.route('/stream/<int:channel_id>', methods=['GET'])
def stream_channel(channel_id):
    """代理转发频道流"""
    token = request.args.get('token')
    
    if not token:
        return jsonify({'error': '缺少 Token'}), 401
    
    user = User.query.filter_by(token=token).first()
    if not user:
        return jsonify({'error': 'Token 无效'}), 401
    
    channel = Channel.query.get(channel_id)
    if not channel:
        return jsonify({'error': '频道不存在'}), 404
    
    if not channel.is_active:
        return jsonify({'error': '频道未启用'}), 403
    
    # 获取实际的流地址
    stream_url = channel.url
    
    # 如果是组播源，通过 UDPxy 转换
    if channel.is_multicast():
        udpxy_url = get_udpxy_url(channel.url)
        if udpxy_url:
            stream_url = udpxy_url
            logger.info(f"组播源转换: {channel.url} -> {stream_url}")
        else:
            return jsonify({'error': 'UDPxy 未配置，无法播放组播源'}), 500
    else:
        logger.debug(f"HTTP 源: {stream_url}")
    
    # 创建观看记录
    watch_record = WatchHistory(user_id=user.id, channel_id=channel.id)
    db.session.add(watch_record)
    db.session.commit()
    watch_record_id = watch_record.id
    
    # 记录活跃连接
    connection_id = f"{user.id}_{channel_id}_{id(request)}"
    active_connections[connection_id] = {
        'user_id': user.id,
        'username': user.username,
        'channel_id': channel.id,
        'channel_name': channel.name,
        'start_time': datetime.now().isoformat(),
        'watch_record_id': watch_record_id
    }
    
    def generate():
        try:
            # 从配置获取缓冲区大小（优先从数据库读取）
            from app.config import get_proxy_buffer_size
            buffer_size = get_proxy_buffer_size()

            with requests.get(stream_url, stream=True, timeout=30) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=buffer_size):
                    if chunk:
                        yield chunk
        except Exception as e:
            logger.error(f"Stream error: {e}")
        finally:
            # 清理连接记录并保存观看时长
            conn_info = active_connections.pop(connection_id, None)
            if conn_info and conn_info.get('watch_record_id'):
                try:
                    record = WatchHistory.query.get(conn_info['watch_record_id'])
                    if record:
                        record.finish()
                        db.session.commit()
                        logger.debug(f"观看记录保存: 用户 {user.username}, 频道 {channel.name}, 时长 {record.duration}秒")
                except Exception as e:
                    logger.error(f"保存观看记录失败: {e}")
    
    # 获取原始响应的 Content-Type
    try:
        head_response = requests.head(stream_url, timeout=10)
        content_type = head_response.headers.get('Content-Type', 'video/mp2t')
    except:
        content_type = 'video/mp2t'
    
    return Response(
        stream_with_context(generate()),
        mimetype=content_type
    )


@bp.route('/status', methods=['GET'])
@login_required
def get_proxy_status():
    """获取代理状态"""
    connections = list(active_connections.values())
    return jsonify({
        'active_connections': len(connections),
        'connections': connections
    })
