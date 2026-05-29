
import json
import math
import random
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
    page_title="命理大师问答详批系统 V6",
    page_icon="☯️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# 基础命理数据
# ============================================================

CURRENT_YEAR = datetime.now().year

HEAVENLY_STEMS = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
EARTHLY_BRANCHES = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

STEM_ELEMENT = {
    "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土", "己": "土",
    "庚": "金", "辛": "金", "壬": "水", "癸": "水",
}
STEM_YINYANG = {
    "甲": "阳", "乙": "阴", "丙": "阳", "丁": "阴", "戊": "阳", "己": "阴",
    "庚": "阳", "辛": "阴", "壬": "阳", "癸": "阴",
}
BRANCH_ELEMENT = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
    "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水",
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
ELEMENT_GENERATES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
ELEMENT_CONTROLS = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

TEN_GODS = ["正印", "偏印", "比肩", "劫财", "食神", "伤官", "正财", "偏财", "正官", "七杀"]
GOD_TO_RELATION = {
    "正印": "印", "偏印": "印",
    "比肩": "比劫", "劫财": "比劫",
    "食神": "食伤", "伤官": "食伤",
    "正财": "财", "偏财": "财",
    "正官": "官杀", "七杀": "官杀",
}
RELATION_ORDER = ["印", "比劫", "食伤", "财", "官杀"]

RELATION_MEANING = {
    "印": {
        "象": "贵人、学历、母亲、长辈、证书、房屋、保护、精神依靠",
        "顺": "读书有悟性，适合借平台、拿资质、走专业路线。",
        "逆": "想得多、行动慢、依赖强，容易把机会拖成顾虑。",
        "问事": "先求凭证、规则、平台、贵人，不宜裸奔硬冲。",
    },
    "比劫": {
        "象": "朋友、兄弟、同辈、竞争者、合伙、团队、体力行动",
        "顺": "有人气、有行动力，遇竞争反而能逼出本事。",
        "逆": "人情消耗、合伙分利、熟人拖累，同辈之间容易有争夺。",
        "问事": "凡涉及合伙、朋友、同辈利益，先定规则再谈感情。",
    },
    "食伤": {
        "象": "才华、表达、技术、作品、口才、创意、子女、自由",
        "顺": "靠本事吃饭，能用技术、表达、作品打开局面。",
        "逆": "嘴快心急，不服管，容易与权威冲撞，想法多而收束难。",
        "问事": "要拿作品、方案、数据说话，少靠情绪争辩。",
    },
    "财": {
        "象": "钱财、资源、项目、客户、市场、资产、现实关系",
        "顺": "有资源感和市场感，适合经营、项目、客户、资产配置。",
        "逆": "为钱为项目耗神，贪快则破，感情里也易被现实条件牵动。",
        "问事": "看现金流、合同、退出机制，别只看眼前收益。",
    },
    "官杀": {
        "象": "职位、权力、领导、规则、压力、考试、责任、风险",
        "顺": "能担事，适合在规则、组织、管理、风控中成名成事。",
        "逆": "压力重、被管束、怕犯错，合同、制度、债务、官非要谨慎。",
        "问事": "先看责任边界、合规风险、上级压力和长期代价。",
    },
}

SEASON_POWER = {
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

CITY_COORDS = {
    "北京": (39.9042, 116.4074), "上海": (31.2304, 121.4737), "天津": (39.3434, 117.3616),
    "重庆": (29.5630, 106.5516), "广州": (23.1291, 113.2644), "深圳": (22.5431, 114.0579),
    "杭州": (30.2741, 120.1551), "南京": (32.0603, 118.7969), "成都": (30.5728, 104.0668),
    "武汉": (30.5928, 114.3055), "西安": (34.3416, 108.9398), "郑州": (34.7466, 113.6254),
    "长沙": (28.2282, 112.9388), "贵阳": (26.6470, 106.6302), "昆明": (24.8801, 102.8329),
    "南宁": (22.8170, 108.3669), "福州": (26.0745, 119.2965), "厦门": (24.4798, 118.0894),
    "济南": (36.6512, 117.1201), "青岛": (36.0671, 120.3826), "沈阳": (41.8057, 123.4315),
    "哈尔滨": (45.8038, 126.5349), "长春": (43.8171, 125.3235), "太原": (37.8706, 112.5489),
    "石家庄": (38.0428, 114.5149), "兰州": (36.0611, 103.8343), "银川": (38.4872, 106.2309),
    "西宁": (36.6171, 101.7782), "乌鲁木齐": (43.8256, 87.6168), "拉萨": (29.6520, 91.1721),
    "台北": (25.0330, 121.5654), "香港": (22.3193, 114.1694), "澳门": (22.1987, 113.5439),
}

QUESTION_MAP = {
    "事业工作": ["正官", "七杀", "正印", "偏印", "食神", "伤官"],
    "财运投资": ["正财", "偏财", "食神", "伤官", "比肩", "劫财"],
    "婚恋感情": ["正财", "偏财", "正官", "七杀", "正印", "偏印"],
    "创业副业": ["食神", "伤官", "正财", "偏财", "比肩", "劫财"],
    "学业考试": ["正印", "偏印", "正官", "七杀"],
    "房产搬迁": ["正财", "偏财", "正印", "偏印"],
    "人际合作": ["比肩", "劫财", "正财", "偏财", "食神", "伤官"],
    "健康状态": ["正印", "偏印", "七杀", "伤官"],
    "综合运势": TEN_GODS,
}


# ============================================================
# 工具函数
# ============================================================

def seed_rng(*parts):
    return random.Random("|".join(map(str, parts)))

def pick(rng, items):
    return rng.choice(items)

@st.cache_data(show_spinner=False, ttl=86400)
def geocode_address(address: str) -> Optional[Dict]:
    address = (address or "").strip()
    if not address:
        return None
    for city, (lat, lon) in CITY_COORDS.items():
        if city in address:
            return {"lat": lat, "lon": lon, "source": "内置城市库", "display": city}
    if GEOPY_AVAILABLE:
        try:
            geolocator = Nominatim(user_agent="bazi_master_v6")
            query = address
            if not re.search(r"中国|China|Taiwan|Hong Kong|Macau", query, re.I):
                query = f"{address}, China"
            loc = geolocator.geocode(query, timeout=8, language="zh-CN")
            if loc:
                return {"lat": float(loc.latitude), "lon": float(loc.longitude), "source": "在线地理编码", "display": loc.address}
        except Exception:
            return None
    return None

def equation_of_time_minutes(day_of_year: int) -> float:
    b = math.radians((360 / 365) * (day_of_year - 81))
    return 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)

