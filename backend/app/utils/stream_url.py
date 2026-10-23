# -*- coding: utf-8 -*-
"""订阅和服务端转发共用的播放地址转换。"""

from app.config import get_udpxy_enabled, get_udpxy_url as get_udpxy_url_config


def get_udpxy_url(original_url):
    """启用 UDPxy 时转换 RTP/UDP 地址，否则返回 None。"""
    if not original_url.lower().startswith(('rtp://', 'udp://')):
        return None
    if not get_udpxy_enabled():
        return None

    udpxy_base = get_udpxy_url_config().rstrip('/')
    addr = original_url.split('://', 1)[1].removeprefix('@')
    return f"{udpxy_base}/udp/{addr}"
