
import json
import math
import re
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

import pandas as pd
import streamlit as st

try:
    from lunar_python import Solar
    LUNAR_AVAILABLE = True
except Exception:
    Solar = None
    LUNAR_AVAILABLE = False

try:
    from geopy.geocoders import Nominatim
    GEOPY_AVAILABLE = True
except Exception:
    Nominatim = None
    GEOPY_AVAILABLE = False


# ============================================================
# 页面配置
# ============================================================

st.set_page_config(
    page_title="八字命理测算系统 V4",
    page_icon="☯️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# 基础命理常量
# ============================================================

CURRENT_YEAR = datetime.now().year

HEAVENLY_STEMS = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
EARTHLY_BRANCHES = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

STEM_ELEMENT = {
    "甲": "木", "乙": "木",
    "丙": "火", "丁": "火",
    "戊": "土", "己": "土",
    "庚": "金", "辛": "金",
    "壬": "水", "癸": "水",
}

STEM_YINYANG = {
    "甲": "阳", "乙": "阴",
    "丙": "阳", "丁": "阴",
    "戊": "阳", "己": "阴",
    "庚": "阳", "辛": "阴",
    "壬": "阳", "癸": "阴",
}

BRANCH_ELEMENT = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木",
    "辰": "土", "巳": "火", "午": "火", "未": "土",
    "申": "金", "酉": "金", "戌": "土", "亥": "水",
}

BRANCH_HIDDEN_STEMS = {
    "子": [("癸", 1.0)],
    "丑": [("己", 0.6), ("癸", 0.25), ("辛", 0.15)],
    "寅": [("甲", 0.6), ("丙", 0.25), ("戊", 0.15)],
    "卯": [("乙", 1.0)],
    "辰": [("戊", 0.6), ("乙", 0.25), ("癸", 0.15)],
    "巳": [("丙", 0.6), ("戊", 0.25), ("庚", 0.15)],
    "午": [("丁", 0.7), ("己", 0.3)],
    "未": [("己", 0.6), ("丁", 0.25), ("乙", 0.15)],
    "申": [("庚", 0.6), ("壬", 0.25), ("戊", 0.15)],
    "酉": [("辛", 1.0)],
    "戌": [("戊", 0.6), ("辛", 0.25), ("丁", 0.15)],
    "亥": [("壬", 0.7), ("甲", 0.3)],
}

ELEMENT_GENERATES = {
    "木": "火",
    "火": "土",
    "土": "金",
    "金": "水",
    "水": "木",
}

ELEMENT_CONTROLS = {
    "木": "土",
    "土": "水",
    "水": "火",
    "火": "金",
    "金": "木",
}

TEN_GODS = [
    "正印", "偏印", "比肩", "劫财",
    "食神", "伤官", "正财", "偏财",
    "正官", "七杀"
]

GOD_TO_RELATION = {
    "正印": "印", "偏印": "印",
    "比肩": "比劫", "劫财": "比劫",
    "食神": "食伤", "伤官": "食伤",
    "正财": "财", "偏财": "财",
    "正官": "官杀", "七杀": "官杀",
}

RELATION_ORDER = ["印", "比劫", "食伤", "财", "官杀"]

RELATION_DESC = {
    "印": {
        "关键词": "学习、贵人、资质、保护、母亲、平台、精神依靠",
        "有利": "适合读书、考证、积累专业、进入有背书的平台。",
        "风险": "过旺则依赖、保守、想太多、行动慢。",
    },
    "比劫": {
        "关键词": "朋友、同辈、竞争、合伙、团队、兄弟、体力行动",
        "有利": "适合团队协作、竞争型环境、需要行动力和号召力的事。",
        "风险": "过旺则分钱、人情债、合伙争权、同业内耗。",
    },
    "食伤": {
        "关键词": "表达、技术、作品、才华、子女、欲望、自由度",
        "有利": "适合创作、技术输出、产品、咨询、内容、销售表达。",
        "风险": "过旺则口舌、叛逆、顶撞权威、想法过多难收束。",
    },
    "财": {
        "关键词": "财富、资源、项目、市场、伴侣现实议题、资产",
        "有利": "适合资源整合、商业变现、投资经营、客户市场。",
        "风险": "过旺则贪财、现金流压力、被项目拖累、欲望重。",
    },
    "官杀": {
        "关键词": "职位、规则、压力、权力、责任、风险、领导、丈夫传统象",
        "有利": "适合管理、组织、体制、法律、风控、高压责任岗位。",
        "风险": "过旺则焦虑、被压制、官非合同风险、责任过重。",
    },
}

DECISION_TYPES = {
    "跳槽/换工作": ["正官", "七杀", "正印", "偏印", "食神", "伤官"],
    "创业/做副业": ["食神", "伤官", "正财", "偏财", "比肩", "劫财"],
    "投资/买资产": ["正财", "偏财", "正官", "七杀"],
    "婚恋/结婚/分手": ["正财", "偏财", "正官", "七杀", "正印", "偏印"],
    "买房/搬家": ["正财", "偏财", "正印", "偏印"],
    "学习/考证/进修": ["正印", "偏印", "正官", "七杀"],
    "合作/合伙": ["比肩", "劫财", "正财", "偏财", "食神", "伤官"],
}

MONTH_SEASON_POWER = {
    "寅": {"木": 1.5, "火": 1.1, "土": 0.8, "金": 0.5, "水": 0.8},
    "卯": {"木": 1.6, "火": 1.1, "土": 0.7, "金": 0.5, "水": 0.8},
    "辰": {"木": 1.1, "火": 1.0, "土": 1.4, "金": 0.8, "水": 0.8},
    "巳": {"木": 0.8, "火": 1.6, "土": 1.2, "金": 0.7, "水": 0.4},
    "午": {"木": 0.8, "火": 1.7, "土": 1.2, "金": 0.6, "水": 0.4},
    "未": {"木": 0.7, "火": 1.1, "土": 1.5, "金": 0.8, "水": 0.5},
    "申": {"木": 0.5, "火": 0.6, "土": 0.9, "金": 1.6, "水": 1.1},
    "酉": {"木": 0.5, "火": 0.5, "土": 0.8, "金": 1.7, "水": 1.1},
    "戌": {"木": 0.6, "火": 0.8, "土": 1.5, "金": 1.1, "水": 0.6},
    "亥": {"木": 1.1, "火": 0.5, "土": 0.7, "金": 0.8, "水": 1.6},
    "子": {"木": 1.0, "火": 0.4, "土": 0.7, "金": 0.9, "水": 1.7},
    "丑": {"木": 0.7, "火": 0.5, "土": 1.5, "金": 1.0, "水": 1.1},
}

