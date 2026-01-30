# gunicorn.conf.py

import multiprocessing
import os
from dotenv import load_dotenv

# 加载 .env 文件
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, '.env')
load_dotenv(ENV_PATH)

# 从环境变量读取绑定地址
SERVER_HOST = os.getenv('SERVER_HOST', '0.0.0.0')
SERVER_PORT = os.getenv('SERVER_PORT', '5000')
bind = f"{SERVER_HOST}:{SERVER_PORT}"

# 工作进程数
workers = multiprocessing.cpu_count() + 1

# 工作模式 对于流媒体转发等 IO 密集型场景，使用 gthread 模式
worker_class = 'gthread'

# 线程数 (对于流媒体转发等 IO 密集型场景，使用 gthread 模式)
threads = 4

# 进程名称
proc_name = 'iptv_proxy_admin'

# 访问日志
# 可通过 GUNICORN_ACCESS_LOG 环境变量配置日志文件路径，默认输出到标准输出
accesslog = '-'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# 错误日志
# 可通过 GUNICORN_ERROR_LOG 环境变量配置日志文件路径，默认输出到标准输出
errorlog = '-'
loglevel = os.getenv('GUNICORN_LOG_LEVEL', 'info')

# 超时设置 timeout = 0 表示无限超时，适合长连接场景 对于 IPTV 流转发，用户可能会观看数小时，不应该有超时限制
timeout = 0
keepalive = 5

# 重载（开发环境可设置为 True，生产环境建议 False）
reload = 'false'

# 守护进程
daemon = False

# 预加载应用
preload_app = True
