# -*- coding: utf-8 -*-
"""
频道健康检测服务
"""

import socket
import struct
import time
from datetime import timedelta
from sqlalchemy import case, or_, update
from sqlalchemy.exc import IntegrityError
from urllib3.exceptions import HTTPError as Urllib3HTTPError
import requests
from loguru import logger
from app.utils.datetime_utils import to_utc_naive

def _extract_rtp_udp_addr(url):
    """从 URL 中解析 RTP/UDP 地址。"""
    if not url:
        return ''

    if url.lower().startswith(('rtp://', 'udp://')):
        return url.split('://', 1)[1].removeprefix('@')
    return url


def _probe_udp_with_udpxy(addr, timeout, udpxy_url):
    """通过 UDPxy 拉流并读取少量数据验证可用性。"""
    if not addr:
        return False

    udpxy_base = (udpxy_url or '').rstrip('/')
    if not udpxy_base:
        return False

    stream_url = f"{udpxy_base}/udp/{addr}"
    response = None
    try:
        response = requests.get(stream_url, timeout=timeout, stream=True)
        if response.status_code not in (200, 206):
            return False
        chunk = response.raw.read1(1024, decode_content=True)
        return chunk is not None and len(chunk) > 0
    finally:
        if response is not None:
            response.close()


def _probe_udp_direct(addr, timeout, channel_name):
    """直接接收组播 UDP 数据验证可用性。"""
    if not addr:
        return False

    if ':' in addr:
        ip, port_text = addr.rsplit(':', 1)
        port = int(port_text)
    else:
        ip = addr
        port = 5000

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(timeout)
        sock.bind(('', port))
        mreq = struct.pack('4sl', socket.inet_aton(ip), socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        data, _ = sock.recvfrom(1024)
        return len(data) > 0
    except socket.timeout:
        return False
    except Exception as e:
        logger.debug(f"组播检测失败 ({channel_name}): {e}")
        return False
    finally:
        sock.close()


def _check_channel_once(channel_info, timeout, udpxy_enabled, udpxy_url):
    """执行单次检测，不包含重试逻辑。"""
    protocol = (channel_info.get('protocol') or '').lower()
    url = channel_info.get('url') or ''

    if protocol in ('http', 'https'):
        # 部分 IPTV 服务拒绝 HEAD；使用与播放器一致的 GET 并验证有数据。
        with requests.get(url, timeout=timeout, stream=True) as response:
            if response.status_code not in (200, 206):
                logger.debug(f"频道 {channel_info.get('id')} GET 检测失败: HTTP {response.status_code}")
                return False
            return bool(response.raw.read1(1024, decode_content=True))

    if protocol in ('rtp', 'udp'):
        addr = _extract_rtp_udp_addr(url)
        if udpxy_enabled:
            return _probe_udp_with_udpxy(addr, timeout, udpxy_url)
        return _probe_udp_direct(addr, timeout, channel_info.get('name'))

    return False


def _check_channel_with_retry(channel_info, timeout, max_retries, udpxy_enabled, udpxy_url):
    """检测单个频道健康状态，带重试。"""
    for attempt in range(max_retries + 1):
        try:
            is_healthy = _check_channel_once(channel_info, timeout, udpxy_enabled, udpxy_url)
        except (requests.exceptions.RequestException, Urllib3HTTPError) as e:
            logger.debug(f"频道 {channel_info.get('id')} 检测网络异常: {type(e).__name__}")
            is_healthy = False
        except Exception as e:
            if attempt == max_retries:
                logger.error(f"健康检测异常 - 频道 {channel_info.get('id')}: {e}")
            is_healthy = False

        if is_healthy:
            return True

        if attempt < max_retries:
            time.sleep(5)
            logger.debug(
                f"频道 {channel_info.get('name')} 检测失败，正在重试 ({attempt + 1}/{max_retries})..."
            )

    return False



class HealthCheckBusy(Exception):
    """另一个进程正在探测，或处于探测间隔中。"""


def _acquire_probe_slot(timeout, retries):
    """数据库租约让 Web 手动检测与 worker 跨进程串行，崩溃后自动过期。"""
    from app import db
    from app.models.settings import Settings

    key = '_health_probe_available_at'
    if Settings.get(key) is None:
        try:
            db.session.add(Settings(key=key, value=''))
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
    now = to_utc_naive()
    lease = (now + timedelta(seconds=(timeout * 2 + 5) * (retries + 1) + 60)).isoformat()
    result = db.session.execute(update(Settings).where(
        Settings.key == key, Settings.value <= now.isoformat()
    ).values(value=lease))
    db.session.commit()
    if not result.rowcount:
        raise HealthCheckBusy('正在检测或等待检测间隔，请稍后重试')
    return lease


def _release_probe_slot(lease):
    from app import db
    from app.models.settings import Settings
    from app.config import get_health_check_channel_delay

    available = to_utc_naive() + timedelta(seconds=get_health_check_channel_delay())
    db.session.execute(update(Settings).where(
        Settings.key == '_health_probe_available_at', Settings.value == lease
    ).values(value=available.isoformat()))
    db.session.commit()


def record_channel_status(channel_id, healthy, started_at, *, automatic=False,
                          playback=False, source_url=None):
    """条件更新：旧探测不能覆盖新播放结果；自动检测两轮失败才离线。"""
    from app import db
    from app.models.channel import Channel

    now = to_utc_naive()
    # 旧 MySQL DATETIME 只有秒精度；同秒内的成功优先于失败，避免丢失精度后误覆盖。
    fresh = (Channel.last_check <= started_at if healthy
             else Channel.last_check < started_at.replace(microsecond=0))
    conditions = [Channel.id == channel_id, or_(Channel.last_check.is_(None), fresh)]
    if source_url is not None:
        conditions.append(Channel.url == source_url)
    if not healthy and not playback:
        from app.models.active_connection import ActiveConnection
        # 播放状态按分钟节流，但新连接/心跳仍能挡住同时进行的旧探测失败。
        playing_since_probe = db.session.query(ActiveConnection.connection_id).filter(
            ActiveConnection.channel_id == channel_id,
            ActiveConnection.last_heartbeat >= started_at.replace(microsecond=0)
        ).exists()
        conditions.append(~playing_since_probe)
    values = {'last_check': now}
    if healthy:
        values.update(is_healthy=True, health_failure_count=0)
        if playback:
            # 多个分片/观看者共享节流：正常播放最多每分钟写一次状态。
            conditions.append(or_(Channel.is_healthy.is_(False),
                                  Channel.health_failure_count > 0,
                                  Channel.health_check_requested_at <= started_at,
                                  Channel.last_check.is_(None),
                                  Channel.last_check <= now - timedelta(seconds=60)))
    elif automatic:
        values.update(health_failure_count=Channel.health_failure_count + 1,
                      is_healthy=case((Channel.health_failure_count >= 1, False),
                                      else_=Channel.is_healthy))
    else:
        values.update(is_healthy=False, health_failure_count=Channel.health_failure_count + 1)
    # 播放结果也可完成待检测请求，避免长时间播放的频道一直挂在队列里。
    # 保留本次探测/播放读取开始之后才提交的新请求。
    values['health_check_requested_at'] = case(
        (Channel.health_check_requested_at <= started_at, None),
        else_=Channel.health_check_requested_at)
    try:
        result = db.session.execute(update(Channel).where(*conditions).values(**values))
        db.session.commit()
        return bool(result.rowcount)
    except Exception:
        db.session.rollback()
        raise


def record_playback_status(channel_id, healthy, started_at, source_url):
    """状态存储故障不能中断实际播放。"""
    try:
        record_channel_status(channel_id, healthy, started_at,
                              playback=True, source_url=source_url)
    except Exception as exc:
        logger.warning(f'保存频道 {channel_id} 播放状态失败: {type(exc).__name__}')


def check_channel_health(channel, max_retries=None, *, automatic=False):
    """单次串行探测并立即持久化，不持有长数据库事务。"""
    from app import db
    from app.models.channel import Channel
    from app.config import (get_health_check_timeout, get_health_check_max_retries,
                            get_udpxy_enabled, get_udpxy_url)

    channel_id = channel.id if isinstance(channel, Channel) else int(channel)
    channel_obj = db.session.get(Channel, channel_id)
    if channel_obj is None:
        raise ValueError('频道不存在')
    info = {key: getattr(channel_obj, key) for key in ('id', 'name', 'url', 'protocol')}
    timeout = min(60, max(1, int(get_health_check_timeout())))
    retries = min(5, max(0, int(get_health_check_max_retries()
                              if max_retries is None else max_retries)))
    udpxy_enabled, udpxy_url = get_udpxy_enabled(), get_udpxy_url()
    db.session.commit()
    lease = _acquire_probe_slot(timeout, retries)
    started_at = to_utc_naive()
    try:
        healthy = _check_channel_with_retry(info, timeout, retries, udpxy_enabled, udpxy_url)
        record_channel_status(channel_id, healthy, started_at,
                              automatic=automatic, source_url=info['url'])
        # 即使并发播放覆盖了探测结果，也向调用者返回当前的实际状态。
        db.session.expire_all()
        current = db.session.get(Channel, channel_id)
        return current.is_healthy if current else healthy
    finally:
        _release_probe_slot(lease)


def check_all_channels():
    """提交后台串行检测，重复点击不会重置已有请求。"""
    from app import db
    from app.models.channel import Channel

    db.session.execute(update(Channel).where(
        Channel.is_active.is_(True), Channel.health_check_requested_at.is_(None)
    ).values(health_check_requested_at=to_utc_naive()))
    db.session.commit()
    return {'total': Channel.query.filter_by(is_active=True).count(),
            'pending': Channel.query.filter(Channel.is_active.is_(True),
                                           Channel.health_check_requested_at.is_not(None)).count()}


def run_health_worker_cycle():
    """每次最多检测一个频道；周期调度只扫描到期项，不再整批拉流。"""
    from app import db
    from app.models.channel import Channel
    from app.models.active_connection import ActiveConnection
    from app.config import config, get_health_check_interval, get_active_heartbeat_timeout_seconds

    now = to_utc_naive()
    due = [Channel.health_check_requested_at.is_not(None)]
    if config.get('health_check', {}).get('enabled', True):
        due.append(or_(Channel.last_check.is_(None),
                       Channel.last_check <= now - timedelta(seconds=get_health_check_interval())))
    playing = db.session.query(ActiveConnection.channel_id).filter(
        ActiveConnection.last_heartbeat >= now - timedelta(seconds=get_active_heartbeat_timeout_seconds()))
    channel = Channel.query.filter(
        Channel.is_active.is_(True), or_(*due), ~Channel.id.in_(playing)
    ).order_by(Channel.health_check_requested_at.is_(None), Channel.last_check, Channel.id).first()
    results = {'total': 0, 'healthy': 0, 'unhealthy': 0}
    if channel is None:
        return results
    automatic = channel.health_check_requested_at is None
    try:
        healthy = check_channel_health(channel, automatic=automatic)
    except HealthCheckBusy:
        return results
    results['total'] = 1
    results['healthy' if healthy else 'unhealthy'] = 1
    return results
