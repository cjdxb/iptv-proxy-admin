# -*- coding: utf-8 -*-
"""
系统设置 API
"""

from flask import Blueprint, request, jsonify
from app.models.settings import Settings
from app.utils.auth import login_required

bp = Blueprint('settings', __name__, url_prefix='/api/settings')


@bp.route('', methods=['GET'])
@login_required
def get_settings():
    """获取所有设置"""
    settings = Settings.get_all()
    return jsonify(settings)


@bp.route('/<key>', methods=['GET'])
@login_required
def get_setting(key):
    """获取单个设置"""
    value = Settings.get(key)
    return jsonify({
        'key': key,
        'value': value
    })


@bp.route('', methods=['POST'])
@login_required
def update_settings():
    """批量更新设置"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': '请提供设置信息'}), 400
    
    for key, value in data.items():
        Settings.set(key, value)
    
    return jsonify({
        'message': '设置更新成功',
        'settings': Settings.get_all()
    })


@bp.route('/<key>', methods=['PUT'])
@login_required
def update_setting(key):
    """更新单个设置"""
    data = request.get_json()
    
    if data is None:
        return jsonify({'error': '请提供设置值'}), 400
    
    value = data.get('value')
    Settings.set(key, value)
    
    return jsonify({
        'message': '设置更新成功',
        'key': key,
        'value': value
    })
