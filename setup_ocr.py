"""
旅行攻略管理器 - OCR 引擎一键安装脚本
=============================================
自动检测、下载、配置便携版 Tesseract OCR（中英文）

用法：
    python setup_ocr.py          # 自动安装
    python setup_ocr.py --check  # 仅检查状态

在项目根目录运行，会在当前目录创建 tesseract/ 文件夹。
"""

import os
import sys

# 修复 Windows 控制台编码问题（支持中文和 Emoji 输出）
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
import shutil
import subprocess
import urllib.request
import tempfile
import zipfile
from pathlib import Path

# ============================================================
# 配置
# ============================================================

PROJECT_DIR = Path(__file__).parent.absolute()
TESSERACT_DIR = PROJECT_DIR / "tesseract"
TESSDATA_DIR = TESSERACT_DIR / "tessdata"

# Tesseract 安装器下载地址 (UB-Mannheim build, Windows 64-bit)
TESSERACT_INSTALLER_URL = (
    "https://github.com/UB-Mannheim/tesseract/releases/download/"
    "v5.4.0.20240606/tesseract-ocr-w64-setup-5.4.0.20240606.exe"
)

# 语言包下载地址
TESSDATA_URLS = {
    "eng": "https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata",
    "chi_sim": "https://github.com/tesseract-ocr/tessdata_fast/raw/main/chi_sim.traineddata",
}

# 系统安装路径（按优先级排列）
SYSTEM_TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe"),
]


# ============================================================
# 工具函数
# ============================================================

