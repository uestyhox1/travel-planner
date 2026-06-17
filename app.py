"""
旅行攻略管理器 - 主应用入口
Flask Web 应用，提供 REST API 和前端页面服务
"""
import os
import sys

# 修复 Windows 控制台编码问题
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import json
import webbrowser
import threading
import time
import socket
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename

# PyInstaller 兼容：获取应用根目录
if getattr(sys, 'frozen', False):
    # 运行在 PyInstaller 打包的 exe 中
    BASE_DIR = sys._MEIPASS
    # 数据目录放在 exe 同级目录
    DATA_DIR = os.path.join(os.path.dirname(sys.executable), 'data')
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, 'data')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, 'uploads'), exist_ok=True)

# 添加模块搜索路径
sys.path.insert(0, BASE_DIR)

import database as db
from ocr_engine import ocr_image
from parser import parse_travel_text
from xiaohongshu import search_xiaohongshu, get_attraction_xhs_posts, search_attractions_by_keyword, CITY_ATTRACTIONS
from pdf_export import generate_pdf
from config_manager import load_config, save_config, get_api_key, get_model, get_api_base

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)
CORS(app)

# 配置
UPLOAD_DIR = os.path.join(DATA_DIR, 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32MB max
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ==================== 静态文件 ====================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/static/<path:path>')
def static_files(path):
    return send_from_directory('static', path)


@app.route('/data/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)


# ==================== Trip API ====================

@app.route('/api/trips', methods=['GET'])
def api_get_trips():
    trips = db.get_all_trips()
    # 为每个 trip 添加统计信息
    for trip in trips:
        trip['stats'] = db.get_trip_stats(trip['id'])
    return jsonify({"success": True, "data": trips})


@app.route('/api/trips', methods=['POST'])
def api_create_trip():
    data = request.get_json() or {}
    title = data.get('title', '未命名攻略')
    trip_id = db.create_trip(title=title)
    return jsonify({"success": True, "data": {"id": trip_id, "title": title}})


@app.route('/api/trips/<int:trip_id>', methods=['GET'])
def api_get_trip(trip_id):
    trip = db.get_trip(trip_id)
    if not trip:
        return jsonify({"success": False, "error": "攻略不存在"}), 404
    trip['days'] = db.get_trip_days(trip_id)
    for day in trip['days']:
        day['activities'] = db.get_day_activities(day['id'])
    trip['todos'] = db.get_trip_todos(trip_id)
    trip['stats'] = db.get_trip_stats(trip_id)
    return jsonify({"success": True, "data": trip})


@app.route('/api/trips/<int:trip_id>', methods=['PUT'])
def api_update_trip(trip_id):
    data = request.get_json() or {}
    allowed_fields = ['title', 'notes']
    updates = {k: v for k, v in data.items() if k in allowed_fields}
    db.update_trip(trip_id, **updates)
    return jsonify({"success": True})


@app.route('/api/trips/<int:trip_id>', methods=['DELETE'])
def api_delete_trip(trip_id):
    db.delete_trip(trip_id)
    return jsonify({"success": True})


@app.route('/api/trips/clear-all', methods=['DELETE'])
def api_clear_all_trips():
    """清除所有行程数据"""
    import database as db
    conn = db.get_db()
    conn.execute("DELETE FROM activities")
    conn.execute("DELETE FROM trip_days")
    conn.execute("DELETE FROM trips")
    conn.execute("DELETE FROM todos")
    conn.execute("DELETE FROM attractions")
    conn.commit()
    conn.close()
    return jsonify({"success": True})


# ==================== OCR API ====================

@app.route('/api/ocr/upload', methods=['POST'])
def api_ocr_upload():
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "没有上传文件"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "文件名为空"}), 400

    if not allowed_file(file.filename):
        return jsonify({"success": False, "error": f"不支持的文件格式，仅支持: {', '.join(ALLOWED_EXTENSIONS)}"}), 400

    # 保存文件
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{int(time.time() * 1000)}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    file.save(filepath)

    # 执行 OCR
    engine = request.form.get('engine', 'auto')
    ocr_result = ocr_image(filepath, engine=engine)

    # 创建 trip
    trip_id = db.create_trip(
        title="新攻略",
        image_path=f"data/uploads/{filename}",
        raw_ocr_text=ocr_result.get('text', '')
    )

    # 如果 OCR 成功，自动解析行程
    parsed = None
    if ocr_result.get('success') and ocr_result.get('text'):
        parsed = parse_travel_text(ocr_result['text'])
        db.save_parsed_itinerary(trip_id, parsed)

    return jsonify({
        "success": True,
        "data": {
            "trip_id": trip_id,
            "image_path": f"data/uploads/{filename}",
            "ocr": ocr_result,
            "parsed": parsed
        }
    })


