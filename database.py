"""
旅行攻略管理器 - 数据库模块
SQLite 数据库，包含 trips, trip_days, activities, attractions, todos 五个核心表
"""
import sqlite3
import json
import os
import sys
from datetime import datetime

# PyInstaller 兼容：确定数据目录
if getattr(sys, 'frozen', False):
    DATA_DIR = os.path.join(os.path.dirname(sys.executable), 'data')
else:
    DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

DB_DIR = DATA_DIR
DB_PATH = os.path.join(DB_DIR, 'trips.db')


def get_db():
    """获取数据库连接"""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """初始化数据库表结构"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            last_login TEXT
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            expires_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS trips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL DEFAULT '未命名攻略',
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            image_path TEXT,
            raw_ocr_text TEXT,
            parsed_json TEXT,
            notes TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS trip_days (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trip_id INTEGER NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
            day_number INTEGER NOT NULL,
            day_title TEXT DEFAULT '',
            date TEXT DEFAULT '',
            UNIQUE(trip_id, day_number)
        );

        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day_id INTEGER NOT NULL REFERENCES trip_days(id) ON DELETE CASCADE,
            sort_order INTEGER NOT NULL DEFAULT 0,
            time_slot TEXT DEFAULT '',
            content TEXT NOT NULL,
            location TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            attraction_id INTEGER REFERENCES attractions(id) ON DELETE SET NULL,
            checked INTEGER DEFAULT 0,
            category TEXT DEFAULT '景点'
        );

        CREATE TABLE IF NOT EXISTS attractions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            city TEXT DEFAULT '',
            description TEXT DEFAULT '',
            category TEXT DEFAULT '景点',
            image_url TEXT DEFAULT '',
            xiaohongshu_posts TEXT DEFAULT '[]',
            source TEXT DEFAULT 'manual',
            last_updated TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trip_id INTEGER REFERENCES trips(id) ON DELETE CASCADE,
            content TEXT NOT NULL,
            done INTEGER DEFAULT 0,
            priority INTEGER DEFAULT 0,
            deadline TEXT DEFAULT '',
            category TEXT DEFAULT '其他',
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );
    """)

    conn.commit()
    conn.close()


def dict_from_row(row):
    """将 sqlite3.Row 转为字典"""
    if row is None:
        return None
    return dict(row)


def dicts_from_rows(rows):
    """将 sqlite3.Row 列表转为字典列表"""
    return [dict(row) for row in rows]


# ==================== Trip CRUD ====================

def create_trip(title="未命名攻略", image_path=None, raw_ocr_text=None):
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO trips (title, image_path, raw_ocr_text) VALUES (?, ?, ?)",
        (title, image_path, raw_ocr_text)
    )
    conn.commit()
    trip_id = cursor.lastrowid
    conn.close()
    return trip_id


def get_all_trips():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM trips ORDER BY updated_at DESC"
    ).fetchall()
    conn.close()
    return dicts_from_rows(rows)


