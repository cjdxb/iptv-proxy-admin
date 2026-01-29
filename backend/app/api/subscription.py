# -*- coding: utf-8 -*-
"""
订阅链接 API
"""

from flask import Blueprint, request, jsonify, Response, url_for
from flask_login import current_user
from app.models.user import User
from app.models.channel import Channel, ChannelGroup
from app.models.settings import Settings
from app.config import config
from app.utils.auth import login_required

bp = Blueprint('subscription', __name__, url_prefix='/api/subscription')


def get_stream_url(channel_id, token, request_obj):
    """生成流代理 URL"""
    host = request_obj.host_url.rstrip('/')
    return f"{host}/api/proxy/stream/{channel_id}?token={token}"


@bp.route('/m3u', methods=['GET'])
def get_m3u():
    """获取 M3U 格式订阅链接"""
    token = request.args.get('token')
    
    if not token:
        return jsonify({'error': '缺少 Token'}), 401
    
    user = User.query.filter_by(token=token).first()
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
    
    # 按分组获取频道
    groups = ChannelGroup.query.order_by(ChannelGroup.sort_order).all()
    ungrouped_channels = Channel.query.filter_by(group_id=None, is_active=True).order_by(Channel.sort_order).all()
    
    # 先输出有分组的频道
    for group in groups:
        channels = Channel.query.filter_by(group_id=group.id, is_active=True).order_by(Channel.sort_order).all()
        for channel in channels:
            stream_url = get_stream_url(channel.id, token, request)
            tvg_id_part = f' tvg-id="{channel.tvg_id}"' if channel.tvg_id else ''
            logo_part = f' tvg-logo="{channel.logo}"' if channel.logo else ''
            lines.append(f'#EXTINF:-1{tvg_id_part} tvg-name="{channel.name}"{logo_part} group-title="{group.name}",{channel.name}')
            lines.append(stream_url)
    
    # 输出未分组的频道
    for channel in ungrouped_channels:
        stream_url = get_stream_url(channel.id, token, request)
        tvg_id_part = f' tvg-id="{channel.tvg_id}"' if channel.tvg_id else ''
        logo_part = f' tvg-logo="{channel.logo}"' if channel.logo else ''
        lines.append(f'#EXTINF:-1{tvg_id_part} tvg-name="{channel.name}"{logo_part},{channel.name}')
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
    
    user = User.query.filter_by(token=token).first()
    if not user:
        return jsonify({'error': 'Token 无效'}), 401
    
    lines = []
    
    # 按分组获取频道
    groups = ChannelGroup.query.order_by(ChannelGroup.sort_order).all()
    ungrouped_channels = Channel.query.filter_by(group_id=None, is_active=True).order_by(Channel.sort_order).all()
    
    # 先输出有分组的频道
    for group in groups:
        channels = Channel.query.filter_by(group_id=group.id, is_active=True).order_by(Channel.sort_order).all()
        if channels:
            lines.append(f'{group.name},#genre#')
            for channel in channels:
                stream_url = get_stream_url(channel.id, token, request)
                lines.append(f'{channel.name},{stream_url}')
    
    # 输出未分组的频道
    if ungrouped_channels:
        lines.append('未分组,#genre#')
        for channel in ungrouped_channels:
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
    base_url = request.host_url.rstrip('/')
    
    return jsonify({
        'm3u_url': f"{base_url}/api/subscription/m3u?token={current_user.token}",
        'txt_url': f"{base_url}/api/subscription/txt?token={current_user.token}",
        'token': current_user.token
    })