def true_solar_time(local_dt: datetime, lon: float) -> Tuple[datetime, Dict]:
    doy = int(local_dt.strftime("%j"))
    longitude_correction = (lon - 120.0) * 4.0
    eot = equation_of_time_minutes(doy)
    total = longitude_correction + eot
    return local_dt + timedelta(minutes=total), {
        "经度修正分钟": round(longitude_correction, 2),
        "均时差分钟": round(eot, 2),
        "总修正分钟": round(total, 2),
    }

def split_gz(gz: str) -> Tuple[str, str]:
    return gz[0], gz[1]

def ganzhi_from_index(idx: int) -> str:
    return HEAVENLY_STEMS[idx % 10] + EARTHLY_BRANCHES[idx % 12]

def gz_index(gz: str) -> int:
    for i in range(60):
        if ganzhi_from_index(i) == gz:
            return i
    return 0

def year_ganzhi(year: int) -> str:
    return ganzhi_from_index((year - 1984) % 60)

def ten_god(day_stem: str, other_stem: str) -> str:
    me = STEM_ELEMENT[day_stem]
    other = STEM_ELEMENT[other_stem]
    same = STEM_YINYANG[day_stem] == STEM_YINYANG[other_stem]
    if other == me:
        return "比肩" if same else "劫财"
    if ELEMENT_GENERATES[other] == me:
        return "偏印" if same else "正印"
    if ELEMENT_GENERATES[me] == other:
        return "食神" if same else "伤官"
    if ELEMENT_CONTROLS[other] == me:
        return "七杀" if same else "正官"
    if ELEMENT_CONTROLS[me] == other:
        return "偏财" if same else "正财"
    return "未知"

def build_bazi(dt: datetime) -> Dict:
    solar = Solar.fromYmdHms(dt.year, dt.month, dt.day, dt.hour, dt.minute, 0)
    lunar = solar.getLunar()
    ec = lunar.getEightChar()
    pillars = {"年柱": ec.getYear(), "月柱": ec.getMonth(), "日柱": ec.getDay(), "时柱": ec.getTime()}
    day_stem, day_branch = split_gz(pillars["日柱"])
    rows, hidden = [], []
    for name, gz in pillars.items():
        stem, branch = split_gz(gz)
        g = "日主" if name == "日柱" else ten_god(day_stem, stem)
        hid = []
        for hs, wt in BRANCH_HIDDEN_STEMS[branch]:
            hg = ten_god(day_stem, hs)
            hid.append(f"{hs}{hg}")
            hidden.append({"柱": name, "地支": branch, "藏干": hs, "十神": hg, "权重": wt})
        rows.append({
            "柱": name, "干支": gz, "天干": stem, "天干五行": STEM_ELEMENT[stem],
            "天干十神": g, "地支": branch, "地支五行": BRANCH_ELEMENT[branch],
            "藏干": "、".join(hid),
        })
    return {
        "solar": solar, "lunar": lunar, "eight_char": ec, "pillars": pillars,
        "day_stem": day_stem, "day_branch": day_branch, "rows": rows, "hidden": hidden,
        "lunar_text": lunar.toString(), "lunar_full": lunar.toFullString(),
    }

def element_scores(bazi: Dict) -> Dict[str, float]:
    month_branch = bazi["rows"][1]["地支"]
    season = SEASON_POWER[month_branch]
    scores = {e: 0.0 for e in ["木", "火", "土", "金", "水"]}
    for r in bazi["rows"]:
        scores[r["天干五行"]] += 1.0 * season[r["天干五行"]]
        scores[r["地支五行"]] += 0.8 * season[r["地支五行"]]
    for h in bazi["hidden"]:
        el = STEM_ELEMENT[h["藏干"]]
        scores[el] += h["权重"] * 0.6 * season[el]
    return {k: round(v, 2) for k, v in scores.items()}

