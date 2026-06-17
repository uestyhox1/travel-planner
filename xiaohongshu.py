"""
旅行攻略管理器 - 小红书服务
提供热门景点的小红书攻略搜索（内置模拟数据 + 真实搜索链接）
"""
import json
import os
import urllib.parse


def _xhs_search_url(keyword):
    """生成小红书搜索链接"""
    return "https://www.xiaohongshu.com/search_result?keyword=" + urllib.parse.quote(keyword) + "&type=51"


# 内置热门景点的小红书模拟数据（含真实搜索链接）
MOCK_XHS_DATA = {
    "故宫": [
        {"id": "xhs_001", "title": "故宫淡季攻略｜人少又好拍，拍出空无一人的太和殿", "author": "旅行小达人", "likes": "2.3w", "cover": "🏯", "tags": ["故宫", "拍照", "攻略"],
         "summary": "冬天去故宫人真的很少！9点开门就去，能拍到空无一人的太和殿广场。建议走西线，人更少。",
         "url": _xhs_search_url("故宫 淡季 攻略")},
        {"id": "xhs_002", "title": "故宫博物院最全游览路线｜4小时走完不留遗憾", "author": "北京土著小张", "likes": "1.8w", "cover": "📜", "tags": ["故宫", "路线", "北京"],
         "summary": "午门进→太和殿→中和殿→保和殿→乾清宫→坤宁宫→御花园→神武门出，一路不回头！",
         "url": _xhs_search_url("故宫 游览路线")},
        {"id": "xhs_003", "title": "故宫拍照绝佳机位分享｜出片率100%", "author": "摄影爱好者Lily", "likes": "5.6k", "cover": "📷", "tags": ["故宫", "拍照"],
         "summary": "这8个机位人少景美，随便拍都是大片质感。",
         "url": _xhs_search_url("故宫 拍照 机位")},
    ],
    "长城": [
        {"id": "xhs_004", "title": "八达岭长城避坑指南｜千万别周未去！", "author": "旅行避坑达人", "likes": "3.1w", "cover": "🏔️", "tags": ["长城", "八达岭", "避坑"],
         "summary": "周一至周五去，人少体验好。建议坐S2线去，比公交车快很多。",
         "url": _xhs_search_url("八达岭长城 避坑")},
        {"id": "xhs_005", "title": "慕田峪长城 vs 八达岭｜到底选哪个？", "author": "长城专业户", "likes": "1.2w", "cover": "🧗", "tags": ["长城", "慕田峪"],
         "summary": "慕田峪人少风景好，有滑道可以滑下山，超刺激！适合年轻人。",
         "url": _xhs_search_url("慕田峪长城 攻略")},
    ],
    "西湖": [
        {"id": "xhs_006", "title": "西湖一日游完美路线｜本地人推荐", "author": "杭州小囡囡", "likes": "4.2w", "cover": "🛶", "tags": ["西湖", "杭州", "一日游"],
         "summary": "断桥→白堤→孤山→苏堤→花港观鱼→雷峰塔，傍晚在长桥公园看日落绝美！",
         "url": _xhs_search_url("西湖 一日游 路线")},
        {"id": "xhs_007", "title": "西湖边这些小吃千万别错过！人均30吃到撑", "author": "吃货小分队", "likes": "2.8w", "cover": "🍜", "tags": ["西湖", "美食"],
         "summary": "葱包烩、定胜糕、片儿川、西湖醋鱼……每一样都好吃到舔盘！",
         "url": _xhs_search_url("西湖 美食 小吃")},
    ],
    "外滩": [
        {"id": "xhs_008", "title": "外滩夜景拍摄全攻略｜三件套最佳机位", "author": "魔都摄影师", "likes": "5.3w", "cover": "🌃", "tags": ["外滩", "夜景", "上海"],
         "summary": "北外滩人少视角好，比南京东路那边强太多！晚上7点亮灯，提前占位。",
         "url": _xhs_search_url("外滩 夜景 拍照")},
        {"id": "xhs_009", "title": "上海3天2夜citywalk路线｜不走回头路", "author": "城市漫步者", "likes": "3.5w", "cover": "🚶", "tags": ["上海", "citywalk"],
         "summary": "Day1外滩-南京路-人民广场，Day2武康路-安福路-思南路，Day3迪士尼！",
         "url": _xhs_search_url("上海 citywalk 路线")},
    ],
    "兵马俑": [
        {"id": "xhs_010", "title": "兵马俑参观全攻略｜避开人流的秘密", "author": "西安向导老王", "likes": "2.1w", "cover": "⚔️", "tags": ["兵马俑", "西安", "攻略"],
         "summary": "8:30开门就进！建议请讲解，否则就是看一堆泥人。游览顺序：一号坑→三号坑→二号坑",
         "url": _xhs_search_url("兵马俑 参观 攻略")},
    ],
    "迪士尼": [
        {"id": "xhs_011", "title": "上海迪士尼超详细攻略｜热门项目一网打尽", "author": "迪士尼在逃公主", "likes": "8.5w", "cover": "🏰", "tags": ["迪士尼", "上海", "攻略"],
         "summary": "早享卡必买！7:30入园先冲飞跃地平线→加勒比海盗→创极速光轮，下午佛系逛拍。",
         "url": _xhs_search_url("上海迪士尼 详细攻略")},
        {"id": "xhs_012", "title": "迪士尼隐藏玩法｜99%的人不知道的彩蛋", "author": "魔法少女Mia", "likes": "4.8w", "cover": "✨", "tags": ["迪士尼", "隐藏玩法"],
         "summary": "和工作人员说'第一次来'会得到惊喜贴纸！某些餐厅的隐藏菜单只有问了才知道。",
         "url": _xhs_search_url("迪士尼 隐藏玩法 彩蛋")},
    ],
    "东方明珠": [
        {"id": "xhs_013", "title": "东方明珠值得上去吗？真实体验分享", "author": "真实测评君", "likes": "9.2k", "cover": "🗼", "tags": ["东方明珠", "上海"],
         "summary": "建议去上海中心大厦或环球金融中心，视野更好价格差不多。",
         "url": _xhs_search_url("东方明珠 值不值得去")},
    ],
    "颐和园": [
        {"id": "xhs_014", "title": "颐和园最美季节｜秋天一定要去苏州街", "author": "帝都漫步者", "likes": "1.5w", "cover": "🍂", "tags": ["颐和园", "秋天", "北京"],
         "summary": "十月底的颐和园美得像画！从北宫门进，先逛苏州街再上山，人少景美。",
         "url": _xhs_search_url("颐和园 秋天 攻略")},
    ],
    "天安门": [
        {"id": "xhs_015", "title": "天安门看升旗仪式全流程｜超详细时间表", "author": "爱国青年小王", "likes": "6.7w", "cover": "🇨🇳", "tags": ["天安门", "升旗"],
         "summary": "提前查好升旗时间，至少提前2小时到。记得带身份证！冬天多穿点，等的时候特别冷。",
         "url": _xhs_search_url("天安门 升旗 攻略")},
    ],
    "大雁塔": [
        {"id": "xhs_016", "title": "大雁塔音乐喷泉｜亚洲最大喷泉看这一篇就够了", "author": "长安夜游人", "likes": "1.8w", "cover": "⛲", "tags": ["大雁塔", "喷泉", "西安"],
         "summary": "晚上8点开始，建议7点半去占位置。大唐不夜城的表演也不要错过！",
         "url": _xhs_search_url("大雁塔 音乐喷泉 攻略")},
    ],
    "洪崖洞": [
        {"id": "xhs_017", "title": "洪崖洞夜景最佳拍摄点｜别再挤在景区门口了", "author": "重庆崽儿", "likes": "3.9w", "cover": "🌉", "tags": ["洪崖洞", "夜景", "重庆"],
         "summary": "去千厮门大桥上拍！或者江对岸，角度绝了。景区里面其实没啥好逛的。",
         "url": _xhs_search_url("洪崖洞 夜景 拍照")},
    ],
    "鼓浪屿": [
        {"id": "xhs_018", "title": "鼓浪屿一日游路线｜避开人流的小众玩法", "author": "厦门土著鱼丸", "likes": "2.5w", "cover": "🏝️", "tags": ["鼓浪屿", "厦门"],
         "summary": "建议坐早班船去，先逛内厝澳那边（人少），下午再去龙头路。日光岩看日落绝了！",
         "url": _xhs_search_url("鼓浪屿 一日游 小众")},
    ],
    "张家界": [
        {"id": "xhs_019", "title": "张家界国家森林公园2日游攻略｜阿凡达取景地", "author": "湘西小哥", "likes": "4.0w", "cover": "🏞️", "tags": ["张家界", "森林公园"],
         "summary": "Day1天子山-袁家界-杨家界，Day2金鞭溪-十里画廊。一定要坐百龙天梯！",
         "url": _xhs_search_url("张家界 森林公园 攻略")},
    ],
    "九寨沟": [
        {"id": "xhs_020", "title": "九寨沟秋季攻略｜五彩池美到窒息", "author": "川西旅行家", "likes": "5.7w", "cover": "💎", "tags": ["九寨沟", "秋天"],
         "summary": "10月中下旬是最佳观赏期！建议住沟内，早上7点进沟避开人流。",
         "url": _xhs_search_url("九寨沟 秋天 攻略")},
    ],
}