@app.route('/api/ocr/parse-text', methods=['POST'])
def api_ocr_parse_text():
    """直接解析用户输入的文本"""
    data = request.get_json() or {}
    text = data.get('text', '')
    trip_id = data.get('trip_id')

    if not text.strip():
        return jsonify({"success": False, "error": "文本为空"}), 400

    parsed = parse_travel_text(text)

    if trip_id:
        db.update_trip(trip_id, raw_ocr_text=text)
        db.save_parsed_itinerary(trip_id, parsed)
    else:
        trip_id = db.create_trip(title=parsed.get("title", "新攻略"), raw_ocr_text=text)
        db.save_parsed_itinerary(trip_id, parsed)

    return jsonify({"success": True, "data": {"trip_id": trip_id, "parsed": parsed}})


# ==================== Itinerary / Day API ====================

@app.route('/api/trips/<int:trip_id>/days', methods=['GET'])
def api_get_days(trip_id):
    days = db.get_trip_days(trip_id)
    for day in days:
        day['activities'] = db.get_day_activities(day['id'])
    return jsonify({"success": True, "data": days})


@app.route('/api/trips/<int:trip_id>/days', methods=['POST'])
def api_create_day(trip_id):
    data = request.get_json() or {}
    day_number = data.get('day_number', 1)
    day_title = data.get('day_title', f"第{day_number}天")
    date = data.get('date', '')
    day_id = db.create_day(trip_id, day_number, day_title, date)
    return jsonify({"success": True, "data": {"id": day_id}})


@app.route('/api/days/<int:day_id>', methods=['DELETE'])
def api_delete_day(day_id):
    db.delete_day(day_id)
    return jsonify({"success": True})


# ==================== Activity API ====================

@app.route('/api/days/<int:day_id>/activities', methods=['GET'])
def api_get_activities(day_id):
    activities = db.get_day_activities(day_id)
    return jsonify({"success": True, "data": activities})


@app.route('/api/days/<int:day_id>/activities', methods=['POST'])
def api_create_activity(day_id):
    data = request.get_json() or {}
    act_id = db.create_activity(
        day_id=day_id,
        content=data.get('content', ''),
        time_slot=data.get('time_slot', ''),
        location=data.get('location', ''),
        notes=data.get('notes', ''),
        attraction_id=data.get('attraction_id'),
        category=data.get('category', '景点')
    )
    # 如果提供了地点，自动关联景点
    if data.get('location'):
        db.get_or_create_attraction(data['location'], category=data.get('category', '景点'))
    return jsonify({"success": True, "data": {"id": act_id}})


@app.route('/api/activities/<int:act_id>', methods=['PUT'])
def api_update_activity(act_id):
    data = request.get_json() or {}
    allowed = ['content', 'time_slot', 'location', 'notes', 'category', 'sort_order']
    updates = {k: v for k, v in data.items() if k in allowed}
    if 'sort_order' in updates:
        db.update_activity_order(act_id, updates.pop('sort_order'))
    db.update_activity(act_id, **updates)
    return jsonify({"success": True})


@app.route('/api/activities/<int:act_id>/toggle', methods=['POST'])
def api_toggle_activity(act_id):
    checked = db.toggle_activity_check(act_id)
    return jsonify({"success": True, "data": {"checked": checked}})


@app.route('/api/activities/<int:act_id>', methods=['DELETE'])
def api_delete_activity(act_id):
    db.delete_activity(act_id)
    return jsonify({"success": True})


# ==================== Todo API ====================

@app.route('/api/trips/<int:trip_id>/todos', methods=['GET'])
def api_get_todos(trip_id):
    todos = db.get_trip_todos(trip_id)
    return jsonify({"success": True, "data": todos})


@app.route('/api/trips/<int:trip_id>/todos', methods=['POST'])
def api_create_todo(trip_id):
    data = request.get_json() or {}
    todo_id = db.create_todo(
        trip_id=trip_id,
        content=data.get('content', ''),
        priority=data.get('priority', 0),
        deadline=data.get('deadline', ''),
        category=data.get('category', '其他')
    )
    return jsonify({"success": True, "data": {"id": todo_id}})


