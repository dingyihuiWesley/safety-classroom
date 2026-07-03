#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
轻卡安全大讲堂 - 后端服务 V3.0
功能：多课程分类 + 模块化学习内容 + 问卷星式考试配置 + 课程手动排序 + 多选题目 + 管理员权限
作者：WorkBuddy
"""

from flask import Flask, request, jsonify, render_template, send_file, session, redirect, url_for
from flask_cors import CORS
from functools import wraps
import sqlite3
import json
import os
import hashlib
import ipaddress
import re
import secrets
import socket
import uuid
import subprocess
import shutil
import tempfile
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from io import BytesIO

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.environ.get('SESSION_COOKIE_SECURE', '').lower() in ('1', 'true', 'yes')
)
CORS(app, resources={r"/api/*": {"origins": os.environ.get('CORS_ORIGINS', 'http://localhost:8888').split(',')}})

# ==================== 文件上传配置 ====================
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'webm', 'ogg', 'mov', 'avi'}
MAX_UPLOAD_SIZE = 200 * 1024 * 1024
MAX_PROXY_IMAGE_SIZE = 10 * 1024 * 1024
REQUIRE_VIDEO_PROGRESS = os.environ.get('REQUIRE_VIDEO_PROGRESS', '').lower() in ('1', 'true', 'yes')
BILIBILI_RE = re.compile(r'(?:video/)?(BV[0-9A-Za-z]+)', re.IGNORECASE)
VIDEO_URL_RE = re.compile(r'/(?:static/)?uploads/videos/|\.((mp4|webm|ogg|mov|avi))(?:[?#]|$)', re.IGNORECASE)
LEGACY_SHA256_RE = re.compile(r'^[0-9a-f]{64}$')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def generate_video_thumbnail(video_path, thumbnail_dir, base_name):
    """
    使用 ffmpeg 或 qlmanage 为视频生成缩略图。
    返回缩略图的 URL 路径（/static/uploads/thumbnails/xxx.jpg），失败返回 None。
    """
    os.makedirs(thumbnail_dir, exist_ok=True)
    thumb_name = base_name + '.jpg'
    thumb_path = os.path.join(thumbnail_dir, thumb_name)
    # 已存在则直接返回
    if os.path.exists(thumb_path):
        return f'/static/uploads/thumbnails/{thumb_name}'
    try:
        ffmpeg = shutil.which('ffmpeg')
        if ffmpeg:
            result = subprocess.run(
                [ffmpeg, '-y', '-ss', '1', '-i', video_path, '-frames:v', '1', '-vf', 'scale=640:-1', thumb_path],
                capture_output=True, timeout=20
            )
            if result.returncode == 0 and os.path.exists(thumb_path):
                return f'/static/uploads/thumbnails/{thumb_name}'

        qlmanage = '/usr/bin/qlmanage'
        if not os.path.exists(qlmanage):
            return None

        # qlmanage 会在 output_dir 生成 <文件名>.png
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = subprocess.run(
                [qlmanage, '-t', '-s', '640', '-o', tmp_dir, video_path],
                capture_output=True, timeout=15
            )
            # 找到生成的 png 文件
            generated = [f for f in os.listdir(tmp_dir) if f.endswith('.png')]
            if generated:
                png_path = os.path.join(tmp_dir, generated[0])
                # 用 Pillow 转 JPEG 并压缩
                try:
                    from PIL import Image
                    img = Image.open(png_path).convert('RGB')
                    img.save(thumb_path, 'JPEG', quality=80, optimize=True)
                except ImportError:
                    # Pillow 不可用时直接复制 png
                    shutil.copy(png_path, thumb_path.replace('.jpg', '.png'))
                    return f'/static/uploads/thumbnails/{base_name}.png'
                return f'/static/uploads/thumbnails/{thumb_name}'
    except Exception as e:
        print(f'[缩略图生成失败] {video_path}: {e}')
    return None
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_SIZE

def get_local_ip():
    """获取本机局域网IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'

DB_PATH = os.path.join(os.path.dirname(__file__), 'data.db')
LOCAL_IP = get_local_ip()


def hash_password(password):
    return generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)


def verify_password(stored_hash, password):
    """兼容旧 SHA256 密码，后续登录成功时会迁移到 Werkzeug 哈希。"""
    if not stored_hash:
        return False
    if LEGACY_SHA256_RE.match(stored_hash):
        return hashlib.sha256(password.encode()).hexdigest() == stored_hash
    return check_password_hash(stored_hash, password)


def should_rehash_password(stored_hash):
    return bool(stored_hash and LEGACY_SHA256_RE.match(stored_hash))


def is_default_password(password):
    return password == 'admin123'


def response_error(code, msg, status=400):
    return jsonify({'code': code, 'msg': msg}), status


def is_video_content(module_type, content):
    content = content or ''
    lower = content.lower()
    return (
        module_type == 'video' or
        '<video' in lower or
        '<iframe' in lower or
        'bilibili' in lower or
        bool(BILIBILI_RE.search(content)) or
        bool(VIDEO_URL_RE.search(content))
    )


def get_required_video_modules(cursor, course_id):
    cursor.execute(
        'SELECT id, title, type, content FROM course_modules WHERE course_id=? ORDER BY sort_order',
        (course_id,)
    )
    modules = []
    for module_id, title, module_type, content in cursor.fetchall():
        if is_video_content(module_type, content):
            modules.append({
                'id': module_id,
                'title': title or '视频学习',
                'type': module_type,
                'content': content or ''
            })
    return modules


