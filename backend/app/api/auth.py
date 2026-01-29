# -*- coding: utf-8 -*-
"""
用户认证 API
"""

from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, current_user
from app import db
from app.models.user import User
from app.utils.auth import login_required

bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': '请提供登录信息'}), 400
    
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400
    
    user = User.query.filter_by(username=username).first()
    
    if not user or not user.check_password(password):
        return jsonify({'error': '用户名或密码错误'}), 401
    
    # 使用 Flask-Login 登录用户（设置 session cookie）
    login_user(user, remember=True)
    
    return jsonify({
        'message': '登录成功',
        'user': user.to_dict()
    })


@bp.route('/logout', methods=['POST'])
def logout():
    """用户登出"""
    logout_user()
    return jsonify({'message': '登出成功'})


@bp.route('/me', methods=['GET'])
@login_required
def get_current_user():
    """获取当前用户信息"""
    return jsonify(current_user.to_dict())


@bp.route('/reset-token', methods=['POST'])
@login_required
def reset_token():
    """重置订阅 Token"""
    new_token = current_user.generate_token()
    db.session.commit()
    
    return jsonify({
        'message': 'Token 已重置',
        'token': new_token
    })


@bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """修改密码"""
    data = request.get_json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not old_password or not new_password:
        return jsonify({'error': '请提供原密码和新密码'}), 400
    
    if not current_user.check_password(old_password):
        return jsonify({'error': '原密码错误'}), 401
    
    if len(new_password) < 6:
        return jsonify({'error': '新密码长度不能少于6位'}), 400
    
    current_user.set_password(new_password)
    db.session.commit()
    
    return jsonify({'message': '密码修改成功'})


@bp.route('/change-username', methods=['POST'])
@login_required
def change_username():
    """修改用户名"""
    data = request.get_json()
    new_username = data.get('username')
    
    if not new_username:
        return jsonify({'error': '用户名不能为空'}), 400
    
    if len(new_username) < 3:
        return jsonify({'error': '用户名长度不能少于3位'}), 400
    
    if new_username == current_user.username:
        return jsonify({'message': '用户名未变更'})
    
    # 检查用户名是否已存在
    existing_user = User.query.filter_by(username=new_username).first()
    if existing_user:
        return jsonify({'error': '用户名已存在'}), 400
    
    current_user.username = new_username
    db.session.commit()
    
    return jsonify({
        'message': '用户名修改成功',
        'username': new_username
    })
