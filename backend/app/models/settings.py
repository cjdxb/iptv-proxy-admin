# -*- coding: utf-8 -*-
"""
系统设置模型
"""

from app import db


class Settings(db.Model):
    """系统设置表"""
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=True)
    
    # 预定义的设置键
    KEY_EPG_URL = 'epg_url'
    KEY_SERVER_NAME = 'server_name'
    KEY_HEALTH_CHECK_INTERVAL = 'health_check_interval'
    KEY_SITE_NAME = 'site_name'
    
    @classmethod
    def get(cls, key, default=None):
        """获取设置值"""
        setting = cls.query.filter_by(key=key).first()
        return setting.value if setting else default
    
    @classmethod
    def set(cls, key, value):
        """设置值"""
        setting = cls.query.filter_by(key=key).first()
        if setting:
            setting.value = value
        else:
            setting = cls(key=key, value=value)
            db.session.add(setting)
        db.session.commit()
        return setting
    
    @classmethod
    def get_all(cls):
        """获取所有设置"""
        settings = cls.query.all()
        return {s.key: s.value for s in settings}
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value
        }
