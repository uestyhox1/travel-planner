# 旅行攻略管理器 (Travel Planner)

桌面版旅行攻略管理工具 — 上传攻略图片 → OCR识别 → 自动生成日程表 → 关联小红书攻略 → 一键导出PDF

## 快速开始

### 方式一：直接运行（推荐）
1. 下载 `dist/TravelPlanner.exe`
2. 双击运行 → 原生桌面窗口自动打开
3. 登录（默认管理员: `admin` / `admin`）
4. 上传攻略图片或输入文本

### 方式二：从源码运行
```bash
pip install flask flask-cors pillow pytesseract pywebview reportlab
python app.py           # 原生桌面窗口
python app.py --browser # 浏览器模式
```

## 功能一览

| 功能 | 说明 |
|------|------|
| 📷 OCR识别 | Tesseract中文OCR，自动提取图片文字（可选安装） |
| 📅 日程解析 | 智能解析"第X天"/"X号"等多种格式 |
| 🤖 AI景点提取 | 通过DeepSeek API自动识别景点并生成简介 |
| 📕 小红书 | 内置30+热门景点攻略，一键跳转真实搜索 |
| ✅ 待办清单 | 优先级/完成追踪/进度条 |
| 📄 PDF导出 | 模板化导出含封面的精美PDF |
| 🎨 深色模式 | 浅色/深色一键切换 |
| 🔐 用户系统 | 注册/登录/图片验证码/修改密码 |
| 🤖 AI助手 | 真实LLM交互，基于行程上下文回答 |

## OCR 安装（可选）

OCR功能需要安装 Tesseract：

1. 下载安装 [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/releases)
2. 安装时勾选 Chinese (Simplified) 语言包
3. 或者将 `tesseract.exe` 和 `tessdata/chi_sim.traineddata` 放到应用的 `tesseract/` 文件夹

> 不安装OCR也能正常使用——上传图片后手动输入文字即可。

## AI 配置

在「系统设置 → API配置」中填入API Key：
- **DeepSeek**: [platform.deepseek.com](https://platform.deepseek.com) 获取Key
- **Anthropic**: [console.anthropic.com](https://console.anthropic.com) 获取Key

## 项目结构

```
旅行攻略/
├── app.py                  # Flask主程序 + 启动入口
├── database.py             # SQLite数据库（7表）
├── ocr_engine.py           # OCR引擎（Tesseract/PaddleOCR/EasyOCR）
├── parser.py               # 行程文本解析
├── xiaohongshu.py          # 小红书攻略服务
├── pdf_export.py           # PDF导出（ReportLab）
├── config_manager.py       # 配置管理
├── templates/index.html    # 前端单页面
├── static/
│   ├── css/style.css       # 样式（含深色模式）
│   └── js/app.js           # 前端逻辑
├── build_exe.bat           # PyInstaller打包脚本
├── requirements.txt        # Python依赖
├── .gitignore
└── README.md
```

## 迁移部署

整个文件夹复制到目标电脑即可运行，无需安装Python：

```
旅行攻略/
├── TravelPlanner.exe      ← 双击运行
├── data/                  ← 自动创建（数据库+配置）
└── tesseract/             ← 可选（放置便携版Tesseract）
```

- 数据库和配置自动保存在 `exe同级目录/data/`
- API Key和其他设置随 `data/config.json` 一起迁移
- 如需OCR，将便携版Tesseract放入 `tesseract/` 文件夹

## 技术栈

- **后端**: Python 3.13 + Flask + SQLite
- **前端**: Vanilla HTML/CSS/JS（无框架依赖）
- **桌面**: PyWebView（原生窗口）
- **打包**: PyInstaller（单文件exe）
- **OCR**: Tesseract + pytesseract
- **AI**: DeepSeek/Anthropic API
- **PDF**: ReportLab

## 构建

```bash
pip install -r requirements.txt
build_exe.bat
# 输出: dist/TravelPlanner.exe (~20MB)
```