NAYIN_TABLE = {
    "甲子": "海中金", "乙丑": "海中金", "丙寅": "炉中火", "丁卯": "炉中火",
    "戊辰": "大林木", "己巳": "大林木", "庚午": "路旁土", "辛未": "路旁土",
    "壬申": "剑锋金", "癸酉": "剑锋金", "甲戌": "山头火", "乙亥": "山头火",
    "丙子": "涧下水", "丁丑": "涧下水", "戊寅": "城头土", "己卯": "城头土",
    "庚辰": "白蜡金", "辛巳": "白蜡金", "壬午": "杨柳木", "癸未": "杨柳木",
    "甲申": "泉中水", "乙酉": "泉中水", "丙戌": "屋上土", "丁亥": "屋上土",
    "戊子": "霹雳火", "己丑": "霹雳火", "庚寅": "松柏木", "辛卯": "松柏木",
    "壬辰": "长流水", "癸巳": "长流水", "甲午": "砂中金", "乙未": "砂中金",
    "丙申": "山下火", "丁酉": "山下火", "戊戌": "平地木", "己亥": "平地木",
    "庚子": "壁上土", "辛丑": "壁上土", "壬寅": "金箔金", "癸卯": "金箔金",
    "甲辰": "覆灯火", "乙巳": "覆灯火", "丙午": "天河水", "丁未": "天河水",
    "戊申": "大驿土", "己酉": "大驿土", "庚戌": "钗钏金", "辛亥": "钗钏金",
    "壬子": "桑柘木", "癸丑": "桑柘木", "甲寅": "大溪水", "乙卯": "大溪水",
    "丙辰": "沙中土", "丁巳": "沙中土", "戊午": "天上火", "己未": "天上火",
    "庚申": "石榴木", "辛酉": "石榴木", "壬戌": "大海水", "癸亥": "大海水",
}

CHANG_SHENG_START = {
    "甲": "亥", "乙": "午", "丙": "寅", "丁": "酉", "戊": "寅",
    "己": "酉", "庚": "巳", "辛": "子", "壬": "申", "癸": "卯",
}
CHANG_SHENG_STAGES = ["长生", "沐浴", "冠带", "临官", "帝旺", "衰", "病", "死", "墓", "绝", "胎", "养"]


CITY_COORDS = {
    "北京": (39.9042, 116.4074), "上海": (31.2304, 121.4737), "天津": (39.3434, 117.3616),
    "重庆": (29.5630, 106.5516), "广州": (23.1291, 113.2644), "深圳": (22.5431, 114.0579),
    "杭州": (30.2741, 120.1551), "南京": (32.0603, 118.7969), "苏州": (31.2989, 120.5853),
    "成都": (30.5728, 104.0668), "武汉": (30.5928, 114.3055), "西安": (34.3416, 108.9398),
    "郑州": (34.7466, 113.6254), "长沙": (28.2282, 112.9388), "青岛": (36.0671, 120.3826),
    "济南": (36.6512, 117.1201), "厦门": (24.4798, 118.0894), "福州": (26.0745, 119.2965),
    "宁波": (29.8683, 121.5440), "无锡": (31.4912, 120.3119), "合肥": (31.8206, 117.2272),
    "南昌": (28.6829, 115.8582), "昆明": (24.8801, 102.8329), "贵阳": (26.6470, 106.6302),
    "南宁": (22.8170, 108.3669), "海口": (20.0440, 110.1999), "太原": (37.8706, 112.5489),
    "石家庄": (38.0428, 114.5149), "沈阳": (41.8057, 123.4315), "长春": (43.8171, 125.3235),
    "哈尔滨": (45.8038, 126.5349), "呼和浩特": (40.8426, 111.7492), "兰州": (36.0611, 103.8343),
    "银川": (38.4872, 106.2309), "西宁": (36.6171, 101.7782), "乌鲁木齐": (43.8256, 87.6168),
    "拉萨": (29.6520, 91.1721), "香港": (22.3193, 114.1694), "澳门": (22.1987, 113.5439),
    "台北": (25.0330, 121.5654), "高雄": (22.6273, 120.3014),
}


# ============================================================
# 工具函数：地址、真太阳时、排盘
# ============================================================

@st.cache_data(show_spinner=False, ttl=86400)
def geocode_address(address: str) -> Optional[Dict]:
    """
    后台自动把地址转经纬度。
    UI 不展示经纬度，只显示是否定位成功。
    """
    address = (address or "").strip()
    if not address:
        return None

    # 1. 先用内置中国主要城市兜底匹配，速度快、稳定。
    for city, (lat, lon) in CITY_COORDS.items():
        if city in address:
            return {
                "lat": lat,
                "lon": lon,
                "display": city,
                "source": "内置城市库",
            }

    # 2. 再用 Nominatim 在线定位。
    if GEOPY_AVAILABLE:
        try:
            geolocator = Nominatim(user_agent="bazi_fortune_streamlit_v4")
            query = address
            if not re.search(r"中国|China|Taiwan|Hong Kong|Macau", query, re.I):
                query = f"{address}, China"
            loc = geolocator.geocode(query, timeout=8, language="zh-CN")
            if loc:
                return {
                    "lat": float(loc.latitude),
                    "lon": float(loc.longitude),
                    "display": loc.address,
                    "source": "在线地理编码",
                }
        except Exception:
            return None

    return None


def equation_of_time_minutes(day_of_year: int) -> float:
    """
    均时差近似公式，单位分钟。
    B = 360/365 * (N-81)
    EoT = 9.87 sin(2B) - 7.53 cos(B) - 1.5 sin(B)
    """
    b = math.radians((360 / 365) * (day_of_year - 81))
    return 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)


def true_solar_time(local_dt: datetime, lon: float) -> Tuple[datetime, Dict]:
    """
    中国标准时间以东经120度为基准。
    真太阳时 = 标准时间 + 经度修正 + 均时差。
    经度修正：每差1度约4分钟。
    """
    doy = int(local_dt.strftime("%j"))
    longitude_correction = (lon - 120.0) * 4.0
    eot = equation_of_time_minutes(doy)
    total = longitude_correction + eot
    adjusted = local_dt + timedelta(minutes=total)
    return adjusted, {
        "longitude_correction_min": round(longitude_correction, 2),
        "equation_of_time_min": round(eot, 2),
        "total_correction_min": round(total, 2),
    }


def stem_branch_index(gz: str) -> int:
    if gz not in NAYIN_TABLE:
        return 0
    stem, branch = gz[0], gz[1]
    for i in range(60):
        if HEAVENLY_STEMS[i % 10] + EARTHLY_BRANCHES[i % 12] == gz:
            return i
    return 0


def ganzhi_from_index(idx: int) -> str:
    return HEAVENLY_STEMS[idx % 10] + EARTHLY_BRANCHES[idx % 12]


