# -*- coding: utf-8 -*-
"""
健康检测 API
"""

from flask import Blueprint, request, jsonify
from app.models.channel import Channel
from app.services.health_checker import check_channel_health, check_all_channels, HealthCheckBusy
from app.utils.auth import login_required
from app.utils.datetime_utils import to_iso8601_utc

bp = Blueprint('health', __name__, url_prefix='/api/health')


@bp.route('/check/<int:channel_id>', methods=['POST'])
@login_required
def check_single_channel(channel_id):
    """检测单个频道"""
    channel = Channel.query.get_or_404(channel_id)
    
    try:
        is_healthy = check_channel_health(channel)
    except HealthCheckBusy as exc:
        return jsonify({'error': str(exc)}), 409
    
    return jsonify({
        'channel_id': channel.id,
        'channel_name': channel.name,
        'is_healthy': is_healthy,
        'last_check': to_iso8601_utc(channel.last_check)
    })


@bp.route('/check-all', methods=['POST'])
@login_required
def check_all():
    """提交后台串行检测所有频道。"""
    results = check_all_channels()
    
    return jsonify({
        'message': '已提交后台串行检测，频道状态将逐个更新；请确保 worker 已启动',
        'total': results['total'],
        'pending': results['pending']
    }), 202


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
        'pending': Channel.query.filter(Channel.is_active.is_(True),
                                        Channel.health_check_requested_at.is_not(None)).count(),
        'unhealthy_channels': [ch.to_dict() for ch in unhealthy_channels]
    })
