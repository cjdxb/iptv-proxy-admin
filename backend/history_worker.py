#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
历史记录 Worker 启动入口（独立进程）
"""

from app import create_app
from app.services.watch_history_saver import start_history_worker


def main():
    app = create_app()
    start_history_worker(app)


if __name__ == '__main__':
    main()
