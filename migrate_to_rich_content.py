#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
课程内容迁移脚本
将 course_modules 表中的旧格式内容迁移到 courses.rich_content 字段
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'data.db')

def migrate_modules_to_rich_content():
    """将 course_modules 内容迁移到 courses.rich_content"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 获取所有课程
    cursor.execute('SELECT id, title FROM courses')
    courses = cursor.fetchall()

    migrated_count = 0

    for course_id, course_title in courses:
        # 检查该课程是否有模块内容但 rich_content 为空或只有占位符
        cursor.execute('''
            SELECT type, title, content
            FROM course_modules
            WHERE course_id = ?
            ORDER BY sort_order
        ''', (course_id,))
        modules = cursor.fetchall()

        if not modules:
            print(f"课程 {course_id}: {course_title} - 无模块内容，跳过")
            continue

        # 检查 rich_content 是否为空或只有占位符
        cursor.execute('SELECT rich_content FROM courses WHERE id = ?', (course_id,))
        row = cursor.fetchone()
        current_rich = row[0] if row else ''

        # 如果 rich_content 已经有效，跳过
        if current_rich and current_rich.strip() not in ['', '<p></p>', '<p>在这里开始编辑课程内容...</p>', '<p><br></p>']:
            print(f"课程 {course_id}: {course_title} - rich_content 已有效，跳过")
            continue

        # 构建 HTML 内容
        html_parts = []
        for m_type, m_title, m_content in modules:
            if m_type == 'text':
                html_parts.append(f'<h2>{m_title}</h2>')
                # 处理换行符
                for line in m_content.split('\n'):
                    line = line.strip()
                    if line:
                        html_parts.append(f'<p>{line}</p>')
            elif m_type == 'html':
                if m_title:
                    html_parts.append(f'<h2>{m_title}</h2>')
                html_parts.append(m_content)
            elif m_type in ('image', 'gif'):
                html_parts.append(f'<h2>{m_title}</h2>')
                html_parts.append(f'<div class="media-wrap"><img src="{m_content}" alt="{m_title}"></div>')
            elif m_type == 'video':
                html_parts.append(f'<h2>{m_title}</h2>')
                # 尝试解析 B 站视频
                if 'bilibili.com' in m_content or 'BV' in m_content:
                    import re
                    bv_match = re.search(r'BV([\w]+)', m_content)
                    if bv_match:
                        bv = bv_match.group(0).replace('video/', '')
                        html_parts.append(f'''<div class="media-wrap" style="position:relative;padding-bottom:56.25%;height:0;overflow:hidden;border-radius:10px;background:#000;">
                            <iframe src="//player.bilibili.com/player.html?bvid={bv}&page=1" frameborder="0" allowfullscreen style="position:absolute;top:0;left:0;width:100%;height:100%;"></iframe>
                        </div>''')
                    else:
                        html_parts.append(f'<div class="media-wrap"><video controls src="{m_content}"></video></div>')
                else:
                    html_parts.append(f'<div class="media-wrap"><video controls src="{m_content}"></video></div>')

        if html_parts:
            new_rich_content = '\n'.join(html_parts)
            cursor.execute('UPDATE courses SET rich_content = ? WHERE id = ?', (new_rich_content, course_id))
            migrated_count += 1
            print(f"✅ 迁移成功: 课程 {course_id}: {course_title}")
        else:
            print(f"⚠️  无有效内容: 课程 {course_id}: {course_title}")

    conn.commit()
    conn.close()

    print(f"\n迁移完成！共迁移 {migrated_count} 个课程")
    return migrated_count

if __name__ == '__main__':
    migrate_modules_to_rich_content()