@app.route('/api/todos/<int:todo_id>/toggle', methods=['POST'])
def api_toggle_todo(todo_id):
    done = db.toggle_todo(todo_id)
    return jsonify({"success": True, "data": {"done": done}})


@app.route('/api/todos/<int:todo_id>', methods=['PUT'])
def api_update_todo(todo_id):
    data = request.get_json() or {}
    allowed = ['content', 'priority', 'deadline', 'category']
    updates = {k: v for k, v in data.items() if k in allowed}
    db.update_todo(todo_id, **updates)
    return jsonify({"success": True})


@app.route('/api/todos/<int:todo_id>', methods=['DELETE'])
def api_delete_todo(todo_id):
    db.delete_todo(todo_id)
    return jsonify({"success": True})


# ==================== Attraction API ====================

@app.route('/api/attractions', methods=['GET'])
def api_get_attractions():
    attractions = db.get_all_attractions()
    return jsonify({"success": True, "data": attractions})


@app.route('/api/attractions/<int:attr_id>', methods=['GET'])
def api_get_attraction(attr_id):
    attr = db.get_attraction(attr_id)
    if not attr:
        return jsonify({"success": False, "error": "景点不存在"}), 404
    # 获取关联的小红书帖子
    xhs_posts = get_attraction_xhs_posts(attr['name'])
    attr['xhs_posts'] = xhs_posts
    return jsonify({"success": True, "data": attr})


# ==================== Xiaohongshu API ====================

@app.route('/api/xiaohongshu/search', methods=['GET'])
def api_xhs_search():
    query = request.args.get('q', '')
    if not query:
        return jsonify({"success": False, "error": "搜索关键词为空"}), 400
    sort = request.args.get('sort', 'default')
    limit = request.args.get('limit', 20, type=int)
    results = search_xiaohongshu(query, limit=limit, sort=sort)
    return jsonify({"success": True, "data": results, "query": query, "sort": sort, "total": len(results)})


@app.route('/api/auth/change-password', methods=['POST'])
def api_change_password():
    import database as db
    data = request.get_json() or {}
    token = data.get('token', '')
    old_pwd = data.get('old_password', '')
    new_pwd = data.get('new_password', '')

    session = db.validate_session(token)
    if not session:
        return jsonify({"success": False, "error": "未登录或会话已过期"}), 401

    if len(new_pwd) < 4:
        return jsonify({"success": False, "error": "新密码至少4位"}), 400

    # Verify old password
    user = db.authenticate_user(session['username'], old_pwd)
    if not user:
        return jsonify({"success": False, "error": "当前密码错误"}), 400

    # Update password
    conn = db.get_db()
    pw_hash = db.hash_password(new_pwd)
    conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (pw_hash, session['user_id']))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "data": {"message": "密码已更新"}})


@app.route('/api/auth/validate', methods=['POST'])
def api_validate_token():
    import database as db
    data = request.get_json() or {}
    token = data.get('token', '')
    session = db.validate_session(token) if token else None
    if session:
        return jsonify({"success": True, "data": {"username": session['username'], "user_id": session['user_id']}})
    return jsonify({"success": False, "error": "invalid token"})


@app.route('/api/attractions/save-searched', methods=['POST'])
def api_save_searched_attraction():
    """Save a manually searched attraction"""
    import database as db
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({"success": False, "error": "name required"}), 400
    attr = db.get_or_create_attraction_sourced(name, category="景点", source="searched")
    xhs_posts = get_attraction_xhs_posts(name)
    db.update_attraction_xhs(attr['id'], json.dumps(xhs_posts, ensure_ascii=False))
    return jsonify({"success": True, "data": attr})


@app.route('/api/attractions/<int:attr_id>', methods=['PUT'])
def api_update_attraction(attr_id):
    """Update attraction details"""
    import database as db
    data = request.get_json() or {}
    db.update_attraction(attr_id, **data)
    return jsonify({"success": True})


