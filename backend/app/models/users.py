# -*- coding: utf-8 -*-
"""
用户模型
"""

import secrets
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.utils.datetime_utils import to_iso8601_utc, to_utc_naive


class Users(db.Model):
    """用户表"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    must_change_password = db.Column(db.Boolean, nullable=False, default=False)
    token = db.Column(db.String(64), unique=True, nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=to_utc_naive)

    watch_history = db.relationship(
        'WatchHistory',
        primaryjoin='Users.id == WatchHistory.user_id',
        foreign_keys='WatchHistory.user_id',
        back_populates='user',
        lazy='dynamic'
    )
    
    def set_password(self, password):
        """设置密码"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)
    
    def generate_token(self):
        """生成新的订阅 Token"""
        self.token = secrets.token_hex(32)
        return self.token
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'username': self.username,
            'must_change_password': bool(self.must_change_password),
            'token': self.token,
            'created_at': to_iso8601_utc(self.created_at)  # UTC 时间 + Z 后缀
        }