def has_completed_required_videos(cursor, course_id, driver_name):
    required_modules = get_required_video_modules(cursor, course_id)
    if not required_modules:
        return True, []
    cursor.execute(
        'SELECT module_id, is_completed FROM learning_progress WHERE course_id=? AND driver_name=?',
        (course_id, driver_name)
    )
    completed = {row[0] for row in cursor.fetchall() if row[1]}
    incomplete = [m for m in required_modules if m['id'] not in completed]
    return len(incomplete) == 0, incomplete


def sanitize_rich_html(html):
    """轻量清理管理员富文本，保留课程排版和媒体标签。"""
    if not html:
        return ''
    cleaned = re.sub(r'<\s*(script|style|object|embed|meta|link)\b[^>]*>.*?<\s*/\s*\1\s*>', '', html, flags=re.I | re.S)
    cleaned = re.sub(r'<\s*(script|style|object|embed|meta|link)\b[^>]*?/?>', '', cleaned, flags=re.I | re.S)
    cleaned = re.sub(r'\s+on[a-z]+\s*=\s*(".*?"|\'.*?\'|[^\s>]+)', '', cleaned, flags=re.I | re.S)
    cleaned = re.sub(r'(href|src)\s*=\s*([\'"])\s*javascript:.*?\2', r'\1="#"', cleaned, flags=re.I | re.S)
    cleaned = re.sub(r'(href|src)\s*=\s*([\'"])\s*data:text/html.*?\2', r'\1="#"', cleaned, flags=re.I | re.S)
    return cleaned


def host_is_private(hostname):
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return True
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
            return True
    return False

# ==================== 数据库操作 ====================

