# -*- coding: utf-8 -*-
"""
频道导入导出服务
"""

import re
import requests
from flask import Blueprint, request, jsonify, Response
from loguru import logger
from app import db
from app.models.channel import Channel, ChannelGroup
from app.utils.auth import login_required

bp = Blueprint('import_export', __name__, url_prefix='/api/import-export')


def parse_m3u(content):
    """解析 M3U 格式内容"""
    channels = []
    lines = content.strip().split('\n')
    
    current_channel = None
    
    for line in lines:
        line = line.strip()
        
        if line.startswith('#EXTM3U'):
            continue
        
        if line.startswith('#EXTINF:'):
            # 解析频道信息
            # 格式: #EXTINF:-1 tvg-name="CCTV-1" tvg-logo="http://xxx" group-title="央视",CCTV-1
            current_channel = {
                'name': '',
                'url': '',
                'logo': '',
                'tvg_id': '',
                'group_name': ''
            }
            
            # 提取显示名称（逗号后面的部分）
            if ',' in line:
                current_channel['name'] = line.split(',', 1)[1].strip()
            
            # 提取 tvg-id
            tvg_id_match = re.search(r'tvg-id="([^"]*)"', line)
            if tvg_id_match:
                current_channel['tvg_id'] = tvg_id_match.group(1)
            
            # 提取 tvg-name
            tvg_name_match = re.search(r'tvg-name="([^"]*)"', line)
            if tvg_name_match:
                current_channel['name'] = tvg_name_match.group(1) or current_channel['name']
            
            # 提取 tvg-logo
            logo_match = re.search(r'tvg-logo="([^"]*)"', line)
            if logo_match:
                current_channel['logo'] = logo_match.group(1)
            
            # 提取 group-title
            group_match = re.search(r'group-title="([^"]*)"', line)
            if group_match:
                current_channel['group_name'] = group_match.group(1)
        
        elif line and not line.startswith('#') and current_channel:
            # URL 行
            current_channel['url'] = line
            if current_channel['name'] and current_channel['url']:
                channels.append(current_channel)
            current_channel = None
    
    return channels


def parse_txt(content):
    """解析 TXT 格式内容"""
    channels = []
    lines = content.strip().split('\n')
    
    current_group = ''
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 检查是否是分组标记
        if ',#genre#' in line:
            current_group = line.replace(',#genre#', '').strip()
            continue
        
        # 解析频道行
        # 格式: 频道名,URL
        if ',' in line:
            parts = line.split(',', 1)
            if len(parts) == 2:
                name, url = parts
                if url.strip().startswith('http') or url.strip().startswith('rtp') or url.strip().startswith('udp'):
                    channels.append({
                        'name': name.strip(),
                        'url': url.strip(),
                        'logo': '',
                        'group_name': current_group
                    })
    
    return channels


def get_or_create_group(group_name):
    """获取或创建分组"""
    if not group_name:
        return None
    
    group = ChannelGroup.query.filter_by(name=group_name).first()
    if not group:
        group = ChannelGroup(name=group_name)
        db.session.add(group)
        db.session.flush()
    return group


def save_imported_channels(channels, overwrite, auto_create_group, include_regex=None, exclude_regex=None):
    """保存导入的频道"""
    if overwrite:
        # 清空现有频道
        Channel.query.delete()
        ChannelGroup.query.delete()
        db.session.commit()
    
    imported_count = 0
    skipped_groups = set()
    skipped_invalid_urls = 0
    skipped_filtered = 0
    
    # 预编译正则
    inc_pattern = None
    if include_regex:
        try:
            inc_pattern = re.compile(include_regex)
        except re.error:
            pass
            
    exc_pattern = None
    if exclude_regex:
        try:
            exc_pattern = re.compile(exclude_regex)
        except re.error:
            pass
    
    for ch_data in channels:
        # 关键词过滤
        if inc_pattern and not inc_pattern.search(ch_data['name']):
            skipped_filtered += 1
            continue
            
        if exc_pattern and exc_pattern.search(ch_data['name']):
            skipped_filtered += 1
            continue
            
        # 验证 URL 合法性
        is_valid, _ = Channel.validate_url(ch_data['url'])
        if not is_valid:
            skipped_invalid_urls += 1
            continue
        
        # 检查是否已存在同名同URL的频道
        existing = Channel.query.filter_by(name=ch_data['name'], url=ch_data['url']).first()
        if existing and not overwrite:
            continue
        
        # 获取或创建分组
        group = None
        group_name = ch_data.get('group_name', '')
        if group_name:
            if auto_create_group:
                group = get_or_create_group(group_name)
            else:
                # 不自动创建分组，只查找现有分组
                group = ChannelGroup.query.filter_by(name=group_name).first()
                if not group:
                    skipped_groups.add(group_name)
        
        channel = Channel(
            name=ch_data['name'],
            url=ch_data['url'],
            logo=ch_data.get('logo', ''),
            tvg_id=ch_data.get('tvg_id', ''),
            group_id=group.id if group else None,
            sort_order=imported_count
        )
        channel.detect_protocol()
        
        db.session.add(channel)
        imported_count += 1
    
    db.session.commit()
    
    result = {
        'message': f'成功导入 {imported_count} 个频道',
        'imported': imported_count,
        'total_parsed': len(channels)
    }
    
    msg_parts = []
    if skipped_groups:
        msg_parts.append(f'跳过 {len(skipped_groups)} 个未知分组')
    
    if skipped_invalid_urls > 0:
        msg_parts.append(f'跳过 {skipped_invalid_urls} 个无效URL')
        
    if skipped_filtered > 0:
        msg_parts.append(f'过滤 {skipped_filtered} 个频道')
        
    if msg_parts:
        result['message'] += '，' + '，'.join(msg_parts)
            
    return result


