# -*- coding: utf-8 -*-
"""
订阅链接 API
"""

from flask import Blueprint, request, jsonify, Response
from app.models.users import Users
from app.models.channel import Channel
from app.models.settings import Settings
from app.utils.auth import login_required, get_current_user

bp = Blueprint('subscription', __name__, url_prefix='/api/subscription')


def get_stream_url(channel_id, token, request_obj):
    """生成流代理 URL"""
    host = request_obj.host_url.rstrip('/')
    return f"{host}/api/proxy/stream/{channel_id}?token={token}"


def get_sorted_active_channels():
    """按频道排序字段获取启用频道（与频道管理列表保持一致）"""
    return Channel.query.filter_by(is_active=True).order_by(Channel.sort_order, Channel.id).all()


@bp.route('/m3u', methods=['GET'])
def get_m3u():
    """获取 M3U 格式订阅链接"""
    token = request.args.get('token')
    
    if not token:
        return jsonify({'error': '缺少 Token'}), 401
    
    user = Users.query.filter_by(token=token).first()
    if not user:
        return jsonify({'error': 'Token 无效'}), 401
    
    # 获取 EPG URL
    epg_url = Settings.get(Settings.KEY_EPG_URL, '')
    
    # 构建 M3U 内容
    lines = []
    if epg_url:
        lines.append(f'#EXTM3U x-tvg-url="{epg_url}"')
    else:
        lines.append('#EXTM3U')
    
    # 按频道排序顺序输出，避免被分组循环打乱
    channels = get_sorted_active_channels()
    for channel in channels:
        stream_url = get_stream_url(channel.id, token, request)
        tvg_id_part = f' tvg-id="{channel.tvg_id}"' if channel.tvg_id else ''
        logo_part = f' tvg-logo="{channel.logo}"' if channel.logo else ''
        group_part = f' group-title="{channel.group.name}"' if channel.group else ''
        lines.append(f'#EXTINF:-1{tvg_id_part} tvg-name="{channel.name}"{logo_part}{group_part},{channel.name}')
        lines.append(stream_url)
    
    content = '\n'.join(lines)
    
    return Response(
        content,
        mimetype='audio/x-mpegurl',
        headers={
            'Content-Disposition': 'attachment; filename="playlist.m3u"'
        }
    )


@bp.route('/txt', methods=['GET'])
def get_txt():
    """获取 TXT 格式订阅链接"""
    token = request.args.get('token')
    
    if not token:
        return jsonify({'error': '缺少 Token'}), 401
    
    user = Users.query.filter_by(token=token).first()
    if not user:
        return jsonify({'error': 'Token 无效'}), 401
    
    lines = []
    
    channels = get_sorted_active_channels()

    current_group_name = None
    for channel in channels:
        group_name = channel.group.name if channel.group else '未分组'
        if group_name != current_group_name:
            lines.append(f'{group_name},#genre#')
            current_group_name = group_name

        stream_url = get_stream_url(channel.id, token, request)
        lines.append(f'{channel.name},{stream_url}')
    
    content = '\n'.join(lines)
    
    return Response(
        content,
        mimetype='text/plain; charset=utf-8',
        headers={
            'Content-Disposition': 'attachment; filename="playlist.txt"'
        }
    )


@bp.route('/urls', methods=['GET'])
@login_required
def get_subscription_urls():
    """获取订阅链接地址"""
    user = get_current_user()
    base_url = request.host_url.rstrip('/')
    
    return jsonify({
        'm3u_url': f"{base_url}/api/subscription/m3u?token={user.token}",
        'txt_url': f"{base_url}/api/subscription/txt?token={user.token}",
        'token': user.token
    })