def init_db():
    """初始化数据库（支持迁移）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 管理员表（支持角色）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'super_admin',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # 为旧表补充新字段
    try:
        cursor.execute("ALTER TABLE admin_users ADD COLUMN role TEXT DEFAULT 'super_admin'")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE admin_users ADD COLUMN is_active INTEGER DEFAULT 1")
    except:
        pass

    # 学习进度表（视频播放进度追踪）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS learning_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            driver_name TEXT NOT NULL,
            module_id INTEGER NOT NULL,
            module_type TEXT NOT NULL,
            played_percent REAL DEFAULT 0,
            watched_seconds REAL DEFAULT 0,
            is_completed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
            FOREIGN KEY (module_id) REFERENCES course_modules(id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('''
        CREATE UNIQUE INDEX IF NOT EXISTS idx_learning_progress_unique
        ON learning_progress(course_id, driver_name, module_id)
    ''')

    # 课程表（支持排序）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            cover_image TEXT,
            passing_score INTEGER DEFAULT 80,
            is_active INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    try:
        cursor.execute("ALTER TABLE courses ADD COLUMN sort_order INTEGER DEFAULT 0")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE courses ADD COLUMN rich_content TEXT")
    except:
        pass

    # 课程内容模块表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS course_modules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            title TEXT,
            content TEXT,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
        )
    ''')

    # 题目表（支持多选）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            options TEXT NOT NULL,
            question_type TEXT DEFAULT 'single',
            answer TEXT NOT NULL,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
        )
    ''')
    try:
        cursor.execute("ALTER TABLE questions ADD COLUMN question_type TEXT DEFAULT 'single'")
    except:
        pass
    # answer 字段：旧数据是 INTEGER，新数据是 JSON数组字符串
    # SQLite 支持动态类型，无需修改列类型

    # 成绩表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            driver_name TEXT NOT NULL,
            driver_phone TEXT,
            driver_city TEXT,
            driver_plate TEXT,
            ip_address TEXT,
            score INTEGER NOT NULL,
            total_questions INTEGER NOT NULL,
            correct_count INTEGER NOT NULL,
            answers TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses(id)
        )
    ''')
    for col, dtype in [('driver_city', 'TEXT'), ('driver_plate', 'TEXT'), ('ip_address', 'TEXT')]:
        try:
            cursor.execute(f"ALTER TABLE scores ADD COLUMN {col} {dtype}")
        except:
            pass

    # 插入默认超级管理员
    cursor.execute('SELECT COUNT(*) FROM admin_users')
    if cursor.fetchone()[0] == 0:
        initial_password = os.environ.get('DEFAULT_ADMIN_PASSWORD') or secrets.token_urlsafe(14)
        password_hash = hash_password(initial_password)
        cursor.execute('INSERT INTO admin_users (username, password, role) VALUES (?, ?, ?)',
                      ('cidi', password_hash, 'super_admin'))
        print(f"首次初始化管理员：cidi / {initial_password}，请登录后立即修改密码")

    conn.commit()
    conn.close()
    print("✅ 数据库初始化完成")


def parse_answer(raw):
    """将数据库中的 answer 字段统一解析为 Python 对象
    旧格式：整数（单个答案索引）
    新格式：JSON数组字符串（多个答案索引）
    """
    if raw is None:
        return [0]
    try:
        val = json.loads(raw)
        if isinstance(val, list):
            return val
        return [int(val)]
    except (json.JSONDecodeError, TypeError, ValueError):
        try:
            return [int(raw)]
        except (TypeError, ValueError):
            return [0]


def format_answer(answer_data):
    """将答案数据格式化为数据库存储格式
    - 如果 answer_data 是列表且长度>1：存 JSON 数组字符串
    - 如果 answer_data 是单个整数或长度为1的列表：存为整数（兼容旧格式）
    """
    if isinstance(answer_data, list):
        if len(answer_data) > 1:
            return json.dumps(answer_data, ensure_ascii=False)
        elif len(answer_data) == 1:
            return str(answer_data[0])
        else:
            return '0'
    return str(answer_data)


# ==================== 认证装饰器 ====================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session or not session['admin_logged_in']:
            return jsonify({'code': 401, 'msg': '请先登录'}), 401
        return f(*args, **kwargs)
    return decorated_function


def super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session or not session['admin_logged_in']:
            return jsonify({'code': 401, 'msg': '请先登录'}), 401
        if session.get('admin_role') != 'super_admin':
            return jsonify({'code': 403, 'msg': '需要超级管理员权限'}), 403
        return f(*args, **kwargs)
    return decorated_function


# ==================== 页面路由 ====================

@app.route('/')
def index():
    """驾驶员端首页 - 课程列表"""
    return render_template('index.html')

@app.route('/course/<int:course_id>')
def course_detail(course_id):
    """课程学习页面"""
    return render_template('course.html', course_id=course_id)

@app.route('/exam/<int:course_id>')
def exam_page(course_id):
    """考试页面"""
    return render_template('exam.html', course_id=course_id)

@app.route('/admin')
def admin():
    """管理后台"""
    return render_template('admin.html')

@app.route('/api/server-ip', methods=['GET'])
def get_server_ip():
    """获取服务器IP供前端用于二维码生成"""
    return jsonify({'code': 200, 'ip': LOCAL_IP, 'port': 8888})

# ==================== 管理员认证API ====================

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.json
    username = data.get('username', '')
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'code': 400, 'msg': '用户名和密码不能为空'}), 400

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, password, role, is_active FROM admin_users WHERE username=?',
                  (username,))
    user = cursor.fetchone()

    if user and verify_password(user[2], password):
        if not user[4]:  # is_active
            conn.close()
            return jsonify({'code': 403, 'msg': '账号已被禁用，请联系超级管理员'}), 403
        if should_rehash_password(user[2]):
            cursor.execute('UPDATE admin_users SET password=? WHERE id=?', (hash_password(password), user[0]))
            conn.commit()
        session['admin_logged_in'] = True
        session['admin_id'] = user[0]
        session['admin_username'] = user[1]
        session['admin_role'] = user[3]
        conn.close()
        data = {'username': user[1], 'role': user[3], 'must_change_password': is_default_password(password)}
        msg = '登录成功，请尽快修改默认密码' if data['must_change_password'] else '登录成功'
        return jsonify({'code': 200, 'msg': msg, 'data': data})

    conn.close()
    return jsonify({'code': 401, 'msg': '用户名或密码错误'}), 401

@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    session.clear()
    return jsonify({'code': 200, 'msg': '已退出登录'})

@app.route('/api/admin/check', methods=['GET'])
def admin_check():
    if 'admin_logged_in' in session and session['admin_logged_in']:
        return jsonify({
            'code': 200,
            'logged_in': True,
            'username': session.get('admin_username', ''),
            'role': session.get('admin_role', 'super_admin')
        })
    return jsonify({'code': 200, 'logged_in': False})

@app.route('/api/admin/password', methods=['PUT'])
@login_required
def change_password():
    data = request.json
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')

    if not old_password or not new_password:
        return jsonify({'code': 400, 'msg': '请填写完整信息'})

    if len(new_password) < 6:
        return jsonify({'code': 400, 'msg': '新密码至少6位'})

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT password FROM admin_users WHERE id=?', (session['admin_id'],))
    row = cursor.fetchone()
    if not row or not verify_password(row[0], old_password):
        conn.close()
        return jsonify({'code': 401, 'msg': '原密码错误'})

    cursor.execute('UPDATE admin_users SET password=? WHERE id=?',
                  (hash_password(new_password), session['admin_id']))
    conn.commit()
    conn.close()

    return jsonify({'code': 200, 'msg': '密码修改成功'})

# ==================== 管理员账号管理API（仅超级管理员）====================

@app.route('/api/admin/accounts', methods=['GET'])
@super_admin_required
def get_admin_accounts():
    """获取所有管理员账号"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, role, is_active, created_at FROM admin_users ORDER BY id')
    rows = cursor.fetchall()
    conn.close()
    return jsonify({
        'code': 200,
        'data': [{'id': r[0], 'username': r[1], 'role': r[2], 'is_active': r[3], 'created_at': r[4]} for r in rows]
    })

@app.route('/api/admin/accounts', methods=['POST'])
@super_admin_required
def add_admin_account():
    """添加管理员账号"""
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    role = data.get('role', 'normal_admin')

    if not username or not password:
        return jsonify({'code': 400, 'msg': '用户名和密码不能为空'})
    if len(password) < 6:
        return jsonify({'code': 400, 'msg': '密码至少6位'})
    if role not in ('super_admin', 'normal_admin'):
        return jsonify({'code': 400, 'msg': '角色无效'})

    password_hash = hash_password(password)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO admin_users (username, password, role) VALUES (?, ?, ?)',
                      (username, password_hash, role))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return jsonify({'code': 200, 'msg': '添加成功', 'data': {'id': new_id}})
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'code': 400, 'msg': '用户名已存在'})

@app.route('/api/admin/accounts/<int:account_id>', methods=['PUT'])
@super_admin_required
def update_admin_account(account_id):
    """更新管理员状态（禁用/启用/修改角色）"""
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 不能修改自己
    if account_id == session['admin_id']:
        conn.close()
        return jsonify({'code': 400, 'msg': '不能修改自己的账号状态'})

    updates = []
    params = []
    if 'is_active' in data:
        updates.append('is_active=?')
        params.append(data['is_active'])
    if 'role' in data:
        if data['role'] not in ('super_admin', 'normal_admin'):
            conn.close()
            return jsonify({'code': 400, 'msg': '角色无效'})
        updates.append('role=?')
        params.append(data['role'])
    if 'password' in data:
        if len(data['password']) < 6:
            conn.close()
            return jsonify({'code': 400, 'msg': '密码至少6位'})
        updates.append('password=?')
        params.append(hash_password(data['password']))

    if not updates:
        conn.close()
        return jsonify({'code': 400, 'msg': '没有要更新的内容'})

    params.append(account_id)
    cursor.execute(f"UPDATE admin_users SET {', '.join(updates)} WHERE id=?", params)
    conn.commit()
    conn.close()
    return jsonify({'code': 200, 'msg': '更新成功'})

