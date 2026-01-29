# -*- coding: utf-8 -*-
"""
用户模型
"""

import secrets
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db


class User(UserMixin, db.Model):
    """用户表"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
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
            'token': self.token,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
