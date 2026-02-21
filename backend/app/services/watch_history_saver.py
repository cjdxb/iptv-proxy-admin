# -*- coding: utf-8 -*-
"""
历史记录 worker 服务（数据库共享状态）
"""

from datetime import timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
from loguru import logger
from app import db
from app.models.active_connection import ActiveConnection
from app.models.watch_history import WatchHistory
from app.utils.datetime_utils import to_utc_naive

MIN_HISTORY_DURATION_SECONDS = WatchHistory.MIN_VALID_DURATION_SECONDS


def _calculate_duration_seconds(start_time, end_time, connection_id=None):
    duration_seconds = int((end_time - start_time).total_seconds())
    if duration_seconds < 0:
        logger.warning(
            f"观看记录时长为负数: connection_id={connection_id}, "
            f"start={start_time}, end={end_time}, duration={duration_seconds}，按0处理并保持单调"
        )
        return 0
    return duration_seconds


def _finalize_watch_record(record, end_time, connection_id=None):
    final_end_time = end_time or to_utc_naive()

    # 一旦已结束，后续并发写入沿用既有 end_time，避免 duration 超过 end_time 对应值
    effective_end_time = record.end_time or final_end_time
    calculated_duration = _calculate_duration_seconds(record.start_time, effective_end_time, connection_id=connection_id)
    record.update_duration_monotonic(calculated_duration)

    if record.end_time is None:
        record.end_time = final_end_time


def update_connection_heartbeat(connection_id, heartbeat_time=None):
    """更新活跃连接心跳时间"""
    heartbeat_time = heartbeat_time or to_utc_naive()
    try:
        updated_rows = ActiveConnection.query.filter_by(connection_id=connection_id).update(
            {ActiveConnection.last_heartbeat: heartbeat_time},
            synchronize_session=False
        )
        if updated_rows > 0:
            db.session.commit()
            return True
        return False
    except Exception as e:
        db.session.rollback()
        logger.error(f"更新连接心跳失败: connection_id={connection_id}, error={e}")
        return False


def close_active_connection(connection_id, end_time=None, fallback_watch_history_id=None):
    """结束活跃连接并幂等写入历史"""
    end_time = end_time or to_utc_naive()
    result = {
        'closed': False,
        'history_updated': False,
        'history_deleted_short': False,
        'duration': None
    }

    try:
        active_conn = db.session.get(ActiveConnection, connection_id)
        watch_history_id = fallback_watch_history_id

        if active_conn:
            watch_history_id = active_conn.watch_history_id
            result['closed'] = True

        if watch_history_id:
            record = db.session.get(WatchHistory, watch_history_id)
            if record:
                _finalize_watch_record(record, end_time, connection_id=connection_id)
                result['duration'] = record.duration
                if (record.duration or 0) < MIN_HISTORY_DURATION_SECONDS:
                    db.session.delete(record)
                    result['history_deleted_short'] = True
                else:
                    result['history_updated'] = True

        if active_conn:
            db.session.delete(active_conn)

        if result['closed'] or result['history_updated'] or result['history_deleted_short']:
            db.session.commit()

        return result
    except Exception:
        db.session.rollback()
        raise


def save_active_watch_records(now=None):
    """
    定时保存所有活跃观看记录（仅更新 duration，不写 end_time）
    返回:
        dict: {'updated': int, 'cleaned': int}
    """
    now = now or to_utc_naive()
    active_rows = ActiveConnection.query.all()
    if not active_rows:
        return {'updated': 0, 'cleaned': 0}

    updated_count = 0
    cleaned_count = 0

    try:
        for active_conn in active_rows:
            record = db.session.get(WatchHistory, active_conn.watch_history_id)
            if not record:
                db.session.delete(active_conn)
                cleaned_count += 1
                continue

            if record.end_time is not None:
                db.session.delete(active_conn)
                cleaned_count += 1
                continue

            calculated_duration = _calculate_duration_seconds(
                record.start_time,
                now,
                connection_id=active_conn.connection_id
            )
            old_duration = record.duration or 0
            record.update_duration_monotonic(calculated_duration)
            if record.duration != old_duration:
                updated_count += 1

        if updated_count > 0 or cleaned_count > 0:
            db.session.commit()

        return {'updated': updated_count, 'cleaned': cleaned_count}
    except Exception:
        db.session.rollback()
        raise


