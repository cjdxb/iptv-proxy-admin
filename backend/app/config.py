# -*- coding: utf-8 -*-
"""
配置文件加载模块
"""

import os
from flask import has_app_context
from dotenv import load_dotenv
from loguru import logger

# 加载 .env 文件
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, '.env')
load_dotenv(ENV_PATH)

def load_config():
    """加载配置"""
    logger.info(f"正在从环境变量加载配置 (文件路径: {ENV_PATH})")
    
    config = {
        'server': {
            'host': os.getenv('SERVER_HOST', '0.0.0.0'),
            'port': int(os.getenv('SERVER_PORT', 5000)),
            'debug': os.getenv('SERVER_DEBUG', 'false').lower() == 'true'
        },
        'database': {
            'type': os.getenv('DATABASE_TYPE', 'sqlite'),
            'path': os.getenv('DATABASE_PATH', 'data/iptv.db'),
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'port': int(os.getenv('MYSQL_PORT', 3306)),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', 'root'),
            'db': os.getenv('MYSQL_DB', 'iptv')
        },
        'jwt': {
            'secret_key': os.getenv('JWT_SECRET_KEY', 'default-jwt-secret-key'),
            'algorithm': os.getenv('JWT_ALGORITHM', 'HS256'),
            'access_expires_hours': int(os.getenv('JWT_ACCESS_EXPIRES_HOURS', 24)),
            'refresh_expires_days': int(os.getenv('JWT_REFRESH_EXPIRES_DAYS', 7))
        },
        'udpxy': {
            'enabled': os.getenv('UDPXY_ENABLED', 'false').lower() == 'true',
            'url': os.getenv('UDPXY_URL', 'http://localhost:3680')
        },
        'health_check': {
            'enabled': os.getenv('HEALTH_CHECK_ENABLED', 'true').lower() == 'true',
            'interval': int(os.getenv('HEALTH_CHECK_INTERVAL', 21600)),
            'channel_delay': int(os.getenv('HEALTH_CHECK_CHANNEL_DELAY', 10)),
            'timeout': int(os.getenv('HEALTH_CHECK_TIMEOUT', 20)),
            'max_retries': int(os.getenv('HEALTH_CHECK_MAX_RETRIES', 1)),
        },
        'proxy': {
            'buffer_size': int(os.getenv('PROXY_BUFFER_SIZE', 8192))
        },
        'watch_history': {
            'heartbeat_interval_seconds': int(os.getenv('HEARTBEAT_INTERVAL_SECONDS', 10)),
            'active_heartbeat_timeout_seconds': int(os.getenv('ACTIVE_HEARTBEAT_TIMEOUT_SECONDS', 45)),
            'history_worker_interval_seconds': int(os.getenv('HISTORY_WORKER_INTERVAL_SECONDS', 15))
        }
    }

    logger.info(f"配置加载完成: UDPxy Enabled={config['udpxy']['enabled']}")
    return config

# 运行时可更新的配置（从数据库加载）
_runtime_config = {}


def _parse_positive_int(raw_value, default_value):
    """解析正整数配置，非法值回退默认值"""
    try:
        value = int(raw_value)
        if value < 1:
            return default_value
        return value
    except (TypeError, ValueError):
        return default_value

def get_runtime_config(key, default=None):
    """获取运行时配置（优先从数据库读取）"""
    return _runtime_config.get(key, default)

def load_runtime_config_from_db():
    """从数据库加载运行时配置到内存"""
    try:
        from app.models.settings import Settings

        # 加载代理缓冲区大小
        buffer_size = Settings.get('proxy_buffer_size')
        if buffer_size:
            _runtime_config['proxy_buffer_size'] = int(buffer_size)
            logger.info(f"从数据库加载配置: proxy_buffer_size={buffer_size}")

        # 加载健康检测超时时间
        health_timeout = Settings.get('health_check_timeout')
        if health_timeout:
            _runtime_config['health_check_timeout'] = int(health_timeout)
            logger.info(f"从数据库加载配置: health_check_timeout={health_timeout}")

        # 加载健康检测重试次数
        health_retries = Settings.get('health_check_max_retries')
        if health_retries:
            _runtime_config['health_check_max_retries'] = int(health_retries)
            logger.info(f"从数据库加载配置: health_check_max_retries={health_retries}")

        # 加载 UDPxy 启用状态
        udpxy_enabled = Settings.get('udpxy_enabled')
        if udpxy_enabled is not None:
            _runtime_config['udpxy_enabled'] = udpxy_enabled.lower() == 'true'
            logger.info(f"从数据库加载配置: udpxy_enabled={udpxy_enabled}")

        # 加载 UDPxy URL
        udpxy_url = Settings.get('udpxy_url')
        if udpxy_url:
            _runtime_config['udpxy_url'] = udpxy_url
            logger.info(f"从数据库加载配置: udpxy_url={udpxy_url}")

        # 加载播放心跳间隔
        heartbeat_interval_seconds = Settings.get('heartbeat_interval_seconds')
        if heartbeat_interval_seconds is not None:
            parsed_value = _parse_positive_int(
                heartbeat_interval_seconds,
                config.get('watch_history', {}).get('heartbeat_interval_seconds', 10)
            )
            _runtime_config['heartbeat_interval_seconds'] = parsed_value
            logger.info(f"从数据库加载配置: heartbeat_interval_seconds={parsed_value}")

        # 加载活跃连接心跳超时阈值
        active_heartbeat_timeout_seconds = Settings.get('active_heartbeat_timeout_seconds')
        if active_heartbeat_timeout_seconds is not None:
            parsed_value = _parse_positive_int(
                active_heartbeat_timeout_seconds,
                config.get('watch_history', {}).get('active_heartbeat_timeout_seconds', 45)
            )
            _runtime_config['active_heartbeat_timeout_seconds'] = parsed_value
            logger.info(f"从数据库加载配置: active_heartbeat_timeout_seconds={parsed_value}")

        # 加载 history-worker 扫描间隔（需要重启 worker 生效）
        history_worker_interval_seconds = Settings.get('history_worker_interval_seconds')
        if history_worker_interval_seconds is not None:
            parsed_value = _parse_positive_int(
                history_worker_interval_seconds,
                config.get('watch_history', {}).get('history_worker_interval_seconds', 15)
            )
            _runtime_config['history_worker_interval_seconds'] = parsed_value
            logger.info(f"从数据库加载配置: history_worker_interval_seconds={parsed_value}")

        return True
    except Exception as e:
        logger.error(f"加载运行时配置失败: {e}")
        return False