@app.route('/api/admin/accounts/<int:account_id>', methods=['DELETE'])
@super_admin_required
def delete_admin_account(account_id):
    """删除管理员账号"""
    if account_id == session['admin_id']:
        return jsonify({'code': 400, 'msg': '不能删除自己的账号'})
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM admin_users WHERE id=?', (account_id,))
    conn.commit()
    conn.close()
    return jsonify({'code': 200, 'msg': '删除成功'})

# ==================== 课程管理API ====================

@app.route('/api/courses', methods=['GET'])
def get_courses():
    """获取课程列表（按 sort_order 排序）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.id, c.title, c.description, c.cover_image, c.passing_score, c.is_active, c.created_at, c.sort_order,
               COUNT(DISTINCT q.id) as question_count
        FROM courses c
        LEFT JOIN questions q ON c.id = q.course_id
        WHERE c.is_active = 1
        GROUP BY c.id
        ORDER BY c.sort_order ASC, c.created_at DESC
    ''')
    courses = cursor.fetchall()
    conn.close()

    return jsonify({
        'code': 200,
        'data': [{
            'id': c[0],
            'title': c[1],
            'description': c[2],
            'cover_image': c[3],
            'passing_score': c[4],
            'is_active': c[5],
            'created_at': c[6],
            'sort_order': c[7],
            'question_count': c[8]
        } for c in courses]
    })

@app.route('/api/courses/<int:course_id>', methods=['GET'])
def get_course(course_id):
    """获取单个课程详情"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM courses WHERE id=?', (course_id,))
    course = cursor.fetchone()
    
    if not course:
        conn.close()
        return jsonify({'code': 404, 'msg': '课程不存在'})
    
    cursor.execute('''
        SELECT id, type, title, content, sort_order 
        FROM course_modules 
        WHERE course_id=? 
        ORDER BY sort_order
    ''', (course_id,))
    modules = cursor.fetchall()
    
    cursor.execute('SELECT COUNT(*) FROM questions WHERE course_id=?', (course_id,))
    question_count = cursor.fetchone()[0]
    
    conn.close()

    return jsonify({
        'code': 200,
        'data': {
            'id': course[0],
            'title': course[1],
            'description': course[2],
            'cover_image': course[3],
            'passing_score': course[4],
            'modules': [{
                'id': m[0],
                'type': m[1],
                'title': m[2],
                'content': m[3],
                'sort_order': m[4]
            } for m in modules],
            'question_count': question_count
        }
    })

@app.route('/api/courses', methods=['POST'])
@login_required
def add_course():
    """添加课程（自动分配 sort_order）"""
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT COALESCE(MAX(sort_order), 0) + 1 FROM courses')
    next_order = cursor.fetchone()[0]
    cursor.execute('''
        INSERT INTO courses (title, description, cover_image, passing_score, sort_order)
        VALUES (?, ?, ?, ?, ?)
    ''', (data['title'], data.get('description', ''), data.get('cover_image', ''), data.get('passing_score', 80), next_order))
    conn.commit()
    course_id = cursor.lastrowid
    conn.close()
    return jsonify({'code': 200, 'msg': '添加成功', 'data': {'id': course_id}})

