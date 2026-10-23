"""Regression coverage for deleting channels with retained watch history."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flask import Flask

from app import db
from app.api.channels import bp as channels_bp
from app.models import Channel, Users, WatchHistory
from app.utils.jwt import create_access_token


class ChannelDeletionTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI='sqlite://')
        db.init_app(self.app)
        self.app.register_blueprint(channels_bp)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        user = Users(username='delete-test', must_change_password=False)
        user.set_password('test-password')
        db.session.add(user)
        db.session.commit()
        self.user_id = user.id
        self.client = self.app.test_client()
        self.headers = {'Authorization': f'Bearer {create_access_token(user.id)}'}

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def create_channel(self, with_history=True):
        channel = Channel(name='Test', url='http://example.com/live.ts')
        db.session.add(channel)
        db.session.flush()
        channel_id = channel.id
        if with_history:
            history = WatchHistory(user_id=self.user_id, channel_id=channel_id)
            history.duration = 60
            db.session.add(history)
        db.session.commit()
        db.session.remove()
        return channel_id

    def assert_history_retained(self, channel_id):
        db.session.remove()
        self.assertIsNone(db.session.get(Channel, channel_id))
        history = WatchHistory.query.filter_by(channel_id=channel_id).one()
        self.assertEqual(history.duration, 60)
        self.assertEqual(history.to_dict()['channel_id'], channel_id)
        self.assertIsNone(history.to_dict()['channel_name'])
        self.assertIsNotNone(db.session.get(Users, self.user_id))

    def test_single_delete_preserves_history(self):
        channel_id = self.create_channel()
        other_id = self.create_channel()
        response = self.client.delete(f'/api/channels/{channel_id}', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assert_history_retained(channel_id)
        self.assertIsNotNone(db.session.get(Channel, other_id))
        self.assertEqual(WatchHistory.query.count(), 2)

    def test_delete_with_history_loaded_in_session(self):
        channel_id = self.create_channel()
        channel = db.session.get(Channel, channel_id)
        history = channel.watch_history.all()[0]
        self.assertIs(history.channel, channel)
        response = self.client.delete(f'/api/channels/{channel_id}', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assert_history_retained(channel_id)

    def test_batch_delete_preserves_history(self):
        ids = [self.create_channel(), self.create_channel()]
        response = self.client.post('/api/channels/batch-delete', headers=self.headers,
                                    json={'ids': ids})
        self.assertEqual(response.status_code, 200)
        for channel_id in ids:
            self.assert_history_retained(channel_id)

    def test_delete_without_history_and_repeat_delete(self):
        channel_id = self.create_channel(with_history=False)
        response = self.client.delete(f'/api/channels/{channel_id}', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        db.session.remove()
        self.assertIsNone(db.session.get(Channel, channel_id))
        response = self.client.delete(f'/api/channels/{channel_id}', headers=self.headers)
        self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()
