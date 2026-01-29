# -*- coding: utf-8 -*-
"""
认证工具模块
"""

from functools import wraps
from flask import jsonify
from flask_login import current_user


def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': '请先登录'}), 401
        return f(*args, **kwargs)
    return decorated_function
