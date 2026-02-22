#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
健康检测 Worker 启动入口（独立进程）
"""

from app import create_app
from app.services.health_checker import start_health_worker


def main():
    app = create_app(start_background_services=False)
    start_health_worker(app)


if __name__ == '__main__':
    main()
