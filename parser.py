"""
旅行攻略管理器 - 文本解析器
将 OCR 识别的文本或用户输入的文本解析为结构化的行程日程
"""
import re


def parse_travel_text(text):
    """
    解析旅行攻略文本，提取天数和活动信息

    支持多种格式：
    1. "第X天" / "Day X" 作为天的分隔
    2. "09:00" / "上午" / "下午" 作为时间标记
    3. 数字列表 1. 2. 3. 作为活动列表
    4. 景点名 + 描述
    """
    if not text or not text.strip():
        return {"title": "未命名攻略", "days": []}

    lines = [line.strip() for line in text.split('\n') if line.strip()]

    # ---- 提取标题 ----
    title = ""
    for i, line in enumerate(lines[:5]):
        if any(kw in line for kw in ['攻略', '游', '行程', '旅行', '之旅', '旅游']):
            title = line[:40]
            # Mark this line as processed (remove from parsing)
            lines[i] = None
            break
    if not title and lines:
        # Use first line as title if it doesn't look like an activity
        first = lines[0]
        if first and not re.search(r'\d{1,2}[:：]\d{2}', first) and not re.search(r'第\s*[一二三四五六七八九十\d]+\s*[天日]', first):
            title = first[:40]
            lines[0] = None

    # Filter out None lines
    lines = [l for l in lines if l is not None]

    if not title:
        title = "旅行攻略"

    # ---- 天数解析 ----
    day_patterns = [
        r'第\s*([一二三四五六七八九十\d]+)\s*[天日]',
        r'[Dd]ay\s*(\d+)',
        r'【?第\s*([一二三四五六七八九十\d]+)\s*[天日]】?',
        r'^(\d{1,2})\s*[号日]\s*[:：]',         # "19号：" or "19号:"
        r'^(\d{1,2})\s*[号日]\s*[晚晨早]?\s*[:：]',  # "18号晚："
        r'^(\d{1,2})\s*[号日]\s*$',              # "19号" on its own
    ]

    time_patterns = [
        r'^(\d{1,2}[:：]\d{2})',
        r'^(上午|中午|下午|晚上|早晨|清晨|早上|凌晨|傍晚|深夜)',
        r'^([上下中]午\s*\d{1,2}[点時])',
        r'^(上午|中午|下午|晚上|早晨|清晨|早上)\s*[_\-—]\s*',  # "上午 _" or "上午 -"
    ]

    chinese_num = {
        '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
        '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
    }

    def parse_day_number(s):
        if s.isdigit():
            return int(s)
        return chinese_num.get(s, 1)

    # Known attractions for location matching
    famous_attractions = [
        "故宫", "长城", "八达岭长城", "慕田峪长城", "天安门", "颐和园", "天坛", "鸟巢", "水立方",
        "北海公园", "圆明园", "雍和宫", "南锣鼓巷", "王府井", "三里屯", "798艺术区",
        "西湖", "雷峰塔", "灵隐寺", "断桥", "苏堤", "花港观鱼",
        "东方明珠", "外滩", "迪士尼", "豫园", "南京路", "武康路",
        "大雁塔", "兵马俑", "钟楼", "鼓楼", "大唐不夜城",
        "宽窄巷子", "锦里", "大熊猫基地", "都江堰", "春熙路",
        "中山陵", "夫子庙", "秦淮河", "总统府",
        "鼓浪屿", "厦门大学", "南普陀", "曾厝垵",
        "栈桥", "八大关", "崂山", "五四广场",
        "象鼻山", "漓江", "阳朔", "西街",
        "黄果树瀑布", "张家界", "九寨沟", "黄山", "泰山", "华山",
        "洪崖洞", "解放碑", "磁器口", "长江索道",
        "布达拉宫", "大昭寺", "八廓街",
        "大三巴", "威尼斯人", "官也街",
        "浅草寺", "东京塔", "大阪城", "清水寺", "道顿堀", "奈良公园",
        "南山塔", "景福宫", "明洞", "弘大",
        "大皇宫", "四面佛", "考山路",
    ]

    days = []
    current_day = None
    day_counter = 0

    for line in lines:
        # Check for new day header
        is_new_day = False
        day_num = None
        day_title = ""

        for pattern in day_patterns:
            match = re.search(pattern, line)
            if match:
                day_num = parse_day_number(match.group(1))
                day_title = line[:40]
                is_new_day = True
                break

        if is_new_day:
            if current_day:
                days.append(current_day)
            day_counter = day_num
            current_day = {
                "day_number": day_num,
                "day_title": day_title,
                "date": "",
                "activities": []
            }
            continue

        # Auto-create first day
        if current_day is None:
            day_counter = 1
            current_day = {
                "day_number": 1,
                "day_title": "第1天",
                "date": "",
                "activities": []
            }

        # Skip lines that are clearly headers/descriptions
        if len(line) > 100 and not re.search(r'\d{1,2}[:：]\d{2}', line):
            continue
        if re.match(r'^[（(]', line) and not re.search(r'\d{1,2}[:：]\d{2}', line):
            continue

        # Extract time
        time_slot = ""
        content = line

        for pattern in time_patterns:
            match = re.search(pattern, line)
            if match:
                time_slot = match.group(1)
                content = line[match.end():].strip()
                content = re.sub(r'^[：:，,、.\s]+', '', content)
                break

        # Extract location from content
        # Strategy: look for famous attraction names in the content
        location = ""

        # First check: does content contain a famous attraction?
        for attr in famous_attractions:
            if attr in content:
                location = attr
                break

        # Second check: parenthetical content - but only if it looks like a place name (short, Chinese)
        if not location:
            paren_match = re.search(r'[（(]([^）)]{2,10})[）)]', content)
            if paren_match:
                candidate = paren_match.group(1)
                # Only use as location if it's short and Chinese (not "提前预约门票" type notes)
                if len(candidate) <= 6 and not any(kw in candidate for kw in ['提前', '预约', '门票', '注意', '建议', '需要', '记得', '不要', '必带']):
                    location = candidate
                # Remove parentheses regardless
                content = re.sub(r'[（(][^）)]+[）)]', '', content).strip()

        # Also remove remaining parenthetical notes
        content = re.sub(r'[（(][^）)]+[）)]', '', content).strip()

        # Remove bullet/list markers
        content = re.sub(r'^[\d]+[.、．]\s*', '', content)
        content = re.sub(r'^[►▸▶●○◆◇▪▫\-]\s*', '', content)

        if not content.strip():
            continue

        # Category detection
        category = "景点"
        food_kw = ['吃', '餐', '饭', '美食', '餐厅', '小吃', '烤鸭', '烤', '火锅', '面', '喝', '咖啡', '奶茶', '酒吧']
        stay_kw = ['住', '酒店', '民宿', '入住', '住宿', '青旅']
        transport_kw = ['交通', '地铁', '公交', '打车', '火车', '飞机', '高铁', '出发', '到达', '机场', '站']
        shop_kw = ['买', '购物', '纪念品', '特产', '商场', '免税店']

        if any(kw in content for kw in food_kw):
            category = "餐饮"
        elif any(kw in content for kw in stay_kw):
            category = "住宿"
        elif any(kw in content for kw in transport_kw):
            category = "交通"
        elif any(kw in content for kw in shop_kw):
            category = "购物"

        current_day["activities"].append({
            "time": time_slot,
            "content": content,
            "location": location,
            "category": category,
            "notes": ""
        })

    # Save last day
    if current_day:
        days.append(current_day)

    # If nothing parsed, create a basic day with all lines
    if not days or not any(d["activities"] for d in days):
        days = [{
            "day_number": 1,
            "day_title": "第1天",
            "date": "",
            "activities": [{"time": "", "content": l, "location": "", "category": "景点", "notes": ""}
                          for l in lines if l][:20]
        }]

    # ---- Second pass: fill missing locations using content match ----
    for day in days:
        for act in day["activities"]:
            if not act["location"]:
                for attr in famous_attractions:
                    if attr in act["content"]:
                        act["location"] = attr
                        break

    # ---- Generate title from locations ----
    all_locations = []
    for day in days:
        for act in day["activities"]:
            if act["location"] and act["location"] not in all_locations:
                all_locations.append(act["location"])
    if all_locations and not title.startswith(tuple(all_locations)):
        # Keep original title if it's good
        if title in ("旅行攻略", "未命名攻略", ""):
            title = "、".join(all_locations[:3]) + " 旅行攻略"

    return {"title": title, "days": days}


def parse_image_to_itinerary(ocr_text):
    """从OCR文本解析行程"""
    return parse_travel_text(ocr_text)
