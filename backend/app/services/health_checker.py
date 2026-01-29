# -*- coding: utf-8 -*-
"""
频道健康检测服务
"""

import requests
import socket
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from apscheduler.schedulers.background import BackgroundScheduler
from loguru import logger
from app.config import config

scheduler = None


def check_channel_health(channel, max_retries=None):
    """检测单个频道健康状态"""
    from app import db
    from app.config import get_health_check_timeout, get_health_check_max_retries

    # 从配置中读取重试次数和超时时间（优先从数据库读取）
    if max_retries is None:
        max_retries = get_health_check_max_retries()

    timeout = get_health_check_timeout()
    is_healthy = False
    
    for attempt in range(max_retries + 1):
        try:
            if channel.protocol in ('http', 'https'):
                # HTTP/HTTPS 源：发送 HEAD 请求
                response = requests.head(channel.url, timeout=timeout, allow_redirects=True)
                is_healthy = response.status_code < 400
            elif channel.protocol in ('rtp', 'udp'):
                # RTP/UDP 源健康检测
                from app.config import get_udpxy_enabled, get_udpxy_url

                # 解析组播地址
                if channel.url.startswith('rtp://'):
                    addr = channel.url[6:]
                elif channel.url.startswith('udp://'):
                    addr = channel.url[6:]
                    if addr.startswith('@'):
                        addr = addr[1:]
                else:
                    addr = channel.url
                
                if get_udpxy_enabled():
                    # 方式1: 通过 UDPxy 代理请求实际流数据验证
                    udpxy_base = get_udpxy_url().rstrip('/')
                    udpxy_stream_url = f"{udpxy_base}/udp/{addr}"
                    
                    try:
                        # 请求流数据，设置较短超时，只获取少量数据验证连通性
                        response = requests.get(
                            udpxy_stream_url,
                            timeout=timeout,
                            stream=True
                        )
                        if response.status_code == 200:
                            # 尝试读取少量数据（1KB）验证流是否正常
                            chunk = next(response.iter_content(chunk_size=1024), None)
                            is_healthy = chunk is not None and len(chunk) > 0
                        else:
                            is_healthy = False
                        response.close()
                    except:
                        is_healthy = False
                else:
                    # 方式2: 直接尝试 UDP 组播连接测试
                    try:
                        # 解析 IP 和端口
                        if ':' in addr:
                            ip, port = addr.rsplit(':', 1)
                            port = int(port)
                        else:
                            ip = addr
                            port = 5000  # 默认端口
                        
                        # 创建 UDP socket 尝试接收组播数据
                        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        sock.settimeout(timeout)
                        
                        # 绑定到组播端口
                        sock.bind(('', port))
                        
                        # 加入组播组
                        import struct
                        mreq = struct.pack('4sl', socket.inet_aton(ip), socket.INADDR_ANY)
                        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
                        
                        # 尝试接收数据
                        try:
                            data, _ = sock.recvfrom(1024)
                            is_healthy = len(data) > 0
                        except socket.timeout:
                            # 超时说明没有收到数据
                            is_healthy = False
                        finally:
                            sock.close()
                    except Exception as e:
                        logger.debug(f"组播检测失败 ({channel.name}): {e}")
                        is_healthy = False
        except requests.exceptions.RequestException:
            is_healthy = False
        except Exception as e:
            if attempt == max_retries:
                logger.error(f"健康检测异常 - 频道 {channel.id}: {e}")
            is_healthy = False
        
        if is_healthy:
            break
        
        if attempt < max_retries:
            logger.debug(f"频道 {channel.name} 检测失败，正在重试 ({attempt + 1}/{max_retries})...")
    
    # 更新频道状态
    channel.is_healthy = is_healthy
    channel.last_check = datetime.utcnow()
    db.session.commit()
    
    return is_healthy


def check_all_channels():
    """检测所有活跃频道（多线程）"""
    from app.models.channel import Channel
    from app.config import get_health_check_threads

    channels = Channel.query.filter_by(is_active=True).all()

    results = {
        'total': len(channels),
        'healthy': 0,
        'unhealthy': 0
    }

    if not channels:
        return results

    # 获取线程数配置
    max_workers = get_health_check_threads()
    logger.info(f"开始多线程健康检测，线程数: {max_workers}，频道数: {len(channels)}")

    # 使用线程池进行并发检测
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有检测任务
        future_to_channel = {
            executor.submit(check_channel_health, channel): channel
            for channel in channels
        }

        # 收集结果
        for future in as_completed(future_to_channel):
            channel = future_to_channel[future]
            try:
                is_healthy = future.result()
                if is_healthy:
                    results['healthy'] += 1
                else:
                    results['unhealthy'] += 1
            except Exception as e:
                logger.error(f"检测频道 {channel.name} 时发生异常: {e}")
                results['unhealthy'] += 1

    return results


def scheduled_health_check():
    """定时健康检测任务"""
    from flask import current_app
    
    logger.info("开始执行定时健康检测...")
    results = check_all_channels()
    logger.info(f"健康检测完成: 总计 {results['total']}, 正常 {results['healthy']}, 异常 {results['unhealthy']}")


def start_health_checker(app):
    """启动健康检测定时任务"""
    global scheduler
    
    if scheduler is not None:
        return
    
    interval = config.get('health_check', {}).get('interval', 1800)  # 默认 30 分钟
    
    scheduler = BackgroundScheduler()
    
    # 添加定时任务
    def job_wrapper():
        with app.app_context():
            scheduled_health_check()
    
    scheduler.add_job(
        job_wrapper,
        'interval',
        seconds=interval,
        id='health_check',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info(f"健康检测服务已启动，检测间隔: {interval} 秒")


def stop_health_checker():
    """停止健康检测定时任务"""
    global scheduler
    if scheduler:
        scheduler.shutdown()
        scheduler = None

