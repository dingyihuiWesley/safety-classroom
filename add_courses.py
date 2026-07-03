#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
轻卡安全大讲堂 - 批量添加安全课程内容
"""

import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'data.db')

# 课程数据（精简版，每个课程5道题）
COURSES_DATA = [
    {
        "title": "🚛 右侧盲区与内轮差（必学）",
        "description": "学习大货车右转弯盲区的危险性，掌握右转必停操作规范，避免死亡弯月事故",
        "passing_score": 80,
        "modules": [
            {
                "type": "text",
                "title": "📖 什么是死亡弯月",
                "content": """<h3>🚛 大货车右转弯的死亡弯月</h3>

<p style="color:#d32f2f; font-size:18px; font-weight:bold;">⚠️ 90%的大型车辆右转事故都是因为它！</p>

<h4>一、什么是内轮差？</h4>
<p>大型车辆在转弯时，前轮和后轮的转弯轨迹不同。后轮的转弯半径比前轮小，形成一个<strong>月牙形的危险区域</strong>，这个区域就是死亡弯月。</p>

<h4>二、盲区的四大杀手</h4>
<ul>
<li><strong>主驾盲区</strong>：右侧A柱遮挡约35度角</li>
<li><strong>内轮差盲区</strong>：前后轮转弯半径差可达2米以上</li>
<li><strong>货物遮挡盲区</strong>：重型货车货物高度影响后视镜视野</li>
<li><strong>低身高盲区</strong>：儿童、老年人、骑行人员</li>
</ul>

<h4>三、惨烈案例</h4>
<blockquote style="background:#ffebee; border-left:4px solid #d32f2f; padding:15px;">
<p>2024年某地，李某驾驶重型货车右转时，未注意右侧电动车骑行者。电动车进入盲区后被碾压，李某浑然不知继续行驶，造成骑行者当场死亡。</p>
<p><strong>法院判决：交通肇事罪，有期徒刑2年，缓刑3年。</strong></p>
</blockquote>"""
            },
            {
                "type": "text",
                "title": "⚖️ 法律法规依据",
                "content": """<h3>📜 相关法律法规</h3>

<h4>一、《道路交通安全法》第三十八条</h4>
<p>车辆、行人应当按照交通信号通行；在没有交通信号的道路上，应当在确保安全、畅通的原则下通行。</p>

<h4>二、《道路交通安全法实施条例》</h4>
<p>机动车通过交叉路口，应当按照交通信号灯、交通标志、交通标线或者交通警察的指挥通过。</p>

<h4>三、交通肇事后果（重点！）</h4>
<table style="width:100%; border-collapse:collapse; background:#fff3e0;">
<tr style="background:#ff9800; color:white;">
<th>事故情形</th><th>责任</th><th>刑事责任</th>
</tr>
<tr><td>死亡1人</td><td>全部/主要责任</td><td style="color:red;"><b>3年以下有期徒刑</b></td></tr>
<tr><td>死亡3人</td><td>全部/主要责任</td><td style="color:red;"><b>3-7年有期徒刑</b></td></tr>
<tr><td>逃逸</td><td>—</td><td style="color:red;"><b>3-7年有期徒刑</b></td></tr>
<tr><td>逃逸致人死亡</td><td>—</td><td style="color:red;"><b>7年以上有期徒刑</b></td></tr>
</table>"""
            },
            {
                "type": "text",
                "title": "✅ 右转必停操作规范",
                "content": """<h3>🛡️ 右转必停四步操作法</h3>

<div style="background:#e8f5e9; padding:20px; border-radius:10px;">
<h4 style="color:#2e7d32;">第一步：停车观察（3秒）</h4>
<p>在右转弯前，完全停下车辆，不要边转边停。</p>

<h4 style="color:#2e7d32;">第二步：左右瞭望</h4>
<p>从车窗探出头观察右侧和左前方有无行人和车辆。</p>

<h4 style="color:#2e7d32;">第三步：鸣笛提醒</h4>
<p>夜间或复杂路况下，按喇叭提醒周围人员。</p>

<h4 style="color:#2e7d32;">第四步：缓步慢行</h4>
<p>转弯过程中保持低速行驶（&lt;10km/h），随时准备刹车。</p>
</div>

