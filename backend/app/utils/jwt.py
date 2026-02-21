# -*- coding: utf-8 -*-
"""
JWT 工具模块
"""

from datetime import timedelta

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from app.config import config
from app.utils.datetime_utils import utcnow


class JwtError(Exception):
    """JWT 校验异常"""

    def __init__(self, message='无效的 Token', error_type='invalid'):
        super().__init__(message)
        self.message = message
        self.error_type = error_type


def _jwt_config():
    jwt_config = config.get('jwt', {})
    secret = jwt_config.get('secret_key') or 'default-jwt-secret-key'
    algorithm = jwt_config.get('algorithm', 'HS256')
    access_hours = max(1, int(jwt_config.get('access_expires_hours', 24)))
    refresh_days = max(1, int(jwt_config.get('refresh_expires_days', 7)))
    return secret, algorithm, access_hours, refresh_days


def get_access_token_expires_seconds():
    """获取 Access Token 过期秒数"""
    _, _, access_hours, _ = _jwt_config()
    return int(timedelta(hours=access_hours).total_seconds())


def get_refresh_token_expires_seconds():
    """获取 Refresh Token 过期秒数"""
    _, _, _, refresh_days = _jwt_config()
    return int(timedelta(days=refresh_days).total_seconds())


def get_refresh_token_expires_delta():
    """获取 Refresh Token 过期时间间隔"""
    _, _, _, refresh_days = _jwt_config()
    return timedelta(days=refresh_days)


def create_access_token(user_id):
    """生成 Access Token"""
    secret, algorithm, access_hours, _ = _jwt_config()
    now = utcnow()
    payload = {
        'sub': str(user_id),
        'type': 'access',
        'iat': now,
        'exp': now + timedelta(hours=access_hours)
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_access_token(token):
    """解码并校验 Access Token"""
    secret, algorithm, _, _ = _jwt_config()
    try:
        payload = jwt.decode(token, secret, algorithms=[algorithm])
    except ExpiredSignatureError as e:
        raise JwtError(message='登录已过期，请重新登录', error_type='expired') from e
    except InvalidTokenError as e:
        raise JwtError(message='登录凭证无效，请重新登录', error_type='invalid') from e

    if payload.get('type') != 'access':
        raise JwtError(message='登录凭证类型错误', error_type='invalid')

    return payload