def ten_scores(bazi: Dict) -> Dict[str, float]:
    scores = {g: 0.0 for g in TEN_GODS}
    for r in bazi["rows"]:
        g = r["天干十神"]
        if g in scores:
            scores[g] += 1.0
    for h in bazi["hidden"]:
        scores[h["十神"]] += h["权重"] * 0.55
    return {k: round(v, 2) for k, v in scores.items()}

def relation_scores(ts: Dict[str, float]) -> Dict[str, float]:
    rel = {r: 0.0 for r in RELATION_ORDER}
    for g, v in ts.items():
        rel[GOD_TO_RELATION[g]] += v
    return {k: round(v, 2) for k, v in rel.items()}

def day_strength(bazi: Dict, es: Dict[str, float]) -> Tuple[str, int, List[str]]:
    day_el = STEM_ELEMENT[bazi["day_stem"]]
    mother = [k for k, v in ELEMENT_GENERATES.items() if v == day_el][0]
    child = ELEMENT_GENERATES[day_el]
    wealth = ELEMENT_CONTROLS[day_el]
    pressure = [k for k, v in ELEMENT_CONTROLS.items() if v == day_el][0]
    score = 50 + es[day_el] * 6 + es[mother] * 5 - es[child] * 3 - es[wealth] * 4 - es[pressure] * 5
    month_branch = bazi["rows"][1]["地支"]
    if day_el in [STEM_ELEMENT[x[0]] for x in BRANCH_HIDDEN_STEMS[month_branch]]:
        score += 10
    score = max(5, min(95, int(round(score))))
    label = "偏强" if score >= 66 else "偏弱" if score <= 42 else "中和"
    reason = [
        f"日主属{day_el}，同类得分{es[day_el]}，印星得分{es[mother]}。",
        f"泄秀得分{es[child]}，财星得分{es[wealth]}，官杀压力得分{es[pressure]}。",
        f"月令为{month_branch}，季节之气已纳入权重。",
    ]
    return label, score, reason

def useful_avoid(strength: str, rs: Dict[str, float]) -> Tuple[List[str], List[str], List[str]]:
    if strength == "偏强":
        useful = ["食神", "伤官", "正财", "偏财", "正官", "七杀"]
        avoid = ["正印", "偏印", "比肩", "劫财"]
        note = "身偏旺，宜泄、宜耗、宜受规矩锻炼；不宜再一味生扶。"
    elif strength == "偏弱":
        useful = ["正印", "偏印", "比肩", "劫财"]
        avoid = ["食神", "伤官", "正财", "偏财", "正官", "七杀"]
        note = "身偏弱，宜先得印比扶身；不宜过早重财重责。"
    else:
        useful, avoid = [], []
        note = "身势中和，喜忌要看格局流通和人生应事，不可机械取用。"
    top = max(rs.items(), key=lambda x: x[1])[0]
    return useful, avoid, [note, f"命局最重之象在「{top}」，此象既是天赋，也是人生反复考试之处。"]

def detect_patterns(ts: Dict[str, float]) -> List[Dict]:
    def s(names):
        return sum(ts.get(n, 0) for n in names)
    pats = []
    if s(["食神", "伤官"]) >= 1.2 and s(["正财", "偏财"]) >= 1.0:
        pats.append(("食伤生财", "靠才华、技术、表达、产品而得财", "最怕想法太多、现金流跟不上"))
    if s(["正官", "七杀"]) >= 1.0 and s(["正印", "偏印"]) >= 1.0:
        pats.append(("官印相生", "压力能化为资质、职位、名分", "最怕只守规矩而失去主动"))
    if s(["正财", "偏财"]) >= 1.0 and s(["正官", "七杀"]) >= 1.0:
        pats.append(("财生官杀", "资源、项目可换权责和身份", "越往上越要守规则"))
    if s(["食神", "伤官"]) >= 1.2 and s(["正官", "七杀"]) >= 1.0:
        pats.append(("食伤制杀", "用技术、方案、作品压住压力", "容易顶撞权威，要靠结果说话"))
    if s(["比肩", "劫财"]) >= 1.2 and s(["正财", "偏财"]) >= 1.0:
        pats.append(("比劫夺财", "朋友、合伙、同辈会牵动钱财", "钱账不明则有损耗"))
    if not pats:
        pats.append(("杂气成局", "格局不走单线，需看大运引动", "不能用一个标签断一生"))
    return [{"名": a, "成处": b, "忌处": c} for a, b, c in pats]

def get_yun(bazi: Dict, gender: str):
    gender_num = 0 if gender == "女" else 1
    ec = bazi["eight_char"]
    for sect in [1, 2]:
        try:
            return ec.getYun(gender_num, sect)
        except Exception:
            continue
    return None