def get_trip(trip_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM trips WHERE id = ?", (trip_id,)).fetchone()
    conn.close()
    return dict_from_row(row)


def update_trip(trip_id, **kwargs):
    if not kwargs:
        return
    kwargs['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    sets = ", ".join(f"{k} = ?" for k in kwargs.keys())
    values = list(kwargs.values()) + [trip_id]
    conn = get_db()
    conn.execute(f"UPDATE trips SET {sets} WHERE id = ?", values)
    conn.commit()
    conn.close()


def delete_trip(trip_id):
    conn = get_db()
    conn.execute("DELETE FROM trips WHERE id = ?", (trip_id,))
    conn.commit()
    conn.close()


# ==================== Trip Day CRUD ====================

def create_day(trip_id, day_number, day_title="", date=""):
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO trip_days (trip_id, day_number, day_title, date) VALUES (?, ?, ?, ?)",
            (trip_id, day_number, day_title, date)
        )
        conn.commit()
        day_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        # Day already exists
        row = conn.execute(
            "SELECT id FROM trip_days WHERE trip_id = ? AND day_number = ?",
            (trip_id, day_number)
        ).fetchone()
        day_id = row['id']
    conn.close()
    return day_id


def get_trip_days(trip_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM trip_days WHERE trip_id = ? ORDER BY day_number",
        (trip_id,)
    ).fetchall()
    conn.close()
    return dicts_from_rows(rows)


def delete_day(day_id):
    conn = get_db()
    conn.execute("DELETE FROM trip_days WHERE id = ?", (day_id,))
    conn.commit()
    conn.close()


# ==================== Activity CRUD ====================

def create_activity(day_id, content, time_slot="", location="", notes="",
                    attraction_id=None, category="景点", sort_order=None):
    conn = get_db()
    if sort_order is None:
        max_order = conn.execute(
            "SELECT MAX(sort_order) FROM activities WHERE day_id = ?", (day_id,)
        ).fetchone()[0]
        sort_order = (max_order or 0) + 1

    cursor = conn.execute(
        """INSERT INTO activities (day_id, sort_order, time_slot, content, location, notes, attraction_id, category)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (day_id, sort_order, time_slot, content, location, notes, attraction_id, category)
    )
    conn.commit()
    act_id = cursor.lastrowid
    conn.close()
    return act_id


def get_day_activities(day_id):
    conn = get_db()
    rows = conn.execute(
        """SELECT a.*, at.name as attraction_name
           FROM activities a
           LEFT JOIN attractions at ON a.attraction_id = at.id
           WHERE a.day_id = ?
           ORDER BY a.sort_order""",
        (day_id,)
    ).fetchall()
    conn.close()
    return dicts_from_rows(rows)


def update_activity(act_id, **kwargs):
    if not kwargs:
        return
    conn = get_db()
    sets = ", ".join(f"{k} = ?" for k in kwargs.keys())
    values = list(kwargs.values()) + [act_id]
    conn.execute(f"UPDATE activities SET {sets} WHERE id = ?", values)
    conn.commit()
    conn.close()


def toggle_activity_check(act_id):
    conn = get_db()
    conn.execute(
        "UPDATE activities SET checked = CASE WHEN checked = 0 THEN 1 ELSE 0 END WHERE id = ?",
        (act_id,)
    )
    conn.commit()
    row = conn.execute("SELECT checked FROM activities WHERE id = ?", (act_id,)).fetchone()
    conn.close()
    return row['checked'] if row else 0


def delete_activity(act_id):
    conn = get_db()
    conn.execute("DELETE FROM activities WHERE id = ?", (act_id,))
    conn.commit()
    conn.close()


def update_activity_order(act_id, new_order):
    conn = get_db()
    conn.execute("UPDATE activities SET sort_order = ? WHERE id = ?", (new_order, act_id))
    conn.commit()
    conn.close()


# ==================== Attraction CRUD ====================

def get_or_create_attraction(name, city="", description="", category="景点"):
    conn = get_db()
    row = conn.execute("SELECT * FROM attractions WHERE name = ?", (name,)).fetchone()
    if row:
        conn.close()
        return dict_from_row(row)
    cursor = conn.execute(
        "INSERT INTO attractions (name, city, description, category) VALUES (?, ?, ?, ?)",
        (name, city, description, category)
    )
    conn.commit()
    attr_id = cursor.lastrowid
    conn.close()
    return {"id": attr_id, "name": name, "city": city, "description": description,
            "category": category, "xiaohongshu_posts": "[]"}


def get_all_attractions():
    conn = get_db()
    rows = conn.execute("SELECT * FROM attractions ORDER BY name").fetchall()
    conn.close()
    return dicts_from_rows(rows)


def get_attraction(attr_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM attractions WHERE id = ?", (attr_id,)).fetchone()
    conn.close()
    return dict_from_row(row)


def update_attraction_xhs(attr_id, posts_json):
    conn = get_db()
    conn.execute(
        "UPDATE attractions SET xiaohongshu_posts = ?, last_updated = datetime('now','localtime') WHERE id = ?",
        (posts_json, attr_id)
    )
    conn.commit()
    conn.close()


# ==================== Todo CRUD ====================

def create_todo(trip_id, content, priority=0, deadline="", category="其他"):
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO todos (trip_id, content, priority, deadline, category) VALUES (?, ?, ?, ?, ?)",
        (trip_id, content, priority, deadline, category)
    )
    conn.commit()
    todo_id = cursor.lastrowid
    conn.close()
    return todo_id


def get_trip_todos(trip_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM todos WHERE trip_id = ? ORDER BY done ASC, priority DESC, created_at DESC",
        (trip_id,)
    ).fetchall()
    conn.close()
    return dicts_from_rows(rows)


def toggle_todo(todo_id):
    conn = get_db()
    conn.execute(
        "UPDATE todos SET done = CASE WHEN done = 0 THEN 1 ELSE 0 END WHERE id = ?",
        (todo_id,)
    )
    conn.commit()
    row = conn.execute("SELECT done FROM todos WHERE id = ?", (todo_id,)).fetchone()
    conn.close()
    return row['done'] if row else 0


def update_todo(todo_id, **kwargs):
    if not kwargs:
        return
    conn = get_db()
    sets = ", ".join(f"{k} = ?" for k in kwargs.keys())
    values = list(kwargs.values()) + [todo_id]
    conn.execute(f"UPDATE todos SET {sets} WHERE id = ?", values)
    conn.commit()
    conn.close()


def delete_todo(todo_id):
    conn = get_db()
    conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    conn.commit()
    conn.close()


# ==================== Statistics ====================

def get_trip_stats(trip_id):
    """获取行程统计数据"""
    conn = get_db()
    days = conn.execute("SELECT COUNT(*) as cnt FROM trip_days WHERE trip_id = ?", (trip_id,)).fetchone()['cnt']
    total_acts = conn.execute(
        "SELECT COUNT(*) as cnt FROM activities a JOIN trip_days d ON a.day_id = d.id WHERE d.trip_id = ?",
        (trip_id,)
    ).fetchone()['cnt']
    checked_acts = conn.execute(
        "SELECT COUNT(*) as cnt FROM activities a JOIN trip_days d ON a.day_id = d.id WHERE d.trip_id = ? AND a.checked = 1",
        (trip_id,)
    ).fetchone()['cnt']
    total_todos = conn.execute(
        "SELECT COUNT(*) as cnt FROM todos WHERE trip_id = ?", (trip_id,)
    ).fetchone()['cnt']
    done_todos = conn.execute(
        "SELECT COUNT(*) as cnt FROM todos WHERE trip_id = ? AND done = 1", (trip_id,)
    ).fetchone()['cnt']
    conn.close()
    return {
        "days": days,
        "total_activities": total_acts,
        "checked_activities": checked_acts,
        "total_todos": total_todos,
        "done_todos": done_todos,
        "activity_progress": round(checked_acts / total_acts * 100, 1) if total_acts else 0,
        "todo_progress": round(done_todos / total_todos * 100, 1) if total_todos else 0
    }


# ==================== Batch operations ====================

def save_parsed_itinerary(trip_id, parsed_data):
    """
    将解析后的行程数据批量保存到数据库（使用单一连接避免锁定）
    parsed_data: {"title": "...", "days": [{"day_number": 1, "day_title": "Day 1", "activities": [...]}]}
    """
    conn = get_db()
    cursor = conn.cursor()

    title = parsed_data.get("title", "未命名攻略")
    conn.execute("UPDATE trips SET title = ?, parsed_json = ? WHERE id = ?",
                 (title, json.dumps(parsed_data, ensure_ascii=False), trip_id))

    # 先删除该 trip 已有的 days（重新解析时清理旧数据）
    conn.execute("DELETE FROM trip_days WHERE trip_id = ?", (trip_id,))

    for day_data in parsed_data.get("days", []):
        day_number = day_data.get("day_number", 1)
        day_title = day_data.get("day_title", "")
        date = day_data.get("date", "")

        try:
            cursor.execute(
                "INSERT INTO trip_days (trip_id, day_number, day_title, date) VALUES (?, ?, ?, ?)",
                (trip_id, day_number, day_title, date)
            )
            day_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            row = conn.execute(
                "SELECT id FROM trip_days WHERE trip_id = ? AND day_number = ?",
                (trip_id, day_number)
            ).fetchone()
            day_id = row['id']

        for i, act in enumerate(day_data.get("activities", [])):
            attr_id = None
            loc = act.get("location", "")
            if loc:
                # 在同一连接中查找或创建景点
                row = conn.execute("SELECT id FROM attractions WHERE name = ?", (loc,)).fetchone()
                if row:
                    attr_id = row['id']
                else:
                    cat = act.get("category", "景点")
                    cursor2 = conn.execute(
                        "INSERT INTO attractions (name, category) VALUES (?, ?)",
                        (loc, cat)
                    )
                    attr_id = cursor2.lastrowid

            cursor.execute(
                """INSERT INTO activities (day_id, sort_order, time_slot, content, location, notes, attraction_id, category)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (day_id, i + 1, act.get("time", ""), act.get("content", ""),
                 loc, act.get("notes", ""), attr_id, act.get("category", "景点"))
            )

    conn.commit()
    conn.close()
    return True


# ==================== User Auth ====================
import hashlib
import secrets

def hash_password(password):
    salt = "travel_planner_salt_2024"
    return hashlib.sha256((password + salt).encode()).hexdigest()

def create_user(username, password):
    conn = get_db()
    try:
        pw_hash = hash_password(password)
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, pw_hash)
        )
        conn.commit()
        uid = cursor.lastrowid
        conn.close()
        return uid
    except sqlite3.IntegrityError:
        conn.close()
        return None