<h3>🚨 特别注意！</h3>
<ul style="color:#c62828;">
<li>⚠️ 车辆360°环视系统只是辅助，不能完全依赖</li>
<li>⚠️ 雨天路滑时更要延长观察时间</li>
<li>⚠️ 夜间行驶盲区更大，建议加装补光灯</li>
</ul>"""
            }
        ],
        "questions": [
            {
                "question": "大货车右转弯时，前后轮轨迹之差叫什么？",
                "options": ["A.刹车距离", "B.内轮差", "C.视野盲区", "D.停车视距"],
                "answer": 1,
                "type": "single"
            },
            {
                "question": "关于右转必停规范，正确的做法是？",
                "options": ["A.边转边停", "B.完全停下观察3秒后再转弯", "C.只看后视镜", "D.快速转弯节省时间"],
                "answer": 1,
                "type": "single"
            },
            {
                "question": "右转弯盲区的主要受害者包括？",
                "options": ["A.行人", "B.骑电动车者", "C.儿童和老年人", "D.以上都是"],
                "answer": 3,
                "type": "single"
            },
            {
                "question": "交通肇事致人死亡，承担主要责任，可能被判多少年？",
                "options": ["A.1年以下", "B.3年以下", "C.3-7年", "D.7年以上"],
                "answer": 1,
                "type": "single"
            },
            {
                "question": "以下哪种设备可以有效预防右转弯事故？",
                "options": ["A.车载导航", "B.行车记录仪", "C.盲区摄像头+雷达预警", "D.倒车影像"],
                "answer": 2,
                "type": "single"
            }
        ]
    },
    {
        "title": "😴 疲劳驾驶危害（必学）",
        "description": "了解疲劳驾驶的生理机制和危害，掌握休息规范，避免因疲劳导致的重特大事故",
        "passing_score": 80,
        "modules": [
            {
                "type": "text",
                "title": "⚠️ 疲劳驾驶的真相",
                "content": """<h3>😴 疲劳驾驶有多可怕？</h3>

<p style="color:#d32f2f; font-size:20px; font-weight:bold;">⏱️ 数据警示</p>
<ul style="font-size:16px;">
<li>连续驾驶<strong>4小时</strong>后，反应速度下降<strong>50%</strong></li>
<li>连续驾驶<strong>6小时</strong>后，反应速度等同于<strong>酒驾</strong>标准</li>
<li><strong>凌晨2-6点</strong>是疲劳驾驶事故高发期，占事故总量的40%以上</li>
<li>疲劳驾驶<strong>3秒</strong>的闭眼，足以让你<strong>失去生命</strong></li>
</ul>

<h3>🚨 疲劳驾驶的典型症状</h3>
<div style="display:flex; flex-wrap:wrap; gap:10px;">
<div style="background:#ffebee; padding:10px; border-radius:5px;">频繁眨眼</div>
<div style="background:#ffebee; padding:10px; border-radius:5px;">打哈欠</div>
<div style="background:#ffebee; padding:10px; border-radius:5px;">反应迟钝</div>
<div style="background:#ffebee; padding:10px; border-radius:5px;">方向不稳</div>
<div style="background:#ffebee; padding:10px; border-radius:5px;">短暂失神</div>
</div>"""
            },
            {
                "type": "text",
                "title": "⏰ 法律法规",
                "content": """<h3>📜 《道路交通安全法》相关规定</h3>

<h4>第二十二条</h4>
<p>机动车驾驶人应当遵守道路交通安全法律、法规的规定，按照操作规范安全驾驶、文明驾驶。<br>
<strong>过度疲劳影响安全驾驶的，不得驾驶机动车。</strong></p>

<h4>《道路交通安全法实施条例》第六十二条</h4>
<p><strong>连续驾驶机动车超过4小时未停车休息或者停车休息时间少于20分钟的</strong>，处200元罚款，记6分。</p>

<h3 style="color:#d32f2f;">⚠️ 疲劳驾驶的法律后果</h3>
<table style="width:100%; border-collapse:collapse;">
<tr style="background:#d32f2f; color:white;"><th>情形</th><th>后果</th></tr>
<tr><td>疲劳驾驶被查到</td><td>罚款200元，记6分</td></tr>
<tr><td>疲劳驾驶引发事故</td><td>承担主要责任，构成交通肇事罪</td></tr>
<tr><td>商业险理赔</td><td>因违法驾驶，保险公司可拒赔</td></tr>
<tr><td>职业生涯</td><td>构成犯罪记录，终身禁驾</td></tr>
</table>"""
            }
        ],
        "questions": [
            {
                "question": "连续驾驶机动车超过多少小时需要休息？",
                "options": ["A.2小时", "B.3小时", "C.4小时", "D.5小时"],
                "answer": 2,
                "type": "single"
            },
            {
                "question": "以下哪个时段是疲劳驾驶事故高发期？",
                "options": ["A.上午9-11点", "B.中午12-14点", "C.下午15-17点", "D.凌晨2-6点"],
                "answer": 3,
                "type": "single"
            },
            {
                "question": "疲劳驾驶被查到，会受到什么处罚？",
                "options": ["A.警告", "B.罚款200元、记6分", "C.行政拘留", "D.刑事拘留"],
                "answer": 1,
                "type": "single"
            },
            {
                "question": "疲劳驾驶引发事故致人死亡，可能承担什么责任？",
                "options": ["A.民事赔偿", "B.行政处罚", "C.交通肇事罪", "D.没有责任"],
                "answer": 2,
                "type": "single"
            },
            {
                "question": "连续驾驶4小时后，驾驶员的反应速度会下降多少？",
                "options": ["A.10%", "B.25%", "C.50%", "D.80%"],
                "answer": 2,
                "type": "single"
            }
        ]
    },
    {
        "title": "📱 分心驾驶的危害（必学）",
        "description": "认识分心驾驶的六大类型和致命危害，养成安全驾驶好习惯",
        "passing_score": 80,
        "modules": [
            {
                "type": "text",
                "title": "📖 分心驾驶六大类型",
                "content": """<h3>📱 分心驾驶的六大"杀手"</h3>