@app.route('/api/attractions/<int:attr_id>', methods=['DELETE'])
def api_delete_attraction(attr_id):
    """删除单个景点"""
    import database as db
    conn = db.get_db()
    # First, NULL out references in activities table
    conn.execute("UPDATE activities SET attraction_id = NULL WHERE attraction_id = ?", (attr_id,))
    conn.execute("DELETE FROM attractions WHERE id = ?", (attr_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route('/api/attractions/clear', methods=['POST'])
def api_clear_attractions():
    """清空所有景点"""
    import database as db
    conn = db.get_db()
    # NULL out all attraction references
    conn.execute("UPDATE activities SET attraction_id = NULL")
    conn.execute("DELETE FROM attractions")
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route('/api/xiaohongshu/attractions', methods=['GET'])
def api_xhs_attractions():
    keyword = request.args.get('keyword', '')
    results = search_attractions_by_keyword(keyword) if keyword else []
    return jsonify({"success": True, "data": results})


@app.route('/api/xiaohongshu/cities', methods=['GET'])
def api_get_cities():
    """获取支持的城市和景点映射"""
    return jsonify({"success": True, "data": CITY_ATTRACTIONS})


# ==================== AI Assistant API ====================

def build_trip_context(trip_id):
    """构建行程上下文文本"""
    import database as db
    if not trip_id:
        return ""

    trip = db.get_trip(trip_id)
    if not trip:
        return ""

    parts = [f"## 当前攻略: {trip.get('title', '未命名')}"]
    days = db.get_trip_days(trip_id)

    for day in days:
        activities = db.get_day_activities(day['id'])
        if not activities:
            continue
        day_num = day.get('day_number', 0)
        day_title = day.get('day_title', '') or ('Day ' + str(day_num))
        parts.append("\n### " + day_title)
        for a in activities:
            time_str = a.get('time_slot', '') or ''
            content = a.get('content', '')
            location = a.get('location', '')
            notes = a.get('notes', '')
            checked = 'V' if a.get('checked') else 'O'
            line = checked + " "
            if time_str:
                line += "[" + time_str + "] "
            line += content
            if location:
                line += " @" + location
            if notes:
                line += " (" + notes + ")"
            parts.append(line)

    # Todos
    todos = db.get_trip_todos(trip_id)
    if todos:
        parts.append("\n### Todo List")
        for t in todos:
            icon = 'V' if t.get('done') else 'O'
            parts.append(icon + " " + t.get('content', '') + " (priority:" + str(t.get('priority', 0)) + ")")

    # Stats
    stats = db.get_trip_stats(trip_id)
    parts.append("\n### Stats: " + str(stats.get('days', 0)) + " days, " +
                  str(stats.get('total_activities', 0)) + " activities, " +
                  str(stats.get('activity_progress', 0)) + "% complete")

    return '\n'.join(parts)


@app.route('/api/ai/ask', methods=['POST'])
def api_ai_ask():
    """AI助手问答 - 调用 Anthropic API 进行真实 AI 交互"""
    import database as db
    data = request.get_json() or {}
    question = data.get('question', '').strip()
    trip_id = data.get('trip_id')

    if not question:
        return jsonify({"success": False, "error": "请输入问题"}), 400

    # 构建行程上下文
    trip_context = build_trip_context(trip_id) if trip_id else ""

    # 构建系统提示
    system_prompt = """你是一个专业的旅行助手，帮助用户规划和管理旅行行程。

你有以下能力：
- 分析用户的行程安排，给出优化建议
- 根据目的地推荐景点、美食、交通方案
- 评估行程的合理性和可行性
- 提供实用的旅行贴士和注意事项
- 回答关于旅行预算、季节、天气等问题

请根据用户提供的行程数据（如果有的话），结合你的旅行知识，给出具体、详细、可操作的建议。
回复使用中文，使用 Markdown 格式，适当使用标题、列表、加粗等排版。
如果用户行程中包含具体景点，请围绕这些景点给出针对性建议。"""

    # 构建用户消息
    user_message = question
    if trip_context:
        user_message = f"我的行程数据如下：\n\n{trip_context}\n\n---\n\n我的问题是：{question}"

    # 尝试调用 Anthropic API
    api_key = get_api_key()

    if api_key:
        try:
            reply = call_anthropic_api(system_prompt, user_message, api_key)
            return jsonify({
                "success": True,
                "data": {
                    "question": question,
                    "reply": reply,
                    "context_used": bool(trip_context),
                    "mode": "api"
                }
            })
        except Exception as e:
            error_msg = str(e)
            # API 调用失败，返回格式化的提示词让用户手动使用
            fallback = format_fallback_prompt(system_prompt, user_message, error_msg)
            return jsonify({
                "success": True,
                "data": {
                    "question": question,
                    "reply": fallback,
                    "context_used": bool(trip_context),
                    "mode": "fallback",
                    "error": error_msg
                }
            })

    # 没有 API Key，返回提示词供 Claude Code 使用
    fallback = format_fallback_prompt(system_prompt, user_message)
    return jsonify({
        "success": True,
        "data": {
            "question": question,
            "reply": fallback,
            "context_used": bool(trip_context),
            "mode": "no_key",
            "needs_key": True
        }
    })


def call_anthropic_api(system_prompt, user_message, api_key):
    """调用 Anthropic Messages API"""
    import urllib.request

    api_base = get_api_base()
    model = get_model()
    api_type = load_config().get('api_type', 'openai')

    if api_type == 'anthropic':
        # Anthropic Messages API
        body = json.dumps({
            "model": model,
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_message}
            ]
        }).encode('utf-8')

        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        req = urllib.request.Request(
            f"{api_base}/v1/messages",
            data=body,
            headers=headers,
            method='POST'
        )

        resp = urllib.request.urlopen(req, timeout=120)
        result = json.loads(resp.read().decode('utf-8'))

        reply_parts = []
        for block in result.get('content', []):
            if block.get('type') == 'text':
                reply_parts.append(block['text'])
        return '\n'.join(reply_parts)

    else:
        # OpenAI-compatible Chat Completions API (DeepSeek, OpenAI, etc.)
        # Combine system prompt and user message
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})

        body = json.dumps({
            "model": model,
            "max_tokens": 4096,
            "temperature": 0.7,
            "messages": messages
        }).encode('utf-8')

        headers = {
            "Authorization": f"Bearer {api_key}",
            "content-type": "application/json",
        }

        req = urllib.request.Request(
            f"{api_base}/v1/chat/completions",
            data=body,
            headers=headers,
            method='POST'
        )

        resp = urllib.request.urlopen(req, timeout=120)
        result = json.loads(resp.read().decode('utf-8'))

        # Extract reply from OpenAI format
        choices = result.get('choices', [])
        if choices:
            return choices[0].get('message', {}).get('content', '')
        return 'No response from API'