@app.route('/api/courses/<int:course_id>', methods=['PUT'])
@login_required
def update_course(course_id):
    """更新课程"""
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE courses SET title=?, description=?, cover_image=?, passing_score=?
        WHERE id=?
    ''', (data['title'], data.get('description', ''), data.get('cover_image', ''), data.get('passing_score', 80), course_id))
    conn.commit()
    conn.close()
    return jsonify({'code': 200, 'msg': '更新成功'})

@app.route('/api/courses/<int:course_id>', methods=['DELETE'])
@super_admin_required  # 仅超级管理员可删除课程
def delete_course(course_id):
    """删除课程"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM courses WHERE id=?', (course_id,))
    conn.commit()
    conn.close()
    return jsonify({'code': 200, 'msg': '删除成功'})

@app.route('/api/courses/reorder', methods=['POST'])
@login_required
def reorder_courses():
    """重新排序课程（拖拽排序后保存）"""
    data = request.json
    course_orders = data.get('course_orders', [])  # [{id: 1, sort_order: 0}, ...]

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for item in course_orders:
        cursor.execute('UPDATE courses SET sort_order=? WHERE id=?',
                      (item['sort_order'], item['id']))
    conn.commit()
    conn.close()
    return jsonify({'code': 200, 'msg': '排序已更新'})


# ==================== 文件上传API ====================

@app.route('/api/upload', methods=['POST'])
@login_required
def upload_file():
    """上传图片/动图/视频文件"""
    if 'file' not in request.files:
        return jsonify({'code': 400, 'msg': '未选择文件'})
    
    file = request.files['file']
    if not file or not file.filename:
        return jsonify({'code': 400, 'msg': '文件为空'})
    
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    
    if ext in ALLOWED_IMAGE_EXTENSIONS:
        subfolder = 'images'
    elif ext in ALLOWED_VIDEO_EXTENSIONS:
        subfolder = 'videos'
    else:
        return jsonify({'code': 400, 'msg': f'不支持的文件格式：{ext}'})

    unique_name = f"{uuid.uuid4().hex}.{ext}"
    save_dir = os.path.join(UPLOAD_FOLDER, subfolder)
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, unique_name)
    
    file.save(save_path)
    url = f'/static/uploads/{subfolder}/{unique_name}'
    
    # 视频上传后自动生成缩略图
    poster_url = None
    if subfolder == 'videos':
        thumbnail_dir = os.path.join(UPLOAD_FOLDER, 'thumbnails')
        base_name = unique_name.rsplit('.', 1)[0]
        poster_url = generate_video_thumbnail(save_path, thumbnail_dir, base_name)
    
    file_type = 'video' if subfolder == 'videos' else ('gif' if ext == 'gif' else 'image')
    resp_data = {'url': url, 'type': file_type}
    if poster_url:
        resp_data['poster_url'] = poster_url
    return jsonify({'code': 200, 'msg': '上传成功', 'data': resp_data})


@app.route('/api/proxy-image')
@login_required
def proxy_image():
    """代理下载外部图片"""
    from urllib.parse import urlparse
    import requests
    
    url = request.args.get('url', '')
    if not url:
        return jsonify({'code': 400, 'msg': '缺少url参数'})
    
    parsed = urlparse(url)
    if not parsed.scheme in ('http', 'https'):
        return jsonify({'code': 400, 'msg': '只支持http/https链接'})
    if not parsed.hostname or host_is_private(parsed.hostname):
        return jsonify({'code': 400, 'msg': '不允许访问内网或本机地址'})

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': parsed.netloc
        }
        resp = requests.get(url, headers=headers, timeout=15, stream=True)
        content_type = resp.headers.get('content-type', '')
        if resp.status_code != 200:
            return jsonify({'code': 404, 'msg': '图片下载失败'})
        if not content_type.startswith('image/'):
            return jsonify({'code': 400, 'msg': '目标链接不是图片'})

        chunks = []
        total = 0
        for chunk in resp.iter_content(chunk_size=65536):
            if not chunk:
                continue
            total += len(chunk)
            if total > MAX_PROXY_IMAGE_SIZE:
                return jsonify({'code': 413, 'msg': '图片过大，最大支持10MB'})
            chunks.append(chunk)

        from flask import Response
        return Response(b''.join(chunks), content_type=content_type or 'image/gif')
    except Exception as e:
        return jsonify({'code': 500, 'msg': f'下载失败: {str(e)}'})


# ==================== 富文本课程内容API ====================

@app.route('/api/courses/<int:course_id>/rich-content', methods=['GET'])
def get_rich_content(course_id):
    """获取课程富文本内容"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT rich_content FROM courses WHERE id=?', (course_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return jsonify({'code': 404, 'msg': '课程不存在'})
    return jsonify({'code': 200, 'data': {'rich_content': row[0] or ''}})


@app.route('/api/courses/<int:course_id>/rich-content', methods=['PUT'])
@login_required
def save_rich_content(course_id):
    """保存课程富文本内容"""
    data = request.json
    rich_html = sanitize_rich_html(data.get('rich_content', ''))
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE courses SET rich_content=? WHERE id=?', (rich_html, course_id))
    cursor.execute('DELETE FROM course_modules WHERE course_id=?', (course_id,))
    cursor.execute('''
        INSERT INTO course_modules (course_id, type, title, content, sort_order)
        VALUES (?, 'html', '课程内容', ?, 1)
    ''', (course_id, rich_html))
    conn.commit()
    conn.close()
    return jsonify({'code': 200, 'msg': '保存成功'})


# ==================== 课程内容模块API ====================

@app.route('/api/courses/<int:course_id>/modules', methods=['GET'])
def get_course_modules(course_id):
    """获取课程内容模块"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, type, title, content, sort_order 
        FROM course_modules 
        WHERE course_id=? 
        ORDER BY sort_order
    ''', (course_id,))
    modules = cursor.fetchall()
    conn.close()

    return jsonify({
        'code': 200,
        'data': [{
            'id': m[0],
            'type': m[1],
            'title': m[2],
            'content': m[3],
            'sort_order': m[4]
        } for m in modules]
    })

# ==================== 学习进度API ====================

