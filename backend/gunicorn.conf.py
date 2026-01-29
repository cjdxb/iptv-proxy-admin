# gunicorn.conf.py

import multiprocessing
import os

# 绑定地址
# Bind to 0.0.0.0:5000
bind = "0.0.0.0:5000"

# 工作进程数
# Workers: CPU cores * 2 + 1
workers = multiprocessing.cpu_count() * 2 + 1

# 线程数 (对于 IO 密集型建议使用 gthread 模式)
# threads = 2 
# worker_class = 'gthread' # 如果使用 threads 需要设置 worker_class

# 工作模式
worker_class = 'sync' # 默认 sync, 也可以是 gevent, eventlet, gthread

# 进程名称
proc_name = 'iptv_proxy_admin'

# 访问日志
accesslog = '-' # 输出到标准输出
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# 错误日志
errorlog = '-' # 输出到标准输出
loglevel = 'info'

# 超时设置
timeout = 120
keepalive = 2

# 重载
reload = False # 生产环境建议 False

# 守护进程
daemon = False

# 预加载应用
preload_app = True
