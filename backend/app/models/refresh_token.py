# -*- coding: utf-8 -*-
"""
刷新令牌模型
"""

from app import db
from app.utils.datetime_utils import to_utc_naive


class RefreshToken(db.Model):
    """刷新令牌表（仅存储哈希值）"""
    __tablename__ = 'refresh_tokens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    token_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    revoked_at = db.Column(db.DateTime, nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=to_utc_naive, nullable=False)

    user = db.relationship(
        'Users',
        primaryjoin='RefreshToken.user_id == Users.id',
        foreign_keys=[user_id],
        backref=db.backref('refresh_tokens', lazy='dynamic')
    )

    def is_active(self, now=None):
        """判断刷新令牌是否仍可用"""
        now = now or to_utc_naive()
        return self.revoked_at is None and self.expires_at > now