<div style="display:grid; grid-template-columns:repeat(2,1fr); gap:15px;">
<div style="background:#fff3e0; padding:15px; border-radius:10px;">
<h4>📞 1. 手机通话</h4>
<p>单手驾驶，注意力分散</p>
</div>
<div style="background:#fff3e0; padding:15px; border-radius:10px;">
<h4>💬 2. 微信/短视频</h4>
<p>视线离开路面3-5秒</p>
</div>
<div style="background:#fff3e0; padding:15px; border-radius:10px;">
<h4>🎵 3. 调节设备</h4>
<p>操作导航、音响</p>
</div>
<div style="background:#fff3e0; padding:15px; border-radius:10px;">
<h4>🍔 4. 吃喝东西</h4>
<p>单手操作，易失控</p>
</div>
<div style="background:#fff3e0; padding:15px; border-radius:10px;">
<h4>🚬 5. 吸烟</h4>
<p>烟雾遮挡，单手驾驶</p>
</div>
<div style="background:#fff3e0; padding:15px; border-radius:10px;">
<h4>💬 6. 与人交谈</h4>
<p>扭头说话，忽略前方</p>
</div>
</div>

<h3 style="color:#d32f2f;">⚠️ 触目惊心的数据</h3>
<ul>
<li>看手机<strong>5秒</strong> = 盲开<strong>100米</strong>（相当于足球场长度）</li>
<li>分心<strong>3秒</strong>，事故概率<strong>翻倍</strong></li>
<li>开车看手机，反应时间<strong>延长30%</strong></li>
</ul>"""
            },
            {
                "type": "text",
                "title": "⚖️ 法律法规",
                "content": """<h3>📜 分心驾驶的法律后果</h3>

<h4>《道路交通安全法实施条例》第六十二条</h4>
<p>拨打接听手持电话、观看电视等<strong>妨碍安全驾驶</strong>的行为，记2分，罚款200元。</p>

<h4>分心驾驶导致事故</h4>
<ul>
<li>承担事故<strong>主要责任</strong>或全部责任</li>
<li>致人死亡：构成<strong>交通肇事罪</strong>，可判<strong>3年以下</strong>有期徒刑</li>
<li>保险公司可能<strong>拒赔</strong></li>
</ul>

<h3 style="color:#2e7d32;">✅ 安全操作规范</h3>
<ul>
<li>出发前<strong>设置好导航</strong></li>
<li>手机调至<strong>静音或免打扰模式</strong></li>
<li>必须接打电话时，<strong>靠边停车</strong></li>
<li>使用<strong>语音助手</strong>操作手机</li>
<li>喝水吃东西<strong>等红灯时</strong></li>
</ul>"""
            }
        ],
        "questions": [
            {
                "question": "开车时看手机5秒，车辆大约会行驶多少米？",
                "options": ["A.10米", "B.50米", "C.100米", "D.200米"],
                "answer": 2,
                "type": "single"
            },
            {
                "question": "开车拨打手机、观看电视，会被记多少分？",
                "options": ["A.不记分", "B.1分", "C.2分", "D.6分"],
                "answer": 2,
                "type": "single"
            },
            {
                "question": "必须接打电话时，正确的做法是？",
                "options": ["A.边开边打", "B.单手接听", "C.靠边停车后再接打", "D.用耳机长时间通话"],
                "answer": 2,
                "type": "single"
            },
            {
                "question": "分心驾驶导致事故致人死亡，会构成什么罪？",
                "options": ["A.危险驾驶罪", "B.交通肇事罪", "C.过失致人死亡罪", "D.故意伤害罪"],
                "answer": 1,
                "type": "single"
            },
            {
                "question": "以下哪项不是分心驾驶的常见类型？",
                "options": ["A.看手机", "B.调节空调", "C.正常观察路况", "D.与乘客交谈"],
                "answer": 2,
                "type": "single"
            }
        ]
    },
    {
        "title": "🔋 新能源电池安全（新能源专项）",
        "description": "学习新能源货车动力电池安全知识，掌握充电规范和火灾应急处置",
        "passing_score": 80,
        "modules": [
            {
                "type": "text",
                "title": "⚠️ 动力电池热失控",
                "content": """<h3>🔋 什么是动力电池热失控？</h3>