def cleanup_stale_active_connections(timeout_seconds, now=None):
    """
    回收心跳超时的活跃连接，并将历史标记为结束
    返回:
        dict: {'recycled': int, 'finalized': int}
    """
    now = now or to_utc_naive()
    timeout_seconds = max(1, int(timeout_seconds))
    cutoff_time = now - timedelta(seconds=timeout_seconds)

    stale_rows = ActiveConnection.query.filter(
        ActiveConnection.last_heartbeat < cutoff_time
    ).all()

    if not stale_rows:
        return {'recycled': 0, 'finalized': 0}

    recycled_count = 0
    finalized_count = 0

    try:
        for active_conn in stale_rows:
            record = db.session.get(WatchHistory, active_conn.watch_history_id)
            if record:
                _finalize_watch_record(
                    record,
                    active_conn.last_heartbeat or now,
                    connection_id=active_conn.connection_id
                )
                if (record.duration or 0) < MIN_HISTORY_DURATION_SECONDS:
                    db.session.delete(record)
                else:
                    finalized_count += 1

            db.session.delete(active_conn)
            recycled_count += 1

        db.session.commit()
        return {'recycled': recycled_count, 'finalized': finalized_count}
    except Exception:
        db.session.rollback()
        raise


def run_history_worker_cycle(timeout_seconds):
    """执行一次 worker 周期：保存活跃时长 + 回收僵尸连接"""
    save_result = save_active_watch_records()
    cleanup_result = cleanup_stale_active_connections(timeout_seconds=timeout_seconds)
    return {
        'saved_updated': save_result['updated'],
        'saved_cleaned': save_result['cleaned'],
        'recycled': cleanup_result['recycled'],
        'recycled_finalized': cleanup_result['finalized']
    }


def start_history_worker(app):
    """启动独立 history-worker（阻塞运行）"""
    from app.config import (
        get_active_heartbeat_timeout_seconds,
        get_history_worker_interval_seconds,
        load_runtime_config_from_db
    )

    worker_interval = get_history_worker_interval_seconds()
    startup_heartbeat_timeout = get_active_heartbeat_timeout_seconds()

    scheduler = BlockingScheduler()

    def job():
        with app.app_context():
            try:
                # 独立 worker 进程需自行刷新运行时配置
                load_runtime_config_from_db()
                heartbeat_timeout = get_active_heartbeat_timeout_seconds()
                result = run_history_worker_cycle(timeout_seconds=heartbeat_timeout)
                if any(result.values()):
                    logger.info(
                        "history-worker执行完成: "
                        f"时长更新={result['saved_updated']}, "
                        f"清理无效活跃={result['saved_cleaned']}, "
                        f"回收僵尸={result['recycled']}, "
                        f"僵尸落历史={result['recycled_finalized']}"
                    )
            except Exception as e:
                logger.error(f"history-worker执行失败: {e}")

    # 启动后先执行一次，减少首次保存等待时间
    job()

    scheduler.add_job(
        job,
        'interval',
        seconds=worker_interval,
        id='history_worker',
        name='历史记录worker',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )

    logger.info(
        "history-worker已启动: "
        f"interval={worker_interval}s, heartbeat_timeout={startup_heartbeat_timeout}s"
    )
    scheduler.start()

    return scheduler


def start_watch_history_saver(app):
    """
    兼容旧入口（阶段B后建议使用独立 history_worker.py 启动）
    """
    logger.warning("start_watch_history_saver 已废弃，请改用独立 history-worker 进程")
    return start_history_worker(app)
