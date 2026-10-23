"""Run with: python -m unittest discover -s backend/tests"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flask import Flask
from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable

from app import db, _ensure_channels_schema
from app.api.channels import bp as channels_bp
from app.models import Channel, Users
from app.services.import_export import bp as import_bp
from app.utils.jwt import create_access_token


# Synthetic credentials: preserve the encoding/length of operator-signed URLs.
LONG_URL = (
    'http://10.0.0.1/PLTV/88888888/224/3221225703/index.m3u8'
    '?fmt=ts2hls&rrsip=10.0.0.2&zoneoffset=480&GuardEncType=2'
    '&accountinfo=%7E%7EV2.0%7E' + 'synthetic_signature_' * 40
    + '%3A20250510113236%2C120574%2CEND&VIP=null'
)


class LongChannelUrlTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI='sqlite://')
        db.init_app(self.app)
        self.app.register_blueprint(channels_bp)
        self.app.register_blueprint(import_bp)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        user = Users(username='url-test', must_change_password=False)
        user.set_password('test-password')
        user.generate_token()
        db.session.add(user)
        db.session.commit()
        self.client = self.app.test_client()
        self.headers = {'Authorization': f'Bearer {create_access_token(user.id)}'}

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_create_update_and_read_preserve_long_url(self):
        self.assertGreater(len(LONG_URL), 500)
        response = self.client.post('/api/channels', headers=self.headers,
                                    json={'name': 'Long URL', 'url': LONG_URL})
        self.assertEqual(response.status_code, 201)
        channel = response.json['channel']
        self.assertEqual(channel['url'], LONG_URL)
        self.assertEqual(channel['protocol'], 'http')
        updated_url = LONG_URL + '&extra=%2F%2B%26%3D'
        response = self.client.put(f"/api/channels/{channel['id']}",
                                   headers=self.headers, json={'url': updated_url})
        self.assertEqual(response.status_code, 200)
        db.session.expire_all()
        response = self.client.get(f"/api/channels/{channel['id']}", headers=self.headers)
        self.assertEqual(response.json['url'], updated_url)

    def test_import_preserves_long_url(self):
        response = self.client.post('/api/import-export/import', headers=self.headers, json={
            'format': 'm3u', 'content': '#EXTM3U\n#EXTINF:-1,Test\n' + LONG_URL,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['imported'], 1)
        self.assertEqual(Channel.query.one().url, LONG_URL)

    def test_mysql_new_schema_uses_text(self):
        ddl = str(CreateTable(Channel.__table__).compile(dialect=mysql.dialect()))
        self.assertIn('url TEXT NOT NULL', ddl)


class ChannelSchemaMigrationTests(unittest.TestCase):
    def test_mysql_old_schema_is_upgraded_once(self):
        with patch('app.db') as database, patch('app.inspect') as inspect:
            database.engine.dialect.name = 'mysql'
            database.String = db.String
            inspector = inspect.return_value
            inspector.get_table_names.return_value = ['channels']
            inspector.get_columns.side_effect = [
                [{'name': 'url', 'type': mysql.VARCHAR(500)}],
                [{'name': 'url', 'type': mysql.TEXT()}],
            ]
            _ensure_channels_schema()
            _ensure_channels_schema()
            database.session.execute.assert_called_once()
            self.assertEqual(str(database.session.execute.call_args.args[0]),
                             'ALTER TABLE channels MODIFY COLUMN url TEXT NOT NULL')
            database.session.commit.assert_called_once()

    def test_existing_text_types_and_sqlite_are_unchanged(self):
        for column_type in (mysql.TEXT(), mysql.MEDIUMTEXT(), mysql.LONGTEXT()):
            with self.subTest(column_type=column_type):
                with patch('app.db') as database, patch('app.inspect') as inspect:
                    database.engine.dialect.name = 'mysql'
                    database.String = db.String
                    inspect.return_value.get_table_names.return_value = ['channels']
                    inspect.return_value.get_columns.return_value = [
                        {'name': 'url', 'type': column_type}]
                    _ensure_channels_schema()
                    database.session.execute.assert_not_called()
        with patch('app.db') as database, patch('app.inspect') as inspect:
            database.engine.dialect.name = 'sqlite'
            _ensure_channels_schema()
            inspect.assert_not_called()


if __name__ == '__main__':
    unittest.main()