<p>动力电池热失控是指电池内部温度快速升高，导致起火甚至爆炸的连锁反应。</p>

<h4 style="color:#d32f2f;">🚨 热失控的三大诱因</h4>
<ol>
<li><strong>机械损伤</strong>：碰撞、挤压导致电池内部短路</li>
<li><strong>电气故障</strong>：过充、过放、快充损伤</li>
<li><strong>高温环境</strong>：外部高温引燃电池</li>
</ol>

<h4 style="color:#d32f2f;">⚠️ 关键数据</h4>
<ul>
<li>热失控到爆燃：仅需<strong>数十秒</strong></li>
<li>灭火困难：电池内部持续反应，<strong>易复燃</strong></li>
<li>有毒气体：释放氟化氢等<strong>剧毒气体</strong></li>
</ul>"""
            },
            {
                "type": "text",
                "title": "⚖️ 充电安全规范",
                "content": """<h3>🔌 新能源货车充电安全规范</h3>

<div style="background:#e8f5e9; padding:20px; border-radius:10px;">
<h4>✅ 正确做法</h4>
<ul>
<li>使用<strong>原装充电设备</strong></li>
<li>充电时<strong>人员远离</strong>车辆（至少5米）</li>
<li>避免<strong>过充</strong>（充到80-90%最佳）</li>
<li>暴雨天气<strong>禁止</strong>充电</li>
<li>充电前检查<strong>充电口</strong>干燥无异物</li>
</ul>
</div>

<div style="background:#ffebee; padding:20px; border-radius:10px; margin-top:15px;">
<h4 style="color:#c62828;">❌ 错误做法</h4>
<ul>
<li>使用非原装充电线</li>
<li>充电时在车内休息</li>
<li>充到100%再拔枪</li>
<li>雨天露天充电</li>
<li>充电时启动车辆</li>
</ul>
</div>"""
            },
            {
                "type": "text",
                "title": "🔥 火灾应急处置",
                "content": """<h3>🚨 新能源汽车火灾应急处置四步法</h3>

<div style="background:#ffebee; padding:20px; border-radius:10px; border:2px solid #d32f2f;">
<h4>第一步：断电熄火 🚗💨</h4>
<p>第一时间切断电源，关闭车辆启动开关</p>

<h4>第二步：疏散人员 👥</h4>
<p><strong>至少撤离50米</strong>，在上风口位置等待</p>

<h4>第三步：拨打119 🚒</h4>
<p>明确告知是<strong>新能源汽车起火</strong>，需要专业设备</p>

<h4>第四步：持续降温 💧</h4>
<p>使用<strong>大量水</strong>持续喷洒电池部位降温</p>
</div>

<h3 style="color:#d32f2f;">⚠️ 严禁使用以下灭火器！</h3>
<ul style="color:#c62828;">
<li>❌ 干粉灭火器（无效）</li>
<li>❌ 二氧化碳灭火器（无效）</li>
<li>❌ 沙土覆盖（无效）</li>
<li>✅ 大量水持续降温（唯一有效方法）</li>
</ul>"""
            }
        ],
        "questions": [
            {
                "question": "新能源电池热失控后，留给人员撤离的时间大约是多少？",
                "options": ["A.5分钟", "B.1分钟", "C.数十秒", "D.10分钟"],
                "answer": 2,
                "type": "single"
            },
            {
                "question": "新能源汽车电池起火，正确的灭火方式是？",
                "options": ["A.干粉灭火器", "B.二氧化碳灭火器", "C.大量水持续降温", "D.沙土覆盖"],
                "answer": 2,
                "type": "single"
            },
            {
                "question": "充电时正确的做法是？",
                "options": ["A.在车内等候", "B.人员远离车辆", "C.边充电边启动", "D.使用非原装充电设备"],
                "answer": 1,
                "type": "single"
            },
            {
                "question": "发现新能源汽车冒烟，正确的第一步操作是？",
                "options": ["A.立即灭火", "B.拍照留证", "C.断电熄火、疏散人员", "D.继续观察"],
                "answer": 2,
                "type": "single"
            },
            {
                "question": "暴雨天气可以给新能源汽车充电吗？",
                "options": ["A.可以", "B.不可以", "C.无所谓", "D.视情况而定"],
                "answer": 1,
                "type": "single"
            }
        ]
    },
    {
        "title": "⚠️ 超载超限的危害（重要专题）",
        "description": "了解超载超限的严重危害和法律责任，做到合法装载、安全运输",
        "passing_score": 80,
        "modules": [
            {
                "type": "text",
                "title": "⚠️ 超载的五大危害",
                "content": """<h3>🚛 超载超限——公路"第一杀手"</h3>

