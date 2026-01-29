# -*- coding: utf-8 -*-
"""
健康检测 API
"""

from flask import Blueprint, request, jsonify
from app.models.channel import Channel
from app.services.health_checker import check_channel_health, check_all_channels
from app.utils.auth import login_required

bp = Blueprint('health', __name__, url_prefix='/api/health')


@bp.route('/check/<int:channel_id>', methods=['POST'])
@login_required
def check_single_channel(channel_id):
    """检测单个频道"""
    channel = Channel.query.get_or_404(channel_id)
    
    is_healthy = check_channel_health(channel)
    
    return jsonify({
        'channel_id': channel.id,
        'channel_name': channel.name,
        'is_healthy': is_healthy,
        'last_check': channel.last_check.isoformat() if channel.last_check else None
    })


@bp.route('/check-all', methods=['POST'])
@login_required
def check_all():
    """检测所有频道"""
    results = check_all_channels()
    
    return jsonify({
        'message': '健康检测完成',
        'total': results['total'],
        'healthy': results['healthy'],
        'unhealthy': results['unhealthy']
    })


@bp.route('/status', methods=['GET'])
@login_required
def get_health_status():
    """获取健康状态统计"""
    total = Channel.query.filter_by(is_active=True).count()
    healthy = Channel.query.filter_by(is_active=True, is_healthy=True).count()
    unhealthy = Channel.query.filter_by(is_active=True, is_healthy=False).count()
    
    # 获取不健康的频道列表
    unhealthy_channels = Channel.query.filter_by(is_active=True, is_healthy=False).all()
    
    return jsonify({
        'total': total,
        'healthy': healthy,
        'unhealthy': unhealthy,
        'unhealthy_channels': [ch.to_dict() for ch in unhealthy_channels]
    })
