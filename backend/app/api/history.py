# -*- coding: utf-8 -*-
"""
观看历史管理 API
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from loguru import logger
from app import db
from app.models.watch_history import WatchHistory
from app.models.settings import Settings
from app.utils.auth import login_required

bp = Blueprint('history', __name__, url_prefix='/api/history')


@bp.route('/cleanup', methods=['POST'])
@login_required
def cleanup_history():
    """
    清空所有观看历史
    """
    try:
        # 查询要删除的记录数量（使用 SQLAlchemy 2.0 兼容的方式）
        count_before = db.session.scalar(select(func.count()).select_from(WatchHistory))

        # 删除所有记录
        deleted_count = WatchHistory.query.delete()

        db.session.commit()

        logger.info(f"手动清空观看历史: 删除了 {deleted_count} 条记录")

        return jsonify({
            'message': f'成功清空 {deleted_count} 条观看历史记录',
            'deleted_count': deleted_count,
            'count_before': count_before,
            'count_after': 0
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"清空观看历史失败: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/list', methods=['GET'])
@login_required
def get_history_list():
    """
    获取历史连接列表
    只显示观看时长 > 0 的记录
    """
    try:
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        # 查询观看时长 > 0 的记录
        query = WatchHistory.query.filter(
            WatchHistory.duration > 0
        ).order_by(WatchHistory.start_time.desc())

        # 分页
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        # 构建返回数据
        items = []
        for record in pagination.items:
            item = {
                'id': record.id,
                'user_id': record.user_id,
                'username': record.user.username if record.user else '未知用户',
                'channel_id': record.channel_id,
                'channel_name': record.channel.name if record.channel else '已删除频道',
                'start_time': record.start_time.isoformat() + 'Z' if record.start_time else None,
                'end_time': record.end_time.isoformat() + 'Z' if record.end_time else None,
                'duration': record.duration,
                'watch_date': record.watch_date.isoformat() if record.watch_date else None
            }
            items.append(item)

        return jsonify({
            'items': items,
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        })

    except Exception as e:
        logger.error(f"获取历史连接列表失败: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/stats', methods=['GET'])
@login_required
def get_history_stats():
    """
    获取观看历史统计信息
    """
    try:
        # 总记录数（使用 SQLAlchemy 2.0 兼容的方式）
        total_count = db.session.scalar(select(func.count()).select_from(WatchHistory))

        # 最早记录时间（使用 start_time）
        earliest_record = db.session.query(
            db.func.min(WatchHistory.start_time)
        ).scalar()

        # 最新记录时间（使用 start_time）
        latest_record = db.session.query(
            db.func.max(WatchHistory.start_time)
        ).scalar()

        return jsonify({
            'total_count': total_count,
            'earliest_date': earliest_record.isoformat() + 'Z' if earliest_record else None,
            'latest_date': latest_record.isoformat() + 'Z' if latest_record else None
        })

    except Exception as e:
        logger.error(f"获取观看历史统计失败: {e}")
        return jsonify({'error': str(e)}), 500
