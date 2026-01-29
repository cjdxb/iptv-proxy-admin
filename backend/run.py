#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
IPTV Proxy Admin 启动入口
"""

from app import create_app
from app.config import config

app = create_app()

if __name__ == '__main__':
    app.run(
        host=config.get('server', {}).get('host', '0.0.0.0'),
        port=config.get('server', {}).get('port', 5000),
        debug=config.get('server', {}).get('debug', False)
    )
