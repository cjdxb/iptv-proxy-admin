"""Regression tests for worker-owned probes and status learned from playback."""
import sys
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flask import Flask
from sqlalchemy import inspect, text
from app import db, _ensure_channel_health_schema
from app.api.health import bp as health_bp
from app.api.proxy import bp as proxy_bp
from app.api.settings import bp as settings_bp
from app.config import config, get_health_check_interval
from app.models import Channel, Users, ActiveConnection
from app.models.settings import Settings
from app.services import health_checker as health
from app.services import unified_worker
from app.utils.datetime_utils import to_utc_naive
from app.utils.jwt import create_access_token


def upstream(body=b'packet', status=200, content_type='video/mp2t'):
    response = MagicMock()
    response.status_code = status
    response.url = 'http://source/live.ts'
    response.headers = {'Content-Type': content_type}
    response.raw.read1.side_effect = [body, b'']
    response.iter_content.return_value = iter([body])
    response.__enter__.return_value = response
    return response


class HealthStatusTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SECRET_KEY='test', SQLALCHEMY_DATABASE_URI='sqlite://')
        db.init_app(self.app)
        for bp in (health_bp, proxy_bp, settings_bp):
            self.app.register_blueprint(bp)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        user = Users(username='health-test', token='health-token', must_change_password=False)
        user.set_password('test-password')
        db.session.add(user)
        db.session.commit()
        self.user_id = user.id
        self.headers = {'Authorization': f'Bearer {create_access_token(user.id)}'}
        self.client = self.app.test_client()
        self.config_patch = patch.dict(config['health_check'], {
            'enabled': True, 'interval': 21600, 'channel_delay': 10,
            'timeout': 20, 'max_retries': 0,
        })
        self.config_patch.start()

    def tearDown(self):
        self.config_patch.stop()
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def channel(self, **kwargs):
        channel = Channel(name='test', url='http://source/live.ts', protocol='http', **kwargs)
        db.session.add(channel)
        db.session.commit()
        return channel

    def play(self, channel, response, buffered=True):
        with patch('app.api.proxy.requests.get', return_value=response) as get:
            result = self.client.get(f'/api/proxy/stream/{channel.id}?token=health-token', buffered=buffered)
        get.assert_called_once()
        return result

    def test_probe_reads_available_bytes_and_accepts_partial_response(self):
        response = upstream(status=206)
        with patch.object(health.requests, 'get', return_value=response):
            self.assertTrue(health._check_channel_once(
                {'id': 1, 'url': response.url, 'protocol': 'http'}, 20, False, ''))
        response.raw.read1.assert_called_once_with(1024, decode_content=True)
        response.iter_content.assert_not_called()
        response.__exit__.assert_called_once()

    def test_retry_waits_and_releases_first_response(self):
        first, second = upstream(body=b''), upstream()
        with patch.object(health.requests, 'get', side_effect=[first, second]), \
                patch.object(health.time, 'sleep') as sleep:
            self.assertTrue(health._check_channel_with_retry(
                {'id': 1, 'url': first.url, 'protocol': 'http'}, 20, 1, False, ''))
        sleep.assert_called_once_with(5)
        first.__exit__.assert_called_once()

    def test_automatic_failure_requires_two_separate_rounds(self):
        channel = self.channel()
        now = to_utc_naive()
        with patch.object(health, '_check_channel_with_retry', return_value=False) as probe, \
                patch.object(health, 'to_utc_naive', return_value=now) as clock:
            self.assertTrue(health.check_channel_health(channel, automatic=True))
            self.assertEqual(channel.health_failure_count, 1)
            self.assertEqual(health.run_health_worker_cycle()['total'], 0)
            clock.return_value = now + timedelta(hours=7)
            self.assertFalse(health.check_channel_health(channel, automatic=True))
            self.assertEqual(channel.health_failure_count, 2)
        self.assertEqual(probe.call_count, 2)

    def test_manual_failure_updates_without_waiting_two_rounds(self):
        channel = self.channel()
        with patch.object(health, '_check_channel_with_retry', return_value=False):
            self.assertFalse(health.check_channel_health(channel))

    def test_worker_checks_one_channel_and_respects_global_gap(self):
        self.channel()
        self.channel()
        with patch.object(health, '_check_channel_with_retry', return_value=True) as probe:
            self.assertEqual(health.run_health_worker_cycle()['total'], 1)
            # Simulate another worker/request with a fresh ORM session.
            db.session.remove()
            self.assertEqual(health.run_health_worker_cycle()['total'], 0)
            probe.assert_called_once()

    def test_live_lease_blocks_manual_probe_and_expired_lease_recovers(self):
        channel = self.channel()
        now = to_utc_naive()
        Settings.set('_health_probe_available_at', (now + timedelta(minutes=10)).isoformat())
        with patch.object(health, '_check_channel_with_retry', return_value=True) as probe:
            result = self.client.post(f'/api/health/check/{channel.id}', headers=self.headers)
            self.assertEqual(result.status_code, 409)
            probe.assert_not_called()
            Settings.set('_health_probe_available_at', (now - timedelta(seconds=1)).isoformat())
            self.assertTrue(health.check_channel_health(channel))

    def test_all_api_only_queues_and_worker_handles_manual_when_auto_disabled(self):
        channel = self.channel(last_check=to_utc_naive())
        self.channel(is_active=False)
        with patch.object(health, '_check_channel_with_retry', return_value=True) as probe:
            response = self.client.post('/api/health/check-all', headers=self.headers)
            self.assertEqual(response.status_code, 202)
            self.assertEqual(response.json['pending'], 1)
            probe.assert_not_called()
            requested = channel.health_check_requested_at
            self.client.post('/api/health/check-all', headers=self.headers)
            self.assertEqual(channel.health_check_requested_at, requested)
            with patch.dict(config['health_check'], {'enabled': False}):
                self.assertEqual(health.run_health_worker_cycle()['total'], 1)
            self.assertIsNone(channel.health_check_requested_at)
            probe.assert_called_once()

    def test_worker_skips_playing_and_recently_checked_channels(self):
        playing = self.channel()
        recent = self.channel(last_check=to_utc_naive())
        db.session.add(ActiveConnection(connection_id='playing', user_id=self.user_id,
                                         watch_history_id=1, start_time=to_utc_naive(),
                                         channel_id=playing.id, last_heartbeat=to_utc_naive()))
        db.session.commit()
        with patch.object(health, '_check_channel_with_retry') as probe:
            self.assertEqual(health.run_health_worker_cycle()['total'], 0)
            probe.assert_not_called()
        self.assertIsNone(playing.last_check)
        self.assertIsNotNone(recent.last_check)

    def test_old_probe_cannot_overwrite_playback_recovery(self):
        channel = self.channel(is_healthy=False)
        def playback_during_probe(*args):
            health.record_playback_status(channel.id, True, to_utc_naive(), channel.url)
            return False
        with patch.object(health, '_check_channel_with_retry', side_effect=playback_during_probe):
            self.assertTrue(health.check_channel_health(channel, automatic=True))
        self.assertEqual(channel.health_failure_count, 0)

    def test_playback_heartbeat_protects_throttled_online_status(self):
        now = to_utc_naive()
        channel = self.channel(last_check=now - timedelta(seconds=10))
        def playback_during_probe(*args):
            db.session.add(ActiveConnection(connection_id='new-playback', user_id=self.user_id,
                                             watch_history_id=1, channel_id=channel.id,
                                             start_time=now, last_heartbeat=now))
            db.session.commit()
            # Throttled: last_check remains older than the probe start.
            health.record_playback_status(channel.id, True, now, channel.url)
            return False
        with patch.object(health, '_check_channel_with_retry', side_effect=playback_during_probe):
            self.assertTrue(health.check_channel_health(channel))
        self.assertEqual(channel.health_failure_count, 0)

    def test_changed_source_does_not_receive_old_probe_result(self):
        channel = self.channel()
        def replace_source(*args):
            channel.url = 'http://source/replacement.ts'
            db.session.commit()
            return False
        with patch.object(health, '_check_channel_with_retry', side_effect=replace_source):
            self.assertTrue(health.check_channel_health(channel))
        self.assertIsNone(channel.last_check)

    def test_playback_recovers_offline_channel_and_normal_eof_keeps_online(self):
        channel = self.channel(is_healthy=False, health_failure_count=2)
        response = self.play(channel, upstream())
        self.assertEqual(response.data, b'packet')
        self.assertTrue(channel.is_healthy)
        self.assertEqual(channel.health_failure_count, 0)
        self.assertIsNotNone(channel.last_check)

    def test_empty_stream_and_http_failure_set_offline(self):
        for response in (upstream(body=b''), upstream(status=503)):
            with self.subTest(status=response.status_code):
                channel = self.channel()
                self.play(channel, response)
                self.assertFalse(channel.is_healthy)

    def test_range_rejection_and_client_disconnect_do_not_set_offline(self):
        channel = self.channel()
        self.play(channel, upstream(status=416))
        self.assertTrue(channel.is_healthy)
        response = self.play(channel, upstream(), buffered=False)
        response.close()
        self.assertTrue(channel.is_healthy)

    def test_read_failure_after_success_marks_offline(self):
        channel = self.channel()
        response = upstream()
        now = to_utc_naive()
        def fail_after_first_packet(*args, **kwargs):
            # Simulate a stream that played for a while before breaking.
            channel.last_check = now - timedelta(minutes=2)
            db.session.commit()
            raise OSError('upstream read failed')
        calls = iter([b'packet', None])
        def read(*args, **kwargs):
            packet = next(calls)
            return packet if packet else fail_after_first_packet()
        response.raw.read1.side_effect = read
        result = self.play(channel, response)
        self.assertEqual(result.data, b'packet')
        self.assertFalse(channel.is_healthy)

    def test_manifest_alone_does_not_recover_failed_media(self):
        channel = self.channel(is_healthy=False)
        response = self.play(channel, upstream(b'#EXTM3U\n#EXTINF:5,\nsegment.ts\n',
                                               content_type='application/vnd.apple.mpegurl'))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(channel.is_healthy)

    def test_playback_status_writes_are_throttled(self):
        channel = self.channel()
        now = to_utc_naive()
        with patch.object(health, 'to_utc_naive', return_value=now) as clock:
            health.record_playback_status(channel.id, True, now, channel.url)
            first_check = channel.last_check
            clock.return_value = now + timedelta(seconds=10)
            health.record_playback_status(channel.id, True, clock.return_value, channel.url)
            self.assertEqual(channel.last_check, first_check)
            clock.return_value = now + timedelta(seconds=61)
            health.record_playback_status(channel.id, True, clock.return_value, channel.url)
            self.assertEqual(channel.last_check, clock.return_value)

    def test_playback_satisfies_pending_check_even_with_recent_status(self):
        channel = self.channel(last_check=to_utc_naive())
        health.check_all_channels()
        self.assertIsNotNone(channel.health_check_requested_at)
        health.record_playback_status(channel.id, True, to_utc_naive(), channel.url)
        self.assertIsNone(channel.health_check_requested_at)
        self.assertTrue(channel.is_healthy)

    def test_settings_are_shared_and_invalid_frequency_is_rejected(self):
        for value in (0, 3599, 1.5, 'invalid'):
            result = self.client.put('/api/settings/health_check_interval',
                                     json={'value': value}, headers=self.headers)
            self.assertEqual(result.status_code, 400)
        Settings.set('health_check_interval', '43200')
        db.session.remove()
        self.assertEqual(get_health_check_interval(), 43200)
        response = self.client.get('/api/settings', headers=self.headers)
        self.assertEqual(response.json['health_check_interval'], 43200)

    def test_old_database_migration_preserves_rows_and_is_idempotent(self):
        db.session.remove()
        db.drop_all()
        db.session.execute(text('CREATE TABLE channels (id INTEGER PRIMARY KEY, name TEXT)'))
        db.session.execute(text("INSERT INTO channels VALUES (1, 'existing')"))
        db.session.commit()
        _ensure_channel_health_schema()
        _ensure_channel_health_schema()
        columns = {col['name'] for col in inspect(db.engine).get_columns('channels')}
        self.assertTrue({'health_failure_count', 'health_check_requested_at'} <= columns)
        row = db.session.execute(text('SELECT name, health_failure_count FROM channels')).one()
        self.assertEqual(tuple(row), ('existing', 0))

    def test_worker_registers_serial_job_without_startup_batch(self):
        with patch.object(unified_worker, 'BlockingScheduler') as scheduler, \
                patch.object(unified_worker, 'run_history_worker_cycle', return_value={}), \
                patch.object(unified_worker, 'load_runtime_config_from_db'), \
                patch.object(unified_worker, 'run_health_worker_cycle') as probe:
            unified_worker.start_unified_worker(self.app)
        probe.assert_not_called()
        jobs = [call.kwargs for call in scheduler.return_value.add_job.call_args_list]
        health_job = next(job for job in jobs if job['id'] == 'health_worker')
        self.assertEqual(health_job['max_instances'], 1)
        scheduler.return_value.start.assert_called_once()

    def test_real_slow_source_is_healthy_on_first_small_packet(self):
        release = threading.Event()
        resumed = threading.Event()
        class Source(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-Type', 'video/mp2t')
                self.send_header('Content-Length', '376')
                self.end_headers()
                self.wfile.write(b'\x47' + b'\x00' * 187)
                self.wfile.flush()
                release.wait(3)
                resumed.set()
        server = ThreadingHTTPServer(('127.0.0.1', 0), Source)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            with patch.dict(os.environ, {'NO_PROXY': '*', 'no_proxy': '*'}):
                self.assertTrue(health._check_channel_once({
                    'id': 1, 'url': f'http://127.0.0.1:{server.server_port}/live.ts',
                    'protocol': 'http',
                }, 1, False, ''))
            self.assertFalse(resumed.is_set(), 'probe waited for a full buffer')
        finally:
            release.set()
            server.shutdown()
            server.server_close()
            worker.join(timeout=5)


if __name__ == '__main__':
    unittest.main()