def authenticate_user(username, password):
    conn = get_db()
    pw_hash = hash_password(password)
    row = conn.execute(
        "SELECT id, username FROM users WHERE username = ? AND password_hash = ?",
        (username, pw_hash)
    ).fetchone()
    if row:
        # Update last login
        conn.execute(
            "UPDATE users SET last_login = datetime('now','localtime') WHERE id = ?",
            (row['id'],)
        )
        conn.commit()
    conn.close()
    return dict_from_row(row) if row else None

def create_session(user_id, expires_hours=24):
    conn = get_db()
    token = secrets.token_hex(32)
    from datetime import datetime, timedelta
    expires = (datetime.now() + timedelta(hours=expires_hours)).strftime('%Y-%m-%d %H:%M:%S')
    conn.execute(
        "INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)",
        (user_id, token, expires)
    )
    conn.commit()
    conn.close()
    return token

def validate_session(token):
    conn = get_db()
    row = conn.execute(
        """SELECT s.*, u.username FROM sessions s
           JOIN users u ON s.user_id = u.id
           WHERE s.token = ? AND s.expires_at > datetime('now','localtime')""",
        (token,)
    ).fetchone()
    conn.close()
    return dict_from_row(row) if row else None

def delete_session(token):
    conn = get_db()
    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_db()
    rows = conn.execute("SELECT id, username, created_at, last_login FROM users ORDER BY id").fetchall()
    conn.close()
    return dicts_from_rows(rows)

