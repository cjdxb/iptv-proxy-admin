# -*- coding: utf-8 -*-
"""
分组管理 API
"""

from flask import Blueprint, request, jsonify
from app import db
from app.models.channel import ChannelGroup
from app.utils.auth import login_required

bp = Blueprint('groups', __name__, url_prefix='/api/groups')


@bp.route('', methods=['GET'])
@login_required
def get_groups():
    """获取分组列表"""
    include_channels = request.args.get('include_channels', 'false').lower() == 'true'
    groups = ChannelGroup.query.order_by(ChannelGroup.sort_order, ChannelGroup.id).all()
    return jsonify([g.to_dict(include_channels=include_channels) for g in groups])


@bp.route('/<int:group_id>', methods=['GET'])
@login_required
def get_group(group_id):
    """获取单个分组"""
    group = ChannelGroup.query.get_or_404(group_id)
    include_channels = request.args.get('include_channels', 'false').lower() == 'true'
    return jsonify(group.to_dict(include_channels=include_channels))


@bp.route('', methods=['POST'])
@login_required
def create_group():
    """创建分组"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': '请提供分组信息'}), 400
    
    name = data.get('name')
    
    if not name:
        return jsonify({'error': '分组名称不能为空'}), 400
    
    group = ChannelGroup(
        name=name,
        sort_order=data.get('sort_order', 0)
    )
    
    db.session.add(group)
    db.session.commit()
    
    return jsonify({
        'message': '分组创建成功',
        'group': group.to_dict()
    }), 201


@bp.route('/<int:group_id>', methods=['PUT'])
@login_required
def update_group(group_id):
    """更新分组"""
    group = ChannelGroup.query.get_or_404(group_id)
    data = request.get_json()
    
    if not data:
        return jsonify({'error': '请提供更新信息'}), 400
    
    if 'name' in data:
        group.name = data['name']
    if 'sort_order' in data:
        group.sort_order = data['sort_order']
    
    db.session.commit()
    
    return jsonify({
        'message': '分组更新成功',
        'group': group.to_dict()
    })


@bp.route('/<int:group_id>', methods=['DELETE'])
@login_required
def delete_group(group_id):
    """删除分组"""
    group = ChannelGroup.query.get_or_404(group_id)
    
    # 检查是否有频道使用该分组
    channel_count = group.channels.count()
    if channel_count > 0:
        return jsonify({'error': f'无法删除：该分组下有 {channel_count} 个频道，请先移除或修改这些频道的分组'}), 400
    
    db.session.delete(group)
    db.session.commit()
    
    return jsonify({'message': '分组删除成功'})


@bp.route('/sort', methods=['POST'])
@login_required
def update_sort_order():
    """更新分组排序"""
    data = request.get_json()
    orders = data.get('orders', [])  # [{id: 1, sort_order: 0}, ...]
    
    if not orders:
        return jsonify({'error': '请提供排序信息'}), 400
    
    for item in orders:
        # 使用 SQLAlchemy 2.0 兼容的方式
        group = db.session.get(ChannelGroup, item['id'])
        if group:
            group.sort_order = item['sort_order']
    
    db.session.commit()
    
    return jsonify({'message': '排序更新成功'})


@bp.route('/empty', methods=['DELETE'])
@login_required
def delete_empty_groups():
    """删除所有空分组"""
    # 查找所有没有频道的分组
    empty_groups = []
    all_groups = ChannelGroup.query.all()
    
    for group in all_groups:
        if group.channels.count() == 0:
            empty_groups.append(group)
    
    if not empty_groups:
        return jsonify({'message': '没有空分组需要删除', 'deleted': 0})
    
    deleted_count = len(empty_groups)
    for group in empty_groups:
        db.session.delete(group)
    
    db.session.commit()
    
    return jsonify({
        'message': f'成功删除 {deleted_count} 个空分组',
        'deleted': deleted_count
    })