def dayun_list(bazi: Dict, gender: str, birth_year: int) -> List[Dict]:
    yun = get_yun(bazi, gender)
    rows = []
    if yun:
        try:
            for dy in yun.getDaYun():
                try:
                    gz = dy.getGanZhi()
                    sy = dy.getStartYear()
                    ey = dy.getEndYear()
                    sa = dy.getStartAge()
                    ea = dy.getEndAge()
                except Exception:
                    continue
                if gz and sy:
                    rows.append({"大运": gz, "起始年龄": sa, "结束年龄": ea, "起始年份": sy, "结束年份": ey})
            if rows:
                return rows[:12]
        except Exception:
            pass
    ystem = bazi["rows"][0]["天干"]
    male = gender != "女"
    forward = (male and STEM_YINYANG[ystem] == "阳") or ((not male) and STEM_YINYANG[ystem] == "阴")
    midx = gz_index(bazi["pillars"]["月柱"])
    for i in range(10):
        idx = midx + i + 1 if forward else midx - i - 1
        rows.append({"大运": ganzhi_from_index(idx % 60), "起始年龄": 8+i*10, "结束年龄": 17+i*10, "起始年份": birth_year+8+i*10, "结束年份": birth_year+17+i*10})
    return rows

def current_dayun(dys: List[Dict], year: int) -> Optional[Dict]:
    for d in dys:
        if d.get("起始年份") and d.get("结束年份") and d["起始年份"] <= year <= d["结束年份"]:
            return d
    return None

def gz_gods(day_stem: str, gz: str) -> List[str]:
    stem, branch = split_gz(gz)
    gods = [ten_god(day_stem, stem)]
    gods.extend([ten_god(day_stem, hs) for hs, _ in BRANCH_HIDDEN_STEMS[branch]])
    return gods

def year_signal(bazi: Dict, year: int, dy: Optional[Dict], useful: List[str], avoid: List[str], birth_year: int) -> Dict:
    ygz = year_ganzhi(year)
    gods = gz_gods(bazi["day_stem"], ygz)
    dgz = dy["大运"] if dy else ""
    dgods = gz_gods(bazi["day_stem"], dgz) if dgz else []
    score, evidence, themes = 0, [], []
    branches = [r["地支"] for r in bazi["rows"]]
    yb = ygz[1]
    for g in gods:
        if g in useful:
            score += 12; evidence.append(f"流年见{g}为用")
        if g in avoid:
            score -= 12; evidence.append(f"流年见{g}为忌")
    for g in dgods:
        if g in useful:
            score += 7; evidence.append(f"大运带{g}为助")
        if g in avoid:
            score -= 7; evidence.append(f"大运带{g}为压")
    clash = {"子":"午","午":"子","丑":"未","未":"丑","寅":"申","申":"寅","卯":"酉","酉":"卯","辰":"戌","戌":"辰","巳":"亥","亥":"巳"}
    if clash.get(yb) in branches:
        score += 8; evidence.append("流年冲动原局"); themes.append("迁移、环境变化、关系转折、方向重选")
    if yb in branches:
        score += 6; evidence.append("流年伏吟原局"); themes.append("旧事重来、主题放大、内外压力重复")
    rels = [GOD_TO_RELATION.get(g) for g in gods + dgods if g in GOD_TO_RELATION]
    for r in set(rels):
        if r == "印": themes.append("学业、证书、贵人、家庭、房屋、长辈")
        elif r == "比劫": themes.append("朋友、竞争、合伙、同辈、人情往来")
        elif r == "食伤": themes.append("表达、作品、技术、离职冲动、子女缘")
        elif r == "财": themes.append("钱财、项目、客户、感情现实、资产")
        elif r == "官杀": themes.append("职位、考试、领导、规则、压力、责任")
    tone = "顺中有成" if score >= 18 else "险中有变" if score <= -18 else "转折平衡"
    age = year - int(birth_year)
    importance = abs(score) + (8 if age in [6, 12, 15, 18, 22, 24, 28, 30, 36, 42, 48, 54, 60] else 0)
    return {"年份": year, "年龄": age, "流年": ygz, "大运": dgz, "分": score, "重要度": importance, "倾向": tone, "主题": list(dict.fromkeys(themes))[:3], "依据": list(dict.fromkeys(evidence))[:4]}

def representative_years(bazi, birth_year, now_year, dys, useful, avoid):
    rows = [year_signal(bazi, y, current_dayun(dys, y), useful, avoid, birth_year) for y in range(birth_year, now_year + 1)]
    rows = sorted(rows, key=lambda x: x["重要度"], reverse=True)
    chosen = []
    for r in rows:
        if len(chosen) >= 10:
            break
        if all(abs(r["年份"] - c["年份"]) >= 2 for c in chosen):
            chosen.append(r)
    return sorted(chosen, key=lambda x: x["年份"])


# ============================================================
# 断语引擎
# ============================================================

def question_category(question: str, selected: str) -> str:
    q = question or ""
    rules = [
        ("创业副业", ["创业", "副业", "开店", "项目", "公司", "生意"]),
        ("财运投资", ["财", "钱", "投资", "股票", "买币", "资产", "收入", "赚钱"]),
        ("婚恋感情", ["婚", "恋", "感情", "对象", "结婚", "离婚", "分手", "桃花"]),
        ("事业工作", ["事业", "工作", "跳槽", "领导", "升职", "职位", "职业"]),
        ("学业考试", ["考试", "考证", "学习", "学历", "读书", "考研"]),
        ("房产搬迁", ["房", "买房", "搬家", "迁移", "城市", "租房"]),
        ("人际合作", ["合作", "合伙", "朋友", "同事", "团队", "人际"]),
        ("健康状态", ["健康", "病", "身体", "睡眠", "焦虑", "体质"]),
    ]
    for cat, kws in rules:
        if any(k in q for k in kws):
            return cat
    return selected