<h4 style="color:#d32f2f;">超载的五大危害</h4>
<ol>
<li><strong>制动失效</strong>：刹车距离增加3-5倍</li>
<li><strong>爆胎风险</strong>：轮胎负荷过大，易发生爆胎</li>
<li><strong>侧翻隐患</strong>：重心偏移，易发生侧翻</li>
<li><strong>桥梁损坏</strong>：超载车辆是桥梁坍塌的重要原因</li>
<li><strong>事故加重</strong>：发生事故时，撞击力成倍增加</li>
</ol>

<h3 style="color:#d32f2f;">⚠️ 真实案例</h3>
<blockquote style="background:#ffebee; border-left:4px solid #d32f2f; padding:15px;">
<p><strong>某地桥梁侧翻事故</strong>：超载货车（实载200吨）通行时导致桥梁侧翻，造成多人伤亡。</p>
<p>法院判决：超载司机承担<strong>刑事责任</strong>，判处有期徒刑。</p>
</blockquote>"""
            },
            {
                "type": "text",
                "title": "⚖️ 法律法规",
                "content": """<h3>📜 超载超限处罚标准（2024）</h3>

<table style="width:100%; border-collapse:collapse;">
<tr style="background:#ff9800; color:white;"><th>超载程度</th><th>罚款</th><th>记分</th></tr>
<tr><td>30%以下</td><td>500-2000元</td><td>记3分</td></tr>
<tr><td>30%-50%</td><td>1000-2000元</td><td>记6分</td></tr>
<tr><td>50%以上</td><td>2000-5000元</td><td>记6分</td></tr>
</table>

<h3>📜 法律依据</h3>
<ul>
<li><strong>《道路交通安全法》第48条</strong>：机动车载物应当符合核定的载质量</li>
<li><strong>《道路交通安全法》第92条</strong>：超载货运车辆，由公安机关交通管理部门扣留机动车至违法状态消除</li>
<li><strong>超载入刑</strong>：严重超载造成事故，可构成交通肇事罪</li>
</ul>

<h3 style="color:#2e7d32;">✅ 合法装载规范</h3>
<ul>
<li>标载运营，不超限</li>
<li>出车前过磅检测</li>
<li>超载货物及时卸载转运</li>
<li>配合执法部门检查</li>
</ul>"""
            }
        ],
        "questions": [
            {
                "question": "货车超载50%以上，一次记多少分？",
                "options": ["A.1分", "B.3分", "C.6分", "D.12分"],
                "answer": 2,
                "type": "single"
            },
            {
                "question": "超载会显著增加哪种风险？",
                "options": ["A.油耗增加", "B.刹车距离增加、侧翻风险", "C.空调不凉", "D.噪音变大"],
                "answer": 1,
                "type": "single"
            },
            {
                "question": "超载50%以上，罚款多少？",
                "options": ["A.100-500元", "B.500-2000元", "C.2000-5000元", "D.不罚款"],
                "answer": 2,
                "type": "single"
            },
            {
                "question": "关于超载入刑，以下说法正确的是？",
                "options": ["A.超载就入刑", "B.严重超载造成事故才可能入刑", "C.超载只罚款不判刑", "D.超载是小违规"],
                "answer": 1,
                "type": "single"
            },
            {
                "question": "发现车辆超载后，正确的做法是？",
                "options": ["A.继续行驶", "B.卸载超载货物", "C.藏起来躲避检查", "D.快速通过检查站"],
                "answer": 1,
                "type": "single"
            }
        ]
    },
    {
        "title": "🍺 酒后驾驶的危害（必学）",
        "description": "认清酒驾醉驾的危害和严重法律后果，开车不喝酒，喝酒不开车",
        "passing_score": 80,
        "modules": [
            {
                "type": "text",
                "title": "📖 酒驾醉驾标准",
                "content": """<h3>🍺 酒驾与醉驾的区别</h3>

<table style="width:100%; border-collapse:collapse; background:#fff3e0;">
<tr style="background:#ff9800; color:white;"><th>类型</th><th>血液酒精含量</th><th>性质</th><th>法律后果</th></tr>
<tr><td><strong>饮酒驾驶</strong></td><td>20-80mg/100ml</td><td>违法</td><td>罚款、记12分</td></tr>
<tr><td><strong>醉酒驾驶</strong></td><td>≥80mg/100ml</td><td><strong>犯罪</strong></td><td>拘役、罚金、吊销驾照</td></tr>
</table>

