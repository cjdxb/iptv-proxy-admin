# -*- coding: utf-8 -*-
"""
用户认证 API
"""

import hashlib
import secrets

from flask import Blueprint, request, jsonify
from app import db
from app.models.users import Users
from app.models.refresh_token import RefreshToken
from app.utils.auth import login_required, get_current_user as get_authenticated_user
from app.utils.datetime_utils import to_utc_naive
from app.utils.jwt import (
    create_access_token,
    get_access_token_expires_seconds,
    get_refresh_token_expires_seconds,
    get_refresh_token_expires_delta
)

bp = Blueprint('auth', __name__, url_prefix='/api/auth')


def _hash_refresh_token(refresh_token):
    """计算刷新令牌哈希值"""
    return hashlib.sha256(refresh_token.encode('utf-8')).hexdigest()


def _create_refresh_token_record(user_id, now=None):
    """创建刷新令牌记录"""
    now = now or to_utc_naive()
    refresh_token = secrets.token_urlsafe(48)
    token_hash = _hash_refresh_token(refresh_token)
    refresh_record = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=now + get_refresh_token_expires_delta()
    )
    return refresh_token, refresh_record


def _build_auth_response(user, access_token, refresh_token):
    """构造统一登录态响应"""
    return {
        'user': user.to_dict(),
        'token_type': 'Bearer',
        'access_token': access_token,
        'refresh_token': refresh_token,
        'expires_in': get_access_token_expires_seconds(),
        'refresh_expires_in': get_refresh_token_expires_seconds()
    }


@bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json(silent=True) or {}
    
    if not data:
        return jsonify({'error': '请提供登录信息'}), 400
    
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400
    
    user = Users.query.filter_by(username=username).first()
    
    if not user or not user.check_password(password):
        return jsonify({'error': '用户名或密码错误'}), 401

    # 使用初始默认凭据登录时，强制首登改密
    if user.username == 'admin' and password == 'admin123' and not user.must_change_password:
        user.must_change_password = True

    now = to_utc_naive()
    access_token = create_access_token(user.id)
    refresh_token, refresh_record = _create_refresh_token_record(user.id, now=now)

    db.session.add(refresh_record)
    db.session.commit()

    return jsonify({
        'message': '登录成功',
        **_build_auth_response(user, access_token, refresh_token)
    })


@bp.route('/logout', methods=['POST'])
def logout():
    """用户登出"""
    data = request.get_json(silent=True) or {}
    refresh_token = data.get('refresh_token')

    if refresh_token:
        token_hash = _hash_refresh_token(refresh_token)
        record = RefreshToken.query.filter_by(token_hash=token_hash).first()
        if record and record.revoked_at is None:
            record.revoked_at = to_utc_naive()
            db.session.commit()

    return jsonify({'message': '登出成功'})


@bp.route('/refresh', methods=['POST'])
def refresh():
    """刷新 Access Token"""
    data = request.get_json(silent=True) or {}
    refresh_token = data.get('refresh_token')

    if not refresh_token:
        return jsonify({'error': '缺少 refresh_token'}), 400

    token_hash = _hash_refresh_token(refresh_token)
    record = RefreshToken.query.filter_by(token_hash=token_hash).first()
    now = to_utc_naive()

    if not record or not record.is_active(now=now):
        return jsonify({'error': '刷新令牌无效或已过期，请重新登录'}), 401

    user = db.session.get(Users, record.user_id)
    if not user:
        record.revoked_at = now
        db.session.commit()
        return jsonify({'error': '用户不存在，请重新登录'}), 401

    # 刷新令牌轮换：旧令牌立即失效
    record.revoked_at = now
    new_refresh_token, new_refresh_record = _create_refresh_token_record(user.id, now=now)
    access_token = create_access_token(user.id)

    db.session.add(new_refresh_record)
    db.session.commit()

    return jsonify({
        'message': '刷新成功',
        **_build_auth_response(user, access_token, new_refresh_token)
    })


@bp.route('/me', methods=['GET'])
@login_required
def get_current_user():
    """获取当前用户信息"""
    user = get_authenticated_user()
    return jsonify(user.to_dict())


@bp.route('/reset-token', methods=['POST'])
@login_required
def reset_token():
    """重置订阅 Token"""
    user = get_authenticated_user()
    new_token = user.generate_token()
    db.session.commit()
    
    return jsonify({
        'message': 'Token 已重置',
        'token': new_token
    })


@bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """修改密码"""
    user = get_authenticated_user()
    data = request.get_json(silent=True) or {}
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not old_password or not new_password:
        return jsonify({'error': '请提供原密码和新密码'}), 400
    
    if not user.check_password(old_password):
        return jsonify({'error': '原密码错误'}), 401
    
    if len(new_password) < 6:
        return jsonify({'error': '新密码长度不能少于6位'}), 400
    
    user.set_password(new_password)
    user.must_change_password = False

    # 密码变更后，废弃当前用户的所有可用刷新令牌，并下发新的令牌对
    now = to_utc_naive()
    RefreshToken.query.filter_by(
        user_id=user.id,
        revoked_at=None
    ).filter(RefreshToken.expires_at > now).update(
        {'revoked_at': now},
        synchronize_session=False
    )

    access_token = create_access_token(user.id)
    refresh_token, refresh_record = _create_refresh_token_record(user.id, now=now)
    db.session.add(refresh_record)
    db.session.commit()

    return jsonify({
        'message': '密码修改成功',
        **_build_auth_response(user, access_token, refresh_token)
    })


@bp.route('/change-username', methods=['POST'])
@login_required
def change_username():
    """修改用户名"""
    user = get_authenticated_user()
    data = request.get_json(silent=True) or {}
    new_username = data.get('username')
    
    if not new_username:
        return jsonify({'error': '用户名不能为空'}), 400
    
    if len(new_username) < 3:
        return jsonify({'error': '用户名长度不能少于3位'}), 400
    
    if new_username == user.username:
        return jsonify({'message': '用户名未变更'})
    
    # 检查用户名是否已存在
    existing_user = Users.query.filter_by(username=new_username).first()
    if existing_user:
        return jsonify({'error': '用户名已存在'}), 400
    
    user.username = new_username
    db.session.commit()
    
    return jsonify({
        'message': '用户名修改成功',
        'username': new_username
    })