@app.route('/api/courses/<int:course_id>/progress', methods=['POST'])
def report_progress(course_id):
    """上报学习进度（UPSERT）"""
    data = request.json
    driver_name = data.get('driver_name', '').strip()
    module_id = data.get('module_id')
    module_type = data.get('module_type', 'video')
    try:
        module_id = int(module_id)
        played_percent = max(0, min(float(data.get('played_percent', 0)), 100))
        watched_seconds = max(0, float(data.get('watched_seconds', 0)))
    except (TypeError, ValueError):
        return jsonify({'code': 400, 'msg': '进度参数无效'}), 400

    print(f'[PROGRESS POST] course={course_id} driver={driver_name} module={module_id} type={module_type} pct={played_percent} sec={watched_seconds}')

    if not driver_name or module_id is None:
        print('[PROGRESS POST] REJECTED: missing params')
        return jsonify({'code': 400, 'msg': '缺少必要参数'}), 400

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT type, content FROM course_modules WHERE id=? AND course_id=?', (module_id, course_id))
    module_row = cursor.fetchone()
    if not module_row:
        conn.close()
        return jsonify({'code': 404, 'msg': '学习模块不存在'}), 404
    if not is_video_content(module_row[0], module_row[1]):
        conn.close()
        return jsonify({'code': 400, 'msg': '该模块不是视频学习内容'}), 400

    # 本地视频按播放比例，B站/外链视频按有效观看计时。
    is_completed = 1 if (played_percent >= 90 or watched_seconds >= 90) else 0

    # 检查是否已有记录
    cursor.execute(
        'SELECT id, is_completed FROM learning_progress WHERE course_id=? AND driver_name=? AND module_id=?',
        (course_id, driver_name, module_id)
    )
    existing = cursor.fetchone()

    if existing:
        # 已完成的不再降级
        if existing[1] == 1:
            conn.close()
            print(f'[PROGRESS POST] SKIP: already completed id={existing[0]}')
            return jsonify({'code': 200, 'data': {'is_completed': True}})
        cursor.execute('''
            UPDATE learning_progress SET played_percent=?, watched_seconds=?, is_completed=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        ''', (played_percent, watched_seconds, is_completed, existing[0]))
        print(f'[PROGRESS POST] UPDATE id={existing[0]} is_completed={is_completed}')
    else:
        cursor.execute('''
            INSERT INTO learning_progress (course_id, driver_name, module_id, module_type, played_percent, watched_seconds, is_completed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (course_id, driver_name, module_id, module_type, played_percent, watched_seconds, is_completed))
        print(f'[PROGRESS POST] INSERT is_completed={is_completed}')

    conn.commit()
    conn.close()
    print(f'[PROGRESS POST] DONE -> is_completed={is_completed}')
    return jsonify({'code': 200, 'data': {'is_completed': is_completed == 1}})


@app.route('/api/courses/<int:course_id>/progress', methods=['GET'])
def get_progress(course_id):
    """查询驾驶员在某课程的学习进度"""
    driver_name = request.args.get('driver_name', '').strip()
    print(f'[PROGRESS GET] course={course_id} driver={driver_name}')
    if not driver_name:
        return jsonify({'code': 400, 'msg': '缺少driver_name参数'})

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    all_modules = get_required_video_modules(cursor, course_id)
    print(f'[PROGRESS GET] found {len(all_modules)} video modules: {[(m["id"], m["type"]) for m in all_modules]}')

    # 查询该驾驶员在此课程的进度
    cursor.execute(
        'SELECT module_id, played_percent, watched_seconds, is_completed FROM learning_progress WHERE course_id=? AND driver_name=?',
        (course_id, driver_name)
    )
    progress_rows = cursor.fetchall()
    progress_map = {r[0]: r for r in progress_rows}
    print(f'[PROGRESS GET] progress rows: {[(r[0], r[3]) for r in progress_rows]}')

    modules_result = []
    all_completed = True
    has_video_module = False

    for m in all_modules:
        mid = m['id']
        mtitle = m['title']
        has_video_module = True
        p = progress_map.get(mid)
        is_completed = bool(p[3]) if p else False
        print(f'[PROGRESS GET] module {mid} ({mtitle}) completed={is_completed} pct={p[1] if p else 0}')
        modules_result.append({
            'module_id': mid,
            'title': mtitle,
            'is_completed': is_completed,
            'played_percent': p[1] if p else 0,
            'watched_seconds': p[2] if p else 0
        })
        if not is_completed:
            all_completed = False

    # 没有视频模块也算完成
    if not has_video_module:
        all_completed = True

    print(f'[PROGRESS GET] RESULT: all_completed={all_completed} has_video={has_video_module}')
    conn.close()
    return jsonify({
        'code': 200,
        'data': {
            'modules': modules_result,
            'all_videos_completed': all_completed
        }
    })


# ==================== 调试端点（上线前记得删） ====================

@app.route('/api/debug/progress/<int:course_id>')
@login_required
def debug_progress(course_id):
    """临时调试：查看 learning_progress 表原始数据"""
    driver_name = request.args.get('driver_name', '')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if driver_name:
        cursor.execute('SELECT * FROM learning_progress WHERE course_id=? AND driver_name=?', (course_id, driver_name))
    else:
        cursor.execute('SELECT * FROM learning_progress WHERE course_id=?', (course_id,))
    rows = cursor.fetchall()
    cols = [d[0] for d in cursor.description]
    conn.close()
    return jsonify({'code': 200, 'columns': cols, 'rows': [dict(zip(cols, r)) for r in rows]})


@app.route('/api/courses/<int:course_id>/modules', methods=['POST'])
@login_required
def add_module(course_id):
    """添加内容模块"""
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO course_modules (course_id, type, title, content, sort_order)
        VALUES (?, ?, ?, ?, ?)
    ''', (course_id, data['type'], data.get('title', ''), data['content'], data.get('sort_order', 0)))
    conn.commit()
    conn.close()
    return jsonify({'code': 200, 'msg': '添加成功'})