<h3 style="color:#d32f2f;">⚠️ 酒驾的危害</h3>
<ul>
<li>判断力下降：无法准确判断距离和速度</li>
<li>反应迟钝：遇到紧急情况无法及时反应</li>
<li>视觉障碍：视线模糊，视野变小</li>
<li>情绪失控：易怒、冲动驾驶</li>
</ul>

<h3>🍻 宿醉也是酒驾！</h3>
<p>酒精代谢因人而异，有些人<strong>第二天早晨</strong>血液中酒精含量仍可能超标。请务必确认完全清醒后再驾驶。</p>"""
            },
            {
                "type": "text",
                "title": "⚖️ 法律法规",
                "content": """<h3>📜 《刑法》第133条之一 —— 危险驾驶罪</h3>

<blockquote style="background:#ffebee; border-left:4px solid #d32f2f; padding:15px;">
<p><strong>在道路上驾驶机动车，有下列情形之一的，处拘役，并处罚金：</strong></p>
<p>（一）追逐竞驶，情节恶劣的；</p>
<p>（二）<strong>醉酒驾驶机动车的</strong>；</p>
<p>（三）从事校车业务或者旅客运输，严重超过额定乘员载客，或者严重超过规定时速行驶的。</p>
</blockquote>

<h3 style="color:#d32f2f;">🚨 酒驾的严重后果</h3>

<table style="width:100%; border-collapse:collapse;">
<tr style="background:#d32f2f; color:white;"><th>后果类型</th><th>具体内容</th></tr>
<tr><td><strong>刑事责任</strong></td><td>拘役1-6个月，并处罚金</td></tr>
<tr><td><strong>驾照</strong></td><td>吊销驾照，5年内不得重新考取</td></tr>
<tr><td><strong>犯罪记录</strong></td><td>留下案底，影响子女政审</td></tr>
<tr><td><strong>工作</strong></td><td>单位可依法解除劳动合同</td></tr>
<tr><td><strong>保险</strong></td><td>商业险拒赔，自行承担赔偿</td></tr>
</table>"""
            }
        ],
        "questions": [
            {
                "question": "血液酒精含量达到多少属于醉酒驾驶？",
                "options": ["A.20mg/100ml", "B.50mg/100ml", "C.80mg/100ml", "D.100mg/100ml"],
                "answer": 2,
                "type": "single"
            },
            {
                "question": "醉酒驾驶机动车的刑事责任是什么？",
                "options": ["A.罚款2000元", "B.行政拘留15天", "C.拘役1-6个月+罚金", "D.无刑事责任"],
                "answer": 2,
                "type": "single"
            },
            {
                "question": "喝了酒睡一晚上，第二天开车还算酒驾吗？",
                "options": ["A.不算", "B.算，因为可能还未完全代谢", "C.无所谓", "D.只要不喝多就没事"],
                "answer": 1,
                "type": "single"
            },
            {
                "question": "醉酒驾驶被查处，驾照会被怎样处理？",
                "options": ["A.记12分", "B.吊销驾照，5年内不得重新考取", "C.扣留驾照6个月", "D.警告处分"],
                "answer": 1,
                "type": "single"
            },
            {
                "question": "以下哪个不属于危险驾驶罪的情形？",
                "options": ["A.追逐竞驶", "B.醉驾", "C.超速20%", "D.严重超载"],
                "answer": 2,
                "type": "single"
            }
        ]
    },
    {
        "title": "💀 人伤/亡事故警示（震撼教育）",
        "description": "通过真实案例认识交通事故的惨烈后果，珍惜生命，安全驾驶",
        "passing_score": 80,
        "modules": [
            {
                "type": "text",
                "title": "💀 交通事故的残酷真相",
                "content": """<h3>⚠️ 每5分钟就有1人死于交通事故</h3>

<p style="font-size:18px;">根据公安部数据，我国每年因交通事故死亡人数超过<strong>6万人</strong>，平均每天约<strong>170人</strong>。</p>

<h3 style="color:#d32f2f;">🚨 大货车事故的残酷真相</h3>
<ul>
<li>大货车质量大，撞击力是普通轿车的<strong>10倍以上</strong></li>
<li>与大货车相撞，行人/骑行者<strong>死亡率超过80%</strong></li>
<li>碾压事故中，<strong>70%</strong>的受害者当场死亡</li>
</ul>

<h3 style="color:#d32f2f;">💔 一个家庭的破碎</h3>
<blockquote style="background:#ffebee; border-left:4px solid #d32f2f; padding:15px;">
<p><strong>真实案例</strong>：2024年某地，大货车司机张某疲劳驾驶，在路口撞倒一名骑电动车送孩子上学的家长，孩子当场死亡，家长重伤。</p>
<p>后果：家长落下终身残疾，孩子永远失去了父亲。司机张某因交通肇事罪被判处有期徒刑3年。</p>
<p><strong>两个家庭，一辈子的伤痛。</strong></p>
</blockquote>"""
            },
            {
                "type": "text",
                "title": "⚖️ 交通肇事罪量刑标准",
                "content": """<h3>📜 《刑法》第133条 —— 交通肇事罪</h3>