def format_fallback_prompt(system_prompt, user_message, error_msg=None):
    """Format fallback prompt when API is unavailable"""
    parts = []
    if error_msg:
        parts.append("**API Error**: " + error_msg + "\n")

    parts.append("**To enable real AI interaction:**\n")
    parts.append("Option 1: Configure API Key")
    parts.append("Click the Settings button and enter your Anthropic API Key.\n")
    parts.append("Option 2: Copy prompt to Claude Code")
    parts.append("Copy the prompt below and paste it into Claude Code:\n")

    full_prompt = "System: " + system_prompt + "\n\n---\n\n" + user_message
    parts.append("```\n" + full_prompt[:3000] + "\n```")

    return '\n'.join(parts)


@app.route('/api/config', methods=['GET'])
def api_get_config():
    """Get config (mask API key)"""
    config = load_config()
    key = config.get('api_key', '')
    masked = key[:8] + '****' + key[-4:] if len(key) > 12 else ('***' if key else '')
    return jsonify({
        "success": True,
        "data": {
            "has_key": bool(key),
            "key_masked": masked,
            "model": config.get('model', 'deepseek-chat'),
            "api_base": config.get('api_base', 'https://api.deepseek.com'),
            "api_type": config.get('api_type', 'openai'),
        }
    })


@app.route('/api/config', methods=['PUT'])
def api_update_config():
    """Update config"""
    data = request.get_json() or {}
    config = load_config()

    if 'api_key' in data:
        config['api_key'] = data['api_key'].strip()
    if 'model' in data:
        config['model'] = data['model'].strip()
    if 'api_base' in data:
        config['api_base'] = data['api_base'].strip()
    if 'api_type' in data:
        config['api_type'] = data['api_type'].strip()

    save_config(config)
    return jsonify({"success": True})


# ==================== PDF Export API ====================

