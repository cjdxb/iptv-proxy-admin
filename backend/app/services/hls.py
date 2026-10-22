"""HLS 清单地址重写：子清单、分片、密钥均经带签名的代理访问。"""
import re
from urllib.parse import urljoin, urlsplit

from flask import current_app, url_for
from itsdangerous import URLSafeSerializer


def resource_signer():
    return URLSafeSerializer(current_app.config['SECRET_KEY'], salt='hls-resource-v1')


def is_hls_response(response):
    content_type = response.headers.get('Content-Type', '').split(';', 1)[0].lower()
    return content_type in ('application/vnd.apple.mpegurl', 'application/x-mpegurl',
                            'audio/mpegurl', 'audio/x-mpegurl') or urlsplit(response.url).path.lower().endswith('.m3u8')


def rewrite_playlist(content, base_url, channel_id, user_id, token, connection_id):
    def proxy_uri(uri):
        target = urljoin(base_url, uri)
        if urlsplit(target).scheme not in ('http', 'https'):
            # Inline data keys and DRM schemes are interpreted by the player.
            return uri
        signed = resource_signer().dumps({
            'url': target, 'channel_id': channel_id, 'user_id': user_id,
            'connection_id': connection_id,
        })
        return url_for('proxy.stream_channel', channel_id=channel_id, token=token, resource=signed)

    lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith('#'):
            line = proxy_uri(stripped)
        elif stripped.startswith('#'):
            line = re.sub(r'\bURI="([^"]+)"', lambda m: 'URI="' + proxy_uri(m.group(1)) + '"', line)
        lines.append(line)
    return '\n'.join(lines) + '\n'
