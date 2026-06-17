"""
旅行攻略管理器 - PDF 导出模块
使用 reportlab 生成格式美观的旅行攻略 PDF
"""
import os
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, PageBreak, HRFlowable, KeepTogether)
from reportlab.platypus.flowables import Flowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


# ======== 中文字体注册 ========
FONT_PATHS = [
    (r'C:\Windows\Fonts\simhei.ttf', 'SimHei'),
    (r'C:\Windows\Fonts\msyh.ttc', 'MicrosoftYaHei'),
    (r'C:\Windows\Fonts\simkai.ttf', 'KaiTi'),
    (r'C:\Windows\Fonts\simsun.ttc', 'SimSun'),
]

FONT_TITLE = 'SimHei'
FONT_BODY = 'MicrosoftYaHei'
FONT_FALLBACK = 'Helvetica'

for path, name in FONT_PATHS:
    if os.path.exists(path):
        try:
            pdfmetrics.registerFont(TTFont(name, path))
        except Exception:
            pass

# Verify which fonts are available
AVAILABLE_FONTS = pdfmetrics.getRegisteredFontNames()
if 'SimHei' not in AVAILABLE_FONTS:
    FONT_TITLE = FONT_FALLBACK
if 'MicrosoftYaHei' not in AVAILABLE_FONTS:
    FONT_BODY = FONT_FALLBACK


# ======== 颜色方案 ========
COLOR_PRIMARY = HexColor('#4F46E5')
COLOR_ACCENT = HexColor('#10B981')
COLOR_WARNING = HexColor('#F59E0B')
COLOR_DANGER = HexColor('#EF4444')
COLOR_BG_LIGHT = HexColor('#F8FAFC')
COLOR_BG_CARD = HexColor('#EEF2FF')
COLOR_TEXT = HexColor('#1E293B')
COLOR_TEXT_SECONDARY = HexColor('#64748B')
COLOR_BORDER = HexColor('#E2E8F0')

# Category colors
CAT_COLORS = {
    '景点': HexColor('#F59E0B'),
    '餐饮': HexColor('#EF4444'),
    '住宿': HexColor('#4F46E5'),
    '交通': HexColor('#10B981'),
    '购物': HexColor('#EC4899'),
}


# ======== 自定义Flowable ========
class ColoredRect(Flowable):
    """彩色矩形块"""
    def __init__(self, width, height, color):
        super().__init__()
        self.width = width
        self.height = height
        self._color = color

    def draw(self):
        self.canv.setFillColor(self._color)
        self.canv.rect(0, 0, self.width, self.height, fill=1, stroke=0)


class GradientBar(Flowable):
    """渐变色条"""
    def __init__(self, width, height=4):
        super().__init__()
        self.width = width
        self.height = height

    def draw(self):
        self.canv.setFillColor(COLOR_PRIMARY)
        self.canv.rect(0, 0, self.width * 0.6, self.height, fill=1, stroke=0)
        self.canv.setFillColor(COLOR_ACCENT)
        self.canv.rect(self.width * 0.6, 0, self.width * 0.4, self.height, fill=1, stroke=0)


def on_first_page(canvas_obj, doc):
    """首页装饰"""
    canvas_obj.saveState()
    # 顶部色条
    canvas_obj.setFillColor(COLOR_PRIMARY)
    canvas_obj.rect(0, A4[1] - 8 * mm, A4[0], 8 * mm, fill=1, stroke=0)
    # 底部色条
    canvas_obj.setFillColor(COLOR_BG_LIGHT)
    canvas_obj.rect(0, 0, A4[0], 20 * mm, fill=1, stroke=0)
    canvas_obj.restoreState()


def on_later_pages(canvas_obj, doc):
    """后续页面装饰"""
    canvas_obj.saveState()
    # 页眉线
    canvas_obj.setStrokeColor(COLOR_BORDER)
    canvas_obj.setLineWidth(0.5)
    canvas_obj.line(20 * mm, A4[1] - 15 * mm, A4[0] - 20 * mm, A4[1] - 15 * mm)
    # 页码
    canvas_obj.setFont(FONT_BODY if 'MicrosoftYaHei' in AVAILABLE_FONTS else FONT_FALLBACK, 8)
    canvas_obj.setFillColor(COLOR_TEXT_SECONDARY)
    canvas_obj.drawCentredString(A4[0] / 2, 12 * mm, f"- {canvas_obj.getPageNumber()} -")
    canvas_obj.restoreState()


