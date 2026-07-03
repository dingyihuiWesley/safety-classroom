import json
import os
import sqlite3
import tempfile
import unittest

import app as appmod


class SafetyClassroomSecurityTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.old_db_path = appmod.DB_PATH
        self.old_require_video_progress = appmod.REQUIRE_VIDEO_PROGRESS
        appmod.REQUIRE_VIDEO_PROGRESS = False
        appmod.DB_PATH = os.path.join(self.tmpdir.name, 'test.db')
        appmod.app.config['TESTING'] = True
        appmod.app.config['SECRET_KEY'] = 'test-secret'
        appmod.init_db()
        self.client = appmod.app.test_client()
        self._seed_course()

    def tearDown(self):
        appmod.DB_PATH = self.old_db_path
        appmod.REQUIRE_VIDEO_PROGRESS = self.old_require_video_progress
        self.tmpdir.cleanup()

    def _seed_course(self):
        conn = sqlite3.connect(appmod.DB_PATH)
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO courses (id, title, description, passing_score, is_active, sort_order) VALUES (1, ?, ?, 80, 1, 1)',
            ('测试课程', 'desc')
        )
        cur.execute(
            'INSERT INTO course_modules (id, course_id, type, title, content, sort_order) VALUES (10, 1, ?, ?, ?, 1)',
            ('video', '测试视频', '/static/uploads/videos/demo.mp4')
        )
        cur.execute(
            'INSERT INTO questions (id, course_id, question, options, question_type, answer, sort_order) VALUES (100, 1, ?, ?, ?, ?, 1)',
            ('第一题', json.dumps(['A', 'B'], ensure_ascii=False), 'single', '0')
        )
        cur.execute(
            'INSERT INTO questions (id, course_id, question, options, question_type, answer, sort_order) VALUES (101, 1, ?, ?, ?, ?, 2)',
            ('第二题', json.dumps(['A', 'B'], ensure_ascii=False), 'single', '1')
        )
        conn.commit()
        conn.close()

    def _complete_video(self, driver='张三'):
        return self.client.post('/api/courses/1/progress', json={
            'driver_name': driver,
            'module_id': 10,
            'module_type': 'video',
            'played_percent': 90.1,
            'watched_seconds': 0,
        })

    def test_answers_endpoint_requires_admin_login(self):
        response = self.client.get('/api/courses/1/questions')
        self.assertEqual(response.status_code, 401)

    def test_submit_does_not_require_video_progress_by_default(self):
        response = self.client.post('/api/courses/1/scores', json={
            'driver_name': '张三',
            'answers': [
                {'question_id': 100, 'selected': [0]},
                {'question_id': 101, 'selected': [1]},
            ],
        })
        self.assertEqual(response.status_code, 200)

    def test_submit_requires_completed_video_when_feature_enabled(self):
        appmod.REQUIRE_VIDEO_PROGRESS = True
        response = self.client.post('/api/courses/1/scores', json={
            'driver_name': '张三',
            'answers': [
                {'question_id': 100, 'selected': [0]},
                {'question_id': 101, 'selected': [1]},
            ],
        })
        self.assertEqual(response.status_code, 403)

    def test_partial_answer_submission_is_rejected_after_video_completion(self):
        self.assertEqual(self._complete_video().status_code, 200)
        response = self.client.post('/api/courses/1/scores', json={
            'driver_name': '张三',
            'answers': [{'question_id': 100, 'selected': [0]}],
        })
        self.assertEqual(response.status_code, 400)

    def test_video_over_90_percent_allows_full_exam_submission(self):
        self.assertEqual(self._complete_video().status_code, 200)
        progress = self.client.get('/api/courses/1/progress?driver_name=%E5%BC%A0%E4%B8%89')
        self.assertTrue(progress.json['data']['all_videos_completed'])

        response = self.client.post('/api/courses/1/scores', json={
            'driver_name': '张三',
            'answers': [
                {'question_id': 100, 'selected': [0]},
                {'question_id': 101, 'selected': [1]},
            ],
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['data']['score'], 100)
        self.assertEqual(response.json['data']['total'], 2)


if __name__ == '__main__':
    unittest.main()