@app.route('/api/modules/<int:module_id>', methods=['PUT'])
@login_required
def update_module(module_id):
    """更新内容模块"""
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE course_modules SET type=?, title=?, content=?, sort_order=?
        WHERE id=?
    ''', (data['type'], data.get('title', ''), data['content'], data.get('sort_order', 0), module_id))
    conn.commit()
    conn.close()
    return jsonify({'code': 200, 'msg': '更新成功'})

@app.route('/api/modules/<int:module_id>', methods=['DELETE'])
@login_required
def delete_module(module_id):
    """删除内容模块"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM course_modules WHERE id=?', (module_id,))
    conn.commit()
    conn.close()
    return jsonify({'code': 200, 'msg': '删除成功'})

@app.route('/api/courses/<int:course_id>/modules/reorder', methods=['POST'])
@login_required
def reorder_modules(course_id):
    """重新排序内容模块"""
    data = request.json
    module_ids = data.get('module_ids', [])
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for i, module_id in enumerate(module_ids):
        cursor.execute('UPDATE course_modules SET sort_order=? WHERE id=? AND course_id=?',
                      (i, module_id, course_id))
    conn.commit()
    conn.close()
    return jsonify({'code': 200, 'msg': '排序已更新'})


# ==================== 题目管理API（支持多选） ====================

@app.route('/api/courses/<int:course_id>/questions', methods=['GET'])
@login_required
def get_course_questions(course_id):
    """获取课程题目列表（含答案，供管理后台使用）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, question, options, question_type, answer, sort_order 
        FROM questions 
        WHERE course_id=? 
        ORDER BY sort_order
    ''', (course_id,))
    questions = cursor.fetchall()
    conn.close()

    result = []
    for q in questions:
        answer_data = parse_answer(q[4])
        result.append({
            'id': q[0],
            'question': q[1],
            'options': json.loads(q[2]),
            'question_type': q[3] or 'single',
            'answer': answer_data,
            'sort_order': q[5]
        })
    return jsonify({'code': 200, 'data': result})

@app.route('/api/courses/<int:course_id>/exam', methods=['GET'])
def get_exam_questions(course_id):
    """获取考试题目（不返回答案）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, question, options, question_type
        FROM questions 
        WHERE course_id=? 
        ORDER BY sort_order
    ''', (course_id,))
    questions = cursor.fetchall()
    conn.close()

    return jsonify({
        'code': 200,
        'data': [{
            'id': q[0],
            'question': q[1],
            'options': json.loads(q[2]),
            'question_type': q[3] or 'single'
        } for q in questions]
    })

@app.route('/api/courses/<int:course_id>/questions', methods=['POST'])
@login_required
def add_question(course_id):
    """添加题目"""
    data = request.json
    answer_str = format_answer(data['answer'])
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO questions (course_id, question, options, question_type, answer, sort_order)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (course_id, data['question'], json.dumps(data['options'], ensure_ascii=False),
          data.get('question_type', 'single'), answer_str, data.get('sort_order', 0)))
    conn.commit()
    conn.close()
    return jsonify({'code': 200, 'msg': '添加成功'})

@app.route('/api/questions/<int:question_id>', methods=['PUT'])
@login_required
def update_question(question_id):
    """更新题目"""
    data = request.json
    answer_str = format_answer(data['answer'])
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE questions SET question=?, options=?, question_type=?, answer=?, sort_order=?
        WHERE id=?
    ''', (data['question'], json.dumps(data['options'], ensure_ascii=False),
          data.get('question_type', 'single'), answer_str,
          data.get('sort_order', 0), question_id))
    conn.commit()
    conn.close()
    return jsonify({'code': 200, 'msg': '更新成功'})

@app.route('/api/questions/<int:question_id>', methods=['DELETE'])
@login_required
def delete_question(question_id):
    """删除题目"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM questions WHERE id=?', (question_id,))
    conn.commit()
    conn.close()
    return jsonify({'code': 200, 'msg': '删除成功'})

@app.route('/api/courses/<int:course_id>/questions/reorder', methods=['POST'])
@login_required
def reorder_questions(course_id):
    """重新排序题目"""
    data = request.json
    question_ids = data.get('question_ids', [])
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for i, question_id in enumerate(question_ids):
        cursor.execute('UPDATE questions SET sort_order=? WHERE id=? AND course_id=?',
                      (i, question_id, course_id))
    conn.commit()
    conn.close()
    return jsonify({'code': 200, 'msg': '排序已更新'})


# ==================== 成绩管理API ====================

@app.route('/api/courses/<int:course_id>/check', methods=['POST'])
@login_required
def check_answers(course_id):
    """检查答案（支持多选：全对才得分）"""
    data = request.json
    answers = data.get('answers', [])

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    results = []
    for ans in answers:
        cursor.execute('SELECT question_type, answer FROM questions WHERE id=? AND course_id=?',
                      (ans['question_id'], course_id))
        row = cursor.fetchone()
        if row:
            q_type = row[0] or 'single'
            correct_answers = parse_answer(row[1])
            selected = ans.get('selected', [])

            # 标准化为列表
            if not isinstance(selected, list):
                selected = [selected]

            if q_type == 'multiple':
                # 多选题：选中的答案集合 == 正确答案集合（全对才得分）
                is_correct = set(selected) == set(correct_answers)
            else:
                # 单选题：完全匹配
                is_correct = (len(selected) == 1 and selected[0] == correct_answers[0])

            results.append({
                'question_id': ans['question_id'],
                'selected': selected,
                'is_correct': is_correct
            })

    conn.close()

    correct_count = sum(1 for r in results if r['is_correct'])
    total = len(results)
    score = int((correct_count / total * 100)) if total > 0 else 0

    return jsonify({
        'code': 200,
        'data': {
            'results': results,
            'score': score,
            'correct_count': correct_count,
            'total': total
        }
    })

