# -*- coding: utf-8 -*-
"""
配置文件加载模块
"""

import os
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
        'session': {
            'secret_key': os.getenv('SESSION_SECRET_KEY', 'default-secret-key')
        },
        'udpxy': {
            'enabled': os.getenv('UDPXY_ENABLED', 'false').lower() == 'true',
            'url': os.getenv('UDPXY_URL', 'http://localhost:3680')
        },
        'health_check': {
            'enabled': os.getenv('HEALTH_CHECK_ENABLED', 'true').lower() == 'true',
            'interval': int(os.getenv('HEALTH_CHECK_INTERVAL', 1800)),
            'timeout': int(os.getenv('HEALTH_CHECK_TIMEOUT', 10)),
            'max_retries': int(os.getenv('HEALTH_CHECK_MAX_RETRIES', 1)),
            'threads': int(os.getenv('HEALTH_CHECK_THREADS', 3))
        },
        'proxy': {
            'buffer_size': int(os.getenv('PROXY_BUFFER_SIZE', 8192))
        },
        'watch_history': {
            'save_interval': int(os.getenv('WATCH_HISTORY_SAVE_INTERVAL', 60))
        }
    }

    logger.info(f"配置加载完成: UDPxy Enabled={config['udpxy']['enabled']}")
    return config

# 运行时可更新的配置（从数据库加载）
_runtime_config = {}

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

        # 加载健康检测线程数
        health_threads = Settings.get('health_check_threads')
        if health_threads:
            _runtime_config['health_check_threads'] = int(health_threads)
            logger.info(f"从数据库加载配置: health_check_threads={health_threads}")

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
    """获取健康检测超时时间（优先从运行时配置读取）"""
    runtime_value = get_runtime_config('health_check_timeout')
    if runtime_value:
        return runtime_value
    return config.get('health_check', {}).get('timeout', 10)

def get_health_check_max_retries():
    """获取健康检测重试次数（优先从运行时配置读取）"""
    runtime_value = get_runtime_config('health_check_max_retries')
    if runtime_value is not None:
        return runtime_value
    return config.get('health_check', {}).get('max_retries', 1)

def get_health_check_threads():
    """获取健康检测线程数（优先从运行时配置读取）"""
    runtime_value = get_runtime_config('health_check_threads')
    if runtime_value is not None:
        return runtime_value
    return config.get('health_check', {}).get('threads', 3)

def get_udpxy_enabled():
    """获取 UDPxy 启用状态（优先从运行时配置读取）"""
    runtime_value = get_runtime_config('udpxy_enabled')
    if runtime_value is not None:
        return runtime_value
    return config.get('udpxy', {}).get('enabled', False)

def get_udpxy_url():
    """获取 UDPxy URL（优先从运行时配置读取）"""
    runtime_value = get_runtime_config('udpxy_url')
    if runtime_value:
        return runtime_value
    return config.get('udpxy', {}).get('url', 'http://localhost:4022')

# 全局配置对象
config = load_config()
