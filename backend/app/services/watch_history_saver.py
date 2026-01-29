# -*- coding: utf-8 -*-
"""
观看历史定期保存服务
每隔一段时间自动保存正在观看的记录
"""

from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from loguru import logger
from app import db
from app.models.watch_history import WatchHistory


def save_active_watch_records():
    """
    定期保存所有活跃的观看记录
    即使用户还在观看，也会更新 end_time 和 duration
    """
    from app.api.proxy import active_connections

    if not active_connections:
        return

    logger.debug(f"定期保存观看记录: {len(active_connections)} 个活跃连接")

    saved_count = 0
    cleaned_count = 0
    now = datetime.utcnow()

    for connection_id, conn_info in list(active_connections.items()):
        watch_record_id = conn_info.get('watch_record_id')
        if not watch_record_id:
            continue

        try:
            record = WatchHistory.query.get(watch_record_id)
            if record:
                # 更新结束时间和时长（增量保存）
                record.end_time = now
                record.duration = int((record.end_time - record.start_time).total_seconds())

                # 更新连接的最后更新时间
                conn_info['last_update'] = now.isoformat() + 'Z'
                saved_count += 1

                # 清理超过 2 小时没更新的僵尸连接（可能是异常断开）
                if record.duration > 7200:  # 2 小时 = 7200 秒
                    logger.warning(f"检测到长时间观看记录，可能是异常连接: {connection_id}, 时长 {record.duration}秒")
                    # 可以选择清理或继续保留
            else:
                # 记录不存在，清理连接
                active_connections.pop(connection_id, None)
                cleaned_count += 1
        except Exception as e:
            logger.error(f"保存观看记录失败 (ID: {watch_record_id}): {e}")

    # 批量提交
    if saved_count > 0:
        try:
            db.session.commit()
            logger.info(f"已保存 {saved_count} 条观看记录" + (f", 清理 {cleaned_count} 个无效连接" if cleaned_count > 0 else ""))
        except Exception as e:
            logger.error(f"提交观看记录失败: {e}")
            db.session.rollback()


def start_watch_history_saver(app):
    """启动观看历史定期保存服务"""
    from app.config import config

    # 获取保存间隔（默认 60 秒）
    save_interval = config.get('watch_history', {}).get('save_interval', 60)

    scheduler = BackgroundScheduler()

    # 使用 app_context 执行数据库操作
    def job():
        with app.app_context():
            try:
                save_active_watch_records()
            except Exception as e:
                logger.error(f"观看历史保存任务执行失败: {e}")

    # 添加定时任务
    scheduler.add_job(
        job,
        'interval',
        seconds=save_interval,
        id='save_watch_history',
        name='定期保存观看历史',
        replace_existing=True
    )

    scheduler.start()
    logger.info(f"观看历史定期保存服务已启动 (间隔: {save_interval}秒)")

    return scheduler
