# -*- coding: utf-8 -*-
"""
仪表盘 API
"""

from flask import Blueprint, jsonify, request
from app.models.channel import Channel, ChannelGroup
from app.models.watch_history import WatchHistory
from app.api.proxy import active_connections
from app.utils.auth import login_required
from app import __version__

bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')


@bp.route('', methods=['GET'])
@login_required
def get_dashboard():
    """获取仪表盘数据"""
    # 频道统计
    total_channels = Channel.query.count()
    active_channels = Channel.query.filter_by(is_active=True).count()
    healthy_channels = Channel.query.filter_by(is_active=True, is_healthy=True).count()
    unhealthy_channels = Channel.query.filter_by(is_active=True, is_healthy=False).count()
    
    # 分组统计
    total_groups = ChannelGroup.query.count()
    
    # 协议统计
    protocol_stats = {}
    for protocol in ['http', 'https', 'rtp', 'udp']:
        count = Channel.query.filter_by(protocol=protocol).count()
        if count > 0:
            protocol_stats[protocol] = count
    
    # 当前代理连接数
    current_connections = len(active_connections)
    
    # 获取不健康的频道（最多显示 10 个）
    unhealthy_list = Channel.query.filter_by(is_active=True, is_healthy=False).limit(10).all()
    
    return jsonify({
        'channels': {
            'total': total_channels,
            'active': active_channels,
            'healthy': healthy_channels,
            'unhealthy': unhealthy_channels
        },
        'groups': {
            'total': total_groups
        },
        'protocols': protocol_stats,
        'proxy': {
            'active_connections': current_connections
        },
        'unhealthy_channels': [ch.to_dict() for ch in unhealthy_list]
    })


@bp.route('/watch-stats', methods=['GET'])
@login_required
def get_watch_stats():
    """获取观看时长统计"""
    days = request.args.get('days', 7, type=int)
    if days < 1:
        days = 7
    elif days > 30:
        days = 30
    
    stats = WatchHistory.get_daily_stats(days=days)
    
    # 计算总观看时长
    total_duration = sum(item['duration'] for item in stats)
    
    return jsonify({
        'stats': stats,
        'total_duration': total_duration,
        'days': days
    })


@bp.route('/channel-ranking', methods=['GET'])
@login_required
def get_channel_ranking():
    """获取频道观看排名"""
    days = request.args.get('days', 7, type=int)
    limit = request.args.get('limit', 10, type=int)
    
    if days < 1:
        days = 7
    elif days > 30:
        days = 30
    
    if limit < 1:
        limit = 10
    elif limit > 50:
        limit = 50
    
    ranking = WatchHistory.get_channel_ranking(days=days, limit=limit)

    return jsonify({
        'ranking': ranking,
        'days': days
    })


@bp.route('/version', methods=['GET'])
def get_version():
    """获取系统版本信息"""
    return jsonify({
        'version': __version__,
        'name': 'IPTV Proxy Admin'
    })