@app.route('/api/courses/<int:course_id>/scores', methods=['POST'])
def submit_score(course_id):
    """提交成绩（后端判分，不信任前端数据）"""
    data = request.json
    driver_name = data.get('driver_name', '').strip()
    if not driver_name or driver_name == '未知':
        return jsonify({'code': 400, 'msg': '缺少驾驶员姓名'}), 400

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    answers = data.get('answers', [])
    if not isinstance(answers, list):
        conn.close()
        return jsonify({'code': 400, 'msg': '答案格式无效'}), 400

    if REQUIRE_VIDEO_PROGRESS:
        progress_ok, incomplete_modules = has_completed_required_videos(cursor, course_id, driver_name)
        if not progress_ok:
            conn.close()
            return jsonify({
                'code': 403,
                'msg': '请先完成视频学习',
                'data': {'incomplete': [m['title'] for m in incomplete_modules]}
            }), 403

    cursor.execute('''
        SELECT id, question_type, answer
        FROM questions
        WHERE course_id=?
        ORDER BY sort_order
    ''', (course_id,))
    question_rows = cursor.fetchall()
    if not question_rows:
        conn.close()
        return jsonify({'code': 400, 'msg': '该课程暂无考试题目'}), 400

    answer_map = {}
    for ans in answers:
        try:
            qid = int(ans.get('question_id'))
        except (TypeError, ValueError, AttributeError):
            conn.close()
            return jsonify({'code': 400, 'msg': '答案中包含无效题目'}), 400
        selected = ans.get('selected', [])
        if selected is None:
            selected = []
        if not isinstance(selected, list):
            selected = [selected]
        try:
            normalized_selected = [int(x) for x in selected]
        except (TypeError, ValueError):
            conn.close()
            return jsonify({'code': 400, 'msg': '答案选项无效'}), 400
        answer_map[qid] = normalized_selected

    required_ids = {row[0] for row in question_rows}
    submitted_ids = set(answer_map.keys())
    if submitted_ids != required_ids:
        conn.close()
        return jsonify({'code': 400, 'msg': '请完成全部题目后再提交'}), 400

    # 后端重新判分：根据 question_id + selected 查题库校验
    correct_count = 0
    server_results = []
    for qid, q_type, raw_answer in question_rows:
        selected = answer_map[qid]
        correct_answers = parse_answer(raw_answer)
        if q_type == 'multiple':
            is_correct = set(selected) == set(correct_answers)
        else:
            is_correct = (len(selected) == 1 and selected[0] == correct_answers[0])

        if is_correct:
            correct_count += 1
        server_results.append({
            'question_id': qid,
            'selected': selected,
            'is_correct': is_correct
        })

    total = len(question_rows)
    score = int((correct_count / total * 100)) if total > 0 else 0

    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip_address and ',' in ip_address:
        ip_address = ip_address.split(',')[0].strip()

    cursor.execute('''
        INSERT INTO scores (course_id, driver_name, driver_phone, driver_city, driver_plate, ip_address, score, total_questions, correct_count, answers)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        course_id,
        driver_name,
        data.get('driver_phone', ''),
        data.get('driver_city', ''),
        data.get('driver_plate', ''),
        ip_address,
        score,
        total,
        correct_count,
        json.dumps(server_results, ensure_ascii=False)
    ))
    # 考试提交后清除学习进度，允许重新学习
    cursor.execute('DELETE FROM learning_progress WHERE course_id=? AND driver_name=?',
                  (course_id, driver_name))
    conn.commit()
    conn.close()

    return jsonify({
        'code': 200,
        'msg': '提交成功',
        'data': {
            'score': score,
            'correct_count': correct_count,
            'total': total,
            'results': server_results
        }
    })

@app.route('/api/courses/<int:course_id>/scores', methods=['GET'])
@login_required
def get_course_scores(course_id):
    """获取课程成绩列表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, driver_name, driver_phone, driver_city, driver_plate, ip_address, score, total_questions, correct_count, created_at
        FROM scores WHERE course_id=? ORDER BY created_at DESC
    ''', (course_id,))
    scores = cursor.fetchall()
    conn.close()

    return jsonify({
        'code': 200,
        'data': [{
            'id': s[0],
            'driver_name': s[1],
            'driver_phone': s[2],
            'driver_city': s[3] or '',
            'driver_plate': s[4] or '',
            'ip_address': s[5] or '',
            'score': s[6],
            'total_questions': s[7],
            'correct_count': s[8],
            'created_at': s[9]
        } for s in scores]
    })

@app.route('/api/courses/<int:course_id>/scores/export', methods=['GET'])
@login_required
def export_course_scores(course_id):
    """导出课程成绩Excel"""
    conn = sqlite3.connect(DB_PATH)
    
    cursor = conn.cursor()
    cursor.execute('SELECT title FROM courses WHERE id=?', (course_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({'code': 404, 'msg': '课程不存在'}), 404
    course_title = row[0]
    
    df = pd.read_sql_query('''
        SELECT
            driver_name as '驾驶员姓名',
            driver_city as '运营城市',
            driver_plate as '车牌号',
            driver_phone as '联系电话',
            ip_address as 'IP地址',
            score as '得分',
            total_questions as '总题数',
            correct_count as '正确数',
            created_at as '考试时间'
        FROM scores WHERE course_id=? ORDER BY created_at DESC
    ''', conn, params=(course_id,))
    conn.close()

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='考试成绩')
    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'{course_title}_考试成绩_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )


# ==================== 启动服务 ====================

if __name__ == '__main__':
    init_db()
    ip = get_local_ip()
    port = int(os.environ.get('PORT', 8888))
    debug = os.environ.get('FLASK_DEBUG', '').lower() in ('1', 'true', 'yes')
    print("🚀 轻卡安全大讲堂服务 V3.0 启动中...")
    print(f"📱 驾驶员端(本机): http://localhost:{port}")
    print(f"📱 驾驶员端(局域网): http://{ip}:{port}")
    print(f"⚙️  管理后台(本机): http://localhost:{port}/admin")
    print(f"⚙️  管理后台(局域网): http://{ip}:{port}/admin")
    if debug:
        print("⚠️  当前启用了 FLASK_DEBUG，仅限本机开发使用")
    app.run(host=os.environ.get('HOST', '0.0.0.0'), port=port, debug=debug)
