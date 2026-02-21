# -*- coding: utf-8 -*-
"""
频道分组模型
"""

from app import db
from app.utils.datetime_utils import to_iso8601_utc, to_utc_naive


class ChannelGroup(db.Model):
    """频道分组表"""
    __tablename__ = 'channel_groups'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=to_utc_naive)

    channels = db.relationship(
        'Channel',
        primaryjoin='ChannelGroup.id == Channel.group_id',
        foreign_keys='Channel.group_id',
        back_populates='group',
        lazy='dynamic'
    )

    def to_dict(self, include_channels=False):
        """转换为字典"""
        data = {
            'id': self.id,
            'name': self.name,
            'sort_order': self.sort_order,
            'channel_count': self.channels.count(),
            'created_at': to_iso8601_utc(self.created_at)
        }
        if include_channels:
            from app.models.channel import Channel
            data['channels'] = [ch.to_dict() for ch in self.channels.order_by(Channel.sort_order).all()]
        return data
