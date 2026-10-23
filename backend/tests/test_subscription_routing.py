import sys
import unittest
from itertools import product
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flask import Flask
from app import db
from app.api.subscription import bp
from app.config import _runtime_config
from app.models import Channel, Users
from app.models.settings import Settings


class SubscriptionRoutingTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI='sqlite://')
        db.init_app(self.app)
        self.app.register_blueprint(bp)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.sources = [
            ('http://source/live.ts?key=%2B%26&token=original', None),
            ('https://source/live.m3u8', None),
            ('udp://@239.0.0.1:1234', '239.0.0.1:1234'),
            ('udp://239.0.0.2:1234', '239.0.0.2:1234'),
            ('rtp://239.0.0.3:1234', '239.0.0.3:1234'),
            ('RTP://@239.0.0.4:1234', '239.0.0.4:1234'),
            ('UDP://@239.0.0.5:1234', '239.0.0.5:1234'),
        ]
        self.channels = [
            Channel(name=f'channel-{index}', url=url, sort_order=index)
            for index, (url, _) in enumerate(self.sources)
        ]
        user = Users(username='test', token='test-token')
        user.set_password('test-password')
        db.session.add_all([user, *self.channels])
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def assert_urls(self, http, multicast, udpxy, base):
        expected = []
        for channel, (source, addr) in zip(self.channels, self.sources):
            if (http if addr is None else multicast):
                expected.append(f'http://localhost/api/proxy/stream/{channel.id}?token=test-token')
            elif addr is not None and udpxy:
                expected.append(f'{base}/udp/{addr}')
            else:
                expected.append(source)
        for fmt in ('m3u', 'txt'):
            response = self.client.get(f'/api/subscription/{fmt}?token=test-token')
            self.assertEqual(response.status_code, 200)
            lines = response.get_data(as_text=True).splitlines()
            urls = ([line for line in lines if not line.startswith('#')]
                    if fmt == 'm3u' else
                    [line.split(',', 1)[1] for line in lines if not line.endswith(',#genre#')])
            self.assertEqual(urls, expected)

    def test_all_switch_combinations_and_live_settings(self):
        # 每轮修改数据库，确保同一进程的新订阅不会使用旧配置。
        for index, (http, multicast, udpxy) in enumerate(product((False, True), repeat=3)):
            with self.subTest(http=http, multicast=multicast, udpxy=udpxy):
                base = f'http://udpxy-{index}:4022'
                Settings.set(Settings.KEY_HTTP_PROXY_ENABLED, str(http).lower())
                Settings.set(Settings.KEY_MULTICAST_PROXY_ENABLED, str(multicast).lower())
                Settings.set(Settings.KEY_UDPXY_ENABLED, str(udpxy).lower())
                Settings.set(Settings.KEY_UDPXY_URL, base + '/')
                with patch.dict(_runtime_config, {
                    'udpxy_enabled': not udpxy, 'udpxy_url': 'http://stale:3680',
                }):
                    self.assert_urls(http, multicast, udpxy, base)

    def test_udpxy_subscription_still_requires_valid_token(self):
        Settings.set(Settings.KEY_MULTICAST_PROXY_ENABLED, 'false')
        Settings.set(Settings.KEY_UDPXY_ENABLED, 'true')
        for fmt in ('m3u', 'txt'):
            for query in ('', '?token=invalid'):
                self.assertEqual(self.client.get(f'/api/subscription/{fmt}{query}').status_code, 401)


if __name__ == '__main__':
    unittest.main()