<table style="width:100%; border-collapse:collapse;">
<tr style="background:#d32f2f; color:white;"><th>事故情形</th><th>责任</th><th>量刑</th></tr>
<tr><td>死亡1人</td><td>全部/主要责任</td><td><strong>3年以下</strong>有期徒刑或拘役</td></tr>
<tr><td>重伤3人</td><td>全部/主要责任</td><td><strong>3年以下</strong>有期徒刑</td></tr>
<tr><td>死亡3人</td><td>全部/主要责任</td><td><strong>3-7年</strong>有期徒刑</td></tr>
<tr><td>逃逸</td><td>—</td><td><strong>3-7年</strong>有期徒刑</td></tr>
<tr><td>逃逸致人死亡</td><td>—</td><td><strong>7年以上</strong>有期徒刑</td></tr>
<tr><td>无能力赔偿60万+</td><td>全责</td><td>可判<strong>3年以下</strong></td></tr>
</table>

<h3 style="color:#2e7d32;">✅ 事故后正确做法</h3>
<ol>
<li><strong>立即停车</strong>，保护现场</li>
<li><strong>拨打120</strong>，救助伤员</li>
<li><strong>拨打110</strong>，报警处理</li>
<li><strong>配合调查</strong>，不逃逸</li>
<li><strong>积极赔偿</strong>，争取谅解（可减刑）</li>
</ol>

<h3 style="color:#d32f2f;">🚨 逃逸的代价</h3>
<ul>
<li>罪加一等：<strong>3-7年</strong>有期徒刑</li>
<li>逃逸致死：<strong>7年以上</strong>有期徒刑</li>
<li>终身禁驾</li>
<li>保险拒赔，需自行赔偿</li>
</ul>"""
            }
        ],
        "questions": [
            {
                "question": "交通肇事致人死亡，承担主要责任，可能被判处多少年有期徒刑？",
                "options": ["A.1年以下", "B.3年以下", "C.3-7年", "D.7年以上"],
                "answer": 1,
                "type": "single"
            },
            {
                "question": "肇事逃逸的量刑是多少年？",
                "options": ["A.1-3年", "B.3-7年", "C.7年以上", "D.10年以上"],
                "answer": 1,
                "type": "single"
            },
            {
                "question": "发生事故后逃逸，会加重还是减轻处罚？",
                "options": ["A.减轻", "B.加重", "C.不影响", "D.看情况"],
                "answer": 1,
                "type": "single"
            },
            {
                "question": "交通肇事后，以下哪项是正确的？",
                "options": ["A.逃逸", "B.私了解决", "C.拨打120、110并配合调查", "D.毁灭证据"],
                "answer": 2,
                "type": "single"
            },
            {
                "question": "与大货车相撞，行人/骑行者死亡率超过多少？",
                "options": ["A.30%", "B.50%", "C.80%", "D.95%"],
                "answer": 2,
                "type": "single"
            }
        ]
    },
    {
        "title": "🛡️ 防御性驾驶技术（进阶）",
        "description": "学习主动安全驾驶技术，提高预判能力，做到惹不起躲得起",
        "passing_score": 80,
        "modules": [
            {
                "type": "text",
                "title": "📖 防御性驾驶五大原则",
                "content": """<h3>🛡️ 防御性驾驶 —— 预见危险，远离事故</h3>

<div style="display:grid; grid-template-columns:repeat(2,1fr); gap:15px;">
<div style="background:#e3f2fd; padding:15px; border-radius:10px;">
<h4>👀 1. 看远顾近</h4>
<p>观察前方至少15秒距离内的路况</p>
</div>
<div style="background:#e8f5e9; padding:15px; border-radius:10px;">
<h4>👁️ 2. 眼观六路</h4>
<p>不只看前方，注意两侧和后视镜</p>
</div>
<div style="background:#fff3e0; padding:15px; border-radius:10px;">
<h4>📏 3. 保持间距</h4>
<p>与前车保持足够的安全距离</p>
</div>
<div style="background:#fce4ec; padding:15px; border-radius:10px;">
<h4>🏃 4. 惹不起躲得起</h4>
<p>预判危险，及时减速或变道</p>
</div>
<div style="background:#f3e5f5; padding:15px; border-radius:10px;">
<h4>🐢 5. 慢速过路口</h4>
<p>路口减速观察，确认安全再通过</p>
</div>
</div>

<h3 style="color:#d32f2f;">🚨 安全距离计算</h3>
<p>高速公路：车速(km/h) ÷ 2 = 最小跟车距离(米)</p>
<p>例如：100km/h → 保持50米以上跟车距离</p>"""
            },
            {
                "type": "text",
                "title": "🔧 主动安全系统使用",
                "content": """<h3>🔧 商用车主动安全系统使用指南</h3>

