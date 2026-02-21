# -*- coding: utf-8 -*-
"""
认证工具模块
"""

from functools import wraps
from flask import jsonify, request, g

from app import db
from app.models.users import Users
from app.utils.jwt import decode_access_token, JwtError

PASSWORD_CHANGE_ALLOWED_ENDPOINTS = {
    'auth.get_current_user',
    'auth.change_password'
}


def get_current_user():
    """获取当前请求中的已认证用户"""
    return getattr(g, 'current_user', None)


def _extract_bearer_token():
    """从 Authorization 头中提取 Bearer Token"""
    auth_header = request.headers.get('Authorization', '').strip()
    if not auth_header.startswith('Bearer '):
        return None

    token = auth_header[7:].strip()
    return token or None


def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = _extract_bearer_token()
        if not token:
            return jsonify({'error': '请先登录'}), 401

        try:
            payload = decode_access_token(token)
            user_id = int(payload.get('sub'))
        except JwtError as e:
            return jsonify({'error': e.message}), 401
        except (TypeError, ValueError):
            return jsonify({'error': '登录状态无效，请重新登录'}), 401

        user = db.session.get(Users, user_id)
        if not user:
            return jsonify({'error': '用户不存在，请重新登录'}), 401

        endpoint = request.endpoint or ''
        if user.must_change_password and endpoint not in PASSWORD_CHANGE_ALLOWED_ENDPOINTS:
            return jsonify({
                'error': '首次登录请先修改密码',
                'code': 'must_change_password'
            }), 403

        g.current_user = user
        return f(*args, **kwargs)

    return decorated_function
