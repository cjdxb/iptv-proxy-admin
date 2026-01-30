# -*- coding: utf-8 -*-
"""
统一的时间处理工具
所有时间统一使用 UTC 时间存储和传输
"""

from datetime import datetime, timezone


def utcnow():
    """
    获取当前 UTC 时间（带时区信息）

    返回:
        datetime: 带有 UTC 时区信息的 datetime 对象

    注意:
        - 推荐使用此函数替代 datetime.now() 或 datetime.utcnow()
        - datetime.utcnow() 返回的是 naive datetime（无时区信息）
        - 本函数返回 aware datetime（有时区信息），更加明确
    """
    return datetime.now(timezone.utc)


def to_utc_naive():
    """
    获取当前 UTC 时间（无时区信息）
    用于兼容数据库存储（SQLAlchemy DateTime 默认存储 naive datetime）

    返回:
        datetime: 不带时区信息的 UTC datetime 对象
    """
    return datetime.utcnow()


def to_iso8601_utc(dt):
    """
    将 datetime 对象转换为 ISO 8601 格式字符串（UTC 时区）

    参数:
        dt (datetime): datetime 对象（可以是 naive 或 aware）

    返回:
        str: ISO 8601 格式的时间字符串，末尾带 'Z' 表示 UTC 时区
             格式: 2024-01-30T12:34:56Z
        None: 如果 dt 为 None

    示例:
        >>> dt = datetime(2024, 1, 30, 12, 34, 56)
        >>> to_iso8601_utc(dt)
        '2024-01-30T12:34:56Z'
    """
    if dt is None:
        return None

    # 如果是 aware datetime，先转换为 UTC
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)

    # 格式化为 ISO 8601，添加 Z 后缀表示 UTC
    # 使用 timespec='seconds' 精确到秒（默认是微秒）
    return dt.replace(tzinfo=None).isoformat(timespec='seconds') + 'Z'


def to_iso8601_date(d):
    """
    将 date 对象转换为 ISO 8601 格式字符串

    参数:
        d (date): date 对象

    返回:
        str: ISO 8601 格式的日期字符串
             格式: 2024-01-30
        None: 如果 d 为 None
    """
    if d is None:
        return None
    return d.isoformat()


def format_duration(seconds):
    """
    将秒数格式化为易读的时长字符串

    参数:
        seconds (int): 秒数

    返回:
        str: 格式化后的时长字符串

    示例:
        >>> format_duration(45)
        '45秒'
        >>> format_duration(150)
        '2分30秒'
        >>> format_duration(3665)
        '1小时1分5秒'
    """
    if seconds is None or seconds < 0:
        return '0秒'

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    parts = []
    if hours > 0:
        parts.append(f'{hours}小时')
    if minutes > 0:
        parts.append(f'{minutes}分')
    if secs > 0 or not parts:  # 如果没有小时和分钟，至少显示秒
        parts.append(f'{secs}秒')

    return ''.join(parts)


# 为了兼容性，提供别名
def now_utc():
    """获取当前 UTC 时间（别名）"""
    return to_utc_naive()


def serialize_datetime(dt):
    """序列化 datetime 为 ISO 8601 字符串（别名）"""
    return to_iso8601_utc(dt)