def print_header(text):
    """打印标题"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")


def print_step(text):
    """打印步骤"""
    print(f"\n  ⏳ {text}...")


def print_ok(text):
    """打印成功"""
    print(f"  ✅ {text}")


def print_warn(text):
    """打印警告"""
    print(f"  ⚠️  {text}")


def print_error(text):
    """打印错误"""
    print(f"  ❌ {text}")


def download_file(url, dest_path, desc="file"):
    """下载文件，带进度条"""
    print_step(f"下载 {desc}")

    def _progress(block_num, block_size, total_size):
        if total_size > 0:
            percent = min(100, int(block_num * block_size * 100 / total_size))
            downloaded = block_num * block_size
            if block_num % 20 == 0:  # 每 20 个 block 打印一次
                print(f"\r    下载中... {percent}% "
                      f"({downloaded/1024/1024:.1f}/{total_size/1024/1024:.1f} MB)", end="")

    try:
        urllib.request.urlretrieve(url, dest_path, _progress)
        print(f"\r    下载完成: {os.path.getsize(dest_path)/1024/1024:.1f} MB")
        return True
    except Exception as e:
        print(f"\r    下载失败: {e}")
        return False


# ============================================================
# 检测函数
# ============================================================

def check_portable_exists():
    """检查便携版是否已存在"""
    tesseract_exe = TESSERACT_DIR / "tesseract.exe"
    eng_data = TESSDATA_DIR / "eng.traineddata"
    chi_data = TESSDATA_DIR / "chi_sim.traineddata"
    return tesseract_exe.exists() and eng_data.exists() and chi_data.exists()


def find_system_tesseract():
    """查找系统中已安装的 Tesseract"""
    for path in SYSTEM_TESSERACT_PATHS:
        if os.path.exists(path):
            return Path(path)
    # 也检查 PATH
    for p in os.environ.get("PATH", "").split(os.pathsep):
        exe = Path(p) / "tesseract.exe"
        if exe.exists():
            return exe
    return None


def check_winget():
    """检查 winget 是否可用"""
    try:
        result = subprocess.run(
            ["winget", "--version"],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def test_tesseract(tesseract_path, tessdata_path):
    """测试 Tesseract 是否能正常工作"""
    try:
        env = os.environ.copy()
        env["TESSDATA_PREFIX"] = str(tessdata_path)
        result = subprocess.run(
            [str(tesseract_path), "--list-langs"],
            capture_output=True, text=True, timeout=15,
            env=env,
        )
        return "eng" in result.stdout and "chi_sim" in result.stdout
    except Exception:
        return False


# ============================================================
# 安装函数
# ============================================================

def copy_from_system(system_exe):
    """从系统安装复制 Tesseract 到便携目录"""
    print_step("从系统安装复制 Tesseract")
    src_dir = system_exe.parent

    # 复制所有文件
    TESSERACT_DIR.mkdir(parents=True, exist_ok=True)

    copied = 0
    total_size = 0
    for item in src_dir.iterdir():
        if item.is_file():
            dest = TESSERACT_DIR / item.name
            if not dest.exists():
                shutil.copy2(item, dest)
                total_size += item.stat().st_size
                copied += 1

    # 复制 tessdata
    src_tessdata = src_dir / "tessdata"
    if src_tessdata.exists():
        if TESSDATA_DIR.exists():
            shutil.rmtree(TESSDATA_DIR)
        shutil.copytree(src_tessdata, TESSDATA_DIR)

    print_ok(f"复制了 {copied} 个文件 ({total_size/1024/1024:.1f} MB)")


def install_via_winget():
    """通过 winget 安装 Tesseract"""
    print_step("winget 安装 Tesseract OCR（可能需要几分钟）")
    print('  如果弹出 UAC 提示，请点击"是"允许安装')
    try:
        result = subprocess.run(
            ["winget", "install", "UB-Mannheim.TesseractOCR",
             "--accept-source-agreements", "--accept-package-agreements"],
            capture_output=False,  # 让用户看到进度
            timeout=300,
        )
        if result.returncode == 0:
            # 安装完成后，找到安装路径并复制
            sys_exe = find_system_tesseract()
            if sys_exe:
                copy_from_system(sys_exe)
                return True
        return False
    except Exception as e:
        print_error(f"winget 安装失败: {e}")
        return False


def download_language_data():
    """下载语言包"""
    TESSDATA_DIR.mkdir(parents=True, exist_ok=True)

    for lang, url in TESSDATA_URLS.items():
        dest = TESSDATA_DIR / f"{lang}.traineddata"
        if dest.exists():
            print_ok(f"{lang}.traineddata 已存在 ({dest.stat().st_size/1024/1024:.1f} MB)")
            continue

        if download_file(url, dest, f"{lang} 语言包"):
            print_ok(f"{lang}.traineddata 下载成功")
        else:
            print_error(f"{lang}.traineddata 下载失败")
            return False
    return True


# ============================================================
# 主流程
# ============================================================

def main():
    print_header("旅行攻略管理器 - OCR 引擎安装向导")

    # ---------- 步骤 1: 检查是否已安装 ----------
    print_step("检查便携版 Tesseract")
    if check_portable_exists():
        print_ok("便携版 Tesseract 已就绪！")
        # 验证可用性
        if test_tesseract(
            TESSERACT_DIR / "tesseract.exe",
            TESSDATA_DIR
        ):
            print_ok("OCR 功能正常，中英文识别可用")
            print_header("安装完成 ✨")
            return 0
        else:
            print_warn("Tesseract 文件存在但无法正常工作，尝试修复...")

    # ---------- 步骤 2: 查找系统安装 ----------
    print_step("查找系统中已安装的 Tesseract")
    system_exe = find_system_tesseract()
    if system_exe:
        print_ok(f"找到系统安装: {system_exe}")
        copy_from_system(system_exe)

        # 下载缺失的语言包
        if not download_language_data():
            print_warn("部分语言包下载失败，仅英文 OCR 可用")

        if check_portable_exists():
            print_ok("便携版 Tesseract 配置完成！")
            print_header("安装完成 ✨")
            return 0

    else:
        print_warn("未检测到系统安装的 Tesseract")

    # ---------- 步骤 3: 尝试 winget ----------
    if check_winget():
        print_ok("检测到 winget 包管理器")
        choice = input("\n  是否通过 winget 自动安装 Tesseract? [Y/n]: ").strip().lower()
        if choice in ("", "y", "yes"):
            if install_via_winget():
                if download_language_data():
                    print_ok("全部安装完成！")
                    print_header("安装完成 ✨")
                    return 0

    # ---------- 步骤 4: 手动安装指引 ----------
    print_header("手动安装 Tesseract OCR")
    print("""
  由于无法自动安装，请手动完成以下步骤：

  【方法 A：一键安装（推荐）】
  在 PowerShell 或 CMD 中运行：
      winget install UB-Mannheim.TesseractOCR

  安装完成后，重新运行本脚本：
      python setup_ocr.py

  【方法 B：手动下载安装】
  1. 打开浏览器，访问：
     https://github.com/UB-Mannheim/tesseract/releases
  2. 下载最新版的 tesseract-ocr-w64-setup-*.exe
  3. 运行安装程序（记住安装路径）
  4. 回到这里，重新运行：python setup_ocr.py

  【方法 C：仅安装语言包（便携版已存在但语言包缺失）】
  如果 tesseract/ 文件夹已有 tesseract.exe（比如从其他电脑复制的），
  但缺少中文语言包，请手动下载并放入 tesseract/tessdata/ ：
      chi_sim.traineddata:
      https://github.com/tesseract-ocr/tessdata_fast/raw/main/chi_sim.traineddata

  注意：不安装 OCR 也能正常使用本应用的所有其他功能，
  只是不能用图片识别，需要手动输入文字。
    """)

    return 1


def check_only():
    """仅检查 OCR 状态"""
    print_header("OCR 状态检查")

    # 便携版
    if check_portable_exists():
        print_ok("便携版 Tesseract: 已安装")
        if test_tesseract(TESSERACT_DIR / "tesseract.exe", TESSDATA_DIR):
            print_ok("OCR 可用性: 正常")
        else:
            print_warn("OCR 可用性: 异常，请重新安装")
    else:
        print_warn("便携版 Tesseract: 未安装")

    # 系统版
    system_exe = find_system_tesseract()
    if system_exe:
        print_ok(f"系统 Tesseract: {system_exe}")
    else:
        print_warn("系统 Tesseract: 未安装")

    # winget
    if check_winget():
        print_ok("winget: 可用")
    else:
        print_warn("winget: 不可用")

    # 文件清单
    print(f"\n  tesseract/tesseract.exe:  "
          f"{'存在' if (TESSERACT_DIR / 'tesseract.exe').exists() else '缺失'}")
    for lang in ["eng", "chi_sim"]:
        print(f"  tesseract/tessdata/{lang}.traineddata:  "
              f"{'存在' if (TESSDATA_DIR / f'{lang}.traineddata').exists() else '缺失'}")


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(check_only())
    else:
        sys.exit(main())
