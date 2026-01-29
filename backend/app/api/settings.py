# -*- coding: utf-8 -*-
"""
系统设置 API
"""

import requests
from flask import Blueprint, request, jsonify
from loguru import logger
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


@bp.route('/reload', methods=['POST'])
@login_required
def reload_settings():
    """重新加载运行时配置"""
    try:
        from app.config import load_runtime_config_from_db
        success = load_runtime_config_from_db()

        if success:
            return jsonify({'message': '配置已重新加载'})
        else:
            return jsonify({'error': '配置重载失败'}), 500
    except Exception as e:
        logger.error(f"重载配置失败: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/test-udpxy', methods=['POST'])
@login_required
def test_udpxy():
    """测试 UDPxy 服务器连接性"""
    data = request.get_json()
    udpxy_url = data.get('url')

    if not udpxy_url:
        return jsonify({'error': '请提供 UDPxy 服务器地址'}), 400

    try:
        # 移除末尾的斜杠
        udpxy_url = udpxy_url.rstrip('/')

        status_url = f"{udpxy_url}/status"

        # 尝试访问 UDPxy 状态页面（通常在根路径）
        response = requests.get(status_url, timeout=5)

        if response.status_code == 200:
            logger.info(f"UDPxy 服务器连接成功: {status_url}")
            return jsonify({
                'success': True,
                'message': 'UDPxy 服务器连接成功',
                'status_code': response.status_code
            })
        else:
            logger.warning(f"UDPxy 服务器返回非 200 状态码: {response.status_code}")
            return jsonify({
                'success': False,
                'message': f'服务器返回状态码: {response.status_code}',
                'status_code': response.status_code
            })

    except requests.exceptions.Timeout:
        logger.error(f"UDPxy 服务器连接超时: {udpxy_url}")
        return jsonify({
            'success': False,
            'message': '连接超时，请检查服务器地址或网络连接'
        })

    except requests.exceptions.ConnectionError:
        logger.error(f"UDPxy 服务器连接失败: {udpxy_url}")
        return jsonify({
            'success': False,
            'message': '无法连接到服务器，请检查地址是否正确'
        })

    except Exception as e:
        logger.error(f"UDPxy 连接测试失败: {e}")
        return jsonify({
            'success': False,
            'message': f'连接测试失败: {str(e)}'
        })
