# -*- coding: utf-8 -*-
"""
流代理 API
"""

import requests
import uuid
from flask import Blueprint, request, jsonify, Response, stream_with_context
from loguru import logger
from sqlalchemy import select
from app import db
from app.models.users import Users
from app.models.channel import Channel
from app.models.watch_history import WatchHistory
from app.models.active_connection import ActiveConnection
from app.config import get_heartbeat_interval_seconds
from app.utils.auth import login_required
from app.utils.datetime_utils import to_iso8601_utc, to_utc_naive
from app.services.watch_history_saver import update_connection_heartbeat, close_active_connection

bp = Blueprint('proxy', __name__, url_prefix='/api/proxy')


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
    
    user = Users.query.filter_by(token=token).first()
    if not user:
        return jsonify({'error': 'Token 无效'}), 401

    # 使用 SQLAlchemy 2.0 兼容的方式
    channel = db.session.get(Channel, channel_id)
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
    
    # 创建观看记录 + 活跃连接（同事务）
    connection_id = f"{user.id}_{channel_id}_{uuid.uuid4().hex}"
    start_time_utc = to_utc_naive()
    watch_record_id = None

    try:
        watch_record = WatchHistory(user_id=user.id, channel_id=channel.id, start_time=start_time_utc)
        db.session.add(watch_record)
        db.session.flush()
        watch_record_id = watch_record.id

        active_connection = ActiveConnection(
            connection_id=connection_id,
            watch_history_id=watch_record_id,
            user_id=user.id,
            channel_id=channel.id,
            start_time=start_time_utc,
            last_heartbeat=start_time_utc
        )
        db.session.add(active_connection)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"创建活跃连接失败: user_id={user.id}, channel_id={channel.id}, error={e}")
        return jsonify({'error': '创建观看会话失败'}), 500

    username = user.username
    channel_name = channel.name
    heartbeat_interval = get_heartbeat_interval_seconds()
    last_heartbeat_at = start_time_utc
    
    def generate():
        nonlocal last_heartbeat_at, heartbeat_interval
        try:
            # 从配置获取缓冲区大小（优先从数据库读取）
            from app.config import get_proxy_buffer_size
            buffer_size = get_proxy_buffer_size()

            with requests.get(stream_url, stream=True, timeout=30) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=buffer_size):
                    now_utc = to_utc_naive()
                    if (now_utc - last_heartbeat_at).total_seconds() >= heartbeat_interval:
                        update_connection_heartbeat(connection_id, heartbeat_time=now_utc)
                        last_heartbeat_at = now_utc
                        heartbeat_interval = get_heartbeat_interval_seconds()

                    if chunk:
                        yield chunk
        except Exception as e:
            logger.error(f"Stream error: {e}")
        finally:
            # 幂等结束连接：落历史 + 删除活跃连接
            try:
                result = close_active_connection(
                    connection_id=connection_id,
                    end_time=to_utc_naive(),
                    fallback_watch_history_id=watch_record_id
                )
                if result.get('history_updated'):
                    logger.debug(
                        f"观看记录保存: 用户 {username}, 频道 {channel_name}, 时长 {result.get('duration', 0)}秒"
                    )
                elif result.get('history_deleted_short'):
                    logger.debug(
                        f"观看记录已忽略(<5秒): 用户 {username}, 频道 {channel_name}, 时长 {result.get('duration', 0)}秒"
                    )
            except Exception as e:
                logger.error(f"保存观看记录失败: connection_id={connection_id}, error={e}")
    
    # 获取原始响应的 Content-Type（失败时回退默认值）
    content_type = 'video/mp2t'
    try:
        head_response = requests.head(stream_url, timeout=10, allow_redirects=True)
        if head_response.ok:
            content_type = head_response.headers.get('Content-Type', content_type)
        else:
            logger.warning(
                f"探测 Content-Type 失败: url={stream_url}, status={head_response.status_code}"
            )
    except requests.RequestException as e:
        logger.warning(f"探测 Content-Type 异常: url={stream_url}, error={e}")
    
    return Response(
        stream_with_context(generate()),
        mimetype=content_type
    )


@bp.route('/status', methods=['GET'])
@login_required
def get_proxy_status():
    """获取代理状态"""
    rows = db.session.execute(
        select(
            ActiveConnection.connection_id,
            ActiveConnection.watch_history_id,
            ActiveConnection.user_id,
            Users.username,
            ActiveConnection.channel_id,
            Channel.name.label('channel_name'),
            ActiveConnection.start_time,
            ActiveConnection.last_heartbeat
        ).select_from(ActiveConnection).join(
            Users,
            ActiveConnection.user_id == Users.id,
            isouter=True
        ).join(
            Channel,
            ActiveConnection.channel_id == Channel.id,
            isouter=True
        ).order_by(
            ActiveConnection.start_time.desc()
        )
    ).all()

    connections = [
        {
            'connection_id': row.connection_id,
            'watch_record_id': row.watch_history_id,
            'user_id': row.user_id,
            'username': row.username or '未知用户',
            'channel_id': row.channel_id,
            'channel_name': row.channel_name or '已删除频道',
            'start_time': to_iso8601_utc(row.start_time),
            'last_heartbeat': to_iso8601_utc(row.last_heartbeat)
        }
        for row in rows
    ]

    return jsonify({
        'active_connections': len(connections),
        'connections': connections
    })
