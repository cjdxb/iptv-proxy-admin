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
            'max_retries': int(os.getenv('HEALTH_CHECK_MAX_RETRIES', 1))
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

# 全局配置对象
config = load_config()
