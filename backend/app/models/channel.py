# -*- coding: utf-8 -*-
"""
频道和分组模型
"""

import re
from datetime import datetime
from app import db
from app.utils.datetime_utils import to_iso8601_utc


class ChannelGroup(db.Model):
    """频道分组表"""
    __tablename__ = 'channel_groups'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关联频道（不级联删除）
    channels = db.relationship('Channel', backref='group', lazy='dynamic')
    
    def to_dict(self, include_channels=False):
        """转换为字典"""
        data = {
            'id': self.id,
            'name': self.name,
            'sort_order': self.sort_order,
            'channel_count': self.channels.count(),
            'created_at': to_iso8601_utc(self.created_at)  # UTC 时间 + Z 后缀
        }
        if include_channels:
            data['channels'] = [ch.to_dict() for ch in self.channels.order_by(Channel.sort_order).all()]
        return data


class Channel(db.Model):
    """频道表"""
    __tablename__ = 'channels'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    logo = db.Column(db.String(500), nullable=True)
    group_id = db.Column(db.Integer, db.ForeignKey('channel_groups.id'), nullable=True)
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    protocol = db.Column(db.String(20), default='http')  # http, https, rtp, udp
    tvg_id = db.Column(db.String(100), nullable=True)  # EPG tvg-id
    
    # 健康检测相关
    last_check = db.Column(db.DateTime, nullable=True)
    is_healthy = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def detect_protocol(self):
        """自动检测协议类型"""
        url_lower = self.url.lower()
        if url_lower.startswith('rtp://'):
            self.protocol = 'rtp'
        elif url_lower.startswith('udp://'):
            self.protocol = 'udp'
        elif url_lower.startswith('https://'):
            self.protocol = 'https'
        else:
            self.protocol = 'http'
    
    def is_multicast(self):
        """判断是否为组播源"""
        return self.protocol in ('rtp', 'udp')
    
    @staticmethod
    def validate_url(url):
        """
        验证 IPTV 源 URL 的合法性
        返回 (is_valid, error_message)
        """
        if not url or not isinstance(url, str):
            return False, 'URL 不能为空'
        
        url = url.strip()
        if not url:
            return False, 'URL 不能为空'
        
        # 支持的协议
        valid_protocols = ('http://', 'https://', 'rtp://', 'udp://')
        
        if not url.lower().startswith(valid_protocols):
            return False, f'不支持的协议，仅支持 http、https、rtp、udp'
        
        # HTTP/HTTPS URL 格式验证
        if url.lower().startswith(('http://', 'https://')):
            # 基本的 URL 格式检查
            http_pattern = r'^https?://[a-zA-Z0-9][-a-zA-Z0-9]*(\.[a-zA-Z0-9][-a-zA-Z0-9]*)*'
            if not re.match(http_pattern, url, re.IGNORECASE):
                # 也支持 IP 地址格式
                ip_pattern = r'^https?://(\d{1,3}\.){3}\d{1,3}'
                if not re.match(ip_pattern, url):
                    return False, 'HTTP/HTTPS URL 格式不正确'
        
        # RTP/UDP URL 格式验证 (格式: rtp://239.0.0.1:5000 或 udp://@239.0.0.1:5000)
        elif url.lower().startswith(('rtp://', 'udp://')):
            # 提取地址部分
            addr_part = url.split('://', 1)[1]
            if addr_part.startswith('@'):
                addr_part = addr_part[1:]
            
            # 验证组播地址格式 (IP:端口)
            multicast_pattern = r'^(\d{1,3}\.){3}\d{1,3}(:\d+)?$'
            if not re.match(multicast_pattern, addr_part):
                return False, 'RTP/UDP 地址格式不正确，应为 IP:端口 格式'
            
            # 验证 IP 地址各段范围
            ip_part = addr_part.split(':')[0]
            octets = ip_part.split('.')
            for octet in octets:
                if not 0 <= int(octet) <= 255:
                    return False, 'IP 地址格式不正确'
        
        return True, None
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'url': self.url,
            'logo': self.logo,
            'tvg_id': self.tvg_id,
            'group_id': self.group_id,
            'group_name': self.group.name if self.group else None,
            'sort_order': self.sort_order,
            'is_active': self.is_active,
            'protocol': self.protocol,
            'last_check': to_iso8601_utc(self.last_check),    # UTC 时间 + Z 后缀
            'is_healthy': self.is_healthy,
            'created_at': to_iso8601_utc(self.created_at),    # UTC 时间 + Z 后缀
            'updated_at': to_iso8601_utc(self.updated_at)     # UTC 时间 + Z 后缀
        }