# ==================== Attraction with source ====================
def get_or_create_attraction_sourced(name, city="", description="", category="景点", source="manual"):
    conn = get_db()
    row = conn.execute("SELECT * FROM attractions WHERE name = ?", (name,)).fetchone()
    if row:
        conn.close()
        return dict_from_row(row)
    cursor = conn.execute(
        "INSERT INTO attractions (name, city, description, category, source) VALUES (?, ?, ?, ?, ?)",
        (name, city, description, category, source)
    )
    conn.commit()
    attr_id = cursor.lastrowid
    conn.close()
    return {"id": attr_id, "name": name, "city": city, "description": description,
            "category": category, "source": source, "xiaohongshu_posts": "[]"}

def update_attraction(attr_id, **kwargs):
    if not kwargs: return
    conn = get_db()
    allowed = ['name', 'city', 'description', 'category', 'source']
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if updates:
        sets = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [attr_id]
        conn.execute(f"UPDATE attractions SET {sets}, last_updated = datetime('now','localtime') WHERE id = ?", values)
        conn.commit()
    conn.close()

# 启动时初始化数据库 + 创建管理员账户
init_db()

# Auto-create admin account
def _ensure_admin():
    conn = get_db()
    row = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()
    if not row:
        pw_hash = hash_password('admin')
        conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", ('admin', pw_hash))
        conn.commit()
    conn.close()

_ensure_admin()