def make_styles():
    """创建段落样式"""
    base = {
        'fontName': FONT_BODY if 'MicrosoftYaHei' in AVAILABLE_FONTS else FONT_FALLBACK,
        'fontSize': 10,
        'leading': 16,
        'textColor': COLOR_TEXT,
    }
    return {
        'title': ParagraphStyle('title', **{**base, 'fontName': FONT_TITLE, 'fontSize': 24, 'leading': 32, 'alignment': TA_CENTER, 'textColor': COLOR_PRIMARY}),
        'subtitle': ParagraphStyle('subtitle', **{**base, 'fontSize': 12, 'leading': 18, 'alignment': TA_CENTER, 'textColor': COLOR_TEXT_SECONDARY}),
        'h2': ParagraphStyle('h2', **{**base, 'fontName': FONT_TITLE, 'fontSize': 16, 'leading': 24, 'textColor': COLOR_PRIMARY, 'spaceBefore': 12, 'spaceAfter': 6}),
        'h3': ParagraphStyle('h3', **{**base, 'fontName': FONT_TITLE, 'fontSize': 13, 'leading': 20, 'textColor': COLOR_TEXT, 'spaceBefore': 8, 'spaceAfter': 4}),
        'body': ParagraphStyle('body', **base),
        'body_small': ParagraphStyle('body_small', **{**base, 'fontSize': 9, 'leading': 14, 'textColor': COLOR_TEXT_SECONDARY}),
        'body_bold': ParagraphStyle('body_bold', **{**base, 'fontName': FONT_TITLE, 'fontSize': 10, 'leading': 16}),
        'stat_value': ParagraphStyle('stat_value', **{**base, 'fontName': FONT_TITLE, 'fontSize': 18, 'leading': 24, 'alignment': TA_CENTER, 'textColor': COLOR_PRIMARY}),
        'stat_label': ParagraphStyle('stat_label', **{**base, 'fontSize': 9, 'leading': 14, 'alignment': TA_CENTER, 'textColor': COLOR_TEXT_SECONDARY}),
        'check_done': ParagraphStyle('check_done', **{**base, 'fontSize': 9, 'textColor': COLOR_ACCENT}),
        'check_pending': ParagraphStyle('check_pending', **{**base, 'fontSize': 9, 'textColor': COLOR_TEXT_SECONDARY}),
        'footer': ParagraphStyle('footer', **{**base, 'fontSize': 8, 'leading': 12, 'alignment': TA_CENTER, 'textColor': COLOR_TEXT_SECONDARY}),
    }


def build_activity_table(activities, styles, width):
    """构建活动表格"""
    if not activities:
        return [Paragraph("暂无活动安排", styles['body_small'])]

    data = []
    for i, act in enumerate(activities):
        checked = act.get('checked', 0)
        time_str = act.get('time_slot', '') or '--'
        content = act.get('content', '')
        location = act.get('location', '')
        category = act.get('category', '景点')
        notes = act.get('notes', '')

        # 状态图标
        status = '✅' if checked else '⬜'

        # 拼接地点和备注
        extra = ''
        if location:
            extra += f'📍{location}'
        if notes:
            extra += f'  📝{notes}'

        row = [
            Paragraph(status, styles['body']),
            Paragraph(f'<font color="#64748B">{time_str}</font>', styles['body_small']),
            Paragraph(f'<b>{content}</b>', styles['body_bold']),
            Paragraph(extra, styles['body_small']) if extra else Paragraph('', styles['body_small']),
        ]
        data.append(row)

    col_widths = [14*mm, 22*mm, width*0.35, width*0.35]
    t = Table(data, colWidths=col_widths, repeatRows=0)
    t.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, COLOR_BORDER),
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_LIGHT if activities.index(act) % 2 == 0 else white),
    ]))
    return [t]