def master_opening(name, bazi, strength, score, rs, patterns, rng):
    day = bazi["day_stem"]
    day_el = STEM_ELEMENT[day]
    month = bazi["rows"][1]["地支"]
    top_rel = max(rs.items(), key=lambda x: x[1])[0]
    pat = patterns[0]["名"]
    style = pick(rng, [
        f"先看此造，不急着断吉凶。命里最要紧的，是日主{day}{day_el}落在{month}月，气势先定。",
        f"这盘一打开，第一眼看的不是财官，而是日主有没有根、有无路可走。此命日主为{day}{day_el}，月令在{month}。",
        f"批这个八字，要先抓主线。此造日主{day}{day_el}，身势判为{strength}，不是平铺直叙的命。"
    ])
    return (
        f"{style}\n\n"
        f"我的总断是：此命不是单靠一项东西成事的人，主线落在「{top_rel}」上，取象为{RELATION_MEANING[top_rel]['象']}。"
        f"局中较明显的结构是「{pat}」，所以一生真正的机会，多不是凭空来的，而是由某种关系、压力或本事转化出来。"
        f"日主强弱约为{score}/100，判作「{strength}」。这个判断很关键，因为同样见财，有人是得财，有人是被财累；同样见官，有人是得名，有人是被压。"
    )

def temperament_text(bazi, strength, rs):
    top = max(rs.items(), key=lambda x: x[1])[0]
    second = sorted(rs.items(), key=lambda x: x[1], reverse=True)[1][0]
    if strength == "偏强":
        core = "骨子里不太愿意被人牵着走，遇事有自己的判断，也有一股不服输的劲。"
        caution = "身旺之人最怕困在自己的判断里，听得进逆耳话，格局才会打开。"
    elif strength == "偏弱":
        core = "外界环境对你影响很大，越是大事，越不能孤军硬扛，必须借平台、借人、借规则。"
        caution = "身弱之人不是不能成事，而是不能用硬冲的方式成事，借力就是命门。"
    else:
        core = "适应力不差，真正决定高低的不是胆子大小，而是有没有找到合适的路径。"
        caution = "中和之命最怕摇摆，方向一乱，优势也会被消耗掉。"
    return (
        f"性情上，{core}命局里「{top}」重，外在表现多带有{RELATION_MEANING[top]['象']}的味道；"
        f"同时「{second}」也不轻，所以人生不是单线条，常常是一边要处理{RELATION_MEANING[top]['象']}，一边又要面对{RELATION_MEANING[second]['象']}。\n\n"
        f"断语：{caution}"
    )

def event_text(e, rng):
    themes = "、".join(e["主题"]) if e["主题"] else "阶段转换"
    candidates = []
    if "学业" in themes or "证书" in themes: candidates.append("学业、考试、证书、老师长辈或平台机会有明显牵动")
    if "钱财" in themes or "项目" in themes: candidates.append("钱财、项目、客户、资产或现实关系出现重要变化")
    if "职位" in themes or "压力" in themes: candidates.append("工作压力、职位责任、规则考试或领导关系成为主题")
    if "朋友" in themes or "合伙" in themes: candidates.append("朋友、同辈、合伙、人情往来容易影响选择")
    if "迁移" in themes or "环境" in themes: candidates.append("居住、学校、工作环境或人生方向可能有变动")
    if not candidates: candidates.append("这一年多主心境、环境或人生节奏的调整")
    if e["倾向"] == "顺中有成":
        tone = "这一年不是完全没有压力，但更容易有收获、有帮助、有突破。"
    elif e["倾向"] == "险中有变":
        tone = "这一年要当作关口看，容易有压力、损耗、关系变化或被迫调整。"
    else:
        tone = "这一年重在转折，不一定大吉大凶，但选择会影响后面的路。"
    return f"约{e['年龄']}岁，{e['流年']}年。{pick(rng, candidates)}。{tone}依据是：{'；'.join(e['依据']) or '流年与原局互动明显'}。"

