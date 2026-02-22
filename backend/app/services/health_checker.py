# -*- coding: utf-8 -*-
"""
频道健康检测服务
"""

import socket
import struct
from concurrent.futures import ThreadPoolExecutor, as_completed
from apscheduler.schedulers.blocking import BlockingScheduler
import requests
from loguru import logger
from app.config import config
from app.utils.datetime_utils import to_utc_naive

def _extract_rtp_udp_addr(url):
    """从 URL 中解析 RTP/UDP 地址。"""
    if not url:
        return ''

    if url.startswith('rtp://'):
        return url[6:]

    if url.startswith('udp://'):
        addr = url[6:]
        if addr.startswith('@'):
            return addr[1:]
        return addr

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
        if response.status_code != 200:
            return False
        chunk = next(response.iter_content(chunk_size=1024), None)
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
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        return response.status_code < 400

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
        except requests.exceptions.RequestException:
            is_healthy = False
        except Exception as e:
            if attempt == max_retries:
                logger.error(f"健康检测异常 - 频道 {channel_info.get('id')}: {e}")
            is_healthy = False

        if is_healthy:
            return True

        if attempt < max_retries:
            logger.debug(
                f"频道 {channel_info.get('name')} 检测失败，正在重试 ({attempt + 1}/{max_retries})..."
            )

    return False


def _check_channel_task(channel_info, timeout, max_retries, udpxy_enabled, udpxy_url):
    """线程池任务：只做网络探测，不触碰数据库会话。"""
    is_healthy = _check_channel_with_retry(channel_info, timeout, max_retries, udpxy_enabled, udpxy_url)
    return channel_info['id'], is_healthy


def check_channel_health(channel, max_retries=None):
    """检测单个频道并写回数据库。"""
    from app import db
    from app.models.channel import Channel
    from app.config import (
        get_health_check_timeout,
        get_health_check_max_retries,
        get_udpxy_enabled,
        get_udpxy_url
    )

    if isinstance(channel, Channel):
        channel_obj = channel
    else:
        channel_obj = db.session.get(Channel, int(channel))

    if channel_obj is None:
        raise ValueError("频道不存在")

    if max_retries is None:
        max_retries = get_health_check_max_retries()

    timeout = max(1, int(get_health_check_timeout()))
    max_retries = max(0, int(max_retries))
    udpxy_enabled = get_udpxy_enabled()
    udpxy_url = get_udpxy_url()

    channel_info = {
        'id': channel_obj.id,
        'name': channel_obj.name,
        'url': channel_obj.url,
        'protocol': channel_obj.protocol
    }
    is_healthy = _check_channel_with_retry(channel_info, timeout, max_retries, udpxy_enabled, udpxy_url)

    channel_obj.is_healthy = is_healthy
    channel_obj.last_check = to_utc_naive()
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return is_healthy


def check_all_channels():
    """检测所有活跃频道（多线程）"""
    from app import db
    from app.models.channel import Channel
    from app.config import (
        get_health_check_threads,
        get_health_check_timeout,
        get_health_check_max_retries,
        get_udpxy_enabled,
        get_udpxy_url
    )

    channels = Channel.query.filter_by(is_active=True).all()
    channel_infos = [
        {
            'id': channel.id,
            'name': channel.name,
            'url': channel.url,
            'protocol': channel.protocol
        }
        for channel in channels
    ]

    results = {
        'total': len(channel_infos),
        'healthy': 0,
        'unhealthy': 0
    }

    if not channel_infos:
        return results

    max_workers = max(1, int(get_health_check_threads()))
    timeout = max(1, int(get_health_check_timeout()))
    max_retries = max(0, int(get_health_check_max_retries()))
    udpxy_enabled = get_udpxy_enabled()
    udpxy_url = get_udpxy_url()

    logger.info(f"开始多线程健康检测，线程数: {max_workers}，频道数: {len(channel_infos)}")

    health_by_channel_id = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_channel = {
            executor.submit(
                _check_channel_task,
                channel_info,
                timeout,
                max_retries,
                udpxy_enabled,
                udpxy_url
            ): channel_info
            for channel_info in channel_infos
        }

        for future in as_completed(future_to_channel):
            channel_info = future_to_channel[future]
            try:
                channel_id, is_healthy = future.result()
            except Exception as e:
                channel_id = channel_info['id']
                is_healthy = False
                logger.error(f"检测频道 {channel_info['name']} 时发生异常: {e}")

            health_by_channel_id[channel_id] = is_healthy
            if is_healthy:
                results['healthy'] += 1
            else:
                results['unhealthy'] += 1

    now = to_utc_naive()
    for channel in channels:
        channel.is_healthy = health_by_channel_id.get(channel.id, False)
        channel.last_check = now

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return results


def run_health_worker_cycle():
    """执行一次健康检测 worker 周期。"""
    return check_all_channels()


def _get_health_check_interval_seconds():
    """读取健康检测间隔（秒）。"""
    return max(1, int(config.get('health_check', {}).get('interval', 1800)))


def start_health_worker(app):
    """启动独立 health-worker（阻塞运行）。"""
    from app.config import load_runtime_config_from_db

    if not config.get('health_check', {}).get('enabled', True):
        logger.warning("HEALTH_CHECK_ENABLED=false，health-worker 未启动")
        return None

    worker_interval = _get_health_check_interval_seconds()
    blocking_scheduler = BlockingScheduler()

    def job():
        with app.app_context():
            try:
                # 独立 worker 进程需自行刷新运行时配置
                load_runtime_config_from_db()
                results = run_health_worker_cycle()
                logger.info(
                    "health-worker执行完成: "
                    f"总计={results['total']}, "
                    f"正常={results['healthy']}, "
                    f"异常={results['unhealthy']}"
                )
            except Exception as e:
                logger.error(f"health-worker执行失败: {e}")

    # 启动后先执行一次，避免首次等待过长
    job()

    blocking_scheduler.add_job(
        job,
        'interval',
        seconds=worker_interval,
        id='health_worker',
        name='健康检测worker',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )

    logger.info(f"health-worker已启动: interval={worker_interval}s")
    blocking_scheduler.start()
    return blocking_scheduler