def get_proxy_buffer_size():
    """获取代理缓冲区大小（优先从运行时配置读取）"""
    # 优先从运行时配置读取（数据库）
    runtime_value = get_runtime_config('proxy_buffer_size')
    if runtime_value:
        return runtime_value

    # 否则使用环境变量默认值
    return config.get('proxy', {}).get('buffer_size', 8192)

def get_health_check_timeout():
    return _get_health_setting('health_check_timeout', 'timeout', 20, 1, 60)

def get_health_check_max_retries():
    return _get_health_setting('health_check_max_retries', 'max_retries', 1, 0, 5)

def _get_health_setting(key, option, default, minimum, maximum):
    """直接读取数据库，Web 和独立 worker 使用相同的最新配置。"""
    value = None
    if has_app_context():
        from app.models.settings import Settings
        value = Settings.get(key)
    if value is None:
        value = config.get('health_check', {}).get(option, default)
    try:
        return min(maximum, max(minimum, int(value)))
    except (TypeError, ValueError):
        return default


def get_health_check_interval():
    return _get_health_setting('health_check_interval', 'interval', 21600, 3600, 604800)


def get_health_check_channel_delay():
    return _get_health_setting('health_check_channel_delay', 'channel_delay', 10, 5, 300)

def get_udpxy_enabled():
    """有应用上下文时读取数据库，避免不同 Web 进程的缓存不一致。"""
    if has_app_context():
        from app.models.settings import Settings
        value = Settings.get(Settings.KEY_UDPXY_ENABLED)
        if value is not None:
            return str(value).lower() == 'true'
        return config.get('udpxy', {}).get('enabled', False)

    runtime_value = get_runtime_config('udpxy_enabled')
    if runtime_value is not None:
        return runtime_value
    return config.get('udpxy', {}).get('enabled', False)

def get_udpxy_url():
    """读取最新数据库地址；未设置时使用环境变量默认值。"""
    if has_app_context():
        from app.models.settings import Settings
        return (Settings.get(Settings.KEY_UDPXY_URL)
                or config.get('udpxy', {}).get('url', 'http://localhost:3680'))

    runtime_value = get_runtime_config('udpxy_url')
    if runtime_value:
        return runtime_value
    return config.get('udpxy', {}).get('url', 'http://localhost:3680')


def get_heartbeat_interval_seconds():
    """获取播放心跳间隔（秒，优先运行时配置）"""
    runtime_value = get_runtime_config('heartbeat_interval_seconds')
    if runtime_value is not None:
        return runtime_value
    return max(1, int(config.get('watch_history', {}).get('heartbeat_interval_seconds', 10)))


def get_active_heartbeat_timeout_seconds():
    """获取活跃连接心跳超时阈值（秒，优先运行时配置）"""
    runtime_value = get_runtime_config('active_heartbeat_timeout_seconds')
    if runtime_value is not None:
        return runtime_value
    return max(1, int(config.get('watch_history', {}).get('active_heartbeat_timeout_seconds', 45)))


def get_history_worker_interval_seconds():
    """获取 history-worker 扫描间隔（秒，优先运行时配置）"""
    runtime_value = get_runtime_config('history_worker_interval_seconds')
    if runtime_value is not None:
        return runtime_value
    return max(1, int(config.get('watch_history', {}).get('history_worker_interval_seconds', 15)))

# 全局配置对象
config = load_config()