def category_master_answer(cat, question, bazi, ts, rs, patterns, useful, avoid, cur_sig, future_rows):
    target = QUESTION_MAP[cat]
    hit_use = set(target) & set(useful)
    hit_avoid = set(target) & set(avoid)
    score = 55 + len(hit_use) * 8 - len(hit_avoid) * 10
    if cur_sig["倾向"] == "顺中有成": score += 8
    if cur_sig["倾向"] == "险中有变": score -= 8
    score = max(0, min(100, score))
    if score >= 78:
        verdict = "可以做，但要带章法做。不是赌一把，而是顺势推进。"
    elif score >= 58:
        verdict = "能试，但不宜重仓。先试、先验、先留退路。"
    else:
        verdict = "此事眼下不宜硬上。先缓一缓，把条件补齐，比强行推进更好。"

    rels = sorted(rs.items(), key=lambda x: x[1], reverse=True)
    top_rel = rels[0][0]
    text = []
    text.append(f"你问的是「{question or cat}」。这个问题在命里主要牵动：{'、'.join(target)}。")
    text.append(f"我先给结论：**{verdict}** 当前可行度约 **{score}/100**。")
    text.append(f"为什么这么断？一是命局主线在「{top_rel}」，{RELATION_MEANING[top_rel]['问事']} 二是今年为{CURRENT_YEAR}年{year_ganzhi(CURRENT_YEAR)}，当前流年倾向为「{cur_sig['倾向']}」，主题在：{'、'.join(cur_sig['主题']) or '阶段调整'}。")
    if hit_use:
        text.append(f"有利处在于：此事能引动你的用处——{'、'.join(hit_use)}。这些象动起来，容易出现助力、机会、资源或可转化的成果。")
    if hit_avoid:
        text.append(f"要防的地方是：此事也会碰到你的忌处——{'、'.join(hit_avoid)}。这些象动起来，容易带来拖累、压力、破耗或反复。")
    if cat == "事业工作":
        text.append("事业上不要只问能不能换、能不能升，要看这份事是否让你形成“位置、能力、资源”的闭环。只给压力不给成长的工作，不宜久留。")
    elif cat == "财运投资":
        text.append("财运要分正财与偏财。正财宜稳，偏财宜谨慎。若现金流、合同、退出机制不清，再好的机会也容易变成耗神之财。")
    elif cat == "婚恋感情":
        text.append("感情不是只看桃花，而要看责任与消耗。能让你心定、路顺、现实压力可共同承担的关系，才是好关系。")
    elif cat == "创业副业":
        text.append("创业副业看食伤生财，也看比劫分财。能用作品、技术、客户验证的可以试；只靠热情、熟人和口头承诺的要避。")
    elif cat == "学业考试":
        text.append("学业考试看印与官。印主吸收，官主规则。此事宜按计划、证书、标准答案走，不宜凭感觉临场发挥。")
    elif cat == "房产搬迁":
        text.append("房产搬迁看财印与冲动。买房要看现金流，搬迁要看是否能带来平台、贵人或事业便利。只为情绪换环境，未必真改运。")
    elif cat == "人际合作":
        text.append("合作最怕人情在前、规则在后。此命问合作，必须先讲钱、权、责、退。不好意思讲清楚，后面就会不好收场。")
    elif cat == "健康状态":
        text.append("健康问命，只能看体质倾向，不能代替检查。眼下要看压力是否过重、睡眠是否被破、饮食作息是否失衡。")
    else:
        text.append("综合看，此阶段最重要的是认清主线，不要被短期情绪带着走。")

    best_years = sorted(future_rows, key=lambda x: x["分"], reverse=True)[:2]
    risk_years = sorted(future_rows, key=lambda x: x["分"])[:2]
    text.append(f"未来十年里，相对好用的年份可重点看：{'、'.join([str(x['年份']) + '年' for x in best_years])}；需要谨慎的年份可重点看：{'、'.join([str(x['年份']) + '年' for x in risk_years])}。")
    text.append("一句话收束：这事不是不能看机会，而是要先看代价；不是不能行动，而是要按你的命局承载力行动。")
    return "\n\n".join(text), score

def career_lines(patterns, rs):
    pnames = [p["名"] for p in patterns]
    lines = []
    if "食伤生财" in pnames: lines.append("事业不要只求稳定，命里有“把本事变成钱”的路。技术、内容、产品、销售、咨询、培训、自媒体、方案型工作，都比纯执行更有空间。")
    if "官印相生" in pnames: lines.append("此命吃平台和资质，适合在有规则、有门槛、有专业背书的系统里往上走。")
    if "财生官杀" in pnames: lines.append("资源能生责任，项目能换位置。适合做经营、管理、商务、项目制工作，但越做大越要守规则。")
    if "食伤制杀" in pnames: lines.append("遇到压力不要硬顶，要拿专业、作品、数据、方案去压住局面。")
    if "比劫夺财" in pnames: lines.append("事业上最怕熟人局、兄弟局、口头承诺局。能合作，但钱账和权责必须先小人后君子。")
    if not lines:
        top = max(rs.items(), key=lambda x: x[1])[0]
        lines.append(f"事业主线落在「{top}」，适合围绕{RELATION_MEANING[top]['象']}去设计路线。")
    return lines

def wealth_lines(ts, useful, avoid):
    wealth = ts["正财"] + ts["偏财"]
    output = ts["食神"] + ts["伤官"]
    bi = ts["比肩"] + ts["劫财"]
    lines = []
    lines.append("财星不弱，一生不会完全绕开钱、资源、项目、市场这些主题。" if wealth >= 1.6 else "财星不是最重，求财不能只靠追逐机会，更要靠能力、平台或长期积累转化。")
    if output >= 1.2: lines.append("食伤有气，钱从才华、技术、表达、作品、服务中来，比单纯投机更稳。")
    if bi >= 1.2: lines.append("比劫牵财，人情钱、合伙钱、朋友项目要特别慎重，账目不清必有后患。")
    if "正财" in avoid or "偏财" in avoid: lines.append("财为风险时，越想快赚，越容易快失；不借钱投资，不替人担保，不碰看不懂的高收益。")
    else: lines.append("财若能为用，宜稳步经营客户、渠道、资产，不宜急躁求暴利。")
    return lines

