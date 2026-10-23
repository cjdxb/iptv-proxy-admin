import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flask import Flask
from app import db
from app.api.subscription import bp
from app.models import Channel, Users
from app.models.settings import Settings


class SubscriptionTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI='sqlite://')
        db.init_app(self.app)
        self.app.register_blueprint(bp)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        user = Users(username='test', token='test-token')
        user.set_password('test-password')
        self.channels = [
            Channel(name=protocol, protocol=protocol, url=url, sort_order=index)
            for index, (protocol, url) in enumerate([
                ('http', 'http://source/live.ts?key=%2B%26&token=original'),
                ('https', 'https://source/live.m3u8?key=secret'),
                ('udp', 'udp://@239.0.0.1:1234'),
                ('rtp', 'rtp://239.0.0.2:1234'),
            ])
        ]
        db.session.add_all([user, *self.channels,
                            Channel(name='disabled', url='http://source/disabled', is_active=False)])
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def assert_playlist(self, direct, multicast_direct=False):
        for fmt in ('m3u', 'txt'):
            response = self.client.get(f'/api/subscription/{fmt}?token=test-token')
            self.assertEqual(response.status_code, 200)
            content = response.get_data(as_text=True)
            self.assertNotIn('disabled', content)
            positions = []
            for channel in self.channels:
                proxy = f'http://localhost/api/proxy/stream/{channel.id}?token=test-token'
                use_direct = direct if channel.protocol in ('http', 'https') else multicast_direct
                expected = channel.url if use_direct else proxy
                self.assertIn(expected, content)
                self.assertNotIn(proxy if expected == channel.url else channel.url, content)
                positions.append(content.index(expected))
            self.assertEqual(positions, sorted(positions))

    def test_missing_setting_preserves_proxy_default(self):
        self.assert_playlist(direct=False)

    def test_toggle_takes_effect_on_next_subscription(self):
        for value, direct in [('false', True), ('true', False), ('false', True)]:
            Settings.set(Settings.KEY_HTTP_PROXY_ENABLED, value)
            self.assert_playlist(direct)

    def test_direct_subscription_still_requires_valid_token(self):
        Settings.set(Settings.KEY_HTTP_PROXY_ENABLED, 'false')
        for fmt in ('m3u', 'txt'):
            for query in ('', '?token=invalid'):
                self.assertEqual(self.client.get(f'/api/subscription/{fmt}{query}').status_code, 401)

    def test_protocol_switches_are_independent(self):
        for http_enabled, multicast_enabled in [(True, False), (False, False), (False, True), (True, True)]:
            Settings.set(Settings.KEY_HTTP_PROXY_ENABLED, str(http_enabled).lower())
            Settings.set(Settings.KEY_MULTICAST_PROXY_ENABLED, str(multicast_enabled).lower())
            self.assert_playlist(not http_enabled, not multicast_enabled)


if __name__ == '__main__':
    unittest.main()
