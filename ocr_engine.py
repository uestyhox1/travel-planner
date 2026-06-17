"""
旅行攻略管理器 - OCR 识别引擎
支持多种后端：PaddleOCR（推荐，中文最佳）、EasyOCR、Tesseract
"""
import os
import sys
from PIL import Image, ImageEnhance, ImageFilter


def preprocess_image(image_path):
    """
    图片预处理：灰度化、增强对比度、锐化，提升OCR识别率
    """
    img = Image.open(image_path)

    # 如果图片过大，等比缩放
    max_size = 2000
    if max(img.size) > max_size:
        ratio = max_size / max(img.size)
        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
        img = img.resize(new_size, Image.LANCZOS)

    # 转为灰度图
    if img.mode != 'L':
        img_gray = img.convert('L')
    else:
        img_gray = img

    # 增强对比度
    enhancer = ImageEnhance.Contrast(img_gray)
    img_enhanced = enhancer.enhance(2.0)

    # 锐化
    img_sharp = img_enhanced.filter(ImageFilter.SHARPEN)

    return img_sharp


def ocr_with_paddleocr(image_path):
    """
    使用 PaddleOCR 进行 OCR 识别（中文识别效果最佳）
    首次运行会自动下载模型文件
    """
    try:
        from paddleocr import PaddleOCR

        # 初始化 PaddleOCR（中英文，启用文本方向分类）
        ocr = PaddleOCR(lang='ch', use_angle_cls=True)

        # 预处理图片
        img = preprocess_image(image_path)
        temp_path = image_path + ".preprocessed.png"
        img.save(temp_path)

        # 执行 OCR
        results = ocr.ocr(temp_path)

        # 清理临时文件
        try:
            os.remove(temp_path)
        except OSError:
            pass

        if not results or not results[0]:
            return {
                "success": False,
                "engine": "paddleocr",
                "error": "图片中未检测到文字",
                "text": "",
                "lines": []
            }

        # 提取文本行
        lines = []
        full_text_parts = []
        details = []

        for line_info in results[0]:
            text = line_info[1][0]  # 识别的文本
            confidence = line_info[1][1]  # 置信度

            if confidence > 0.5:  # 只保留置信度 > 50% 的结果
                lines.append(text)
                full_text_parts.append(text)
                details.append({
                    "text": text,
                    "confidence": round(confidence, 3),
                    "bbox": line_info[0]  # 边界框坐标
                })

        # 对文本行进行排序（按Y坐标从上到下，X坐标从左到右）
        # PaddleOCR 结果已经按阅读顺序排列，但我们可以进一步优化

        return {
            "success": True,
            "engine": "paddleocr",
            "text": "\n".join(full_text_parts),
            "lines": lines,
            "details": details
        }

    except ImportError:
        return {
            "success": False,
            "engine": "paddleocr",
            "error": "PaddleOCR 未安装，请运行: pip install paddleocr",
            "text": "",
            "lines": []
        }
    except Exception as e:
        return {
            "success": False,
            "engine": "paddleocr",
            "error": str(e),
            "text": "",
            "lines": []
        }


def ocr_with_easyocr(image_path):
    """
    使用 EasyOCR 进行 OCR 识别（纯 Python 实现，支持中文）
    """
    try:
        import easyocr
        reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
        img = preprocess_image(image_path)
        temp_path = image_path + ".temp.png"
        img.save(temp_path)

        results = reader.readtext(temp_path)

        try:
            os.remove(temp_path)
        except OSError:
            pass

        results.sort(key=lambda r: (r[0][0][1], r[0][0][0]))

        lines = []
        full_text_parts = []
        for bbox, text, conf in results:
            if conf > 0.3:
                lines.append(text)
                full_text_parts.append(text)

        return {
            "success": True,
            "engine": "easyocr",
            "text": "\n".join(full_text_parts),
            "lines": lines,
            "details": [{"text": t, "confidence": c} for _, t, c in results if c > 0.3]
        }
    except ImportError:
        return {"success": False, "engine": "easyocr", "error": "easyocr 未安装", "text": "", "lines": []}
    except Exception as e:
        return {"success": False, "engine": "easyocr", "error": str(e), "text": "", "lines": []}


