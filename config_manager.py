"""
旅行攻略管理器 - 配置管理
管理 API Key 等用户设置
"""
import os
import json
import sys

# 数据目录
if getattr(sys, 'frozen', False):
    DATA_DIR = os.path.join(os.path.dirname(sys.executable), 'data')
else:
    DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

CONFIG_PATH = os.path.join(DATA_DIR, 'config.json')

DEFAULT_CONFIG = {
    "api_key": "",
    "model": "deepseek-chat",
    "api_base": "https://api.deepseek.com",
    "api_type": "openai",  # "anthropic" or "openai" (DeepSeek uses OpenAI-compatible API)
}


def load_config():
    """加载配置"""
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)
            # 合并默认值
            for k, v in DEFAULT_CONFIG.items():
                if k not in config:
                    config[k] = v
            return config
        except (json.JSONDecodeError, IOError):
            pass
    return dict(DEFAULT_CONFIG)


def save_config(config):
    """保存配置"""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_api_key():
    """获取 API Key"""
    config = load_config()
    return config.get('api_key', '').strip()


def get_model():
    """获取模型名称"""
    config = load_config()
    return config.get('model', 'claude-sonnet-4-6')


def get_api_base():
    """获取 API Base URL"""
    config = load_config()
    return config.get('api_base', 'https://api.anthropic.com')
