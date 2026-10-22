# -*- coding: utf-8 -*-
"""
流代理 API
"""

import requests
import uuid
from itsdangerous import BadSignature
from flask import Blueprint, request, jsonify, Response, stream_with_context, redirect, url_for
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
from app.services.hls import is_hls_response, resource_signer, rewrite_playlist

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
    resource = request.args.get('resource')
    resource_data = None
    if resource:
        try:
            resource_data = resource_signer().loads(resource)
            if resource_data['channel_id'] != channel_id or resource_data['user_id'] != user.id:
                raise BadSignature('resource mismatch')
            stream_url = resource_data['url']
        except (BadSignature, KeyError, TypeError):
            return jsonify({'error': 'HLS 资源签名无效'}), 403

    # 在发送响应头、创建观看记录之前发起 GET；不使用上游可能拒绝的 HEAD。
    upstream = None
    try:
        headers = {}
        if request.headers.get('Range'):
            headers['Range'] = request.headers['Range']
        upstream = requests.get(stream_url, stream=True, timeout=(10, 30), headers=headers)
        if upstream.status_code not in (200, 206):
            status = upstream.status_code
            upstream.close()
            logger.warning(f'频道 {channel_id} 上游 GET 失败: HTTP {status}')
            return jsonify({'error': f'播放源返回 HTTP {status}', 'upstream_status': status}), 502
        hls = is_hls_response(upstream)
        playlist = None
        if hls:
            # 清单有限大小；分片和连续 TS 流仍采用流式转发。
            content = bytearray()
            for chunk in upstream.iter_content(chunk_size=8192):
                content.extend(chunk)
                if len(content) > 2 * 1024 * 1024:
                    upstream.close()
                    return jsonify({'error': 'HLS 清单过大'}), 502
            playlist = content.decode('utf-8-sig')
            upstream.close()
            if not playlist.lstrip().startswith('#EXTM3U'):
                return jsonify({'error': '播放源未返回有效的 HLS 清单'}), 502
    except (requests.RequestException, UnicodeError) as e:
        if upstream is not None:
            upstream.close()
        logger.warning(f'频道 {channel_id} 上游请求失败: {type(e).__name__}')
        return jsonify({'error': '播放源连接失败或响应无效'}), 502
    
    # 创建观看记录 + 活跃连接（同事务）
    connection_id = (resource_data['connection_id'] if resource_data
                     else f"{user.id}_{channel_id}_{uuid.uuid4().hex}")
    start_time_utc = to_utc_naive()
    watch_record_id = None

    try:
        if resource_data:
            update_connection_heartbeat(connection_id, heartbeat_time=start_time_utc)
        else:
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
        upstream.close()
        db.session.rollback()
        logger.error(f"创建活跃连接失败: user_id={user.id}, channel_id={channel.id}, error={e}")
        return jsonify({'error': '创建观看会话失败'}), 500

    if hls:
        if not resource_data:
            # 固定本次播放的清单 URL，直播清单刷新时复用同一观看会话。
            signed = resource_signer().dumps({
                'url': upstream.url, 'channel_id': channel_id, 'user_id': user.id,
                'connection_id': connection_id,
            })
            response = redirect(url_for('proxy.stream_channel', channel_id=channel_id,
                                        token=token, resource=signed), code=302)
            response.headers['Cache-Control'] = 'no-store'
            return response
        body = rewrite_playlist(playlist, upstream.url, channel_id, user.id, token, connection_id)
        # HLS 是多个短请求，靠子资源请求续心跳，由 worker 回收停止播放的会话。
        return Response(body, content_type='application/vnd.apple.mpegurl',
                        headers={'Cache-Control': 'no-store'})

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

            with upstream as r:
                # read1 返回当前可用数据，不像 iter_content/read 等待凑满缓冲区。
                # 使用 urllib3 的公开接口，保留 chunked 解帧和内容解压。
                while True:
                    chunk = r.raw.read1(buffer_size, decode_content=True)
                    if not chunk:
                        break
                    yield chunk
                    now_utc = to_utc_naive()
                    if (now_utc - last_heartbeat_at).total_seconds() >= heartbeat_interval:
                        update_connection_heartbeat(connection_id, heartbeat_time=now_utc)
                        last_heartbeat_at = now_utc
                        heartbeat_interval = get_heartbeat_interval_seconds()

        except Exception as e:
            logger.error(f"频道 {channel_id} 流读取失败: {type(e).__name__}")
        finally:
            upstream.close()
            if not resource_data:
                # 连续流结束时关闭会话；HLS 分片结束不代表用户停止播放。
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
    
    response = Response(
        stream_with_context(generate()),
        status=upstream.status_code,
        content_type=upstream.headers.get('Content-Type', 'video/mp2t')
    )
    for name in ('Content-Range', 'Accept-Ranges'):
        if name in upstream.headers:
            response.headers[name] = upstream.headers[name]
    response.headers['X-Accel-Buffering'] = 'no'
    response.headers['Cache-Control'] = 'no-store, no-transform'
    response.call_on_close(upstream.close)
    return response


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
