# -*- coding: utf-8 -*-
"""
活跃连接模型
"""

from app import db
from app.utils.datetime_utils import to_utc_naive


class ActiveConnection(db.Model):
    """当前活跃连接（跨进程共享）"""
    __tablename__ = 'active_connections'

    connection_id = db.Column(db.String(64), primary_key=True)
    watch_history_id = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    channel_id = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    last_heartbeat = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=to_utc_naive)

    __table_args__ = (
        db.UniqueConstraint('watch_history_id', name='uk_active_watch_history_id'),
        db.Index('idx_active_user_id', 'user_id'),
        db.Index('idx_active_channel_id', 'channel_id'),
        db.Index('idx_active_last_heartbeat', 'last_heartbeat'),
        db.Index('idx_active_user_channel', 'user_id', 'channel_id'),
    )