# 默认攻略帖子（当景点没有匹配数据时）
DEFAULT_XHS_POSTS = [
    {"id": "xhs_def_1", "title": "【超全攻略】第一次来一定要看！避坑+路线+美食", "author": "旅行助手机器人", "likes": "1.5w", "cover": "📝", "tags": ["攻略", "旅行"],
     "summary": "整理了一份超详细的旅行攻略，包含所有必打卡景点和隐藏小众玩法。",
     "url": _xhs_search_url("旅行 超全攻略")},
    {"id": "xhs_def_2", "title": "本地人强推！这些地方比网红景点好玩100倍", "author": "当地向导", "likes": "9.8k", "cover": "🗺️", "tags": ["小众", "推荐"],
     "summary": "避开人挤人的网红景点，这些本地人才知道的好去处值得一去。",
     "url": _xhs_search_url("本地人推荐 小众景点")},
    {"id": "xhs_def_3", "title": "人均预算公开！旅行真实花费明细", "author": "精打细算旅行家", "likes": "2.3w", "cover": "💰", "tags": ["预算", "花费"],
     "summary": "机酒+门票+餐饮+购物，每一项花费都列出来了，比想象中便宜！",
     "url": _xhs_search_url("旅行 花费 预算")},
]


def search_xiaohongshu(query, limit=20, sort='default'):
    """
    搜索小红书帖子
    query: 搜索关键词
    limit: 返回数量上限
    sort: 排序方式 - 'default'(综合), 'newest'(最新), 'likes'(最多点赞)
    """
    results = []
    query_lower = query.lower().strip()

    # 1) 精确匹配景点名
    if query in MOCK_XHS_DATA:
        results = list(MOCK_XHS_DATA[query])
    else:
        # 2) 景点名包含query 或 query包含景点名（全词匹配）
        for key, posts in MOCK_XHS_DATA.items():
            if query_lower in key.lower() or key.lower() in query_lower:
                results.extend(posts)

        # 3) 模糊搜索：在标题中搜索关键词
        if not results:
            for key, posts in MOCK_XHS_DATA.items():
                for post in posts:
                    if query_lower in post['title'].lower() or query_lower in ' '.join(post.get('tags', [])).lower():
                        results.append(post)

        # 4) 逐字匹配（只在query>=2字符时）
        if not results and len(query) >= 2:
            for key, posts in MOCK_XHS_DATA.items():
                if any(c in key for c in query):
                    results.extend(posts[:1])

    # 去重
    seen_ids = set()
    unique_results = []
    for r in results:
        if r['id'] not in seen_ids:
            seen_ids.add(r['id'])
            unique_results.append(r)

    # 排序
    if sort == 'likes':
        def parse_likes(post):
            l = post.get('likes', '0').replace('w', '0000').replace('k', '0').replace('.', '')
            try: return int(l)
            except: return 0
        unique_results.sort(key=parse_likes, reverse=True)
    elif sort == 'newest':
        # 模拟最新排序：反转顺序
        unique_results.reverse()

    if unique_results:
        return unique_results[:limit]

    # 没有匹配时，返回与该query相关的默认帖子（而非完全不相关的）
    # 尝试用query的前几个字做标签搜索
    for post in DEFAULT_XHS_POSTS:
        post_copy = dict(post)
        post_copy['title'] = f'🔍 "{query}" 的相关攻略'
        post_copy['summary'] = f'在小红书上搜索"{query}"，发现更多实时攻略和隐藏玩法。'
        post_copy['tags'] = [query, '攻略', '旅行']
        post_copy['url'] = _xhs_search_url(f'{query} 攻略')
        unique_results.append(post_copy)

    return unique_results[:limit]


