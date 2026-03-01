#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统一 Worker 启动入口（单进程调度 history-worker + health-worker）
"""

from app import create_app
from app.services.unified_worker import start_unified_worker


def main():
    app = create_app()
    start_unified_worker(app)


if __name__ == '__main__':
    main()
