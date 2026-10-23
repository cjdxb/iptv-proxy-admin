import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flask import Flask
from app import db
from app.api.proxy import bp as proxy_bp
from app.api.subscription import bp as subscription_bp
from app.config import _runtime_config, config, get_udpxy_enabled, get_udpxy_url
from app.models import Channel, Users, ActiveConnection, WatchHistory
from app.models.settings import Settings


class UdpxyConfigTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI='sqlite://')
        db.init_app(self.app)
        self.app.register_blueprint(proxy_bp)
        self.app.register_blueprint(subscription_bp)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        user = Users(username='test', token='test-token')
        user.set_password('test-password')
        channel = Channel(name='test', url='udp://@239.0.0.1:1234', protocol='udp')
        db.session.add_all([user, channel])
        db.session.commit()
        self.path = f'/api/proxy/stream/{channel.id}?token=test-token'
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def set_udpxy(self, enabled, url='http://new-proxy:3680'):
        Settings.set(Settings.KEY_UDPXY_ENABLED, enabled)
        Settings.set(Settings.KEY_UDPXY_URL, url)

    def assert_stream(self, path, expected_url):
        upstream = MagicMock()
        upstream.status_code = 200
        upstream.url = expected_url
        upstream.headers = {'Content-Type': 'video/mp2t'}
        upstream.raw.read1.side_effect = [b'ts-data', b'']
        upstream.__enter__.return_value = upstream
        with patch('app.api.proxy.requests.get', return_value=upstream) as get:
            response = self.client.get(path, buffered=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b'ts-data')
        self.assertEqual(get.call_args.args[0], expected_url)
        self.assertEqual(ActiveConnection.query.count(), 0)
        upstream.close.assert_called()

    def test_preview_and_subscription_use_saved_config_in_every_worker(self):
        self.set_udpxy('true')
        for cached_enabled in (False, True):
            with self.subTest(cached_enabled=cached_enabled), patch.dict(
                _runtime_config,
                {'udpxy_enabled': cached_enabled, 'udpxy_url': 'http://old-proxy:3680'},
                clear=True,
            ):
                self.assert_stream(self.path, 'http://new-proxy:3680/udp/239.0.0.1:1234')
                for fmt in ('m3u', 'txt'):
                    playlist = self.client.get(f'/api/subscription/{fmt}?token=test-token')
                    line = playlist.get_data(as_text=True).splitlines()[-1]
                    url = line if fmt == 'm3u' else line.split(',', 1)[1]
                    parsed = urlsplit(url)
                    self.assert_stream(parsed.path + '?' + parsed.query,
                                       'http://new-proxy:3680/udp/239.0.0.1:1234')

    def test_address_update_takes_effect_without_reload(self):
        self.set_udpxy('true', 'http://first-proxy:3680')
        self.assert_stream(self.path, 'http://first-proxy:3680/udp/239.0.0.1:1234')
        Settings.set(Settings.KEY_UDPXY_URL, 'http://second-proxy:4022/')
        self.assert_stream(self.path, 'http://second-proxy:4022/udp/239.0.0.1:1234')

    def test_disabled_setting_overrides_enabled_worker_cache(self):
        self.set_udpxy('false')
        with patch.dict(_runtime_config, {'udpxy_enabled': True}), \
                patch('app.api.proxy.requests.get') as get:
            response = self.client.get(self.path)
        self.assertEqual(response.status_code, 500)
        self.assertIn('UDPxy', response.json['error'])
        get.assert_not_called()
        self.assertEqual(WatchHistory.query.count(), 0)

    def test_missing_settings_use_environment_not_stale_worker_cache(self):
        for enabled in (False, True):
            with self.subTest(enabled=enabled), patch.dict(
                config, {'udpxy': {'enabled': enabled, 'url': 'http://env-proxy:3680'}}
            ), patch.dict(_runtime_config, {'udpxy_enabled': not enabled,
                                           'udpxy_url': 'http://old-proxy:3680'}):
                self.assertEqual(get_udpxy_enabled(), enabled)
                self.assertEqual(get_udpxy_url(), 'http://env-proxy:3680')


if __name__ == '__main__':
    unittest.main()
