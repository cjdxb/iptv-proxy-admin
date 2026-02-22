# -*- coding: utf-8 -*-
"""
Flask 应用工厂
"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from sqlalchemy import inspect, text
from loguru import logger

from .config import config

db = SQLAlchemy()

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


def _ensure_users_schema():
    """兼容旧库：为 users 表补充 must_change_password 列"""
    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())
    if 'users' not in table_names:
        return

    columns = {column['name'] for column in inspector.get_columns('users')}
    if 'must_change_password' in columns:
        return

    db.session.execute(
        text("ALTER TABLE users ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT 0")
    )
    db.session.commit()


def _quote_mysql_identifier(identifier):
    """为 MySQL 标识符添加安全引用"""
    return f"`{identifier.replace('`', '``')}`"


def _drop_mysql_foreign_keys():
    """移除 MySQL 库中现存的外键约束（仅迁移历史数据用）"""
    if db.engine.dialect.name != 'mysql':
        return

    inspector = inspect(db.engine)
    fk_items = []
    for table_name in inspector.get_table_names():
        for fk in inspector.get_foreign_keys(table_name):
            fk_name = fk.get('name')
            if fk_name:
                fk_items.append((table_name, fk_name))

    if not fk_items:
        return

    dropped_count = 0
    for table_name, fk_name in fk_items:
        try:
            db.session.execute(
                text(
                    f"ALTER TABLE {_quote_mysql_identifier(table_name)} "
                    f"DROP FOREIGN KEY {_quote_mysql_identifier(fk_name)}"
                )
            )
            db.session.commit()
            dropped_count += 1
        except Exception as e:
            db.session.rollback()
            logger.error(f"移除外键失败: table={table_name}, fk={fk_name}, error={e}")

    if dropped_count > 0:
        logger.info(f"已移除历史外键约束: {dropped_count} 个")


def create_app():
    """创建并配置 Flask 应用"""
    app = Flask(__name__)
    
    # 基础配置
    app.config['SECRET_KEY'] = config.get('jwt', {}).get('secret_key', 'default-jwt-secret-key')
    
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
    CORS(app, supports_credentials=True)
    
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
        _drop_mysql_foreign_keys()
        _ensure_users_schema()

        # 初始化默认管理员用户
        from .models.users import Users
        admin = Users.query.filter_by(username='admin').first()
        if not admin:
            admin = Users(username='admin')
            admin.set_password('admin123')
            admin.must_change_password = True
            admin.generate_token()
            db.session.add(admin)
            db.session.commit()
        elif admin.check_password('admin123') and not admin.must_change_password:
            # 兼容旧版本：若仍使用默认密码，则强制首登改密
            admin.must_change_password = True
            db.session.commit()

        # 加载数据库中的运行时配置
        from .config import load_runtime_config_from_db
        load_runtime_config_from_db()
    
    return app