@app.route('/api/trips/<int:trip_id>/export/pdf', methods=['GET'])
def api_export_pdf(trip_id):
    """导出攻略为 PDF 文件"""
    import database as db
    trip = db.get_trip(trip_id)
    if not trip:
        return jsonify({"success": False, "error": "攻略不存在"}), 404

    # 收集完整数据
    days = db.get_trip_days(trip_id)
    for day in days:
        day['activities'] = db.get_day_activities(day['id'])

    trip['days'] = days
    trip['todos'] = db.get_trip_todos(trip_id)
    trip['stats'] = db.get_trip_stats(trip_id)
    trip['attractions'] = db.get_all_attractions()

    try:
        pdf_buf = generate_pdf(trip)
        pdf_data = pdf_buf.read()
        pdf_buf.close()

        from flask import Response
        filename = f"{trip.get('title', '旅行攻略')}.pdf"
        # URL encode the filename for Content-Disposition
        from urllib.parse import quote
        return Response(
            pdf_data,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f"attachment; filename*=UTF-8''{quote(filename)}",
                'Content-Length': str(len(pdf_data)),
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": f"PDF生成失败: {str(e)}"}), 500


# ==================== AI Attraction Extraction ====================

@app.route('/api/ocr/<int:trip_id>/extract-attractions', methods=['POST'])
def api_extract_attractions(trip_id):
    """使用 AI 从 OCR 文本中提取景点名称"""
    import database as db
    trip = db.get_trip(trip_id)
    if not trip:
        return jsonify({"success": False, "error": "攻略不存在"}), 404

    ocr_text = trip.get('raw_ocr_text', '')
    if not ocr_text:
        return jsonify({"success": False, "error": "没有 OCR 文本"}), 400

    api_key = get_api_key()
    if not api_key:
        return jsonify({"success": False, "error": "请先配置 API Key"}), 400

    prompt = f"""从以下旅行攻略文本中，提取所有的旅游景点、景区、地标名称，并为每个景点写一句简短描述（15字以内）。

返回格式（严格JSON数组）：
[
  {{"name": "景点名", "desc": "一句话简介"}},
  ...
]

注意：
1. 只提取具体可游览的景点/景区/地标
2. 排除餐厅、酒店、火车站/机场等交通枢纽
3. desc字段用15字以内的中文简要描述该景点特色
4. 如果没有明确的景点，返回空数组 []

OCR文本：
{ocr_text[:3000]}"""

    try:
        # Save current config and temporarily use AI extraction mode
        reply = call_anthropic_api(
            "你是一个专业的旅行信息提取助手。你只返回景点名称，每行一个。不返回任何解释。",
            prompt,
            api_key
        )

        # Parse AI response - try JSON first, fall back to line-by-line
        attractions_found = []
        try:
            # Try to parse as JSON
            reply_clean = reply.strip()
            if '```' in reply_clean:
                reply_clean = reply_clean.split('```')[1]
                if reply_clean.startswith('json'):
                    reply_clean = reply_clean[4:]
            parsed = json.loads(reply_clean)
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and item.get('name'):
                        attractions_found.append({
                            'name': item['name'].strip(),
                            'desc': item.get('desc', '').strip()[:30]
                        })
        except (json.JSONDecodeError, ValueError, IndexError):
            # Fallback: line-by-line parsing
            for line in reply.strip().split('\n'):
                line = line.strip().strip('*-•·1234567890.、').strip()
                if line and len(line) >= 2 and len(line) <= 30:
                    if not any(kw in line.lower() for kw in ['没有', '无', '景点', '以下是', '如下', 'null', 'none', 'json', '```']):
                        attractions_found.append({'name': line, 'desc': ''})

        # Save to database with descriptions
        saved = []
        for item in attractions_found:
            name = item['name'] if isinstance(item, dict) else item
            desc = item.get('desc', '') if isinstance(item, dict) else ''
            attr = db.get_or_create_attraction_sourced(
                name, city="", description=desc, category="景点", source="ai_identified"
            )
            saved.append(attr)
            # Populate XHS posts
            xhs_posts = get_attraction_xhs_posts(name)
            db.update_attraction_xhs(attr['id'], json.dumps(xhs_posts, ensure_ascii=False))

        return jsonify({
            "success": True,
            "data": {
                "found": len(saved),
                "attractions": saved,
                "ai_raw": reply
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"AI提取失败: {str(e)}"}), 500


# ==================== Login / Auth API ====================

@app.route('/api/auth/register', methods=['POST'])
def api_register():
    import database as db
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    captcha = data.get('captcha', '').strip()

    if not username or not password:
        return jsonify({"success": False, "error": "Username and password required"}), 400
    if len(username) < 2 or len(username) > 20:
        return jsonify({"success": False, "error": "Username must be 2-20 chars"}), 400
    if len(password) < 4:
        return jsonify({"success": False, "error": "Password must be at least 4 chars"}), 400

    # Verify captcha
    captcha_id = data.get('captcha_id', '')
    expected = _captcha_store.get(captcha_id, '')
    if not expected or captcha.strip() != expected:
        return jsonify({"success": False, "error": "Wrong captcha"}), 400
    # Clear used captcha
    if captcha_id in _captcha_store:
        del _captcha_store[captcha_id]

    uid = db.create_user(username, password)
    if uid is None:
        return jsonify({"success": False, "error": "Username already exists"}), 400

    token = db.create_session(uid)
    return jsonify({"success": True, "data": {"token": token, "username": username, "user_id": uid}})


@app.route('/api/auth/login', methods=['POST'])
def api_login():
    import database as db
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({"success": False, "error": "Username and password required"}), 400

    captcha_id = data.get('captcha_id', '')
    expected = _captcha_store.get(captcha_id, '')
    if not expected or data.get('captcha', '').strip() != expected:
        return jsonify({"success": False, "error": "Wrong captcha"}), 400
    if captcha_id in _captcha_store:
        del _captcha_store[captcha_id]

    user = db.authenticate_user(username, password)
    if not user:
        return jsonify({"success": False, "error": "用户名或密码错误"}), 401

    token = db.create_session(user['id'])
    return jsonify({"success": True, "data": {"token": token, "username": user['username'], "user_id": user['id']}})


@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    data = request.get_json() or {}
    token = data.get('token', '')
    if token:
        import database as db
        db.delete_session(token)
    return jsonify({"success": True})


# Image captcha store
_captcha_store = {}
_captcha_counter = 0

import random
import string
import base64
import io as io_module
from PIL import Image as PILImage, ImageDraw, ImageFont, ImageFilter


def generate_captcha_image():
    """Generate an image captcha with distorted text. Returns (base64_png, answer_string)"""
    width, height = 160, 60

    # Random background color (light)
    bg_r = random.randint(235, 250)
    bg_g = random.randint(235, 250)
    bg_b = random.randint(240, 255)
    img = PILImage.new('RGB', (width, height), (bg_r, bg_g, bg_b))
    draw = ImageDraw.Draw(img)

    # Generate random 4-char code (mix of letters+digits, excluding confusing chars)
    chars = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'
    code = ''.join(random.choice(chars) for _ in range(4))

    # Try to find a usable font (Windows system fonts are always available)
    win_font_dir = os.path.expandvars(r'%SystemRoot%\Fonts')
    font_paths = [
        os.path.join(win_font_dir, 'arial.ttf'),
        os.path.join(win_font_dir, 'calibri.ttf'),
        os.path.join(win_font_dir, 'segoeui.ttf'),
        os.path.join(win_font_dir, 'consola.ttf'),
        os.path.join(win_font_dir, 'impact.ttf'),
    ]
    font = None
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, 36)
                break
            except Exception:
                continue
    if font is None:
        font = ImageFont.load_default()

    # Draw each character with random rotation and offset
    for i, char in enumerate(code):
        # Create a temporary image for this character (for rotation)
        char_img = PILImage.new('RGBA', (40, 50), (0, 0, 0, 0))
        char_draw = ImageDraw.Draw(char_img)

        # Random color (dark)
        cr = random.randint(20, 120)
        cg = random.randint(20, 120)
        cb = random.randint(20, 120)
        char_draw.text((4, 2), char, font=font, fill=(cr, cg, cb))

        # Random rotation
        angle = random.randint(-30, 30)
        char_img = char_img.rotate(angle, expand=True, fillcolor=(0, 0, 0, 0))

        # Paste onto main image with random y-offset
        x = 15 + i * 35 + random.randint(-5, 5)
        y = random.randint(2, 12)
        img.paste(char_img, (x, y), char_img)

    # Add noise: random dots
    for _ in range(80):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        c = random.randint(100, 200)
        draw.point((x, y), fill=(c, c, c))

    # Add noise: random lines
    for _ in range(3):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        c = random.randint(150, 220)
        draw.line([(x1, y1), (x2, y2)], fill=(c, c, c), width=1)

    # Apply slight blur for anti-aliasing effect
    img = img.filter(ImageFilter.GaussianBlur(radius=0.3))

    # Convert to base64 PNG
    buf = io_module.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode('utf-8')

    return 'data:image/png;base64,' + b64, code


@app.route('/api/auth/captcha', methods=['GET'])
def api_get_captcha():
    """Get image captcha - returns base64 image, stores answer server-side"""
    global _captcha_counter
    img_b64, answer = generate_captcha_image()
    _captcha_counter += 1
    captcha_id = str(_captcha_counter)
    _captcha_store[captcha_id] = answer
    # Auto-expire after 5 min
    return jsonify({
        "success": True,
        "data": {
            "captcha_id": captcha_id,
            "image": img_b64,
            "hint": "Enter the 4 characters shown in the image"
        }
    })


# ==================== Concurrency Test ====================

@app.route('/api/test/concurrency', methods=['GET'])
def api_concurrency_test():
    """高并发测试端点"""
    import database as db
    import time as time_mod
    import concurrent.futures

    count = request.args.get('count', 10, type=int)
    count = min(count, 100)

    def single_query(i):
        start = time_mod.time()
        conn = db.get_db()
        conn.execute("SELECT 1").fetchone()
        conn.close()
        elapsed = time_mod.time() - start
        return {"id": i, "elapsed_ms": round(elapsed * 1000, 2), "ok": True}

    results = []
    errors = []
    start_total = time_mod.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(count, 20)) as executor:
        futures = [executor.submit(single_query, i) for i in range(count)]
        for f in concurrent.futures.as_completed(futures):
            try:
                results.append(f.result())
            except Exception as e:
                errors.append(str(e))

    total_elapsed = time_mod.time() - start_total

    # Calculate stats
    if results:
        avg_ms = sum(r['elapsed_ms'] for r in results) / len(results)
        max_ms = max(r['elapsed_ms'] for r in results)
        min_ms = min(r['elapsed_ms'] for r in results)
    else:
        avg_ms = max_ms = min_ms = 0

    return jsonify({
        "success": True,
        "data": {
            "total_queries": count,
            "successful": len(results),
            "errors": len(errors),
            "total_time_ms": round(total_elapsed * 1000, 2),
            "avg_query_ms": round(avg_ms, 2),
            "max_query_ms": round(max_ms, 2),
            "min_query_ms": round(min_ms, 2),
            "qps": round(count / total_elapsed, 1) if total_elapsed > 0 else 0,
            "error_details": errors[:5]
        }
    })