def relationship_lines(bazi, gender, avoid):
    day_branch = bazi["day_branch"]
    hidden_gods = [ten_god(bazi["day_stem"], hs) for hs, _ in BRANCH_HIDDEN_STEMS[day_branch]]
    lines = [f"感情先看日支，此命日支坐「{day_branch}」，内里带「{'、'.join(hidden_gods)}」之象。"]
    if gender == "男":
        lines.append("男命看关系不能只看财星，但财星确实代表现实关系、伴侣议题和责任交换。")
        bad = any(g in avoid for g in ["正财", "偏财"])
    elif gender == "女":
        lines.append("女命传统以官杀看伴侣与关系责任，但现代要同时看自我边界和现实选择。")
        bad = any(g in avoid for g in ["正官", "七杀"])
    else:
        lines.append("不限定性别时，关系重点看日支、财官、边界和责任是否平衡。")
        bad = any(g in avoid for g in ["正财", "偏财", "正官", "七杀"])
    lines.append("关系里最怕因为现实条件、压力、控制欲或责任不对等而委屈自己。" if bad else "适合找能共同承担现实、又不压制你发展路径的人。")
    return lines

def health_lines(es):
    weak = min(es.items(), key=lambda x: x[1])[0]
    strong = max(es.items(), key=lambda x: x[1])[0]
    body = {
        "木": "肝胆、筋膜、情绪疏泄",
        "火": "心火、睡眠、血压、神经兴奋",
        "土": "脾胃、消化、代谢、湿气",
        "金": "肺、皮肤、呼吸道、边界感",
        "水": "肾、泌尿、生殖、精力储备",
    }
    return [f"五行偏弱在「{weak}」，平时要留心{body[weak]}。", f"五行偏旺在「{strong}」，旺处也会成过载点，尤其在压力大时要留心{body[strong]}。", "健康断语只作体质提醒，不能替代检查和治疗；有症状要看医生。"]


# ============================================================
# UI 输入
# ============================================================

st.title("☯️ 命理大师问答详批系统 V6")
st.caption("自动排盘 + 大师总断 + 出生至今十件应事 + 针对性问答。前台像师傅断盘，后台自动算命盘。")

if not LUNAR_AVAILABLE:
    st.error("缺少 lunar-python，请先安装：pip install lunar-python")
    st.stop()

with st.sidebar:
    st.header("命主信息")
    name = st.text_input("姓名/代号", value="测试用户")
    gender = st.selectbox("性别", ["男", "女", "其他/不指定"], index=0)
    st.subheader("出生时间")
    year = st.number_input("年", min_value=1600, max_value=2200, value=1990, step=1)
    month = st.number_input("月", min_value=1, max_value=12, value=1, step=1)
    day = st.number_input("日", min_value=1, max_value=31, value=1, step=1)
    hour = st.number_input("时", min_value=0, max_value=23, value=8, step=1)
    minute = st.number_input("分", min_value=0, max_value=59, value=0, step=1)
    address = st.text_input("出生地址", value="中国 贵州 贵阳")
    use_true_solar = st.checkbox("自动换算真太阳时", value=True)
    st.divider()
    st.header("大师问事")
    selected_cat = st.selectbox("问题方向", list(QUESTION_MAP.keys()), index=8)
    question = st.text_area("具体想问什么", value="今年适不适合做副业或创业？", height=100)
    answer_button = st.button("请大师断此一问", type="primary")

try:
    local_dt = datetime(int(year), int(month), int(day), int(hour), int(minute), 0)
except ValueError as e:
    st.error(f"出生日期无效：{e}")
    st.stop()

geo = geocode_address(address)
lon = geo["lon"] if geo else 120.0
if use_true_solar:
    chart_dt, solar_corr = true_solar_time(local_dt, lon)
else:
    chart_dt, solar_corr = local_dt, {"经度修正分钟": 0, "均时差分钟": 0, "总修正分钟": 0}

bazi = build_bazi(chart_dt)
es = element_scores(bazi)
ts = ten_scores(bazi)
rs = relation_scores(ts)
strength, strength_score, strength_reason = day_strength(bazi, es)
useful, avoid, use_notes = useful_avoid(strength, rs)
patterns = detect_patterns(ts)
dys = dayun_list(bazi, gender, int(year))
cur_dy = current_dayun(dys, CURRENT_YEAR)
cur_signal = year_signal(bazi, CURRENT_YEAR, cur_dy, useful, avoid, int(year))
rep_years = representative_years(bazi, int(year), CURRENT_YEAR, dys, useful, avoid)
future_rows = [year_signal(bazi, y, current_dayun(dys, y), useful, avoid, int(year)) for y in range(CURRENT_YEAR, CURRENT_YEAR + 10)]
rng = seed_rng(name, chart_dt.isoformat(), bazi["pillars"]["日柱"])

col1, col2, col3, col4 = st.columns(4)
col1.metric("四柱", f"{bazi['pillars']['年柱']} {bazi['pillars']['月柱']} {bazi['pillars']['日柱']} {bazi['pillars']['时柱']}")
col2.metric("日主", f"{bazi['day_stem']}{STEM_ELEMENT[bazi['day_stem']]}")
col3.metric("身势", f"{strength} {strength_score}/100")
col4.metric("当前大运", cur_dy["大运"] if cur_dy else "未识别")
st.caption(f"排盘时间：{chart_dt.strftime('%Y-%m-%d %H:%M')}。地址经纬度在后台用于真太阳时换算，前台不展示。")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["大师问答", "大师总断", "十件应事", "事业财运", "婚恋健康", "命盘依据"])