def generate_pdf(trip_data):
    """
    生成旅行攻略 PDF
    trip_data: 包含 trip, days, activities, todos, stats 的完整数据
    """
    buf = io.BytesIO()
    styles = make_styles()
    page_w = A4[0] - 40 * mm  # 可用宽度

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title=trip_data.get('title', '旅行攻略'),
        author='旅行攻略管理器',
    )

    story = []

    # ======== 封面区域 ========
    story.append(Spacer(1, 30 * mm))
    story.append(Paragraph(trip_data.get('title', '旅行攻略'), styles['title']))
    story.append(Spacer(1, 6 * mm))
    story.append(GradientBar(page_w))
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph(f"导出时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}", styles['subtitle']))
    if trip_data.get('notes'):
        story.append(Paragraph(trip_data['notes'][:100], styles['subtitle']))
    story.append(Spacer(1, 16 * mm))

    # 统计卡片
    stats = trip_data.get('stats', {})
    stat_items = [
        (str(stats.get('days', 0)), '行程天数'),
        (str(stats.get('total_activities', 0)), '活动总数'),
        (str(stats.get('checked_activities', 0)), '已完成'),
        (f"{stats.get('activity_progress', 0)}%", '完成率'),
    ]
    stat_data = [[
        Paragraph(v, styles['stat_value']),
        Paragraph(v2, styles['stat_value']),
        Paragraph(v3, styles['stat_value']),
        Paragraph(v4, styles['stat_value']),
    ] for (v, _), (v2, _), (v3, _), (v4, _) in zip(stat_items[:1], stat_items[1:2], stat_items[2:3], stat_items[3:4])]
    stat_labels = [[
        Paragraph(l, styles['stat_label']),
        Paragraph(l2, styles['stat_label']),
        Paragraph(l3, styles['stat_label']),
        Paragraph(l4, styles['stat_label']),
    ] for (_, l), (_, l2), (_, l3), (_, l4) in zip(stat_items[:1], stat_items[1:2], stat_items[2:3], stat_items[3:4])]

    # Combine: each stat has value on top, label below
    combined = []
    for i in range(4):
        combined.append([stat_data[0][i], stat_labels[0][i]])

    stat_table_data = [[
        Table([[combined[0][0]], [combined[0][1]]], colWidths=[page_w/4]),
        Table([[combined[1][0]], [combined[1][1]]], colWidths=[page_w/4]),
        Table([[combined[2][0]], [combined[2][1]]], colWidths=[page_w/4]),
        Table([[combined[3][0]], [combined[3][1]]], colWidths=[page_w/4]),
    ]]
    stat_t = Table(stat_table_data, colWidths=[page_w/4]*4)
    stat_t.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_CARD),
        ('ROUNDEDCORNERS', [4, 4, 4, 4]),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(stat_t)

    story.append(PageBreak())

    # ======== 每日行程 ========
    story.append(Paragraph('📅 行程日程', styles['h2']))
    story.append(GradientBar(page_w))
    story.append(Spacer(1, 6 * mm))

    days = trip_data.get('days', [])
    for day_idx, day in enumerate(days):
        day_title = day.get('day_title', f"第{day.get('day_number', day_idx+1)}天")
        activities = day.get('activities', [])

        # Day header
        checked_count = sum(1 for a in activities if a.get('checked', 0))
        total_count = len(activities)
        progress_str = f"  ({checked_count}/{total_count} 已完成)" if total_count > 0 else ""

        story.append(Paragraph(f'<font color="{COLOR_PRIMARY.hexval()}">▍</font> {day_title}{progress_str}', styles['h3']))

        # Activity table
        table_flows = build_activity_table(activities, styles, page_w - 8*mm)
        for tf in table_flows:
            story.append(tf)
        story.append(Spacer(1, 4 * mm))

    story.append(PageBreak())

    # ======== 待办清单 ========
    todos = trip_data.get('todos', [])
    if todos:
        story.append(Paragraph('✅ 待办清单', styles['h2']))
        story.append(GradientBar(page_w))
        story.append(Spacer(1, 4 * mm))

        done_count = sum(1 for t in todos if t.get('done', 0))
        story.append(Paragraph(f'共 {len(todos)} 项，已完成 {done_count} 项', styles['body_small']))
        story.append(Spacer(1, 3 * mm))

        for todo in todos:
            done = todo.get('done', 0)
            icon = '✅' if done else '⬜'
            priority = todo.get('priority', 0)
            prio_label = {2: '🔴紧急', 1: '🟡重要', 0: ''}.get(priority, '')
            content = todo.get('content', '')
            deadline = todo.get('deadline', '')

            line = f'{icon} {content}'
            if prio_label:
                line += f'  <font color="#EF4444">{prio_label}</font>'
            if deadline:
                line += f'  <font color="#64748B">📅{deadline}</font>'

            style = styles['check_done'] if done else styles['check_pending']
            story.append(Paragraph(line, style))
            story.append(Spacer(1, 1 * mm))

    # ======== 景点参考 ========
    attractions = trip_data.get('attractions', [])
    if attractions:
        story.append(PageBreak())
        story.append(Paragraph('🏛️ 景点参考', styles['h2']))
        story.append(GradientBar(page_w))
        story.append(Spacer(1, 4 * mm))

        for attr in attractions:
            name = attr.get('name', '未知景点')
            city = attr.get('city', '')
            desc = attr.get('description', '')
            cat = attr.get('category', '景点')

            story.append(Paragraph(f'<b>{name}</b>  {f"📍{city}" if city else ""}  <font color="{CAT_COLORS.get(cat, COLOR_TEXT_SECONDARY).hexval()}">[{cat}]</font>', styles['body_bold']))
            if desc:
                story.append(Paragraph(desc[:120], styles['body_small']))
            story.append(Spacer(1, 2 * mm))

    # ======== 页脚 ========
    story.append(Spacer(1, 10 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_BORDER))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph('由 旅行攻略管理器 生成 | 小红书攻略数据仅供参考', styles['footer']))

    # 构建 PDF
    doc.build(story, onFirstPage=on_first_page, onLaterPages=on_later_pages)
    buf.seek(0)
    return buf