def split_ganzhi(gz: str) -> Tuple[str, str]:
    if not gz or len(gz) < 2:
        return "", ""
    return gz[0], gz[1]


def get_ten_god(day_stem: str, other_stem: str) -> str:
    me_el = STEM_ELEMENT[day_stem]
    other_el = STEM_ELEMENT[other_stem]
    same_yinyang = STEM_YINYANG[day_stem] == STEM_YINYANG[other_stem]

    if other_el == me_el:
        return "比肩" if same_yinyang else "劫财"

    if ELEMENT_GENERATES[other_el] == me_el:
        return "偏印" if same_yinyang else "正印"

    if ELEMENT_GENERATES[me_el] == other_el:
        return "食神" if same_yinyang else "伤官"

    if ELEMENT_CONTROLS[other_el] == me_el:
        return "七杀" if same_yinyang else "正官"

    if ELEMENT_CONTROLS[me_el] == other_el:
        return "偏财" if same_yinyang else "正财"

    return "未知"


def get_changsheng(day_stem: str, branch: str) -> str:
    start_branch = CHANG_SHENG_START.get(day_stem)
    if not start_branch:
        return ""
    start_idx = EARTHLY_BRANCHES.index(start_branch)

    # 阳干顺行，阴干逆行。
    if STEM_YINYANG[day_stem] == "阳":
        idx = (EARTHLY_BRANCHES.index(branch) - start_idx) % 12
    else:
        idx = (start_idx - EARTHLY_BRANCHES.index(branch)) % 12

    return CHANG_SHENG_STAGES[idx]


