# -*- coding: utf-8 -*-
"""
Flask 应用工厂
"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_cors import CORS

from .config import config

db = SQLAlchemy()
login_manager = LoginManager()

# 读取版本号
def get_version():
    """获取应用版本号"""
    version_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'VERSION')
    try:
        with open(version_file, 'r') as f:
            return f.read().strip()
    except Exception:
        return 'unknown'

__version__ = get_version()


def create_app():
    """创建并配置 Flask 应用"""
    app = Flask(__name__)
    
    # 基础配置
    app.config['SECRET_KEY'] = config.get('session', {}).get('secret_key', 'dev-secret-key')
    
    # Session Cookie 配置
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    # 数据库配置
    db_config = config.get('database', {})
    db_type = db_config.get('type', 'sqlite')
    
    if db_type == 'mysql':
        db_user = db_config.get('user', 'root')
        db_password = db_config.get('password', 'root')
        db_host = db_config.get('host', 'localhost')
        db_port = db_config.get('port', 3306)
        db_name = db_config.get('db', 'iptv')
        
        # MySQL URI: mysql+pymysql://user:password@host:port/dbname
        app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4'
    else:
        # SQLite 配置
        db_path = db_config.get('path', 'data/iptv.db')
        # 如果是相对路径，转换为基于 backend 目录的绝对路径
        if not os.path.isabs(db_path):
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(backend_dir, db_path)
            
        # 确保数据目录存在
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # 初始化扩展
    db.init_app(app)
    login_manager.init_app(app)
    CORS(app, supports_credentials=True)
    
    # 配置用户加载器
    @login_manager.user_loader
    def load_user(user_id):
        from .models.user import User
        # 使用 SQLAlchemy 2.0 兼容的方式
        return db.session.get(User, int(user_id))
    
    # 注册蓝图
    from .api import auth, channels, groups, settings, subscription, proxy, health, dashboard, history
    from .services import import_export
    app.register_blueprint(auth.bp)
    app.register_blueprint(channels.bp)
    app.register_blueprint(groups.bp)
    app.register_blueprint(settings.bp)
    app.register_blueprint(subscription.bp)
    app.register_blueprint(proxy.bp)
    app.register_blueprint(health.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(history.bp)
    app.register_blueprint(import_export.bp)
    
    # 创建数据库表
    with app.app_context():
        db.create_all()
        # 初始化默认管理员用户
        from .models.user import User
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin')
            admin.set_password('admin123')
            admin.generate_token()
            db.session.add(admin)
            db.session.commit()

        # 加载数据库中的运行时配置
        from .config import load_runtime_config_from_db
        load_runtime_config_from_db()
    
    # 启动健康检测定时任务
    if config.get('health_check', {}).get('enabled', True):
        from .services.health_checker import start_health_checker
        start_health_checker(app)

    # 启动观看历史定期保存服务
    from .services.watch_history_saver import start_watch_history_saver
    start_watch_history_saver(app)

    return app