# ==================== Stats API ====================

@app.route('/api/trips/<int:trip_id>/stats', methods=['GET'])
def api_get_stats(trip_id):
    stats = db.get_trip_stats(trip_id)
    return jsonify({"success": True, "data": stats})


# ==================== 启动 ====================

def find_free_port(start=5000):
    """Find a free port starting from `start`"""
    for port in range(start, 5100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
    return 5000


def run_flask(port):
    """Run Flask in a daemon thread"""
    app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)


def launch_browser_mode(port):
    """Browser mode: open system browser"""
    print("=" * 50)
    print("   Travel Planner v2.0 (Browser Mode)")
    print("=" * 50)
    print(f"   Data dir: {DATA_DIR}")
    print(f"   URL: http://127.0.0.1:{port}")
    print("=" * 50)

    def _open():
        time.sleep(1)
        webbrowser.open(f'http://127.0.0.1:{port}')
    threading.Thread(target=_open, daemon=True).start()
    app.run(host='127.0.0.1', port=port, debug=False)


def launch_native_mode(port):
    """Native desktop mode: use pywebview for a standalone window"""
    try:
        import webview
        import platform

        print("=" * 50)
        print("   Travel Planner v2.0 (Desktop Mode)")
        print("=" * 50)
        print(f"   Data dir: {DATA_DIR}")
        print("=" * 50)

        # Start Flask in background thread
        flask_thread = threading.Thread(target=run_flask, args=(port,), daemon=True)
        flask_thread.start()
        time.sleep(0.5)

        # Create native window
        window_title = "Travel Planner - Travel Guide Manager"
        url = f'http://127.0.0.1:{port}'

        # Window config
        webview.create_window(
            title=window_title,
            url=url,
            width=1400,
            height=900,
            min_size=(1000, 650),
            resizable=True,
            fullscreen=False,
            easy_drag=True,
            confirm_close=True,
            text_select=True,
        )

        webview.start(debug=False, http_server=False)

    except ImportError:
        print("pywebview not installed, falling back to browser mode...")
        launch_browser_mode(port)
    except Exception as e:
        print(f"Native window error: {e}, falling back to browser...")
        launch_browser_mode(port)


if __name__ == '__main__':
    port = find_free_port(5000)

    # Default: native desktop window; use --browser flag for browser mode
    if '--browser' in sys.argv:
        launch_browser_mode(port)
    else:
        launch_native_mode(port)
