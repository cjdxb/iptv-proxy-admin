# -*- coding: utf-8 -*-
"""
频道管理 API
"""

from flask import Blueprint, request, jsonify
from app import db
from app.models.channel import Channel, ChannelGroup
from app.utils.auth import login_required

bp = Blueprint('channels', __name__, url_prefix='/api/channels')


@bp.route('', methods=['GET'])
@login_required
def get_channels():
    """获取频道列表"""
    # 查询参数
    group_id = request.args.get('group_id', type=int)
    is_active = request.args.get('is_active', type=lambda x: x.lower() == 'true')
    protocol = request.args.get('protocol', '')
    is_healthy = request.args.get('is_healthy', type=lambda x: x.lower() == 'true')
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    query = Channel.query

    if group_id:
        query = query.filter_by(group_id=group_id)

    if is_active is not None:
        query = query.filter_by(is_active=is_active)

    if protocol:
        query = query.filter_by(protocol=protocol.lower())

    if is_healthy is not None:
        query = query.filter_by(is_healthy=is_healthy)

    if search:
        query = query.filter(Channel.name.contains(search))

    # 排序
    query = query.order_by(Channel.sort_order, Channel.id)

    # 分页
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'items': [ch.to_dict() for ch in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    })


@bp.route('/<int:channel_id>', methods=['GET'])
@login_required
def get_channel(channel_id):
    """获取单个频道"""
    channel = Channel.query.get_or_404(channel_id)
    return jsonify(channel.to_dict())


@bp.route('', methods=['POST'])
@login_required
def create_channel():
    """创建频道"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': '请提供频道信息'}), 400
    
    name = data.get('name')
    url = data.get('url')
    
    if not name or not url:
        return jsonify({'error': '频道名称和地址不能为空'}), 400
    
    # 验证 URL 合法性
    is_valid, error_msg = Channel.validate_url(url)
    if not is_valid:
        return jsonify({'error': error_msg}), 400
    
    channel = Channel(
        name=name,
        url=url,
        logo=data.get('logo'),
        tvg_id=data.get('tvg_id'),
        group_id=data.get('group_id'),
        sort_order=data.get('sort_order', 0),
        is_active=data.get('is_active', True)
    )
    channel.detect_protocol()
    
    db.session.add(channel)
    db.session.commit()
    
    return jsonify({
        'message': '频道创建成功',
        'channel': channel.to_dict()
    }), 201


@bp.route('/<int:channel_id>', methods=['PUT'])
@login_required
def update_channel(channel_id):
    """更新频道"""
    channel = Channel.query.get_or_404(channel_id)
    data = request.get_json()
    
    if not data:
        return jsonify({'error': '请提供更新信息'}), 400
    
    if 'name' in data:
        channel.name = data['name']
    if 'url' in data:
        # 验证 URL 合法性
        is_valid, error_msg = Channel.validate_url(data['url'])
        if not is_valid:
            return jsonify({'error': error_msg}), 400
        channel.url = data['url']
        channel.detect_protocol()
    if 'logo' in data:
        channel.logo = data['logo']
    if 'tvg_id' in data:
        channel.tvg_id = data['tvg_id']
    if 'group_id' in data:
        channel.group_id = data['group_id']
    if 'sort_order' in data:
        channel.sort_order = data['sort_order']
    if 'is_active' in data:
        channel.is_active = data['is_active']
    
    db.session.commit()
    
    return jsonify({
        'message': '频道更新成功',
        'channel': channel.to_dict()
    })


@bp.route('/<int:channel_id>', methods=['DELETE'])
@login_required
def delete_channel(channel_id):
    """删除频道"""
    channel = Channel.query.get_or_404(channel_id)
    
    db.session.delete(channel)
    db.session.commit()
    
    return jsonify({'message': '频道删除成功'})


@bp.route('/batch-delete', methods=['POST'])
@login_required
def batch_delete_channels():
    """批量删除频道"""
    data = request.get_json()
    ids = data.get('ids', [])
    
    if not ids:
        return jsonify({'error': '请提供要删除的频道 ID'}), 400
    
    Channel.query.filter(Channel.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()
    
    return jsonify({'message': f'已删除 {len(ids)} 个频道'})


@bp.route('/sort', methods=['POST'])
@login_required
def update_sort_order():
    """更新频道排序"""
    data = request.get_json()
    orders = data.get('orders', [])  # [{id: 1, sort_order: 0}, ...]
    
    if not orders:
        return jsonify({'error': '请提供排序信息'}), 400
    
    for item in orders:
        # 使用 SQLAlchemy 2.0 兼容的方式
        channel = db.session.get(Channel, item['id'])
        if channel:
            channel.sort_order = item['sort_order']
    
    db.session.commit()
    
    return jsonify({'message': '排序更新成功'})
