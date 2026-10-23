import sys
import os
import re
import unittest
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.parse import urlsplit, parse_qs

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from flask import Flask
from app import db
from app.api.proxy import bp
from app.models import Channel, Users, ActiveConnection, WatchHistory
from app.services.health_checker import _check_channel_once
from app.services.hls import resource_signer


def upstream(body, url='http://source/live/index.m3u8', status=200, content_type='application/vnd.apple.mpegurl'):
    response = MagicMock()
    response.status_code = status
    response.url = url
    response.headers = {'Content-Type': content_type}
    response.iter_content.side_effect = lambda **kwargs: iter([body])
    response.raw.read1.side_effect = [body, b'']
    response.__enter__.return_value = response
    return response


class HlsProxyTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SECRET_KEY='test-secret', SQLALCHEMY_DATABASE_URI='sqlite://')
        db.init_app(self.app)
        self.app.register_blueprint(bp)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        user = Users(username='test', token='test-token')
        user.set_password('test-password')
        channel = Channel(name='test', url='http://source/live/index.m3u8', protocol='http')
        db.session.add_all([user, channel])
        db.session.commit()
        self.channel_id = channel.id
        self.path = f'/api/proxy/stream/{channel.id}?token=test-token'
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_get_probe_accepts_head_incompatible_source_and_closes(self):
        response = upstream(b'#EXTM3U\n')
        with patch('app.services.health_checker.requests.get', return_value=response) as get:
            self.assertTrue(_check_channel_once({'id': 1, 'protocol': 'http', 'url': 'http://source'}, 3, False, ''))
            get.assert_called_once_with('http://source', timeout=3, stream=True)
            response.__exit__.assert_called_once()

    def test_error_is_not_reported_as_success_or_recorded(self):
        response = upstream(b'', status=403)
        with patch('app.api.proxy.requests.get', return_value=response):
            result = self.client.get(self.path)
        self.assertEqual(result.status_code, 502)
        self.assertEqual(result.json['upstream_status'], 403)
        self.assertEqual(WatchHistory.query.count(), 0)
        response.close.assert_called()

    def test_playlist_resources_and_ranges_share_session(self):
        playlist = (b'#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,URI="../key?k=%2B%26"\n'
                    b'#EXT-X-MAP:URI="init.mp4"\n#EXTINF:5,\nsegment.ts?a=%2F%26\n')
        response = upstream(playlist, url='http://cdn/redirect/live/index.m3u8')
        with patch('app.api.proxy.requests.get', return_value=response):
            root = self.client.get(self.path)
            self.assertEqual(root.status_code, 302)
            manifest = self.client.get(root.location)
            again = self.client.get(root.location)
        self.assertEqual(manifest.status_code, 200)
        self.assertEqual(ActiveConnection.query.count(), 1)
        self.assertEqual(WatchHistory.query.count(), 1)
        text = manifest.get_data(as_text=True)
        self.assertNotIn('http://cdn', text)
        targets = []
        for uri in re.findall(r'URI="([^"]+)"', text):
            signature = parse_qs(urlsplit(uri).query)['resource'][0]
            targets.append(resource_signer().loads(signature)['url'])
        self.assertEqual(targets, ['http://cdn/redirect/key?k=%2B%26',
                                   'http://cdn/redirect/live/init.mp4'])
        resource_url = text.splitlines()[-1]
        signed = parse_qs(urlsplit(resource_url).query)['resource'][0]
        payload = resource_signer().loads(signed)
        self.assertEqual(payload['url'], 'http://cdn/redirect/live/segment.ts?a=%2F%26')
        segment = upstream(b'bytes', url=payload['url'], status=206, content_type='video/mp2t')
        segment.headers['Content-Range'] = 'bytes 0-4/10'
        with patch('app.api.proxy.requests.get', return_value=segment) as get:
            result = self.client.get(resource_url, headers={'Range': 'bytes=0-4'}, buffered=True)
        self.assertEqual(result.status_code, 206)
        self.assertEqual(result.data, b'bytes')
        self.assertEqual(result.headers['Content-Range'], 'bytes 0-4/10')
        self.assertEqual(get.call_args.kwargs['headers']['Range'], 'bytes=0-4')
        self.assertEqual(ActiveConnection.query.count(), 1)
        segment.close.assert_called()

    def test_unsigned_resource_is_rejected_without_network(self):
        with patch('app.api.proxy.requests.get') as get:
            result = self.client.get(self.path + '&resource=http://arbitrary/target')
        self.assertEqual(result.status_code, 403)
        get.assert_not_called()

    def test_resource_cannot_be_reused_for_another_user_or_channel(self):
        for user_id, channel_id in ((999, self.channel_id), (1, 999)):
            signed = resource_signer().dumps({'url': 'http://source/segment.ts',
                                            'user_id': user_id, 'channel_id': channel_id,
                                            'connection_id': 'test'})
            with patch('app.api.proxy.requests.get') as get:
                result = self.client.get(self.path + '&resource=' + signed)
            self.assertEqual(result.status_code, 403)
            get.assert_not_called()

    def test_regular_ts_stream_uses_one_get_and_closes_session(self):
        response = upstream(b'ts-bytes', url='http://source/live.ts', content_type='video/mp2t')
        with patch('app.api.proxy.requests.get', return_value=response) as get:
            result = self.client.get(self.path, buffered=True)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data, b'ts-bytes')
        get.assert_called_once()
        self.assertEqual(ActiveConnection.query.count(), 0)
        response.close.assert_called()

    def test_live_first_packet_does_not_wait_for_buffer_or_eof(self):
        # A real HTTP source sends one TS packet, then pauses. Mocked iterators
        # cannot reproduce urllib3's fixed-size network read buffering.
        for chunked in (False, True):
            with self.subTest(chunked=chunked):
                release = threading.Event()
                source_resumed = threading.Event()
                packet = b'\x47' + b'\x00' * 187

                class Source(BaseHTTPRequestHandler):
                    protocol_version = 'HTTP/1.1'

                    def log_message(self, *args):
                        pass

                    def do_GET(self):
                        self.send_response(200)
                        self.send_header('Content-Type', 'video/mp2t')
                        if chunked:
                            self.send_header('Transfer-Encoding', 'chunked')
                        else:
                            self.send_header('Content-Length', str(2 * len(packet)))
                        self.end_headers()
                        # Even a single HTTP chunk may arrive in multiple writes.
                        if chunked:
                            self.wfile.write(f'{2 * len(packet):x}\r\n'.encode())
                        self.wfile.write(packet)
                        self.wfile.flush()
                        release.wait(3)
                        source_resumed.set()
                        try:
                            self.wfile.write(packet)
                            if chunked:
                                self.wfile.write(b'\r\n0\r\n\r\n')
                            self.wfile.flush()
                        except OSError:
                            pass

                server = ThreadingHTTPServer(('127.0.0.1', 0), Source)
                worker = threading.Thread(target=server.serve_forever, daemon=True)
                worker.start()
                channel = db.session.get(Channel, self.channel_id)
                channel.url = f'http://127.0.0.1:{server.server_port}/live.ts'
                db.session.commit()
                result = None
                try:
                    with patch.dict(os.environ, {'NO_PROXY': '*', 'no_proxy': '*'}), \
                            patch('app.config.get_proxy_buffer_size', return_value=65536):
                        result = self.client.get(self.path, buffered=False)
                        self.assertEqual(result.status_code, 200)
                        self.assertEqual(next(iter(result.response)), packet)
                        self.assertFalse(source_resumed.is_set(), 'first packet waited for more upstream data')
                        self.assertEqual(result.headers['X-Accel-Buffering'], 'no')
                        self.assertIn('no-transform', result.headers['Cache-Control'])
                        release.set()
                        self.assertEqual(b''.join(result.response), packet)
                finally:
                    release.set()
                    if result is not None:
                        result.close()
                    server.shutdown()
                    server.server_close()
                    worker.join(timeout=5)
                self.assertEqual(ActiveConnection.query.count(), 0)


if __name__ == '__main__':
    unittest.main()