def calculate_kongwang(day_gz: str) -> str:
    idx = stem_branch_index(day_gz)
    xun_start = (idx // 10) * 10
    used_branches = [EARTHLY_BRANCHES[(xun_start + i) % 12] for i in range(10)]
    empty = [b for b in EARTHLY_BRANCHES if b not in used_branches]
    return "".join(empty)


def build_bazi(dt: datetime) -> Dict:
    if not LUNAR_AVAILABLE:
        raise RuntimeError("未安装 lunar-python，请先 pip install lunar-python")

    solar = Solar.fromYmdHms(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
    lunar = solar.getLunar()
    ec = lunar.getEightChar()

    pillars = {
        "年柱": ec.getYear(),
        "月柱": ec.getMonth(),
        "日柱": ec.getDay(),
        "时柱": ec.getTime(),
    }

    day_stem, day_branch = split_ganzhi(pillars["日柱"])
    rows = []
    hidden_rows = []

    for p, gz in pillars.items():
        stem, branch = split_ganzhi(gz)
        ten_god = "日主" if p == "日柱" else get_ten_god(day_stem, stem)

        h_list = []
        for hs, weight in BRANCH_HIDDEN_STEMS[branch]:
            hg = get_ten_god(day_stem, hs)
            h_list.append(f"{hs}{hg}")
            hidden_rows.append({
                "柱": p,
                "地支": branch,
                "藏干": hs,
                "权重": weight,
                "藏干十神": hg,
            })

        rows.append({
            "柱": p,
            "干支": gz,
            "纳音": NAYIN_TABLE.get(gz, ""),
            "天干": stem,
            "天干五行": STEM_ELEMENT[stem],
            "天干阴阳": STEM_YINYANG[stem],
            "天干十神": ten_god,
            "地支": branch,
            "地支五行": BRANCH_ELEMENT[branch],
            "藏干十神": "、".join(h_list),
            "十二长生": get_changsheng(day_stem, branch),
        })

    return {
        "solar": solar,
        "lunar": lunar,
        "eight_char": ec,
        "pillars": pillars,
        "day_stem": day_stem,
        "day_branch": day_branch,
        "rows": rows,
        "hidden_rows": hidden_rows,
        "kongwang": calculate_kongwang(pillars["日柱"]),
        "lunar_text": lunar.toString(),
        "lunar_full": lunar.toFullString(),
    }


def element_scores(bazi: Dict) -> Dict[str, float]:
    month_branch = bazi["rows"][1]["地支"]
    season = MONTH_SEASON_POWER.get(month_branch, {e: 1.0 for e in ["木", "火", "土", "金", "水"]})

    scores = {e: 0.0 for e in ["木", "火", "土", "金", "水"]}

    for r in bazi["rows"]:
        scores[r["天干五行"]] += 1.0 * season[r["天干五行"]]
        scores[r["地支五行"]] += 0.8 * season[r["地支五行"]]

    for hr in bazi["hidden_rows"]:
        el = STEM_ELEMENT[hr["藏干"]]
        scores[el] += hr["权重"] * 0.6 * season[el]

    return {k: round(v, 2) for k, v in scores.items()}


def ten_god_scores(bazi: Dict) -> Dict[str, float]:
    result = {g: 0.0 for g in TEN_GODS}
    for r in bazi["rows"]:
        g = r["天干十神"]
        if g in result:
            result[g] += 1.0

    for hr in bazi["hidden_rows"]:
        g = hr["藏干十神"]
        if g in result:
            result[g] += hr["权重"] * 0.55

    return {k: round(v, 2) for k, v in result.items()}


def relation_scores(ten_scores: Dict[str, float]) -> Dict[str, float]:
    res = {r: 0.0 for r in RELATION_ORDER}
    for g, v in ten_scores.items():
        res[GOD_TO_RELATION[g]] += v
    return {k: round(v, 2) for k, v in res.items()}


def judge_day_master_strength(bazi: Dict, elem_scores: Dict[str, float], ten_scores: Dict[str, float]) -> Tuple[str, int, List[str]]:
    day_el = STEM_ELEMENT[bazi["day_stem"]]
    month_branch = bazi["rows"][1]["地支"]

    same = elem_scores[day_el]
    mother = elem_scores[[k for k, v in ELEMENT_GENERATES.items() if v == day_el][0]]
    output = elem_scores[ELEMENT_GENERATES[day_el]]
    wealth = elem_scores[ELEMENT_CONTROLS[day_el]]
    pressure = elem_scores[[k for k, v in ELEMENT_CONTROLS.items() if v == day_el][0]]

    raw = 50 + same * 6 + mother * 5 - output * 3 - wealth * 4 - pressure * 5

    if day_el in [STEM_ELEMENT[h] for h, _ in BRANCH_HIDDEN_STEMS[month_branch]]:
        raw += 10

    score = max(5, min(95, int(round(raw))))

    if score >= 66:
        label = "偏强"
    elif score <= 42:
        label = "偏弱"
    else:
        label = "中和"

    reasons = [
        f"日主为{bazi['day_stem']}{day_el}，同类五行得分 {same}，生扶五行得分 {mother}。",
        f"输出五行得分 {output}，财富五行得分 {wealth}，官杀压力五行得分 {pressure}。",
        f"月令为{month_branch}，季节旺衰已经计入五行权重。",
    ]

    return label, score, reasons


def suggest_useful_avoid(strength: str, rel_scores: Dict[str, float]) -> Tuple[List[str], List[str], List[str]]:
    useful = []
    avoid = []
    notes = []

    if strength == "偏强":
        useful = ["食神", "伤官", "正财", "偏财", "正官", "七杀"]
        avoid = ["正印", "偏印", "比肩", "劫财"]
        notes.append("日主偏强，宜泄秀、耗身、受规则锻炼；忌印比继续加重自我。")
    elif strength == "偏弱":
        useful = ["正印", "偏印", "比肩", "劫财"]
        avoid = ["食神", "伤官", "正财", "偏财", "正官", "七杀"]
        notes.append("日主偏弱，宜印比生扶；忌财官食伤过多造成过劳、失控或压力。")
    else:
        notes.append("日主中和，喜忌要以格局流通和历史应验校准，不能机械断定。")

    top_rel = max(rel_scores.items(), key=lambda x: x[1])[0]
    notes.append(f"命局最突出的关系类别为「{top_rel}」，人生主题容易围绕：{RELATION_DESC[top_rel]['关键词']}。")

    return useful, avoid, notes


def detect_patterns(ten_scores: Dict[str, float], strength: str) -> List[Dict]:
    patterns = []

    def s(names):
        return sum(ten_scores.get(x, 0) for x in names)

    if s(["食神", "伤官"]) >= 1.2 and s(["正财", "偏财"]) >= 1.0:
        patterns.append({
            "格局/链条": "食伤生财",
            "含义": "靠技术、表达、作品、创意、服务转化为财富，适合内容、产品、销售、咨询、技术变现。",
            "风险": "想法多、项目多、现金流管理不足。",
        })

    if s(["正官", "七杀"]) >= 1.0 and s(["正印", "偏印"]) >= 1.0:
        patterns.append({
            "格局/链条": "官印相生 / 杀印相生",
            "含义": "压力、规则、考试、组织系统可转化为资质、职位、专业背书。",
            "风险": "长期高压、依赖平台、行动保守。",
        })

    if s(["正财", "偏财"]) >= 1.0 and s(["正官", "七杀"]) >= 1.0:
        patterns.append({
            "格局/链条": "财生官杀",
            "含义": "资源、项目、经营能力可以转成职位、权责、社会身份。",
            "风险": "钱与责任绑定，项目越大压力越大。",
        })

    if s(["比肩", "劫财"]) >= 1.2 and s(["食神", "伤官"]) >= 1.0:
        patterns.append({
            "格局/链条": "比劫生食伤",
            "含义": "团队、圈层、竞争力能转化为表达、产品、市场行动。",
            "风险": "同伴内耗、利益分配不清。",
        })

    if s(["食神", "伤官"]) >= 1.2 and s(["正官", "七杀"]) >= 1.0:
        patterns.append({
            "格局/链条": "食伤制官杀",
            "含义": "可用技术、表达、方案、专业能力处理压力、规则和风险。",
            "风险": "容易与权威冲突，必须靠专业结果说话。",
        })

    if not patterns:
        patterns.append({
            "格局/链条": "结构未形成明显单一链条",
            "含义": "命局主题较混合，需结合大运、流年和个人经历校准。",
            "风险": "不能用单一标签下结论。",
        })

    return patterns


def simple_shensha(bazi: Dict) -> List[Dict]:
    year_branch = bazi["rows"][0]["地支"]
    day_branch = bazi["day_branch"]
    branches = [r["地支"] for r in bazi["rows"]]

    groups = {
        "申子辰": {"桃花": "酉", "驿马": "寅", "华盖": "辰"},
        "寅午戌": {"桃花": "卯", "驿马": "申", "华盖": "戌"},
        "巳酉丑": {"桃花": "午", "驿马": "亥", "华盖": "丑"},
        "亥卯未": {"桃花": "子", "驿马": "巳", "华盖": "未"},
    }

    def group_of(branch):
        for k in groups:
            if branch in k:
                return groups[k]
        return {}

    result = []
    for base_name, base_branch in [("年支", year_branch), ("日支", day_branch)]:
        g = group_of(base_branch)
        for star, target in g.items():
            if target in branches:
                result.append({
                    "神煞": star,
                    "依据": f"以{base_name}{base_branch}起，见{target}",
                    "解释": {
                        "桃花": "人缘、审美、情感吸引力、曝光度增强；过旺则情感复杂。",
                        "驿马": "迁移、奔波、变化、出差、异地发展信号。",
                        "华盖": "孤高、艺术、宗教哲学、研究、独处、专业深钻。",
                    }[star]
                })

    day_stem = bazi["day_stem"]
    tianyi = {
        "甲": ["丑", "未"], "戊": ["丑", "未"], "庚": ["丑", "未"],
        "乙": ["子", "申"], "己": ["子", "申"],
        "丙": ["亥", "酉"], "丁": ["亥", "酉"],
        "壬": ["卯", "巳"], "癸": ["卯", "巳"],
        "辛": ["寅", "午"],
    }.get(day_stem, [])
    for b in tianyi:
        if b in branches:
            result.append({
                "神煞": "天乙贵人",
                "依据": f"日干{day_stem}见{b}",
                "解释": "遇事较容易得贵人、制度、平台或关键人物帮助。"
            })

    return result


# ============================================================
# 大运流年
# ============================================================

def get_yun_auto(bazi: Dict, gender: str):
    """
    优先调用 lunar-python 自带大运系统。
    gender: 男/女/其他
    """
    if gender == "女":
        gender_num = 0
    else:
        gender_num = 1

    ec = bazi["eight_char"]
    for sect in [1, 2]:
        try:
            return ec.getYun(gender_num, sect)
        except Exception:
            continue
    return None


def extract_dayun(bazi: Dict, gender: str, birth_year: int) -> List[Dict]:
    yun = get_yun_auto(bazi, gender)
    result = []

    if yun:
        try:
            da_yun_list = yun.getDaYun()
            for dy in da_yun_list:
                try:
                    gz = dy.getGanZhi()
                except Exception:
                    gz = ""
                try:
                    start_year = dy.getStartYear()
                except Exception:
                    start_year = None
                try:
                    end_year = dy.getEndYear()
                except Exception:
                    end_year = None
                try:
                    start_age = dy.getStartAge()
                except Exception:
                    start_age = None
                try:
                    end_age = dy.getEndAge()
                except Exception:
                    end_age = None

                if gz:
                    result.append({
                        "大运": gz,
                        "起始年龄": start_age,
                        "结束年龄": end_age,
                        "起始年份": start_year,
                        "结束年份": end_year,
                    })
            # 去掉空运，并限制
            result = [x for x in result if x["大运"] and x["起始年份"]]
            if result:
                return result[:12]
        except Exception:
            pass

    # fallback：按月柱顺逆粗排，不计算精确起运。
    year_stem = bazi["rows"][0]["天干"]
    male = gender != "女"
    yang_year = STEM_YINYANG[year_stem] == "阳"
    forward = (male and yang_year) or ((not male) and (not yang_year))
    month_idx = stem_branch_index(bazi["pillars"]["月柱"])

    for i in range(1, 11):
        idx = month_idx + i if forward else month_idx - i
        result.append({
            "大运": ganzhi_from_index(idx % 60),
            "起始年龄": 8 + (i - 1) * 10,
            "结束年龄": 17 + (i - 1) * 10,
            "起始年份": birth_year + 8 + (i - 1) * 10,
            "结束年份": birth_year + 17 + (i - 1) * 10,
        })

    return result


def current_dayun(dayun_list: List[Dict], year: int) -> Optional[Dict]:
    for dy in dayun_list:
        sy = dy.get("起始年份")
        ey = dy.get("结束年份")
        if sy and ey and sy <= year <= ey:
            return dy
    return None


def year_ganzhi(year: int) -> str:
    # 1984 甲子
    idx = (year - 1984) % 60
    return ganzhi_from_index(idx)


def gz_ten_gods(day_stem: str, gz: str) -> List[str]:
    st, br = split_ganzhi(gz)
    gods = [get_ten_god(day_stem, st)]
    for hs, wt in BRANCH_HIDDEN_STEMS.get(br, []):
        gods.append(get_ten_god(day_stem, hs))
    return gods


def fortune_year_score(
    bazi: Dict,
    useful: List[str],
    avoid: List[str],
    year: int,
    dayun: Optional[Dict],
    age: int,
) -> Dict:
    ygz = year_ganzhi(year)
    ygods = gz_ten_gods(bazi["day_stem"], ygz)

    dy_gz = dayun["大运"] if dayun else ""
    dgods = gz_ten_gods(bazi["day_stem"], dy_gz) if dy_gz else []

    branches = [r["地支"] for r in bazi["rows"]]
    y_branch = ygz[1]

    score = 0
    tags = []
    themes = []

    for g in ygods:
        if g in useful:
            score += 12
            tags.append(f"流年{g}为喜")
        if g in avoid:
            score -= 12
            tags.append(f"流年{g}为忌")

    for g in dgods:
        if g in useful:
            score += 8
            tags.append(f"大运{g}为喜")
        if g in avoid:
            score -= 8
            tags.append(f"大运{g}为忌")

    # 冲动四柱地支：子午、丑未、寅申、卯酉、辰戌、巳亥
    clash_pairs = {"子": "午", "午": "子", "丑": "未", "未": "丑", "寅": "申", "申": "寅",
                   "卯": "酉", "酉": "卯", "辰": "戌", "戌": "辰", "巳": "亥", "亥": "巳"}
    if clash_pairs.get(y_branch) in branches:
        score += 8
        tags.append("流年冲动原局")
        themes.append("环境变化、迁移、关系转折或重要选择")

    if y_branch in branches:
        score += 6
        tags.append("流年伏吟/重复原局主题")
        themes.append("旧问题重复出现，人生主题被放大")

    # 十神主题
    main_relations = [GOD_TO_RELATION.get(g, "") for g in ygods + dgods if g in GOD_TO_RELATION]
    for r in set(main_relations):
        if r == "印":
            themes.append("学习、证书、贵人、家庭、保护系统")
        elif r == "比劫":
            themes.append("朋友、竞争、合伙、同辈关系")
        elif r == "食伤":
            themes.append("表达、作品、技术、子女、自由变化")
        elif r == "财":
            themes.append("钱财、资源、项目、感情现实议题")
        elif r == "官杀":
            themes.append("工作压力、职位、规则、考试、责任风险")

    abs_score = abs(score)
    importance = abs_score + (10 if age in [6, 12, 18, 24, 30, 36, 42, 48, 54, 60] else 0)

    if score >= 20:
        tone = "偏顺"
    elif score <= -20:
        tone = "偏险"
    else:
        tone = "转折/平衡"

    return {
        "年份": year,
        "年龄": age,
        "流年": ygz,
        "大运": dy_gz,
        "倾向": tone,
        "重要度": importance,
        "主题": "；".join(list(dict.fromkeys(themes))[:3]) if themes else "阶段变化",
        "命理依据": "；".join(list(dict.fromkeys(tags))[:4]) if tags else "流年与原局互动较平",
        "score": score,
    }


def representative_events(bazi: Dict, birth_year: int, current_year: int, useful: List[str], avoid: List[str], dayun_list: List[Dict]) -> List[Dict]:
    events = []
    for year in range(birth_year, current_year + 1):
        age = year - birth_year
        dy = current_dayun(dayun_list, year)
        item = fortune_year_score(bazi, useful, avoid, year, dy, age)
        events.append(item)

    # 选择重要度最高的10年，同时避免年份过于集中。
    events_sorted = sorted(events, key=lambda x: x["重要度"], reverse=True)
    chosen = []
    for e in events_sorted:
        if len(chosen) >= 10:
            break
        if all(abs(e["年份"] - c["年份"]) >= 2 for c in chosen):
            chosen.append(e)

    return sorted(chosen, key=lambda x: x["年份"])


# ============================================================
# 文案生成
# ============================================================

def paragraph_core_fortune(bazi: Dict, strength: str, strength_score: int, rel_scores: Dict, patterns: List[Dict], useful: List[str], avoid: List[str]) -> str:
    top_rel = max(rel_scores.items(), key=lambda x: x[1])[0]
    pattern_text = "、".join([p["格局/链条"] for p in patterns[:3]])

    return (
        f"此命以日干「{bazi['day_stem']}」为我，日支「{bazi['day_branch']}」为身体与亲密关系落点。"
        f"系统判断日主为「{strength}」，强弱分约 {strength_score}/100。"
        f"命局最突出的社会关系是「{top_rel}」，其主题为：{RELATION_DESC[top_rel]['关键词']}。"
        f"当前识别出的主要结构为：{pattern_text}。"
        f"初步喜用取「{'、'.join(useful) if useful else '需校准'}」，风险点取「{'、'.join(avoid) if avoid else '需校准'}」。"
        "这表示此人一生不宜只看单一五行或单一十神，而应看关系能否流通、压力能否转化、资源能否承载。"
    )


def career_advice(patterns: List[Dict], rel_scores: Dict, useful: List[str]) -> List[str]:
    advice = []
    pat_names = [p["格局/链条"] for p in patterns]

    if "食伤生财" in pat_names:
        advice.append("事业上宜走“能力输出—产品/服务—变现”的路线，适合技术、内容、咨询、销售、产品、培训、自媒体、创意型商业。")
    if "官印相生 / 杀印相生" in pat_names:
        advice.append("适合进入有规则、有资质、有晋升系统的平台，例如体制、大厂、专业机构、法律、金融风控、医疗教育、工程管理。")
    if "财生官杀" in pat_names:
        advice.append("可通过资源、项目、客户、市场经营换取职位、管理权与社会身份，但越往上走责任越重。")
    if "比劫生食伤" in pat_names:
        advice.append("适合借助团队、社群、圈层和竞争环境起势，但必须提前设计分钱和退出机制。")
    if "食伤制官杀" in pat_names:
        advice.append("面对权威、规则和压力时，不宜硬冲，宜用专业方案、技术结果和可量化成果说话。")

    top_rel = max(rel_scores.items(), key=lambda x: x[1])[0]
    advice.append(f"长期来看，你的事业主题会反复围绕「{top_rel}」展开：{RELATION_DESC[top_rel]['有利']}")

    return list(dict.fromkeys(advice))


def wealth_advice(ten_scores: Dict, useful: List[str], avoid: List[str]) -> List[str]:
    wealth = ten_scores.get("正财", 0) + ten_scores.get("偏财", 0)
    output = ten_scores.get("食神", 0) + ten_scores.get("伤官", 0)
    bi = ten_scores.get("比肩", 0) + ten_scores.get("劫财", 0)

    advice = []
    if wealth >= 1.5 and any(g in useful for g in ["正财", "偏财"]):
        advice.append("财星有力且可用，适合主动经营资源、客户、项目和资产，但仍要重视现金流。")
    elif wealth >= 1.5:
        advice.append("财星明显，但不等于一定发财；若财为忌，反而容易因项目、欲望、投资或感情现实问题耗神。")
    else:
        advice.append("命局财星不是最重的主题，求财宜先靠能力、平台、资质或团队间接转化，不宜只追快钱。")

    if output >= 1.2:
        advice.append("有食伤信号，赚钱更宜靠技术、表达、内容、产品或服务，而不是单纯赌行情。")

    if bi >= 1.2:
        advice.append("比劫信号较强，涉及朋友合伙、熟人项目、共同投资时尤其要钱账分明。")

    if any(g in avoid for g in ["正财", "偏财"]):
        advice.append("财星被列为风险点时，忌重仓、忌借贷投资、忌替人担保，尤其不要因焦虑或贪心做决定。")

    return advice


def relationship_advice(bazi: Dict, ten_scores: Dict, gender: str, avoid: List[str]) -> List[str]:
    advice = []
    spouse_branch = bazi["day_branch"]
    day_hidden = [get_ten_god(bazi["day_stem"], hs) for hs, _ in BRANCH_HIDDEN_STEMS[spouse_branch]]

    advice.append(f"日支为「{spouse_branch}」，亲密关系和身体感受容易带有「{'、'.join(day_hidden)}」的色彩。")

    if gender == "男":
        spouse_gods = ["正财", "偏财"]
        advice.append("男命传统上以财星观察伴侣与现实关系议题，但现代解读还要结合日支、情绪边界和现实责任。")
    elif gender == "女":
        spouse_gods = ["正官", "七杀"]
        advice.append("女命传统上以官杀观察伴侣与关系责任议题，但现代解读还要结合日支、自我边界和现实选择。")
    else:
        spouse_gods = ["正财", "偏财", "正官", "七杀"]
        advice.append("不限定性别时，亲密关系重点看日支、财官互动、自我边界与现实责任。")

    if any(g in avoid for g in spouse_gods):
        advice.append("伴侣星或关系责任被列为风险点时，感情中要警惕控制、依赖、经济绑定、压力不对等。")
    else:
        advice.append("关系中宜寻找能共同承担现实、又不压制你核心发展路径的人。")

    return advice


def health_advice(elem_scores: Dict, strength: str) -> List[str]:
    sorted_e = sorted(elem_scores.items(), key=lambda x: x[1])
    weak = sorted_e[0][0]
    strong = sorted_e[-1][0]

    map_body = {
        "木": "肝胆、筋膜、情绪疏泄",
        "火": "心血管、睡眠、神经兴奋",
        "土": "脾胃、消化、代谢稳定",
        "金": "肺、皮肤、呼吸系统、边界感",
        "水": "肾、泌尿、生殖、精力储备",
    }

    return [
        f"五行中相对偏弱的是「{weak}」，日常可关注：{map_body[weak]}。",
        f"五行中相对偏旺的是「{strong}」，旺处也可能成为过载点，可关注：{map_body[strong]}。",
        "健康部分只作体质倾向提醒；任何症状、诊断和治疗必须以正规医疗为准。",
    ]


def decision_score(useful: List[str], avoid: List[str], decision_type: str, current_year_item: Dict) -> Tuple[int, str, List[str]]:
    target = DECISION_TYPES[decision_type]
    base = 55

    useful_hit = len(set(target) & set(useful))
    avoid_hit = len(set(target) & set(avoid))

    base += useful_hit * 8
    base -= avoid_hit * 10

    if current_year_item["倾向"] == "偏顺":
        base += 10
    elif current_year_item["倾向"] == "偏险":
        base -= 10

    score = max(0, min(100, base))

    if score >= 80:
        light = "🟢 可推进"
    elif score >= 60:
        light = "🟡 可试点"
    else:
        light = "🔴 宜暂缓"

    reasons = [
        f"该事项主要引动：{'、'.join(target)}。",
        f"与喜用神交集：{'、'.join(set(target) & set(useful)) or '无明显交集'}。",
        f"与风险十神交集：{'、'.join(set(target) & set(avoid)) or '无明显交集'}。",
        f"当前年份倾向：{current_year_item['倾向']}，主题：{current_year_item['主题']}。",
    ]

    return score, light, reasons


# ============================================================
# 输入区
# ============================================================

st.title("☯️ 八字命理测算系统 V4")
st.caption("以算命详批为主体：自动地址定位、自动真太阳时、自动排盘、自动大运流年、自动推演出生至今十件代表性事件。")

with st.expander("使用说明与边界", expanded=False):
    st.markdown(
        """
        本系统把传统八字术语转成普通人能读懂的命理报告。  
        系统会自动计算：四柱、十神、五行旺衰、真太阳时、大运流年、代表性年份、事业财运感情健康建议。  

        注意：命理测算属于传统文化与象征性分析，不应替代法律、医学、投资、职业等专业判断。
        """
    )

if not LUNAR_AVAILABLE:
    st.error("缺少 lunar-python，请先安装：pip install lunar-python")
    st.stop()

with st.sidebar:
    st.header("出生信息")
    name = st.text_input("测算者姓名/代号", value="测试用户")
    gender = st.selectbox("性别", ["男", "女", "其他/不指定"], index=0)

    year = st.number_input("出生年", min_value=1600, max_value=2200, value=1990, step=1)
    month = st.number_input("出生月", min_value=1, max_value=12, value=1, step=1)
    day = st.number_input("出生日", min_value=1, max_value=31, value=1, step=1)
    hour = st.number_input("出生时", min_value=0, max_value=23, value=8, step=1)
    minute = st.number_input("出生分", min_value=0, max_value=59, value=0, step=1)

    address = st.text_input("出生地址", value="中国 贵州 贵阳")
    st.caption("只需输入地址，系统后台自动定位并换算真太阳时，不需要填写经纬度。")

    use_true_solar = st.checkbox("按真太阳时排盘", value=True)

    st.divider()
    st.header("附属决策模块")
    decision_type = st.selectbox("要顺便判断的决策", list(DECISION_TYPES.keys()), index=1)
    decision_desc = st.text_area("具体问题", value="例如：今年是否适合创业或做副业？", height=90)

try:
    local_dt = datetime(int(year), int(month), int(day), int(hour), int(minute), 0)
except ValueError as e:
    st.error(f"出生日期无效：{e}")
    st.stop()

geo = geocode_address(address)
if address and not geo:
    st.warning("出生地址暂未成功定位。系统将按东经120度标准时间排盘；建议把地址写成“省 市 区/县”的形式。")
    lon = 120.0
    geo_status = "定位失败，按东八区标准经线处理"
else:
    lon = geo["lon"] if geo else 120.0
    geo_status = "定位成功" if geo else "未填写地址，按东八区标准经线处理"

if use_true_solar:
    chart_dt, solar_corr = true_solar_time(local_dt, lon)
else:
    chart_dt = local_dt
    solar_corr = {"longitude_correction_min": 0, "equation_of_time_min": 0, "total_correction_min": 0}

bazi = build_bazi(chart_dt)
elem_scores = element_scores(bazi)
ten_scores = ten_god_scores(bazi)
rel_scores = relation_scores(ten_scores)
strength, strength_score, strength_reasons = judge_day_master_strength(bazi, elem_scores, ten_scores)
auto_useful, auto_avoid, useful_notes = suggest_useful_avoid(strength, rel_scores)
patterns = detect_patterns(ten_scores, strength)
shensha = simple_shensha(bazi)
dayun_list = extract_dayun(bazi, gender, int(year))
current_dy = current_dayun(dayun_list, CURRENT_YEAR)
current_year_item = fortune_year_score(bazi, auto_useful, auto_avoid, CURRENT_YEAR, current_dy, CURRENT_YEAR - int(year))
ten_events = representative_events(bazi, int(year), CURRENT_YEAR, auto_useful, auto_avoid, dayun_list)


# ============================================================
# 顶部摘要
# ============================================================

top1, top2, top3, top4 = st.columns(4)
with top1:
    st.metric("排盘时间", chart_dt.strftime("%Y-%m-%d %H:%M"))
with top2:
    st.metric("定位状态", geo_status)
with top3:
    st.metric("日主", f"{bazi['day_stem']}{STEM_ELEMENT[bazi['day_stem']]}")
with top4:
    st.metric("日主强弱", f"{strength} {strength_score}/100")

if use_true_solar:
    st.caption(
        f"已按真太阳时排盘：本地钟表时间 {local_dt.strftime('%Y-%m-%d %H:%M')} → 真太阳时 {chart_dt.strftime('%Y-%m-%d %H:%M')}。"
        "经纬度仅后台计算，不在页面展示。"
    )


# ============================================================
# 主体 Tabs
# ============================================================

tab0, tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "命盘总览",
    "出生至今十件事",
    "命运详批",
    "大运流年",
    "人生建议",
    "附属决策",
    "导出报告",
])


