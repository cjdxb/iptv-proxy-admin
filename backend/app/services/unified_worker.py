# -*- coding: utf-8 -*-
"""
统一 worker 服务：在单进程内调度 history-worker 与 health-worker。
"""

from apscheduler.schedulers.blocking import BlockingScheduler
from loguru import logger

from app.config import (
    config,
    get_active_heartbeat_timeout_seconds,
    get_history_worker_interval_seconds,
    load_runtime_config_from_db
)
from app.services.health_checker import run_health_worker_cycle
from app.services.watch_history_saver import run_history_worker_cycle


def _is_health_worker_enabled():
    """读取是否启用健康检测定时任务。"""
    return config.get('health_check', {}).get('enabled', True)


def _get_health_check_interval_seconds():
    """读取健康检测间隔（秒）。"""
    return max(1, int(config.get('health_check', {}).get('interval', 1800)))


def start_unified_worker(app):
    """启动统一 worker（阻塞运行）。"""
    history_interval = get_history_worker_interval_seconds()
    health_enabled = _is_health_worker_enabled()
    health_interval = _get_health_check_interval_seconds()

    scheduler = BlockingScheduler()

    def history_job():
        with app.app_context():
            try:
                # 统一 worker 进程每轮都刷新运行时配置
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

    def health_job():
        with app.app_context():
            try:
                # 统一 worker 进程每轮都刷新运行时配置
                load_runtime_config_from_db()
                results = run_health_worker_cycle()
                logger.info(
                    "health-worker执行完成: "
                    f"总计={results['total']}, "
                    f"正常={results['healthy']}, "
                    f"异常={results['unhealthy']}"
                )
            except Exception as e:
                logger.error(f"health-worker执行失败: {e}")

    # 启动后先执行一次，减少首次等待时间
    history_job()
    if health_enabled:
        health_job()
    else:
        logger.warning("HEALTH_CHECK_ENABLED=false，health-worker 任务未注册")

    scheduler.add_job(
        history_job,
        'interval',
        seconds=history_interval,
        id='history_worker',
        name='历史记录worker',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )

    if health_enabled:
        scheduler.add_job(
            health_job,
            'interval',
            seconds=health_interval,
            id='health_worker',
            name='健康检测worker',
            replace_existing=True,
            max_instances=1,
            coalesce=True
        )

    logger.info(
        "unified-worker已启动: "
        f"history_interval={history_interval}s, "
        f"health_enabled={health_enabled}, "
        f"health_interval={health_interval}s"
    )
    scheduler.start()
    return scheduler