with tab1:
    st.header("大师问答")
    cat = question_category(question, selected_cat)
    answer, qscore = category_master_answer(cat, question, bazi, ts, rs, patterns, useful, avoid, cur_signal, future_rows)

    st.markdown(f"### 此问归类：{cat}")
    st.progress(qscore / 100)
    st.markdown(answer)

    st.divider()
    st.markdown("#### 追问提示")
    st.write("你可以把问题改得更具体，例如：")
    st.write("- “我今年要不要离职创业？”")
    st.write("- “这段关系要不要继续？”")
    st.write("- “未来三年适合买房吗？”")
    st.write("- “我适合做内容、自媒体、销售还是管理？”")

with tab2:
    st.header("大师总断")
    st.markdown(master_opening(name, bazi, strength, strength_score, rs, patterns, rng))
    st.markdown("### 性情与命中主线")
    st.markdown(temperament_text(bazi, strength, rs))
    st.markdown("### 此命最要紧的三句话")
    top_rel = max(rs.items(), key=lambda x: x[1])[0]
    for x in [
        f"第一，命里最重的是「{top_rel}」，这是贯穿一生的主线。",
        f"第二，身势为「{strength}」，所以做事方法要顺着身势走，不能照搬别人的路。",
        f"第三，当前大运在「{cur_dy['大运'] if cur_dy else '未识别'}」，眼下这十年的主题不是随机的，要按大运节奏行事。",
    ]:
        st.write(f"- {x}")
    st.markdown("### 取用与避忌")
    st.write(f"**宜用：** {'、'.join(useful) if useful else '需结合过往应事校准'}")
    st.write(f"**忌重：** {'、'.join(avoid) if avoid else '需结合过往应事校准'}")
    for n in use_notes:
        st.write(f"- {n}")

with tab3:
    st.header("出生至今十件应事")
    st.caption("这是命理上最容易应验、最该回头核对的十个年份。")
    for i, e in enumerate(rep_years, 1):
        with st.expander(f"{i}. {e['年份']}年，约{e['年龄']}岁：{e['倾向']}", expanded=(i <= 3)):
            st.markdown(event_text(e, rng))
    st.info("若这十个年份里，有六七个能对应人生大事，此盘取象基本可用；若多数不应，优先检查出生时辰、出生地和真太阳时。")

with tab4:
    st.header("事业与财运")
    st.markdown("### 事业怎么走")
    for line in career_lines(patterns, rs):
        st.write(f"- {line}")
    st.markdown("### 财从哪里来，坑在哪里")
    for line in wealth_lines(ts, useful, avoid):
        st.write(f"- {line}")
    st.markdown("### 格局取象")
    for p in patterns:
        st.write(f"**{p['名']}**：成处在于{p['成处']}；忌处在于{p['忌处']}。")

with tab5:
    st.header("婚恋与健康")
    st.markdown("### 婚恋关系")
    for line in relationship_lines(bazi, gender, avoid):
        st.write(f"- {line}")
    st.markdown("### 健康体质")
    for line in health_lines(es):
        st.write(f"- {line}")

with tab6:
    st.header("命盘依据")
    st.caption("给懂命理的人复核用，普通用户可不看。")
    st.subheader("四柱与十神")
    st.dataframe(pd.DataFrame(bazi["rows"]), use_container_width=True, hide_index=True)
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("五行得分")
        st.dataframe(pd.DataFrame([{"五行": k, "得分": v} for k, v in es.items()]), hide_index=True)
    with c2:
        st.subheader("十神得分")
        st.dataframe(pd.DataFrame([{"十神": k, "得分": v, "关系": GOD_TO_RELATION[k]} for k, v in ts.items()]).sort_values("得分", ascending=False), hide_index=True)
    st.subheader("大运")
    st.dataframe(pd.DataFrame(dys), use_container_width=True, hide_index=True)
    st.subheader("未来十年")
    future_df = pd.DataFrame([{"年份": x["年份"], "年龄": x["年龄"], "流年": x["流年"], "大运": x["大运"], "倾向": x["倾向"], "主题": "；".join(x["主题"]), "依据": "；".join(x["依据"])} for x in future_rows])
    st.dataframe(future_df, use_container_width=True, hide_index=True)

    report = {
        "姓名": name, "性别": gender,
        "输入时间": local_dt.strftime("%Y-%m-%d %H:%M"),
        "排盘时间": chart_dt.strftime("%Y-%m-%d %H:%M"),
        "出生地址": address,
        "四柱": bazi["pillars"],
        "日主": bazi["day_stem"],
        "身势": strength,
        "强弱分": strength_score,
        "五行": es, "十神": ts, "关系": rs,
        "喜用": useful, "忌重": avoid,
        "格局": patterns, "大运": dys,
        "十件应事": rep_years,
        "当前流年": cur_signal,
        "当前问题": {"方向": cat, "问题": question, "回答": answer, "可行度": qscore},
        "免责声明": "命理内容为传统文化与象征性分析，不替代法律、医学、投资、职业等专业判断。",
    }
    st.download_button(
        "下载完整命理报告 JSON",
        data=json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8"),
        file_name=f"{name}_命理大师问答详批_V6.json",
        mime="application/json",
    )
