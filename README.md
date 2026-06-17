# 🗺️ 旅行攻略管理器 (Travel Planner)

> 桌面版旅行攻略管理工具 — 上传攻略图片 → OCR识别 → 自动生成日程表 → 关联小红书攻略 → AI智能分析 → 一键导出PDF

## 目录

- [快速开始](#快速开始)
- [功能概览](#功能概览)
- [项目架构](#项目架构)
- [数据库设计](#数据库设计)
- [API文档](#api文档)
- [前端架构](#前端架构)
- [部署迁移](#部署迁移)
- [开发指南](#开发指南)

---

## 快速开始

### 直接运行（无需安装任何东西）

```bash
1. 下载 dist/TravelPlanner.exe （20MB，单文件）
2. 双击运行 → 原生桌面窗口打开
3. 登录（默认管理员账户: admin / admin）
4. 开始使用
```

### 从源码运行

```bash
pip install -r requirements.txt
python app.py           # 原生桌面窗口模式
python app.py --browser # 浏览器模式 (http://127.0.0.1:5000)
```

### OCR 安装（可选）

图片文字识别需要 Tesseract OCR，不安装也能正常使用（手动输入文字即可）：

```bash
# 方式A: 安装官方版
winget install UB-Mannheim.TesseractOCR
# 安装后需下载中文语言包 chi_sim.traineddata 放入 tessdata 目录

# 方式B: 便携版（推荐，随项目迁移）
将 tesseract.exe 和 tessdata/chi_sim.traineddata 放入项目的 tesseract/ 文件夹
```

### AI 配置

在应用内「系统设置 → API配置」中配置：

| 服务 | 获取地址 | 默认模型 |
|------|---------|---------|
| DeepSeek | [platform.deepseek.com](https://platform.deepseek.com) | `deepseek-chat` |
| Anthropic | [console.anthropic.com](https://console.anthropic.com) | `claude-sonnet-4-6` |
| OpenAI | [platform.openai.com](https://platform.openai.com) | 兼容接口 |

---

## 功能概览

### 核心工作流

```
上传攻略图片 → OCR识别文字 → 解析为结构化日程
    ↓
按天查看时间线 → 勾选完成活动 → 追踪进度
    ↓
AI提取景点 → 关联小红书攻略 → 添加待办事项
    ↓
导出PDF攻略文档
```

### 功能清单

| 模块 | 功能 | 说明 |
|------|------|------|
| 📷 **OCR识别** | 图片文字提取 | Tesseract引擎，支持中英文，三级路径自动检测 |
| 📅 **日程解析** | 文本→结构化行程 | 支持"第X天"/"X号"/"Day X"等格式，智能时间检测 |
| 🏷️ **景点管理** | AI自动识别景点 | DeepSeek提取景点名+一句话简介，按来源颜色区分 |
| 📕 **小红书** | 攻略搜索 | 30+热门景点内置数据，真实搜索链接一键跳转 |
| ✅ **待办清单** | 任务管理 | 优先级/完成追踪/进度条/筛选（全部/未完成/已完成/高优先） |
| 🤖 **AI助手** | 智能问答 | 真实LLM交互，基于行程上下文给出个性化建议 |
| 📄 **PDF导出** | 攻略文档 | ReportLab生成，中文封面+日程表+待办+景点参考 |
| 🔐 **用户系统** | 注册/登录 | 图片验证码（扭曲字符+噪点+干扰线），SHA256密码哈希 |
| 🎨 **深色模式** | 主题切换 | 50+CSS变量覆盖，所有组件同步切换 |
| ⚙️ **偏好设置** | 个性化 | 默认启动页/自动OCR/自动跳转/主题切换 |
| 💾 **数据管理** | 导入导出 | JSON备份导出，一键清除，localStorage偏好持久化 |
| 🖥️ **原生窗口** | PyWebView | 独立桌面窗口，1400×900可调，不依赖浏览器 |

---

## 项目架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────┐
│                    桌面窗口 (PyWebView)                    │
│  ┌───────────────────────────────────────────────────┐  │
│  │              前端 SPA (HTML/CSS/JS)                │  │
│  │  ┌─────┐ ┌────────┐ ┌──────────┐ ┌───────────┐  │  │
│  │  │登录页│ │行程总览│ │景点管理  │ │AI助手     │  │  │
│  │  ├─────┤ ├────────┤ ├──────────┤ ├───────────┤  │  │
│  │  │注册页│ │上传攻略│ │待办清单  │ │系统设置   │  │  │
│  │  └─────┘ └────────┘ └──────────┘ └───────────┘  │  │
│  └──────────────────┬────────────────────────────────┘  │
└─────────────────────┼────────────────────────────────────┘
                      │ HTTP (127.0.0.1:5000)
┌─────────────────────┼────────────────────────────────────┐
│               Flask 后端 (app.py)                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ OCR路由  │ │行程路由  │ │AI路由    │ │用户路由  │   │
│  ├──────────┤ ├──────────┤ ├──────────┤ ├──────────┤   │
│  │图片上传  │ │CRUD操作  │ │API调用   │ │注册/登录 │   │
│  │文字识别  │ │日程管理  │ │景点提取  │ │验证码    │   │
│  │文本解析  │ │活动管理  │ │智能问答  │ │密码修改  │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │                  服务层                            │   │
│  │  ocr_engine  │  parser  │  xiaohongshu  │  pdf    │   │
│  │  (Tesseract) │ (文本→结构)│ (攻略搜索)   │ (导出)  │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │                  数据层                            │   │
│  │     SQLite (trips.db)  │  config.json  │  files   │   │
│  │     7 tables           │  (API key)    │ (uploads)│   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

### 文件结构

```
旅行攻略/
├── app.py                    # Flask主程序 + 所有API路由 + 启动入口
├── database.py               # SQLite数据库（7表+CRUD+用户认证）
├── ocr_engine.py             # OCR引擎（PaddleOCR→EasyOCR→Tesseract三级回退）
├── parser.py                 # 行程文本解析器（多格式支持）
├── xiaohongshu.py            # 小红书服务（30+景点内置数据+真实搜索URL）
├── pdf_export.py             # PDF生成器（ReportLab+中文字体）
├── config_manager.py         # 配置管理（API Key/模型/偏好）
│
├── templates/
│   └── index.html            # 前端单页面（6个视图+登录注册页）
│
├── static/
│   ├── css/
│   │   └── style.css         # 完整样式表（含深色模式50+变量）
│   └── js/
│       └── app.js            # 前端逻辑（~1800行）
│
├── data/                     # 运行时数据（自动创建，不提交Git）
│   ├── trips.db              # SQLite数据库
│   ├── config.json           # 用户配置（API Key等）
│   └── uploads/              # 上传的图片
│
├── dist/                     # 构建输出（不提交Git）
│   └── TravelPlanner.exe     # 打包后的可执行文件
│
├── build_exe.bat             # PyInstaller一键打包脚本
├── requirements.txt          # Python依赖
├── .gitignore                # Git忽略规则
└── README.md                 # 本文档
```

### 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| 桌面容器 | PyWebView 6.2 | 原生Windows窗口，嵌入Web前端 |
| 后端框架 | Flask 3.1 | REST API服务，静态文件托管 |
| 数据库 | SQLite3 + 原生SQL | 本地存储，零配置，支持并发 |
| 前端 | Vanilla HTML/CSS/JS | 无框架依赖，兼容所有浏览器 |
| OCR引擎 | Tesseract 5.4 + pytesseract | 中文OCR，三级路径自动检测 |
| AI接口 | DeepSeek/Anthropic/OpenAI | HTTP调用，支持三种API格式 |
| PDF生成 | ReportLab 4.5 | 中文字体嵌入，模板化排版 |
| 图片处理 | Pillow 11 | 预处理+验证码生成 |
| 打包工具 | PyInstaller 6.21 | 单文件exe，包含Python运行时 |

---

## 数据库设计

### ER图

```
users ──1:N── sessions
  │
trips ──1:N── trip_days ──1:N── activities ──N:1── attractions
  │
  └──1:N── todos
```

### 表结构

```sql
-- 用户表
users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,        -- SHA256(password + salt)
    created_at TEXT,
    last_login TEXT
)

-- 会话表
sessions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token TEXT UNIQUE NOT NULL,          -- secrets.token_hex(32)
    created_at TEXT,
    expires_at TEXT                      -- 24小时有效期
)

-- 攻略表
trips (
    id INTEGER PRIMARY KEY,
    title TEXT DEFAULT '未命名攻略',
    created_at TEXT,
    updated_at TEXT,
    image_path TEXT,                     -- 上传的图片路径
    raw_ocr_text TEXT,                   -- OCR原始文本
    parsed_json TEXT,                    -- 解析后的JSON
    notes TEXT
)

-- 行程天表
trip_days (
    id INTEGER PRIMARY KEY,
    trip_id INTEGER REFERENCES trips(id) ON DELETE CASCADE,
    day_number INTEGER NOT NULL,
    day_title TEXT,
    date TEXT,
    UNIQUE(trip_id, day_number)
)

-- 活动表
activities (
    id INTEGER PRIMARY KEY,
    day_id INTEGER REFERENCES trip_days(id) ON DELETE CASCADE,
    sort_order INTEGER,
    time_slot TEXT,                      -- 时间段（09:00/上午）
    content TEXT NOT NULL,               -- 活动内容
    location TEXT,                        -- 地点
    notes TEXT,                           -- 备注
    attraction_id INTEGER REFERENCES attractions(id) ON DELETE SET NULL,
    checked INTEGER DEFAULT 0,           -- 完成状态
    category TEXT DEFAULT '景点'         -- 分类（景点/餐饮/住宿/交通/购物）
)

-- 景点表
attractions (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    city TEXT,
    description TEXT,                    -- AI生成的一句话简介
    category TEXT DEFAULT '景点',
    source TEXT DEFAULT 'manual',        -- 来源: ai_identified/searched/manual
    xiaohongshu_posts TEXT,              -- JSON格式的小红书帖子数据
    last_updated TEXT
)

-- 待办表
todos (
    id INTEGER PRIMARY KEY,
    trip_id INTEGER REFERENCES trips(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    done INTEGER DEFAULT 0,
    priority INTEGER DEFAULT 0,          -- 0=普通 1=重要 2=紧急
    deadline TEXT,
    category TEXT DEFAULT '其他',
    created_at TEXT
)
```

---

## API文档

### 认证 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/auth/captcha` | 获取图片验证码（返回base64 PNG） |
| POST | `/api/auth/register` | 注册 `{username, password, captcha, captcha_id}` |
| POST | `/api/auth/login` | 登录 `{username, password, captcha, captcha_id}` |
| POST | `/api/auth/logout` | 退出 `{token}` |
| POST | `/api/auth/validate` | 验证Token `{token}` |
| POST | `/api/auth/change-password` | 修改密码 `{token, old_password, new_password}` |

### 攻略 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/trips` | 获取全部攻略列表（含统计） |
| POST | `/api/trips` | 创建攻略 `{title}` |
| GET | `/api/trips/:id` | 获取攻略详情（含days/activities/todos/stats） |
| PUT | `/api/trips/:id` | 更新攻略 `{title, notes}` |
| DELETE | `/api/trips/:id` | 删除攻略 |
| DELETE | `/api/trips/clear-all` | 清除所有数据 |

### OCR API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/ocr/upload` | 上传图片+OCR（multipart: file, engine） |
| POST | `/api/ocr/parse-text` | 解析文本为行程 `{text, trip_id}` |
| POST | `/api/ocr/:trip_id/extract-attractions` | AI提取景点（需API Key） |

### 活动 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/days/:day_id/activities` | 添加活动 `{content, time_slot, location, ...}` |
| PUT | `/api/activities/:id` | 编辑活动 |
| POST | `/api/activities/:id/toggle` | 切换完成状态 |
| DELETE | `/api/activities/:id` | 删除活动 |

### 待办 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/trips/:id/todos` | 获取待办列表 |
| POST | `/api/trips/:id/todos` | 添加待办 `{content, priority, deadline}` |
| POST | `/api/todos/:id/toggle` | 切换完成 |
| DELETE | `/api/todos/:id` | 删除待办 |

### 景点/小红书 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/attractions` | 景点列表 |
| GET | `/api/attractions/:id` | 景点详情（含XHS帖子） |
| PUT | `/api/attractions/:id` | 编辑景点 |
| DELETE | `/api/attractions/:id` | 删除景点 |
| POST | `/api/attractions/clear` | 清空全部 |
| POST | `/api/attractions/save-searched` | 保存搜索的景点 `{name}` |
| GET | `/api/xiaohongshu/search?q=&sort=&limit=` | 搜索攻略 |
| GET | `/api/xiaohongshu/attractions?keyword=` | 搜索景点 |
| GET | `/api/xiaohongshu/cities` | 城市景点映射 |

### AI API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/ai/ask` | AI问答 `{question, trip_id}` → 真实LLM回复 |

### 其他 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/trips/:id/export/pdf` | 导出PDF |
| GET | `/api/trips/:id/stats` | 行程统计 |
| GET | `/api/config` | 获取配置（API Key掩码显示） |
| PUT | `/api/config` | 更新配置 `{api_key, model, api_base, api_type}` |
| GET | `/api/test/concurrency?count=` | 高并发测试 |

---

## 前端架构

### 页面/视图结构

```
App
├── 登录页 (login-page)
│   └── 登录表单 → 跳转注册页
├── 注册页 (register-page)
│   └── 注册表单 → 返回登录页
└── 主应用 (app-main)
    ├── 侧边栏 (sidebar)
    │   ├── Logo + 导航菜单（6项）
    │   ├── 攻略列表（可切换/删除）
    │   └── 新建攻略按钮
    ├── 顶部栏 (top-bar)
    │   ├── 当前攻略标题
    │   ├── 统计信息（天/活动/完成率）
    │   ├── 导出PDF按钮
    │   └── 设置按钮
    ├── 主视图区 (view-container)
    │   ├── 行程总览 → 天标签页 + 时间线
    │   ├── 上传攻略 → 图片拖拽 + 文本输入
    │   ├── 景点管理 → 颜色分类卡片 + 搜索
    │   ├── 待办清单 → 进度条 + 筛选 + 添加
    │   ├── AI助手 → 聊天界面 + 快捷提问
    │   └── 系统设置 → 账户/API/偏好三标签
    └── 小红书面板 (xhs-panel)
        ├── 搜索框 + 排序标签
        ├── 搜索历史
        └── 帖子列表（可点击打开链接+详情）
```

### 设计系统

```
配色方案:
  浅色主题:  主色 #6366F1 (靛蓝)  强调 #F43F5E (玫瑰红)  背景 #F0F2F8
  深色主题:  主色 #818CF8          强调 #FB7185            背景 #0F172A

组件样式:
  按钮: 全圆角胶囊 + 渐变背景 + hover上浮
  卡片: 玻璃拟态 backdrop-filter blur(20px) + 半透明
  输入: 圆角 + focus发光环
  模态: 弹性缩放动画 cubic-bezier(0.34,1.56,0.64,1)

动画:
  页面切换: fadeSlideIn (淡入+上滑12px)
  卡片hover: translateY + 阴影加深
  进度条: shimmer闪光扫过
  勾选: popIn弹性缩放
  消息: msgIn滑入
  Toast: slideInRight + 弹性缓动
  图标: float上下漂浮
```

---

## 部署迁移

### 完全可移植

项目设计为 **复制即运行**（copy-to-run）：

```
目标电脑只需要:
  1. Windows 10/11 操作系统
  2. 无需安装 Python
  3. 无需安装任何依赖
```

### 迁移步骤

```bash
# 在源电脑
复制整个 旅行攻略/ 文件夹 → U盘/网络传输

# 在目标电脑
粘贴到任意位置 → 双击 TravelPlanner.exe → 开始使用
```

### 数据携带

| 数据 | 位置 | 说明 |
|------|------|------|
| 行程数据 | `data/trips.db` | SQLite数据库 |
| API配置 | `data/config.json` | API Key等 |
| 上传图片 | `data/uploads/` | 图片文件 |
| 偏好设置 | 浏览器 localStorage | 主题/默认页等（需重新设置） |

### Tesseract 便携部署

```bash
# 目标电脑如需OCR功能，任选一种:
# 方案A: 放入便携版（推荐，随项目迁移）
旅行攻略/
└── tesseract/
    ├── tesseract.exe
    └── tessdata/
        └── chi_sim.traineddata   # 中文语言包

# 方案B: 安装官方版
winget install UB-Mannheim.TesseractOCR
# 再下载 chi_sim.traineddata 放入 tessdata 目录
```

---

## 开发指南

### 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 启动（浏览器模式，方便调试）
python app.py --browser
# 访问 http://127.0.0.1:5000

# 启动（桌面窗口模式）
python app.py
```

### 构建exe

```bash
# 一键构建
build_exe.bat

# 或手动
pyinstaller --onefile --name "TravelPlanner" \
    --add-data "templates;templates" \
    --add-data "static;static" \
    --hidden-import flask \
    --hidden-import flask_cors \
    --hidden-import database \
    --hidden-import ocr_engine \
    --hidden-import parser \
    --hidden-import xiaohongshu \
    --hidden-import pdf_export \
    --hidden-import config_manager \
    --hidden-import webview \
    --hidden-import reportlab \
    --hidden-import PIL \
    --exclude-module torch \
    --exclude-module scipy \
    --exclude-module pandas \
    --exclude-module numpy \
    --clean \
    app.py

# 输出: dist/TravelPlanner.exe (~20MB)
```

### Python 依赖

```
flask>=3.0              # Web框架
flask-cors>=4.0         # 跨域支持
pillow>=10.0            # 图片处理+验证码
pytesseract>=0.3        # OCR接口（需安装Tesseract）
pywebview>=6.0          # 原生桌面窗口
reportlab>=4.5          # PDF生成
pyinstaller>=6.0        # exe打包
```

### 添加新景点数据

编辑 `xiaohongshu.py` 中的 `MOCK_XHS_DATA` 字典：

```python
MOCK_XHS_DATA = {
    "景点名": [
        {
            "id": "xhs_xxx",
            "title": "帖子标题",
            "author": "作者名",
            "likes": "1.5w",
            "cover": "🏯",
            "tags": ["标签1", "标签2"],
            "summary": "帖子摘要内容",
            "url": _xhs_search_url("搜索关键词")
        },
    ],
}
```

### 添加新的AI模型

在 `app.py` 的 `call_anthropic_api` 函数中处理新的API格式。
API类型在 `config.json` 的 `api_type` 字段控制：`"openai"` 或 `"anthropic"`。

---

## License

MIT

---

**Made with Python + Flask + Vanilla JS**  
🤖 AI powered by DeepSeek / Anthropic Claude