def get_attraction_xhs_posts(attraction_name, refresh=False):
    """获取景点的关联小红书帖子"""
    return search_xiaohongshu(attraction_name)


def search_attractions_by_keyword(keyword):
    """根据关键词搜索景点"""
    results = []
    for name in MOCK_XHS_DATA:
        if keyword in name or any(keyword in post["title"] for post in MOCK_XHS_DATA[name]):
            results.append({
                "name": name,
                "post_count": len(MOCK_XHS_DATA[name]),
                "top_post": MOCK_XHS_DATA[name][0]
            })
    return results


# 热门城市-景点映射
CITY_ATTRACTIONS = {
    "北京": ["故宫", "长城", "天安门", "颐和园", "天坛", "鸟巢", "水立方"],
    "上海": ["外滩", "东方明珠", "迪士尼", "豫园", "南京路"],
    "杭州": ["西湖", "雷峰塔", "灵隐寺"],
    "西安": ["兵马俑", "大雁塔", "钟楼", "鼓楼"],
    "成都": ["宽窄巷子", "锦里", "大熊猫基地", "都江堰"],
    "重庆": ["洪崖洞", "解放碑", "磁器口"],
    "厦门": ["鼓浪屿", "厦门大学", "南普陀"],
    "张家界": ["张家界"],
    "九寨沟": ["九寨沟"],
}