@bp.route('/import', methods=['POST'])
@login_required
def import_channels():
    """导入频道"""
    # 检查是否有文件上传
    if 'file' in request.files:
        file = request.files['file']
        content = file.read().decode('utf-8')
        filename = file.filename.lower()
        data = request.form
    else:
        # 从请求体获取内容
        data = request.get_json()
        if not data:
            return jsonify({'error': '请提供导入内容'}), 400
        content = data.get('content', '')
        filename = data.get('format', 'm3u')
    
    if not content:
        return jsonify({'error': '导入内容为空'}), 400
    
    # 根据格式解析
    if 'm3u' in filename or filename == 'm3u':
        channels = parse_m3u(content)
    else:
        channels = parse_txt(content)
    
    if not channels:
        return jsonify({'error': '未解析到有效频道'}), 400
    
    # 导入选项
    overwrite = data.get('overwrite', False)
    if isinstance(overwrite, str):
        overwrite = overwrite.lower() == 'true'
        
    auto_create_group = data.get('auto_create_group', True)  # 默认自动创建分组
    if isinstance(auto_create_group, str):
        auto_create_group = auto_create_group.lower() == 'true'
        
    include_regex = data.get('include_regex', '').strip()
    exclude_regex = data.get('exclude_regex', '').strip()
    
    result = save_imported_channels(channels, overwrite, auto_create_group, include_regex, exclude_regex)
    
    return jsonify(result)


@bp.route('/import-url', methods=['POST'])
@login_required
def import_from_url():
    """从 URL 导入频道"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': '请提供导入参数'}), 400
    
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': '请提供有效的 URL'}), 400
    
    # 验证 URL 格式
    if not url.startswith(('http://', 'https://')):
        return jsonify({'error': 'URL 必须以 http:// 或 https:// 开头'}), 400
    
    try:
        # 获取远程文件内容
        logger.info(f"正在从 URL 获取频道列表: {url}")
        response = requests.get(url, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
        
        # 尝试检测编码
        content = response.content.decode('utf-8', errors='ignore')
        
        if not content.strip():
            return jsonify({'error': '获取的文件内容为空'}), 400
        
    except requests.exceptions.Timeout:
        return jsonify({'error': '请求超时，请检查 URL 是否可访问'}), 400
    except requests.exceptions.RequestException as e:
        logger.error(f"获取 URL 失败: {e}")
        return jsonify({'error': f'无法获取 URL: {str(e)}'}), 400
    
    # 自动检测格式
    format_type = data.get('format', 'auto')
    if format_type == 'auto':
        # 根据 URL 后缀或内容判断格式
        if url.lower().endswith('.m3u') or url.lower().endswith('.m3u8') or content.strip().startswith('#EXTM3U'):
            format_type = 'm3u'
        else:
            format_type = 'txt'
    
    # 解析内容
    if format_type == 'm3u':
        channels = parse_m3u(content)
    else:
        channels = parse_txt(content)
    
    if not channels:
        return jsonify({'error': '未解析到有效频道，请检查 URL 内容格式'}), 400
    
    logger.info(f"从 URL 解析到 {len(channels)} 个频道")
    
    # 导入选项
    overwrite = data.get('overwrite', False)
    auto_create_group = data.get('auto_create_group', True)
    include_regex = data.get('include_regex', '').strip()
    exclude_regex = data.get('exclude_regex', '').strip()
    
    result = save_imported_channels(channels, overwrite, auto_create_group, include_regex, exclude_regex)
    
    return jsonify(result)

@bp.route('/export', methods=['GET'])
@login_required
def export_channels():
    """导出频道"""
    format_type = request.args.get('format', 'm3u')
    
    lines = []
    
    if format_type == 'm3u':
        lines.append('#EXTM3U')
        
        # 按分组获取频道
        groups = ChannelGroup.query.order_by(ChannelGroup.sort_order).all()
        ungrouped = Channel.query.filter_by(group_id=None, is_active=True).order_by(Channel.sort_order).all()
        
        for group in groups:
            channels = Channel.query.filter_by(group_id=group.id, is_active=True).order_by(Channel.sort_order).all()
            for channel in channels:
                logo_part = f' tvg-logo="{channel.logo}"' if channel.logo else ''
                lines.append(f'#EXTINF:-1 tvg-name="{channel.name}"{logo_part} group-title="{group.name}",{channel.name}')
                lines.append(channel.url)
        
        for channel in ungrouped:
            logo_part = f' tvg-logo="{channel.logo}"' if channel.logo else ''
            lines.append(f'#EXTINF:-1 tvg-name="{channel.name}"{logo_part},{channel.name}')
            lines.append(channel.url)
        
        content = '\n'.join(lines)
        mimetype = 'audio/x-mpegurl'
        filename = 'channels.m3u'
    else:
        # TXT 格式
        groups = ChannelGroup.query.order_by(ChannelGroup.sort_order).all()
        ungrouped = Channel.query.filter_by(group_id=None, is_active=True).order_by(Channel.sort_order).all()
        
        for group in groups:
            channels = Channel.query.filter_by(group_id=group.id, is_active=True).order_by(Channel.sort_order).all()
            if channels:
                lines.append(f'{group.name},#genre#')
                for channel in channels:
                    lines.append(f'{channel.name},{channel.url}')
        
        if ungrouped:
            lines.append('未分组,#genre#')
            for channel in ungrouped:
                lines.append(f'{channel.name},{channel.url}')
        
        content = '\n'.join(lines)
        mimetype = 'text/plain; charset=utf-8'
        filename = 'channels.txt'
    
    return Response(
        content,
        mimetype=mimetype,
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
    )