def ocr_with_tesseract(image_path, lang='chi_sim+eng'):
    """
    Use Tesseract for OCR (auto-detect installation)
    Searches: portable folder > user install > system install
    """
    try:
        import pytesseract

        # Get the app's root directory (works in both dev and exe)
        if getattr(sys, 'frozen', False):
            app_dir = os.path.dirname(sys.executable)
        else:
            app_dir = os.path.dirname(os.path.abspath(__file__))

        # Priority 1: Portable Tesseract bundled with the app
        portable_paths = [
            os.path.join(app_dir, 'tesseract', 'tesseract.exe'),
            os.path.join(app_dir, '..', 'tesseract', 'tesseract.exe'),
        ]

        # Priority 2: User-local install
        user_paths = [
            os.path.expandvars(r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe"),
            os.path.join(os.path.expandvars(r"%LOCALAPPDATA%"), 'Tesseract-OCR', 'tesseract.exe'),
        ]

        # Priority 3: System-wide install
        system_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]

        all_paths = portable_paths + user_paths + system_paths
        tesseract_found = False

        for path in all_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                tesseract_found = True
                break

        if not tesseract_found:
            return {
                "success": False,
                "engine": "tesseract",
                "error": "Tesseract not found. Place tesseract.exe in the 'tesseract/' folder next to the app, or install Tesseract OCR.",
                "text": "",
                "lines": []
            }

        # Find tessdata: portable first, then installed
        tessdata_paths = [
            os.path.join(app_dir, 'tesseract', 'tessdata'),
            os.path.join(app_dir, '..', 'tesseract', 'tessdata'),
            os.path.expandvars(r"%LOCALAPPDATA%\tesseract\tessdata"),
        ]

        # Also check next to found tesseract.exe
        tesseract_dir = os.path.dirname(pytesseract.pytesseract.tesseract_cmd)
        tessdata_paths.insert(0, os.path.join(tesseract_dir, 'tessdata'))

        for td in tessdata_paths:
            chi_sim = os.path.join(td, 'chi_sim.traineddata')
            if os.path.exists(chi_sim):
                os.environ['TESSDATA_PREFIX'] = td
                break

        img = preprocess_image(image_path)
        text = pytesseract.image_to_string(img, lang=lang)

        return {
            "success": True,
            "engine": "tesseract",
            "text": text.strip(),
            "lines": [line.strip() for line in text.split('\n') if line.strip()]
        }
    except ImportError:
        return {"success": False, "engine": "tesseract", "error": "pytesseract 未安装", "text": "", "lines": []}
    except Exception as e:
        return {"success": False, "engine": "tesseract", "error": str(e), "text": "", "lines": []}


def ocr_image(image_path, engine='auto'):
    """
    统一的 OCR 接口，自动选择可用引擎
    优先级：PaddleOCR > EasyOCR > Tesseract
    engine: 'auto' | 'paddleocr' | 'easyocr' | 'tesseract'
    """
    result = None

    # PaddleOCR - best for Chinese
    if engine in ('auto', 'paddleocr'):
        result = ocr_with_paddleocr(image_path)
        if result['success']:
            return result

    # EasyOCR - fallback
    if engine in ('auto', 'easyocr'):
        result = ocr_with_easyocr(image_path)
        if result['success']:
            return result

    # Tesseract - last resort
    if engine in ('auto', 'tesseract'):
        result = ocr_with_tesseract(image_path)
        if result['success']:
            return result

    if result and not result['success']:
        return {
            "success": False,
            "engine": "none",
            "error": "所有 OCR 引擎都不可用。\n"
                     "推荐安装 PaddleOCR: pip install paddleocr\n"
                     "或使用手动文本输入。",
            "text": "",
            "lines": []
        }

    return {"success": False, "engine": "none", "error": "OCR引擎未配置", "text": "", "lines": []}