with tab0:
    st.header("命盘总览")

    c1, c2, c3, c4 = st.columns(4)
    pillars = bazi["pillars"]
    with c1:
        st.metric("年柱", pillars["年柱"])
    with c2:
        st.metric("月柱", pillars["月柱"])
    with c3:
        st.metric("日柱", pillars["日柱"])
    with c4:
        st.metric("时柱", pillars["时柱"])

    st.subheader("四柱、十神、纳音、十二长生")
    st.dataframe(pd.DataFrame(bazi["rows"]), use_container_width=True, hide_index=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("五行旺衰")
        elem_df = pd.DataFrame([{"五行": k, "得分": v} for k, v in elem_scores.items()])
        st.bar_chart(elem_df.set_index("五行"))
        st.dataframe(elem_df, use_container_width=True, hide_index=True)

    with col_b:
        st.subheader("十神结构")
        ten_df = pd.DataFrame([{"十神": k, "得分": v, "关系": GOD_TO_RELATION[k]} for k, v in ten_scores.items()])
        st.bar_chart(ten_df.set_index("十神")["得分"])
        st.dataframe(ten_df.sort_values("得分", ascending=False), use_container_width=True, hide_index=True)

    st.subheader("核心判断")
    st.write(paragraph_core_fortune(bazi, strength, strength_score, rel_scores, patterns, auto_useful, auto_avoid))

    st.write("**系统取用说明：**")
    for n in useful_notes:
        st.write(f"- {n}")

    st.write("**日主强弱依据：**")
    for r in strength_reasons:
        st.write(f"- {r}")

    st.subheader("识别出的格局/能力链条")
    st.dataframe(pd.DataFrame(patterns), use_container_width=True, hide_index=True)

    st.subheader("神煞参考")
    if shensha:
        st.dataframe(pd.DataFrame(shensha), use_container_width=True, hide_index=True)
    else:
        st.info("未识别到本系统简表中的明显神煞。")


with tab1:
    st.header("出生至今最具代表性的十件事")
    st.caption("这是根据大运、流年、十神喜忌、冲合伏吟等信号自动推演出的十个代表性年份。它不是历史事实记录，而是命理上最应验、最容易发生重要事件的年份提示。")

    event_rows = []
    for idx, e in enumerate(ten_events, 1):
        event_rows.append({
            "序号": idx,
            "年份": e["年份"],
            "年龄": e["年龄"],
            "大运": e["大运"],
            "流年": e["流年"],
            "倾向": e["倾向"],
            "可能代表事件": e["主题"],
            "命理依据": e["命理依据"],
        })

    st.dataframe(pd.DataFrame(event_rows), use_container_width=True, hide_index=True)

    st.subheader("逐年解释")
    for idx, e in enumerate(ten_events, 1):
        with st.expander(f"{idx}. {e['年份']}年，约{e['年龄']}岁：{e['倾向']}"):
            st.write(f"**可能主题：** {e['主题']}")
            st.write(f"**命理依据：** {e['命理依据']}")
            if e["倾向"] == "偏顺":
                st.success("这一年更容易出现帮助、机会、突破、资源到位或阶段性成果。")
            elif e["倾向"] == "偏险":
                st.error("这一年更容易出现压力、损耗、关系冲突、破财、健康或方向调整。")
            else:
                st.warning("这一年更像转折年，重点不在吉凶，而在选择、变化和重新平衡。")


with tab2:
    st.header("命运详批")

    st.subheader("一、总体命格")
    st.write(paragraph_core_fortune(bazi, strength, strength_score, rel_scores, patterns, auto_useful, auto_avoid))

    st.subheader("二、性格与内在驱动力")
    top_rel = max(rel_scores.items(), key=lambda x: x[1])[0]
    st.write(
        f"命局中「{top_rel}」最突出，因此此人做事的底层驱动力常围绕「{RELATION_DESC[top_rel]['关键词']}」。"
        f"若这个关系为喜，则容易成为优势；若失衡，则会成为人生反复遇到的课题。"
    )
    if strength == "偏强":
        st.write("日主偏强，主观能量足，遇事不太愿意完全被动，适合主动开路，但要防固执、自我、过度承担。")
    elif strength == "偏弱":
        st.write("日主偏弱，环境、压力、资源、人际对自己影响更大，适合借平台、借贵人、借团队，不宜孤军硬冲。")
    else:
        st.write("日主中和，适应性较强，但真正成败取决于能否找到顺畅的关系链条和合适的大运时机。")

    st.subheader("三、事业")
    for x in career_advice(patterns, rel_scores, auto_useful):
        st.write(f"- {x}")

    st.subheader("四、财运")
    for x in wealth_advice(ten_scores, auto_useful, auto_avoid):
        st.write(f"- {x}")

    st.subheader("五、婚恋关系")
    for x in relationship_advice(bazi, ten_scores, gender, auto_avoid):
        st.write(f"- {x}")

    st.subheader("六、健康体质")
    for x in health_advice(elem_scores, strength):
        st.write(f"- {x}")


with tab3:
    st.header("大运流年")
    st.caption("普通用户不需要输入大运流年，本系统已自动排出。")

    st.subheader("大运表")
    st.dataframe(pd.DataFrame(dayun_list), use_container_width=True, hide_index=True)

    if current_dy:
        st.success(f"当前大运：{current_dy['大运']}，约 {current_dy['起始年份']}–{current_dy['结束年份']} 年。")
    else:
        st.info("暂未识别到当前大运，可能是排盘库返回信息不完整。")

    st.subheader("未来十年流年提示")
    future_rows = []
    for y in range(CURRENT_YEAR, CURRENT_YEAR + 10):
        dy = current_dayun(dayun_list, y)
        item = fortune_year_score(bazi, auto_useful, auto_avoid, y, dy, y - int(year))
        future_rows.append({
            "年份": y,
            "年龄": y - int(year),
            "大运": item["大运"],
            "流年": item["流年"],
            "倾向": item["倾向"],
            "主题": item["主题"],
            "命理依据": item["命理依据"],
        })
    st.dataframe(pd.DataFrame(future_rows), use_container_width=True, hide_index=True)


with tab4:
    st.header("人生建议")

    st.subheader("事业建议")
    for x in career_advice(patterns, rel_scores, auto_useful):
        st.write(f"- {x}")

    st.subheader("财务建议")
    for x in wealth_advice(ten_scores, auto_useful, auto_avoid):
        st.write(f"- {x}")

    st.subheader("关系建议")
    for x in relationship_advice(bazi, ten_scores, gender, auto_avoid):
        st.write(f"- {x}")

    st.subheader("健康与生活方式建议")
    for x in health_advice(elem_scores, strength):
        st.write(f"- {x}")

    st.subheader("避坑建议")
    avoid_relations = sorted(rel_scores.items(), key=lambda x: x[1], reverse=True)[:3]
    for rel, score in avoid_relations:
        st.write(f"- 「{rel}」主题较重：{RELATION_DESC[rel]['风险']} 建议：{RELATION_DESC[rel]['有利']}")


with tab5:
    st.header("附属决策模块")
    st.caption("此模块只是辅助，主系统仍以完整命理详批和大运流年为主体。")

    score, light, reasons = decision_score(auto_useful, auto_avoid, decision_type, current_year_item)

    st.subheader(f"决策判断：{light}")
    st.metric("决策分", score)
    st.progress(score / 100)
    st.write(f"**问题：** {decision_desc}")

    for r in reasons:
        st.write(f"- {r}")

    st.subheader("操作建议")
    if score >= 80:
        st.success("可以推进，但要设止损线，不要取消现实风控。")
    elif score >= 60:
        st.warning("可以小规模试点，先验证，不宜一次性重仓。")
    else:
        st.error("不宜贸然推进，建议延后、缩小规模或换方案。")


with tab6:
    st.header("导出报告")

    report = {
        "测算者": name,
        "性别": gender,
        "输入出生时间": local_dt.strftime("%Y-%m-%d %H:%M"),
        "排盘时间": chart_dt.strftime("%Y-%m-%d %H:%M"),
        "出生地址": address,
        "定位状态": geo_status,
        "真太阳时修正": solar_corr,
        "四柱": bazi["pillars"],
        "农历": bazi["lunar_text"],
        "日主": bazi["day_stem"],
        "日支": bazi["day_branch"],
        "空亡": bazi["kongwang"],
        "日主强弱": strength,
        "强弱分": strength_score,
        "五行得分": elem_scores,
        "十神得分": ten_scores,
        "关系得分": rel_scores,
        "喜用神": auto_useful,
        "风险十神": auto_avoid,
        "格局链条": patterns,
        "神煞": shensha,
        "大运": dayun_list,
        "出生至今十件代表性事件": event_rows,
        "未来十年": future_rows if "future_rows" in locals() else [],
        "事业建议": career_advice(patterns, rel_scores, auto_useful),
        "财务建议": wealth_advice(ten_scores, auto_useful, auto_avoid),
        "婚恋建议": relationship_advice(bazi, ten_scores, gender, auto_avoid),
        "健康建议": health_advice(elem_scores, strength),
        "附属决策": {
            "类型": decision_type,
            "问题": decision_desc,
            "评分": score if "score" in locals() else None,
            "结论": light if "light" in locals() else None,
        },
        "免责声明": "本报告为传统命理与象征性分析，不替代法律、医学、投资、职业等专业判断。",
    }

    report_text = json.dumps(report, ensure_ascii=False, indent=2)
    st.code(report_text, language="json")

    st.download_button(
        "下载 JSON 报告",
        data=report_text.encode("utf-8"),
        file_name=f"{name}_八字命理详批_V4.json",
        mime="application/json",
    )
