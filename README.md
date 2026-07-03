# 轻卡安全大讲堂 V2.0

## 功能特性

### 驾驶员端
- 课程列表展示（支持多课程分类）
- 模块化学习内容（文字 + 视频 + 图片 + 动图）
- 视频支持B站视频嵌入
- 学习进度追踪
- 在线考试（自动判分）
- 成绩展示

### 管理后台
- **课程管理**：添加/编辑/删除课程
- **内容管理**：添加/编辑/删除学习模块（支持4种类型）
  - 📄 文字内容
  - 🎬 视频内容（支持B站链接）
  - 🖼️ 图片内容
  - 🎞️ 动图内容
- **题库管理**：问卷星式题目编辑器
  - 支持单选/多选题
  - 可视化选项编辑
  - 正确答案标记
- **成绩管理**：查看成绩、导出Excel
- **二维码生成**：一键生成课程入口二维码
- **管理员登录验证**

---

## 快速开始

### 1. 安装依赖

```bash
cd safety-classroom
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python app.py
```

服务启动后：
- **驾驶员端**：`http://localhost:8888`
- **管理后台**：`http://localhost:8888/admin`

### 3. 登录管理后台

- **主账号**：`cidi`
- 首次初始化时如未设置 `DEFAULT_ADMIN_PASSWORD`，服务会生成一次性随机密码并打印到启动日志。生产环境请显式设置强密码并登录后立即修改。

---

## 二、项目结构

```
safety-classroom/
├── app.py              # Flask后端主程序
├── requirements.txt    # Python依赖
├── templates/
│   ├── index.html      # 驾驶员端首页（课程列表）
│   ├── course.html     # 课程学习页面
│   ├── exam.html      # 在线考试页面
│   └── admin.html     # 管理后台
└── data.db            # SQLite数据库（自动生成）
```

---

## 三、管理后台使用指南

### 3.1 课程管理

1. 点击「+ 添加课程」
2. 填写课程名称、介绍、及格分数
3. 保存

### 3.2 添加学习内容

1. 在课程列表点击「内容管理」
2. 点击「+ 添加内容」
3. 选择内容类型：
   - **文字**：直接输入文字内容
   - **视频**：输入B站视频链接或普通视频URL
   - **图片**：输入图片URL
   - **动图**：输入GIF链接
4. 设置标题和排序
5. 保存

### 3.3 添加考试题目

1. 在课程详情页，点击「+ 添加题目」
2. 输入题目内容
3. 填写选项（A/B/C/D）
4. 点击单选按钮选择正确答案
5. 保存

### 3.4 生成二维码

1. 点击左侧「入口二维码」
2. 每个课程会显示对应的二维码
3. 可直接截图发给驾驶员

### 3.5 查看成绩

1. 点击左侧「成绩管理」
2. 选择课程
3. 查看成绩列表
4. 点击「导出Excel」下载成绩单

---

## 四、API接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/courses` | GET | 获取课程列表 |
| `/api/courses/<id>` | GET | 获取课程详情 |
| `/api/courses/<id>/modules` | GET/POST | 获取/添加内容模块 |
| `/api/courses/<id>/questions` | GET/POST | 获取/添加题目 |
| `/api/courses/<id>/scores` | GET/POST | 获取/提交成绩 |
| `/api/courses/<id>/scores/export` | GET | 导出成绩Excel |

---

## 五、部署说明

### 生产环境部署

1. 安装 Python 依赖和系统视频工具：
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Linux 服务器建议安装，用于上传视频后生成缩略图
sudo apt-get update && sudo apt-get install -y ffmpeg
```

2. 设置生产环境变量：
```bash
export SECRET_KEY='replace-with-a-long-random-secret'
export CORS_ORIGINS='https://your-domain.com'
export PORT=8888

# 如需恢复“视频学习完成后才能考试”，再打开这一项
# export REQUIRE_VIDEO_PROGRESS=1
```

3. 使用 Gunicorn 启动：
```bash
gunicorn -w 2 -b 127.0.0.1:8888 wsgi:app
```

4. 使用 Nginx 反向代理，并把上传体限制调大：
```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 250m;

    location / {
        proxy_pass http://127.0.0.1:8888;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

5. 需要一起部署/备份的数据：
- `data.db`：课程、题目、成绩、管理员账号
- `static/uploads/`：图片、视频、缩略图素材
- `templates/`、`app.py`、`wsgi.py`、`requirements.txt`

不要上传 `venv/`、`__pycache__/`、`*.log`、`.DS_Store`。

### 服务器部署

将项目上传到服务器后：
```bash
cd safety-classroom
pip install -r requirements.txt
SECRET_KEY='replace-with-a-long-random-secret' gunicorn -w 2 -b 127.0.0.1:8888 wsgi:app
```

---

## 六、常见问题

### Q: 端口被占用？
使用环境变量指定端口：
```bash
PORT=5001 python app.py
```

### Q: 如何修改管理员密码？
管理后台 → 系统设置 → 修改密码

### Q: 如何添加更多管理员？
目前只支持单管理员。如需多管理员，可以扩展admin_users表

### Q: B站视频无法播放？
确保使用完整的B站视频链接，如：
`https://www.bilibili.com/video/BV1xx411c7mD`

---

## 七、技术栈

- **后端**：Python 3 + Flask
- **数据库**：SQLite
- **前端**：HTML5 + CSS3 + JavaScript
- **图表**：原生CSS，无依赖
- **二维码**：api.qrserver.com
