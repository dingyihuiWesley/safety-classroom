#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为课程添加图片和视频素材
"""

import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'data.db')

# 已生成的图片路径（相对于 /static）
COURSE_MATERIALS = {
    # 课程ID: 课程名称关键词
    5: {  # 右侧盲区与内轮差
        "cover_image": "/static/uploads/images/震撼警示海报_大货车右转弯盲区危险_一辆红色大货车正在右转__2026-05-08T06-16-01.png",
        "video_url": "https://www.bilibili.com/video/BV1a1421m78L/",  # 2024年货运车右转盲区警示片
        "video_title": "2024年货运车右转盲区警示片",
        "images": [
            {
                "title": "内轮差原理示意图",
                "url": "/static/uploads/images/震撼警示海报_大货车右转弯盲区危险_一辆红色大货车正在右转__2026-05-08T06-16-01.png",
                "desc": "大货车转弯时的内轮差示意图，红色区域为危险区域"
            }
        ]
    },
    6: {  # 疲劳驾驶
        "cover_image": "/static/uploads/images/震撼警示海报_疲劳驾驶危险_一辆大货车行驶在公路上_驾驶员在_2026-05-08T06-15-56.png",
        "video_url": "https://www.bilibili.com/video/BV1rNp3eUENi/",  # 两客一危一货道路交通安全警示片
        "video_title": "疲劳驾驶事故警示教育片",
        "images": [
            {
                "title": "疲劳驾驶危险",
                "url": "/static/uploads/images/震撼警示海报_疲劳驾驶危险_一辆大货车行驶在公路上_驾驶员在_2026-05-08T06-15-56.png",
                "desc": "驾驶员疲劳驾驶，眼睛半闭，极易发生事故"
            }
        ]
    },
    7: {  # 分心驾驶
        "cover_image": "/static/uploads/images/震撼警示海报_分心驾驶危险_一辆大货车正在行驶_司机一只手拿_2026-05-08T06-14-59.png",
        "video_url": "https://haokan.baidu.com/v?pd=wisenatural&vid=3237002548740270445",  # 公安部疲劳驾驶警示片
        "video_title": "分心驾驶危害警示片",
        "images": [
            {
                "title": "分心驾驶危险",
                "url": "/static/uploads/images/震撼警示海报_分心驾驶危险_一辆大货车正在行驶_司机一只手拿_2026-05-08T06-14-59.png",
                "desc": "开车看手机5秒，盲开100米，相当于足球场长度"
            }
        ]
    },
    8: {  # 新能源电池安全
        "cover_image": "/static/uploads/images/a90b53d04b924c83953b531536635659.png",  # 使用现有的科技感图片
        "video_url": "https://v.qq.com/x/page/j3537w3yqd5.html",  # 2024年道路交通事故警示教育片
        "video_title": "新能源汽车安全警示片",
        "images": [
            {
                "title": "新能源电池热失控",
                "url": "/static/uploads/images/a90b53d04b924c83953b531536635659.png",
                "desc": "动力电池热失控，仅需数十秒即可爆燃"
            }
        ]
    },
    9: {  # 超载超限
        "cover_image": "/static/uploads/images/震撼警示海报_货车超载危险_一辆严重超载的货车轮胎被压扁_旁_2026-05-08T06-15-56.png",
        "video_url": "https://v.qq.com/x/page/l3330xywx8d.html",  # 货车超限超载交通事故警示教育片
        "video_title": "货车超载事故警示片",
        "images": [
            {
                "title": "超载危害",
                "url": "/static/uploads/images/震撼警示海报_货车超载危险_一辆严重超载的货车轮胎被压扁_旁_2026-05-08T06-15-56.png",
                "desc": "超载导致刹车距离增加3-5倍，易发生侧翻"
            }
        ]
    },
    10: {  # 酒后驾驶
        "cover_image": "/static/uploads/images/f4c1195676994d43bd1f3fa566e3bafb.png",  # 使用现有的警示图片
        "video_url": "https://www.bilibili.com/video/BV1rNp3eUENi/",
        "video_title": "酒驾醉驾警示教育片",
        "images": [
            {
                "title": "酒驾醉驾标准",
                "url": "/static/uploads/images/f4c1195676994d43bd1f3fa566e3bafb.png",
                "desc": "血液酒精含量80mg/100ml以上即为醉驾，构成犯罪"
            }
        ]
    },
    11: {  # 人伤/亡事故警示
        "cover_image": "/static/uploads/images/3b58aa36bc1f43a7a78600bbf54f3c4d.png",  # 使用现有的事故图片
        "video_url": "https://v.qq.com/x/page/j3537w3yqd5.html",  # 2024年道路交通事故警示教育片
        "video_title": "道路交通事故警示片",
        "images": [
            {
                "title": "交通事故警示",
                "url": "/static/uploads/images/3b58aa36bc1f43a7a78600bbf54f3c4d.png",
                "desc": "交通事故现场，珍爱生命，安全驾驶"
            }
        ]
    },
    12: {  # 防御性驾驶
        "cover_image": "/static/uploads/images/震撼警示海报_防御性驾驶技术_一辆大货车安全行驶在公路上_周_2026-05-08T06-16-48.png",
        "video_url": "https://www.bilibili.com/video/BV1rNp3eUENi/",
        "video_title": "防御性驾驶技术教学片",
        "images": [
            {
                "title": "防御性驾驶",
                "url": "/static/uploads/images/震撼警示海报_防御性驾驶技术_一辆大货车安全行驶在公路上_周_2026-05-08T06-16-48.png",
                "desc": "预见危险，远离事故，安全驾驶"
            }
        ]
    }
}


def add_materials():
    """为课程添加图片和视频素材"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    updated_courses = []

    for course_id, materials in COURSE_MATERIALS.items():
        # 获取课程标题
        cursor.execute('SELECT title FROM courses WHERE id=?', (course_id,))
        result = cursor.fetchone()
        if not result:
            print(f"❌ 课程ID {course_id} 不存在")
            continue

        course_title = result[0]
        print(f"📚 为课程添加素材: {course_title}")

        # 更新课程封面图
        if materials.get("cover_image"):
            cursor.execute('UPDATE courses SET cover_image=? WHERE id=?',
                         (materials["cover_image"], course_id))
            print(f"   ✅ 更新封面图")

        # 添加视频模块
        if materials.get("video_url"):
            # 获取当前最大sort_order
            cursor.execute('SELECT COALESCE(MAX(sort_order), 0) + 1 FROM course_modules WHERE course_id=?', (course_id,))
            next_order = cursor.fetchone()[0]

            video_html = f'''<div style="background:#e3f2fd; padding:20px; border-radius:10px; margin:10px 0;">
<h4 style="color:#1565c0;">🎬 视频学习：{materials.get("video_title", "警示教育片")}</h4>
<p style="margin:10px 0;">点击下方链接观看完整视频：</p>
<p><a href="{materials["video_url"]}" target="_blank" style="color:#1976d2; font-size:16px; font-weight:bold;">👉 点击观看：{materials.get("video_title", "警示教育片")}</a></p>
<p style="color:#666; font-size:12px;">提示：视频来源为官方交通安全警示片，建议完整观看</p>
</div>'''

            cursor.execute('''
                INSERT INTO course_modules (course_id, type, title, content, sort_order)
                VALUES (?, 'html', '视频学习', ?, ?)
            ''', (course_id, video_html, next_order))
            print(f"   ✅ 添加视频模块")

        # 添加图片模块
        if materials.get("images"):
            for img in materials["images"]:
                cursor.execute('SELECT COALESCE(MAX(sort_order), 0) + 1 FROM course_modules WHERE course_id=?', (course_id,))
                next_order = cursor.fetchone()[0]

                img_html = f'''<div style="background:#fff; padding:15px; border-radius:10px; margin:10px 0; text-align:center;">
<h4 style="color:#333;">{img["title"]}</h4>
<img src="{img["url"]}" alt="{img["title"]}" style="max-width:100%; border-radius:8px; margin:10px 0;">
<p style="color:#666; font-size:14px;">{img["desc"]}</p>
</div>'''

                cursor.execute('''
                    INSERT INTO course_modules (course_id, type, title, content, sort_order)
                    VALUES (?, 'html', '配图学习', ?, ?)
                ''', (course_id, img_html, next_order))
                print(f"   ✅ 添加图片模块: {img['title']}")

        updated_courses.append(course_title)

    conn.commit()
    conn.close()

    print(f"\n🎉 完成！共更新 {len(updated_courses)} 个课程")
    for title in updated_courses:
        print(f"  - {title}")

    return updated_courses


if __name__ == '__main__':
    add_materials()