<table style="width:100%; border-collapse:collapse;">
<tr style="background:#2196f3; color:white;"><th>系统名称</th><th>功能</th><th>重要性</th></tr>
<tr><td><strong>FCW</strong>前撞预警</td><td>检测前方车辆，提醒减速</td><td>⭐⭐⭐⭐⭐</td></tr>
<tr><td><strong>AEB</strong>自动紧急制动</td><td>自动刹车避免碰撞</td><td>⭐⭐⭐⭐⭐</td></tr>
<tr><td><strong>LDW</strong>车道偏离预警</td><td>提醒车辆偏离车道</td><td>⭐⭐⭐⭐</td></tr>
<tr><td><strong>BSD</strong>盲区监测</td><td>提醒盲区内的车辆行人</td><td>⭐⭐⭐⭐⭐</td></tr>
<tr><td><strong>DMS</strong>驾驶员监测</td><td>监测疲劳、分心状态</td><td>⭐⭐⭐⭐⭐</td></tr>
</table>

<h3 style="color:#2e7d32;">✅ 养成好习惯</h3>
<ul>
<li>出车前检查主动安全设备是否正常</li>
<li>不要关闭安全预警系统</li>
<li>听到预警立即响应</li>
<li>定期维护传感器和摄像头</li>
</ul>"""
            }
        ],
        "questions": [
            {
                "question": "防御性驾驶的核心原则是什么？",
                "options": ["A.开快一点", "B.预见危险，提前采取措施", "C.跟着前车走", "D.看手机不影响"],
                "answer": 1,
                "type": "single"
            },
            {
                "question": "车速100km/h时，高速公路上最小跟车距离应该是多少米？",
                "options": ["A.20米", "B.50米", "C.100米", "D.200米"],
                "answer": 1,
                "type": "single"
            },
            {
                "question": "AEB系统的作用是什么？",
                "options": ["A.车道保持", "B.自动刹车避免碰撞", "C.盲区监测", "D.疲劳监测"],
                "answer": 1,
                "type": "single"
            },
            {
                "question": "以下哪个不是防御性驾驶的原则？",
                "options": ["A.看远顾近", "B.保持间距", "C.开英雄车", "D.眼观六路"],
                "answer": 2,
                "type": "single"
            },
            {
                "question": "出车前应该检查主动安全设备是否正常吗？",
                "options": ["A.不需要", "B.需要", "C.无所谓", "D.设备会自动检测"],
                "answer": 1,
                "type": "single"
            }
        ]
    }
]


def init_db():
    """初始化数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 检查courses表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='courses'")
    if not cursor.fetchone():
        print("❌ 数据库未初始化，请先运行 app.py")
        conn.close()
        return None

    conn.close()
    return DB_PATH


def add_courses():
    """添加课程和题目"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    added_courses = []

    for i, course_data in enumerate(COURSES_DATA):
        # 获取下一个sort_order
        cursor.execute('SELECT COALESCE(MAX(sort_order), 0) + 1 FROM courses')
        next_order = cursor.fetchone()[0]

        # 插入课程
        cursor.execute('''
            INSERT INTO courses (title, description, passing_score, sort_order)
            VALUES (?, ?, ?, ?)
        ''', (course_data['title'], course_data['description'],
              course_data.get('passing_score', 80), next_order))

        course_id = cursor.lastrowid
        print(f"✅ 添加课程 [{i+1}/{len(COURSES_DATA)}]：{course_data['title']}")
        added_courses.append((course_id, course_data['title']))

        # 添加课程内容模块
        for j, module in enumerate(course_data.get('modules', [])):
            cursor.execute('''
                INSERT INTO course_modules (course_id, type, title, content, sort_order)
                VALUES (?, ?, ?, ?, ?)
            ''', (course_id, module['type'], module['title'], module['content'], j))

        print(f"   └─ 添加了 {len(course_data.get('modules', []))} 个内容模块")

        # 添加考试题目
        for k, question in enumerate(course_data.get('questions', [])):
            answer_str = str(question['answer'])
            cursor.execute('''
                INSERT INTO questions (course_id, question, options, question_type, answer, sort_order)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                course_id,
                question['question'],
                json.dumps(question['options'], ensure_ascii=False),
                question.get('type', 'single'),
                answer_str,
                k
            ))

        print(f"   └─ 添加了 {len(course_data.get('questions', []))} 道考试题目")

    conn.commit()
    conn.close()

    print(f"\n🎉 完成！共添加 {len(added_courses)} 个课程")
    return added_courses


if __name__ == '__main__':
    db = init_db()
    if db:
        add_courses()
