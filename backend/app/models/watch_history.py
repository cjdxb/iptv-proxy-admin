# -*- coding: utf-8 -*-
"""
观看历史模型
"""

from datetime import datetime, date
from app import db


class WatchHistory(db.Model):
    """用户观看历史记录"""
    __tablename__ = 'watch_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('channels.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)
    duration = db.Column(db.Integer, default=0)  # 观看时长（秒）
    watch_date = db.Column(db.Date, nullable=False, index=True)  # 用于按日汇总
    
    # 关联
    user = db.relationship('User', backref=db.backref('watch_history', lazy='dynamic'))
    channel = db.relationship('Channel', backref=db.backref('watch_history', lazy='dynamic'))
    
    def __init__(self, user_id, channel_id, start_time=None):
        self.user_id = user_id
        self.channel_id = channel_id
        self.start_time = start_time or datetime.now()
        self.watch_date = self.start_time.date()
    
    def finish(self):
        """结束观看，计算时长"""
        from loguru import logger

        self.end_time = datetime.now()
        calculated_duration = int((self.end_time - self.start_time).total_seconds())

        # 防止负数时长（可能由于系统时间回退或时区问题导致）
        if calculated_duration < 0:
            logger.warning(f"观看记录时长为负数: start={self.start_time}, end={self.end_time}, duration={calculated_duration}，已设置为0")
            self.duration = 0
        else:
            self.duration = calculated_duration
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'channel_id': self.channel_id,
            'channel_name': self.channel.name if self.channel else None,
            'start_time': self.start_time.isoformat() + 'Z' if self.start_time else None,
            'end_time': self.end_time.isoformat() + 'Z' if self.end_time else None,
            'duration': self.duration,
            'watch_date': self.watch_date.isoformat() if self.watch_date else None
        }
    
    @staticmethod
    def get_daily_stats(user_id=None, days=7):
        """
        获取每日观看时长统计
        返回最近 N 天的每日总观看时长
        """
        from sqlalchemy import func
        from datetime import timedelta
        
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)
        
        query = db.session.query(
            WatchHistory.watch_date,
            func.sum(WatchHistory.duration).label('total_duration')
        ).filter(
            WatchHistory.watch_date >= start_date,
            WatchHistory.watch_date <= end_date
        )
        
        if user_id:
            query = query.filter(WatchHistory.user_id == user_id)
        
        query = query.group_by(WatchHistory.watch_date).order_by(WatchHistory.watch_date)
        
        results = query.all()
        
        # 构建完整的日期序列（包括没有数据的日期）
        stats = {}
        for i in range(days):
            d = start_date + timedelta(days=i)
            stats[d.isoformat()] = 0
        
        for row in results:
            stats[row.watch_date.isoformat()] = row.total_duration or 0
        
        # 转换为有序列表
        return [
            {'date': d, 'duration': stats[d]}
            for d in sorted(stats.keys())
        ]
    
    @staticmethod
    def get_channel_ranking(days=7, limit=10):
        """
        获取频道观看排名
        返回按观看时长排序的频道列表
        """
        from sqlalchemy import func
        from datetime import timedelta
        from app.models.channel import Channel
        
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)
        
        query = db.session.query(
            WatchHistory.channel_id,
            Channel.name.label('channel_name'),
            func.sum(WatchHistory.duration).label('total_duration'),
            func.count(WatchHistory.id).label('watch_count')
        ).join(
            Channel, WatchHistory.channel_id == Channel.id
        ).filter(
            WatchHistory.watch_date >= start_date,
            WatchHistory.watch_date <= end_date,
            WatchHistory.duration > 0
        ).group_by(
            WatchHistory.channel_id, Channel.name
        ).order_by(
            func.sum(WatchHistory.duration).desc()
        ).limit(limit)
        
        results = query.all()
        
        return [
            {
                'channel_id': row.channel_id,
                'channel_name': row.channel_name,
                'total_duration': row.total_duration or 0,
                'watch_count': row.watch_count or 0
            }
            for row in results
        ]

