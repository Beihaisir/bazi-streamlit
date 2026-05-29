
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
# 页面
# ============================================================

st.set_page_config(
    page_title="高级八字命理报告 V8",
    page_icon="☯️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# 常量
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
    "子": [("癸", 1.0)], "丑": [("己", 0.6), ("癸", 0.25), ("辛", 0.15)],
    "寅": [("甲", 0.6), ("丙", 0.25), ("戊", 0.15)], "卯": [("乙", 1.0)],
    "辰": [("戊", 0.6), ("乙", 0.25), ("癸", 0.15)], "巳": [("丙", 0.6), ("戊", 0.25), ("庚", 0.15)],
    "午": [("丁", 0.7), ("己", 0.3)], "未": [("己", 0.6), ("丁", 0.25), ("乙", 0.15)],
    "申": [("庚", 0.6), ("壬", 0.25), ("戊", 0.15)], "酉": [("辛", 1.0)],
    "戌": [("戊", 0.6), ("辛", 0.25), ("丁", 0.15)], "亥": [("壬", 0.7), ("甲", 0.3)],
}
ELEMENT_GENERATES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
ELEMENT_CONTROLS = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

TEN_GODS = ["正印", "偏印", "比肩", "劫财", "食神", "伤官", "正财", "偏财", "正官", "七杀"]
GOD_TO_RELATION = {
    "正印": "印", "偏印": "印", "比肩": "比劫", "劫财": "比劫",
    "食神": "食伤", "伤官": "食伤", "正财": "财", "偏财": "财",
    "正官": "官杀", "七杀": "官杀",
}
RELATIONS = ["印", "比劫", "食伤", "财", "官杀"]

RELATION_TEXT = {
    "印": {
        "象": "学习、贵人、长辈、证书、保护、平台、房屋、精神依靠",
        "顺": "适合拿资质、靠平台、做专业积累，贵人和制度能帮你。",
        "逆": "过旺则想多做少，依赖安全感，容易把机会拖成顾虑。",
        "事业": "教育、咨询、研究、医疗、法律、文化、专业服务、大平台岗位。",
        "财": "知识财、资质财、平台财，不宜只求快钱。",
    },
    "比劫": {
        "象": "朋友、同辈、竞争、合伙、团队、人气、行动力",
        "顺": "适合竞争环境、团队作战、社群、销售、创业早期起势。",
        "逆": "过旺则合伙分利、人情消耗、朋友拖累、钱账难清。",
        "事业": "销售团队、社群运营、合伙创业、竞技型行业、线下服务。",
        "财": "人脉财、团队财，但必须先定规则后谈感情。",
    },
    "食伤": {
        "象": "才华、表达、技术、作品、创意、口才、子女、自由",
        "顺": "适合靠技术、内容、产品、表达、作品打开局面。",
        "逆": "过旺则不服管、嘴快、项目太多、与权威冲突。",
        "事业": "内容、自媒体、设计、产品、技术、培训、咨询、销售表达。",
        "财": "技能财、作品财、流量财，先有输出后有财。",
    },
    "财": {
        "象": "钱财、资源、客户、项目、资产、市场、现实关系",
        "顺": "适合经营、商务、项目、客户、资产配置、资源整合。",
        "逆": "过旺则被钱和项目拖住，现金流焦虑，感情也易现实化。",
        "事业": "贸易、销售、投资、商务、供应链、项目制、资产管理。",
        "财": "经营财、项目财、资源财，重合同、现金流和退出机制。",
    },
    "官杀": {
        "象": "规则、职位、权力、领导、压力、考试、责任、风险",
        "顺": "适合管理、组织、风控、体制、法律、工程、责任岗位。",
        "逆": "过旺则压力大、被管束、合同债务官非风险。",
        "事业": "管理、体制、法律、金融风控、安全、工程管理、高压岗位。",
        "财": "权责财、职位财、规则财，越做大越要合规。",
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

MONTH_BRANCH = {1: "寅", 2: "卯", 3: "辰", 4: "巳", 5: "午", 6: "未", 7: "申", 8: "酉", 9: "戌", 10: "亥", 11: "子", 12: "丑"}

DIMENSIONS = ["事业", "财运", "感情", "健康", "人际"]
DIM_GODS = {
    "事业": ["正官", "七杀", "正印", "偏印", "食神", "伤官"],
    "财运": ["正财", "偏财", "食神", "伤官", "比肩", "劫财"],
    "感情": ["正财", "偏财", "正官", "七杀"],
    "健康": ["正印", "偏印", "七杀", "伤官"],
    "人际": ["比肩", "劫财", "食神", "伤官", "正财", "偏财"],
}

# ============================================================
# 工具函数
# ============================================================

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
            geolocator = Nominatim(user_agent="bazi_advanced_v8")
            query = address if re.search(r"中国|China|Taiwan|Hong Kong|Macau", address, re.I) else f"{address}, China"
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
    longitude_correction = (lon - 120.0) * 4.0
    eot = equation_of_time_minutes(int(local_dt.strftime("%j")))
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
    me, other = STEM_ELEMENT[day_stem], STEM_ELEMENT[other_stem]
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
    pillars = {
        "年柱": ec.getYear(),
        "月柱": ec.getMonth(),
        "日柱": ec.getDay(),
        "时柱": ec.getTime(),
    }
    day_stem, day_branch = split_gz(pillars["日柱"])
    rows, hidden = [], []
    for name, gz in pillars.items():
        stem, branch = split_gz(gz)
        tg = "日主" if name == "日柱" else ten_god(day_stem, stem)
        hid = []
        for hs, wt in BRANCH_HIDDEN_STEMS[branch]:
            hg = ten_god(day_stem, hs)
            hid.append(f"{hs}{hg}")
            hidden.append({"柱": name, "地支": branch, "藏干": hs, "十神": hg, "权重": wt})
        rows.append({
            "柱": name,
            "干支": gz,
            "天干": stem,
            "天干五行": STEM_ELEMENT[stem],
            "天干十神": tg,
            "地支": branch,
            "地支五行": BRANCH_ELEMENT[branch],
            "藏干": "、".join(hid),
        })
    return {
        "solar": solar, "lunar": lunar, "eight_char": ec, "pillars": pillars,
        "day_stem": day_stem, "day_branch": day_branch, "rows": rows, "hidden": hidden,
        "lunar_text": lunar.toString(), "lunar_full": lunar.toFullString(),
    }

def element_scores(bazi: Dict) -> Dict[str, float]:
    mb = bazi["rows"][1]["地支"]
    season = SEASON_POWER[mb]
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
    rel = {r: 0.0 for r in RELATIONS}
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
    mb = bazi["rows"][1]["地支"]
    if day_el in [STEM_ELEMENT[x[0]] for x in BRANCH_HIDDEN_STEMS[mb]]:
        score += 10
    score = max(5, min(95, int(round(score))))
    label = "偏强" if score >= 66 else "偏弱" if score <= 42 else "中和"
    return label, score, [
        f"日主属{day_el}，同类得分{es[day_el]}，印星得分{es[mother]}。",
        f"泄秀得分{es[child]}，财星得分{es[wealth]}，官杀压力得分{es[pressure]}。",
        f"月令为{mb}，季节之气已纳入权重。",
    ]

def useful_avoid(strength: str) -> Tuple[List[str], List[str]]:
    if strength == "偏强":
        return ["食神", "伤官", "正财", "偏财", "正官", "七杀"], ["正印", "偏印", "比肩", "劫财"]
    if strength == "偏弱":
        return ["正印", "偏印", "比肩", "劫财"], ["食神", "伤官", "正财", "偏财", "正官", "七杀"]
    return [], []

def detect_patterns(ts: Dict[str, float]) -> List[Dict]:
    def s(names): return sum(ts.get(n, 0) for n in names)
    pats = []
    if s(["食神", "伤官"]) >= 1.2 and s(["正财", "偏财"]) >= 1.0:
        pats.append({"格局": "食伤生财", "成处": "靠才华、技术、表达、产品而得财", "风险": "想法太多，现金流跟不上"})
    if s(["正官", "七杀"]) >= 1.0 and s(["正印", "偏印"]) >= 1.0:
        pats.append({"格局": "官印相生", "成处": "压力能化为资质、职位、名分", "风险": "只守规矩，主动性不足"})
    if s(["正财", "偏财"]) >= 1.0 and s(["正官", "七杀"]) >= 1.0:
        pats.append({"格局": "财生官杀", "成处": "资源、项目可换权责和身份", "风险": "越往上越要守规则"})
    if s(["食神", "伤官"]) >= 1.2 and s(["正官", "七杀"]) >= 1.0:
        pats.append({"格局": "食伤制杀", "成处": "用技术、方案、作品压住压力", "风险": "容易顶撞权威"})
    if s(["比肩", "劫财"]) >= 1.2 and s(["正财", "偏财"]) >= 1.0:
        pats.append({"格局": "比劫夺财", "成处": "人脉、团队牵动资源", "风险": "钱账不明则损耗"})
    if not pats:
        pats.append({"格局": "杂气成局", "成处": "格局不走单线，需看大运引动", "风险": "不能用一个标签断一生"})
    return pats

def get_yun(bazi: Dict, gender: str):
    gender_num = 0 if gender == "女" else 1
    for sect in [1, 2]:
        try:
            return bazi["eight_char"].getYun(gender_num, sect)
        except Exception:
            pass
    return None

def dayun_list(bazi: Dict, gender: str, birth_year: int) -> List[Dict]:
    yun = get_yun(bazi, gender)
    rows = []
    if yun:
        try:
            for dy in yun.getDaYun():
                try:
                    gz, sy, ey, sa, ea = dy.getGanZhi(), dy.getStartYear(), dy.getEndYear(), dy.getStartAge(), dy.getEndAge()
                    if gz and sy:
                        rows.append({"大运": gz, "起始年龄": sa, "结束年龄": ea, "起始年份": sy, "结束年份": ey})
                except Exception:
                    continue
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
    st, br = split_gz(gz)
    gods = [ten_god(day_stem, st)]
    gods.extend([ten_god(day_stem, hs) for hs, _ in BRANCH_HIDDEN_STEMS[br]])
    return gods

def year_signal(bazi, year, dy, useful, avoid, birth_year):
    ygz = year_ganzhi(year)
    gods = gz_gods(bazi["day_stem"], ygz)
    dgz = dy["大运"] if dy else ""
    dgods = gz_gods(bazi["day_stem"], dgz) if dgz else []
    score, evidence, themes = 0, [], []
    branches = [r["地支"] for r in bazi["rows"]]
    yb = ygz[1]
    for g in gods:
        if g in useful: score += 12; evidence.append(f"流年{g}为用")
        if g in avoid: score -= 12; evidence.append(f"流年{g}为忌")
    for g in dgods:
        if g in useful: score += 7; evidence.append(f"大运{g}为助")
        if g in avoid: score -= 7; evidence.append(f"大运{g}为压")
    clash = {"子":"午","午":"子","丑":"未","未":"丑","寅":"申","申":"寅","卯":"酉","酉":"卯","辰":"戌","戌":"辰","巳":"亥","亥":"巳"}
    if clash.get(yb) in branches:
        score += 8; evidence.append("流年冲动原局"); themes.append("变化迁移")
    if yb in branches:
        score += 6; evidence.append("流年伏吟原局"); themes.append("旧题重现")
    rels = [GOD_TO_RELATION.get(g) for g in gods + dgods if g in GOD_TO_RELATION]
    for r in set(rels):
        if r == "印": themes.append("学业证书贵人")
        elif r == "比劫": themes.append("朋友竞争合作")
        elif r == "食伤": themes.append("表达作品技术")
        elif r == "财": themes.append("钱财项目资产")
        elif r == "官杀": themes.append("职位规则压力")
    tone = "顺势年" if score >= 18 else "谨慎年" if score <= -18 else "调整年"
    return {
        "年份": year, "年龄": year - birth_year, "流年": ygz, "大运": dgz, "总分": max(0, min(100, 60 + score)),
        "原始分": score, "倾向": tone, "主题": "、".join(list(dict.fromkeys(themes))[:3]), "依据": "；".join(list(dict.fromkeys(evidence))[:4])
    }

def dimension_scores(bazi, sig, useful, avoid):
    ygods = gz_gods(bazi["day_stem"], sig["流年"])
    dgods = gz_gods(bazi["day_stem"], sig["大运"]) if sig["大运"] else []
    allg = ygods + dgods
    out = {}
    for dim, gods in DIM_GODS.items():
        s = 60
        s += len(set(allg) & set(useful) & set(gods)) * 10
        s -= len(set(allg) & set(avoid) & set(gods)) * 10
        s += int(sig["原始分"] * 0.25)
        out[dim] = max(0, min(100, s))
    return out

def representative_years(bazi, birth_year, now_year, dys, useful, avoid):
    rows = [year_signal(bazi, y, current_dayun(dys, y), useful, avoid, birth_year) for y in range(birth_year, now_year + 1)]
    rows = sorted(rows, key=lambda x: abs(x["原始分"]) + (8 if x["年龄"] in [6,12,15,18,22,24,28,30,36,42,48,54,60] else 0), reverse=True)
    chosen = []
    for r in rows:
        if len(chosen) >= 10: break
        if all(abs(r["年份"] - c["年份"]) >= 2 for c in chosen):
            chosen.append(r)
    return sorted(chosen, key=lambda x: x["年份"])

def shensha(bazi):
    yb, db = bazi["rows"][0]["地支"], bazi["day_branch"]
    branches = [r["地支"] for r in bazi["rows"]]
    groups = {
        "申子辰": {"桃花": "酉", "驿马": "寅", "华盖": "辰"},
        "寅午戌": {"桃花": "卯", "驿马": "申", "华盖": "戌"},
        "巳酉丑": {"桃花": "午", "驿马": "亥", "华盖": "丑"},
        "亥卯未": {"桃花": "子", "驿马": "巳", "华盖": "未"},
    }
    desc = {
        "桃花": "人缘、审美、曝光、情感吸引力；过旺则感情复杂。",
        "驿马": "迁移、奔波、出差、异地发展、换环境。",
        "华盖": "孤高、艺术、宗教哲学、研究、专业深钻。",
        "天乙贵人": "贵人、制度、平台、关键人物帮助。",
    }
    def g_of(b):
        for k, v in groups.items():
            if b in k: return v
        return {}
    result = []
    for base_name, base_branch in [("年支", yb), ("日支", db)]:
        g = g_of(base_branch)
        for star, target in g.items():
            if target in branches:
                result.append({"神煞": star, "依据": f"以{base_name}{base_branch}起，见{target}", "解释": desc[star]})
    day_stem = bazi["day_stem"]
    tianyi = {
        "甲": ["丑", "未"], "戊": ["丑", "未"], "庚": ["丑", "未"],
        "乙": ["子", "申"], "己": ["子", "申"],
        "丙": ["亥", "酉"], "丁": ["亥", "酉"],
        "壬": ["卯", "巳"], "癸": ["卯", "巳"], "辛": ["寅", "午"],
    }.get(day_stem, [])
    for b in tianyi:
        if b in branches:
            result.append({"神煞": "天乙贵人", "依据": f"日干{day_stem}见{b}", "解释": desc["天乙贵人"]})
    return result

def nine_palace(year):
    # 简化年飞星：2004年五黄入中，逆飞
    center = ((5 - (year - 2004)) - 1) % 9 + 1
    palace_names = ["中宫", "西北", "西", "东北", "南", "北", "西南", "东", "东南"]
    stars = [((center + i - 1) % 9) + 1 for i in range(9)]
    meaning = {
        1:"人缘、智慧、学习", 2:"病符、脾胃、保守", 3:"口舌、竞争、冲突",
        4:"文昌、桃花、创作", 5:"五黄、压力、意外", 6:"权力、贵人、规则",
        7:"破耗、口舌、金融", 8:"财库、稳定、房产", 9:"喜庆、名气、火旺",
    }
    return [{"宫位": p, "飞星": s, "取象": meaning[s]} for p, s in zip(palace_names, stars)]

def month_calendar(bazi, year, useful, avoid):
    rows = []
    for m in range(1, 13):
        mb = MONTH_BRANCH[m]
        gods = []
        for hs, _ in BRANCH_HIDDEN_STEMS[mb]:
            gods.append(ten_god(bazi["day_stem"], hs))
        score = 60 + len(set(gods) & set(useful)) * 10 - len(set(gods) & set(avoid)) * 10
        if score >= 70:
            action = "适合推进、拜访、发布、谈合作"
        elif score <= 50:
            action = "宜保守、复盘、控风险、少重仓"
        else:
            action = "适合准备、试点、修正方案"
        rows.append({"月份": f"{year}-{m:02d}", "月支": mb, "引动十神": "、".join(gods), "行动评分": max(0, min(100, score)), "行动建议": action})
    return rows

def master_summary(bazi, strength, score, rs, patterns):
    top = max(rs.items(), key=lambda x: x[1])[0]
    pat = patterns[0]["格局"]
    day = bazi["day_stem"]
    el = STEM_ELEMENT[day]
    return (
        f"此造日主为「{day}{el}」，身势判为「{strength}」，强弱分约 {score}/100。"
        f"命局主线落在「{top}」，取象为：{RELATION_TEXT[top]['象']}。"
        f"局中较明显的结构是「{pat}」，说明机会多半不是凭空来的，而是由能力、资源、规则或关系转化出来。"
        f"看此命，不能只问吉凶，要看何处能成事、何处会破局。"
    )

def personality_text(strength, rs):
    top = max(rs.items(), key=lambda x: x[1])[0]
    if strength == "偏强":
        base = "主观能量足，不喜被牵着走，遇事有自己的判断和坚持。"
    elif strength == "偏弱":
        base = "环境感受强，外界压力和资源对你影响很大，适合借力成事。"
    else:
        base = "适应力较强，但最怕方向摇摆，路径一乱就容易消耗优势。"
    return f"{base} 命局「{top}」重，因此性格中会反复出现{RELATION_TEXT[top]['象']}这些主题。顺则{RELATION_TEXT[top]['顺']}逆则{RELATION_TEXT[top]['逆']}"

def career_text(patterns, rs):
    top = max(rs.items(), key=lambda x: x[1])[0]
    parts = [f"事业主线宜围绕「{top}」展开：{RELATION_TEXT[top]['事业']}"]
    for p in patterns[:3]:
        parts.append(f"{p['格局']}：成处在于{p['成处']}；风险在于{p['风险']}。")
    return "\n\n".join(parts)

def wealth_text(ts, useful, avoid):
    wealth = ts["正财"] + ts["偏财"]
    output = ts["食神"] + ts["伤官"]
    bi = ts["比肩"] + ts["劫财"]
    lines = []
    lines.append("财星不弱，一生绕不开钱、资源、客户、项目和资产配置。" if wealth >= 1.6 else "财星不是最重，求财要靠能力、平台或长期积累转化。")
    if output >= 1.2: lines.append("食伤有气，钱宜从技术、表达、产品、服务、内容中来。")
    if bi >= 1.2: lines.append("比劫牵财，朋友、合伙、熟人项目必须钱账分明。")
    if set(["正财","偏财"]) & set(avoid): lines.append("财为风险时，忌借贷投资、替人担保、重仓高收益项目。")
    return "\n\n".join(lines)

def relationship_text(bazi, gender, avoid):
    db = bazi["day_branch"]
    hidden_gods = [ten_god(bazi["day_stem"], hs) for hs, _ in BRANCH_HIDDEN_STEMS[db]]
    base = f"感情看日支，此命日支坐「{db}」，内里带「{'、'.join(hidden_gods)}」之象。"
    if gender == "男":
        bad = bool(set(["正财","偏财"]) & set(avoid))
        extra = "男命传统以财星看伴侣与现实关系议题。"
    elif gender == "女":
        bad = bool(set(["正官","七杀"]) & set(avoid))
        extra = "女命传统以官杀看伴侣与关系责任议题。"
    else:
        bad = bool(set(["正财","偏财","正官","七杀"]) & set(avoid))
        extra = "不限定性别时，重点看日支、财官、边界与责任。"
    end = "关系里要防控制、现实压力、经济绑定和责任不对等。" if bad else "适合寻找能共同承担现实、又不压制你发展路径的人。"
    return f"{base}\n\n{extra}{end}"

def health_text(es):
    weak = min(es.items(), key=lambda x: x[1])[0]
    strong = max(es.items(), key=lambda x: x[1])[0]
    body = {"木":"肝胆、筋膜、情绪疏泄","火":"心火、睡眠、血压、神经兴奋","土":"脾胃、消化、代谢、湿气","金":"肺、皮肤、呼吸道、边界感","水":"肾、泌尿、生殖、精力储备"}
    return f"五行偏弱在「{weak}」，宜关注{body[weak]}。五行偏旺在「{strong}」，压力大时也容易在{body[strong]}上过载。健康内容仅作体质倾向提醒，不能替代医疗。"



# ============================================================
# V8：细致人话版解读引擎
# ============================================================

def strength_plain_language(strength, strength_score):
    if strength == "偏强":
        return (
            "你的日主偏强，可以理解为“自我发动机比较足”。这种人不怕做事，怕的是太相信自己的判断，"
            "容易在不知不觉中把事情扛到自己身上。好处是抗压、主动、有主见；坏处是固执、硬撑、听不进提醒。"
            f"强弱分约 {strength_score}/100，说明不是轻微偏强，而是做决策时确实要防“我觉得可以，所以就冲”的惯性。"
        )
    if strength == "偏弱":
        return (
            "你的日主偏弱，不是说人弱，而是说人生很多大事不能靠硬扛。你更适合借平台、借团队、借贵人、借制度成事。"
            "这类命最怕一个人孤军深入，尤其是钱、责任、压力同时压上来的时候，很容易心累、睡不好、判断变形。"
            f"强弱分约 {strength_score}/100，说明做大事之前，必须先看资源、后盾、现金流和身体承受力。"
        )
    return (
        "你的日主中和，适应力不错，既不是完全靠别人，也不是只能靠自己。"
        "这种命的关键不是“有没有能力”，而是“方向能不能定住”。方向对了，优势能顺着走；方向反复，就会把精力耗散。"
        f"强弱分约 {strength_score}/100，说明不要用极端方式做事，最适合走稳中带进、边做边校准的路线。"
    )

def relation_plain_language(rel):
    data = RELATION_TEXT[rel]
    return (
        f"命局里「{rel}」最重。讲人话就是，你人生最常被牵动的主题是：{data['象']}。"
        f"这个东西用得好，就是你的优势：{data['顺']} "
        f"用不好，就会变成反复踩坑的地方：{data['逆']} "
        "所以不要简单理解成吉或凶，它更像你人生里的主考题。考得好，它给你分；处理不好，它反复让你补课。"
    )

def detailed_overview_text(bazi, strength, strength_score, rs, patterns, useful, avoid):
    top = max(rs.items(), key=lambda x: x[1])[0]
    second = sorted(rs.items(), key=lambda x: x[1], reverse=True)[1][0]
    pat = patterns[0]
    day = bazi["day_stem"]
    el = STEM_ELEMENT[day]
    month_branch = bazi["rows"][1]["地支"]

    return f"""
### 1）先给总断

此命日主是 **{day}{el}**，出生月令落在 **{month_branch}**，系统判断身势为 **{strength}**。

{strength_plain_language(strength, strength_score)}

### 2）你的命局主线

{relation_plain_language(top)}

第二重的主题是 **{second}**，也就是：{RELATION_TEXT[second]['象']}。  
这说明你的人生不是单线条，不是只靠某一种东西成功，而是经常要在两个主题之间切换：一边处理 **{top}**，一边又被 **{second}** 牵动。

### 3）最明显的格局/能力链条

系统识别到最明显的结构是 **{pat['格局']}**。  
它的成处是：**{pat['成处']}**。  
它的风险是：**{pat['风险']}**。

讲人话就是：你不是没有机会，但机会通常不是直接掉下来，而是要经过一层“转化”。  
比如把能力转成作品，把作品转成客户，把客户转成收入；或者把压力转成资质，把资质转成位置。

### 4）喜用和风险

- **比较能帮你的力量**：{('、'.join(useful) if useful else '需要结合过往年份继续校准')}
- **比较容易让你吃亏的力量**：{('、'.join(avoid) if avoid else '需要结合过往年份继续校准')}

这里要特别注意：喜用不是“越多越好”，忌神也不是“完全不能碰”。  
真正的判断是：某个力量来了之后，你能不能承接、能不能转化、会不会过载。
"""

def detailed_personality_text(strength, rs, bazi):
    top = max(rs.items(), key=lambda x: x[1])[0]
    second = sorted(rs.items(), key=lambda x: x[1], reverse=True)[1][0]
    day_branch = bazi["day_branch"]

    if strength == "偏强":
        decision_style = (
            "你做决定时，通常不是完全没主见的人。相反，你内心有一套自己的判断。"
            "别人越催你、压你，你越容易本能地抗拒。"
            "这会让你在关键时刻有冲劲，但也容易因为太相信自己的判断而错过别人的提醒。"
        )
        emotional_style = (
            "情绪上你不一定外露，但内在不服输。真正让你难受的，往往不是辛苦，而是被人否定、被人控制、被人看轻。"
        )
    elif strength == "偏弱":
        decision_style = (
            "你做决定时很容易受环境影响。别人一句话、一个机会、一个压力，都会让你反复权衡。"
            "这不是坏事，说明你感知力强，但如果没有稳定的判断标准，就容易被外界牵着走。"
        )
        emotional_style = (
            "情绪上你容易累在心里。你未必会立刻爆发，但压力会慢慢积累，最后变成睡眠、胃口、焦虑或拖延。"
        )
    else:
        decision_style = (
            "你的判断方式比较看场景。环境顺的时候，你可以推进得很快；环境乱的时候，你也容易犹豫。"
            "所以你最需要的不是鸡血，而是清晰的阶段目标。"
        )
        emotional_style = (
            "情绪上你不是单纯外放或内收，而是容易跟现实处境绑定。事情有进展，你状态就起；事情卡住，你就容易耗。"
        )

    return f"""
### 1）性格底色

{decision_style}

### 2）情绪和内在驱动力

{emotional_style}

### 3）命局里最重的性格主题

你命里 **{top}** 重。讲人话就是：{RELATION_TEXT[top]['象']} 这些事情，会经常影响你的情绪、选择和人生节奏。  
它的好处是：{RELATION_TEXT[top]['顺']}  
它的坏处是：{RELATION_TEXT[top]['逆']}

### 4）别人眼中的你 vs 你心里的你

第二重主题是 **{second}**。所以别人看到的你，和你内心真正焦虑的点，可能不是完全一样。  
外面看你可能是在处理 **{top}** 的问题，但你心里真正反复想的，常常还牵涉 **{second}**。

### 5）日支看亲密感和身体感

你的日支是 **{day_branch}**。日支代表内在落点、亲密关系和身体感受。  
这说明你真正放松下来之后，最在意的不是表面热闹，而是能不能稳定、能不能安心、能不能在关系里不被消耗。
"""

def detailed_career_text(patterns, rs, useful, avoid):
    top = max(rs.items(), key=lambda x: x[1])[0]
    lines = [f"""
### 1）事业总方向

事业不能只看“喜欢什么”，还要看命局里什么东西能形成闭环。  
你的事业主线落在 **{top}**，适合围绕这些方向发力：**{RELATION_TEXT[top]['事业']}**。

讲人话就是：你不是随便找一份工作就能长期舒服的人。你需要让工作和自己的命局主线接上。  
接上了，工作会变成平台、资源和成就；接不上，就会变成消耗、压抑和反复换方向。
"""]

    for p in patterns:
        lines.append(f"""
### {p['格局']}

这个结构的成处是：**{p['成处']}**。  
现实里表现为：你适合把某种能力、资源、压力或关系进行转化，而不是停留在原地。

风险是：**{p['风险']}**。  
所以你不能只看到机会，也要看到机会背后的代价。  
如果这个结构用得好，会变成你的事业抓手；用不好，就会变成反复卡住你的地方。
""")

    if set(["正印", "偏印"]) & set(useful):
        lines.append("""
### 适合的事业策略：先拿凭证，再放大

你的命局需要印来扶，说明学习、资质、平台、贵人、专业背书对你很重要。  
你不适合完全野路子硬冲。先拿到资格、方法、案例、背书，再去扩大，会比单纯拼胆子稳得多。
""")
    if set(["食神", "伤官"]) & set(useful):
        lines.append("""
### 适合的事业策略：靠作品说话

食伤为用，说明你要有输出。  
不要只停在“我会”“我懂”，而要变成作品、方案、内容、产品、服务、案例。  
一旦你能持续输出，事业机会会比单纯等贵人更可靠。
""")
    if set(["正财", "偏财"]) & set(useful):
        lines.append("""
### 适合的事业策略：把能力接到市场

财为用时，客户、资源、项目、现金流非常关键。  
你不能只做清高的事，也不能只埋头干活。要学会报价、谈合作、管理成本、经营客户。
""")

    if set(["比肩", "劫财"]) & set(avoid):
        lines.append("""
### 事业避坑：熟人合作要谨慎

比劫为忌时，最怕朋友、同事、合伙人把你的资源分走，或者人情关系让你不好拒绝。  
合作不是不能做，但必须先讲规则：谁出钱、谁出力、谁负责、怎么分钱、怎么退出。
""")
    if set(["正官", "七杀"]) & set(avoid):
        lines.append("""
### 事业避坑：不要被压力推着走

官杀为忌时，职位、领导、规则、KPI、合同、责任都可能带来压力。  
越是高压环境，越要看边界。不是所有“看起来更高级”的机会都适合你。
""")

    return "\n".join(lines)

def detailed_wealth_text(ts, useful, avoid, rs):
    wealth = ts["正财"] + ts["偏财"]
    output = ts["食神"] + ts["伤官"]
    bi = ts["比肩"] + ts["劫财"]
    top = max(rs.items(), key=lambda x: x[1])[0]

    text = f"""
### 1）你的财运不是一句“有财没财”能说完

你的财星得分约为 **{round(wealth, 2)}**。  
这个数字不是直接等于钱多少，而是说明“钱、资源、客户、项目、资产”这些主题在命局里有多明显。

财运真正要看三件事：

1. 你有没有机会接触钱；
2. 你有没有能力承接钱；
3. 钱来了之后，是帮你，还是拖累你。

### 2）你的赚钱方式

命局主线在 **{top}**，所以你的财路也会受它影响。  
{RELATION_TEXT[top]['财']}
"""

    if output >= 1.2:
        text += """
你命里食伤不弱，说明钱比较适合从 **技术、表达、内容、产品、服务、方案** 中来。  
换句话说，先有可交付的东西，再有钱。  
如果没有作品、没有服务、没有可复制的方法，只想直接追钱，反而容易焦虑。
"""
    if wealth >= 1.6:
        text += """
财星本身不弱，代表你一生不会完全绕开钱和资源。  
你会遇到项目、客户、合作、资产配置、现实利益分配这些事情。  
好处是有机会，坏处是容易被钱牵着走。
"""
    else:
        text += """
财星不是最重，说明你不适合只靠追风口发财。  
更稳的方式是先建立能力、资质、平台、人脉，再让钱自然流进来。
"""
    if bi >= 1.2:
        text += """
比劫也有力量，钱财上要特别注意“人”的问题。  
朋友介绍的项目、熟人合作、亲戚借钱、合伙分账，都要慎重。  
你不是不能合作，而是不能糊涂合作。
"""
    if set(["正财", "偏财"]) & set(avoid):
        text += """
### 3）财运最大风险

财星在你的风险位时，越想快赚，越容易快失。  
尤其要避开：借钱投资、替人担保、高杠杆、看不懂的项目、只听别人说很赚钱的机会。  
你要记住：你能赚认知以内的钱，认知以外的钱多半会以学费形式还回去。
"""
    else:
        text += """
### 3）财运建议

财如果能为用，就要重视长期经营。  
少赌一次暴富，多做稳定复利：客户复购、技能升级、资产配置、现金流管理，都会比冲动投机更适合你。
"""
    return text

def detailed_relationship_text(bazi, gender, avoid):
    db = bazi["day_branch"]
    hidden_gods = [ten_god(bazi["day_stem"], hs) for hs, _ in BRANCH_HIDDEN_STEMS[db]]

    if gender == "男":
        lens = "男命传统以财星看伴侣与现实关系议题，但现代不能只看妻财，还要看日支、边界、责任和现实承压能力。"
        bad = bool(set(["正财", "偏财"]) & set(avoid))
    elif gender == "女":
        lens = "女命传统以官杀看伴侣与关系责任，但现代不能只看夫星，还要看自我边界、日支稳定度和现实选择。"
        bad = bool(set(["正官", "七杀"]) & set(avoid))
    else:
        lens = "不限定性别时，感情重点看日支、财官互动、边界感和责任分配。"
        bad = bool(set(["正财", "偏财", "正官", "七杀"]) & set(avoid))

    risk = (
        "你的关系里要特别防现实压力、控制感、经济绑定、责任不对等。喜欢不是问题，真正的问题是这段关系会不会长期消耗你。"
        if bad else
        "你的关系不怕现实，怕的是双方不能共同成长。适合找能一起承担现实、又不压制你发展路径的人。"
    )

    return f"""
### 1）感情底层模式

你的日支是 **{db}**，日支是亲密关系的落点，也代表你真正放松之后的状态。  
日支藏干带有 **{'、'.join(hidden_gods)}** 的味道，这会影响你在关系里的安全感、表达方式和现实选择。

### 2）伴侣与关系议题

{lens}

### 3）你在感情里真正需要什么

你需要的不是表面热闹，而是关系能不能让你心定。  
如果一段关系让你长期内耗、反复猜、反复证明自己，那就算有吸引力，也未必是好关系。

### 4）感情风险

{risk}

### 5）建议

感情里不要只看感觉，要看三件事：

1. 对方是否让你更稳定；
2. 双方是否能共同承担现实；
3. 这段关系是否支持你的事业和身心状态。

能做到这三点，就是能走长线的关系。
"""

def detailed_health_text(es, strength):
    weak = min(es.items(), key=lambda x: x[1])[0]
    strong = max(es.items(), key=lambda x: x[1])[0]
    body = {
        "木": "肝胆、筋膜、眼睛、情绪疏泄",
        "火": "心火、睡眠、血压、神经兴奋、焦躁感",
        "土": "脾胃、消化、代谢、湿气、稳定感",
        "金": "肺、皮肤、呼吸道、鼻咽、边界感",
        "水": "肾、泌尿、生殖、精力储备、恐惧感",
    }

    if strength == "偏强":
        style = "身偏强的人，最怕长期硬撑。你未必一开始就觉得累，但一旦过载，往往是突然垮下来。"
    elif strength == "偏弱":
        style = "身偏弱的人，身体很容易替你承受压力。心里不说，身体会先有反应。"
    else:
        style = "身势中和的人，健康重点在节奏。节奏稳，状态就稳；节奏乱，身体就容易跟着乱。"

    return f"""
### 1）体质总论

{style}

### 2）偏弱五行

五行里相对偏弱的是 **{weak}**，建议留心：{body[weak]}。  
偏弱不是一定生病，而是说这一类系统更需要保养，压力大、睡眠差、饮食乱的时候更容易先出反应。

### 3）偏旺五行

五行里相对偏旺的是 **{strong}**，建议留心：{body[strong]}。  
旺的地方代表能量足，也代表容易过载。比如某个系统平时很能扛，但长期扛太多，也会成为问题。

### 4）生活建议

- 不要长期熬夜透支；
- 不要用情绪硬扛压力；
- 饮食、睡眠、运动要比临时补救更重要；
- 每年做基础体检；
- 有具体症状时，一定以正规医疗为准。

命理只能提醒体质倾向，不能替代医学诊断。
"""

def detailed_master_advice(top, useful, avoid, strength):
    if strength == "偏强":
        main = "你的人生策略不是继续硬冲，而是学会泄、学会转化、学会让规则和结果帮你说话。"
    elif strength == "偏弱":
        main = "你的人生策略不是单打独斗，而是先找支点。平台、贵人、团队、资质，都是你成事的杠杆。"
    else:
        main = "你的人生策略是稳住方向，不要频繁改赛道。中和之命最吃路径，一旦路径顺，发展会比较稳。"

    return f"""
### 1）总建议

{main}

### 2）围绕命局主线用力

你的主线在 **{top}**。  
成处：{RELATION_TEXT[top]['顺']}  
忌处：{RELATION_TEXT[top]['逆']}

所以你要做的不是逃开这个主题，而是把它用顺。  
它是你的题，也是你的路。

### 3）做决定的顺序

以后遇到重大决策，不要只问“我想不想”，要按这个顺序看：

1. 这件事是否符合我的长期主线？
2. 现在的大运流年是否支持？
3. 我有没有资源、现金流、身体和人手承接？
4. 最坏结果我能不能承担？
5. 有没有退出机制？

### 4）喜用与风险

- 喜用：{('、'.join(useful) if useful else '需要结合过往年份校准')}
- 风险：{('、'.join(avoid) if avoid else '需要结合过往年份校准')}

喜用来了要抓住，但不能贪；风险来了要谨慎，但不是完全逃避。  
真正的趋利避害，是知道什么时候进，什么时候退，什么时候等。
"""

def detailed_dayun_text(d, bazi, useful, avoid, birth_year):
    start_year = int(d["起始年份"]) if d.get("起始年份") else birth_year
    sig = year_signal(bazi, start_year, d, useful, avoid, birth_year)
    return (
        f"**{d['大运']}大运（约{d['起始年龄']}–{d['结束年龄']}岁，{d['起始年份']}–{d['结束年份']}年）**\n\n"
        f"这步运的主题偏向：{sig['主题'] or '阶段转换'}。"
        f"倾向为：{sig['倾向']}。依据：{sig['依据'] or '大运与原局互动平稳'}。\n\n"
        f"讲人话：这十年不是单看好坏，而是看它把你命里的哪类问题放大。"
        f"如果放大的是喜用，就容易出成绩；如果放大的是风险，就要学会收缩、修正和避坑。"
    )

def detailed_year_text(target_year, target_sig, dim):
    sorted_dims = sorted(dim.items(), key=lambda x: x[1], reverse=True)
    best = sorted_dims[0]
    worst = sorted_dims[-1]
    return f"""
### {target_year} 年总断

这一年是 **{target_sig['倾向']}**，总分约 **{target_sig['总分']}/100**。  
主题是：**{target_sig['主题'] or '阶段调整'}**。  
命理依据：{target_sig['依据'] or '流年与原局互动较平'}。

### 五维强弱

今年最有机会的维度是 **{best[0]}（{best[1]}分）**。  
这代表这一块可以主动一点，但仍要看现实条件是否配合。

今年最需要谨慎的维度是 **{worst[0]}（{worst[1]}分）**。  
这一块不宜冲动，不宜赌，不宜在情绪上头时做重大决定。

### 行动原则

- 分数高的维度：可以推进，但要设边界；
- 分数中等的维度：适合试点、观察、修正；
- 分数低的维度：宜保守，先补条件，不要硬冲。
"""

def detailed_month_advice(row):
    score = row["行动评分"]
    if score >= 70:
        return f"{row['月份']}：这个月适合主动推进。可以谈合作、发布作品、拜访客户、启动计划。但分数高不代表可以鲁莽，仍要留好合同和边界。"
    if score <= 50:
        return f"{row['月份']}：这个月宜收不宜放。适合复盘、修正、做准备、控风险，不建议重仓投入或情绪化决策。"
    return f"{row['月份']}：这个月适合试点。可以小范围尝试、收集反馈、调整方案，不宜一步到位。"


# ============================================================
# 输入
# ============================================================

st.title("☯️ 高级八字命理报告 V8")
st.caption("对标完整高级报告：排盘、五行、神煞、性格、事业、财运、情感、健康、大师建议、大运周期、未来十年、流年五维、九宫飞星、12个月行动日历。")

if not LUNAR_AVAILABLE:
    st.error("缺少 lunar-python，请先安装：pip install lunar-python")
    st.stop()

with st.sidebar:
    st.header("生成高级报告")
    name = st.text_input("姓名/代号", "测试用户")
    gender = st.selectbox("性别", ["男", "女", "其他/不指定"], 0)
    year = st.number_input("出生年", 1600, 2200, 1990)
    month = st.number_input("出生月", 1, 12, 1)
    day = st.number_input("出生日", 1, 31, 1)
    hour = st.number_input("出生时", 0, 23, 8)
    minute = st.number_input("出生分", 0, 59, 0)
    address = st.text_input("出生地址", "中国 贵州 贵阳")
    use_true_solar = st.checkbox("自动换算真太阳时", True)
    target_year = st.number_input("重点查看年份", min_value=1900, max_value=2200, value=CURRENT_YEAR)
    generate = st.button("生成高级报告", type="primary")

try:
    local_dt = datetime(int(year), int(month), int(day), int(hour), int(minute), 0)
except ValueError as e:
    st.error(f"出生日期无效：{e}")
    st.stop()

geo = geocode_address(address)
lon = geo["lon"] if geo else 120.0
chart_dt, solar_corr = true_solar_time(local_dt, lon) if use_true_solar else (local_dt, {"经度修正分钟":0, "均时差分钟":0, "总修正分钟":0})

bazi = build_bazi(chart_dt)
es = element_scores(bazi)
ts = ten_scores(bazi)
rs = relation_scores(ts)
strength, strength_score, strength_reason = day_strength(bazi, es)
useful, avoid = useful_avoid(strength)
patterns = detect_patterns(ts)
dys = dayun_list(bazi, gender, int(year))
cur_dy = current_dayun(dys, CURRENT_YEAR)
target_dy = current_dayun(dys, int(target_year))
target_sig = year_signal(bazi, int(target_year), target_dy, useful, avoid, int(year))
rep_years = representative_years(bazi, int(year), CURRENT_YEAR, dys, useful, avoid)
future = [year_signal(bazi, y, current_dayun(dys, y), useful, avoid, int(year)) for y in range(CURRENT_YEAR, CURRENT_YEAR + 10)]
future_df = pd.DataFrame([{**x, **dimension_scores(bazi, x, useful, avoid)} for x in future])
shen = shensha(bazi)
palace = nine_palace(int(target_year))
calendar = month_calendar(bazi, int(target_year), useful, avoid)

# ============================================================
# 顶部
# ============================================================

m1, m2, m3, m4 = st.columns(4)
m1.metric("四柱", f"{bazi['pillars']['年柱']} {bazi['pillars']['月柱']} {bazi['pillars']['日柱']} {bazi['pillars']['时柱']}")
m2.metric("日主", f"{bazi['day_stem']}{STEM_ELEMENT[bazi['day_stem']]}")
m3.metric("身势", f"{strength} {strength_score}/100")
m4.metric("当前大运", cur_dy["大运"] if cur_dy else "未识别")
st.caption(f"排盘时间：{chart_dt.strftime('%Y-%m-%d %H:%M')}。出生地址经纬度仅后台用于真太阳时换算，前台不展示。")

tabs = st.tabs([
    "总览", "命盘排盘", "五行十神", "神煞详解", "性格", "事业", "财运", "情感", "健康",
    "大师建议", "大运周期", "未来十年", "流年五维", "九宫飞星", "12个月行动日历", "导出"
])

with tabs[0]:
    st.header("高级报告总览")
    st.success(master_summary(bazi, strength, strength_score, rs, patterns))
    st.markdown(detailed_overview_text(bazi, strength, strength_score, rs, patterns, useful, avoid))
    c1, c2, c3 = st.columns(3)
    c1.metric("年度总分", target_sig["总分"])
    c2.metric("年度倾向", target_sig["倾向"])
    c3.metric("重点年份", int(target_year))
    st.subheader("出生至今十件代表性应事")
    for i, x in enumerate(rep_years, 1):
        st.write(f"{i}. **{x['年份']}年，约{x['年龄']}岁，{x['倾向']}**：{x['主题']}。依据：{x['依据']}")

with tabs[1]:
    st.header("基础八字排盘")
    st.dataframe(pd.DataFrame(bazi["rows"]), use_container_width=True, hide_index=True)
    st.write(f"农历：{bazi['lunar_text']}")
    st.write(f"真太阳时修正：{solar_corr}")

with tabs[2]:
    st.header("五行分析图表与十神分布")
    c1, c2 = st.columns(2)
    with c1:
        elem_df = pd.DataFrame([{"五行": k, "得分": v} for k, v in es.items()])
        st.bar_chart(elem_df.set_index("五行"))
        st.dataframe(elem_df, hide_index=True, use_container_width=True)
    with c2:
        ten_df = pd.DataFrame([{"十神": k, "得分": v, "关系": GOD_TO_RELATION[k]} for k, v in ts.items()]).sort_values("得分", ascending=False)
        st.bar_chart(ten_df.set_index("十神")["得分"])
        st.dataframe(ten_df, hide_index=True, use_container_width=True)

with tabs[3]:
    st.header("神煞详解")
    if shen:
        st.dataframe(pd.DataFrame(shen), hide_index=True, use_container_width=True)
    else:
        st.info("未见本系统简表中的明显神煞。")

with tabs[4]:
    st.header("性格分析完整版")
    st.markdown(detailed_personality_text(strength, rs, bazi))
    st.write("日主强弱依据：")
    for r in strength_reason:
        st.write(f"- {r}")

with tabs[5]:
    st.header("事业分析完整版")
    st.markdown(detailed_career_text(patterns, rs, useful, avoid))

with tabs[6]:
    st.header("财运分析完整版")
    st.markdown(detailed_wealth_text(ts, useful, avoid, rs))

with tabs[7]:
    st.header("情感分析完整版")
    st.markdown(detailed_relationship_text(bazi, gender, avoid))

with tabs[8]:
    st.header("健康分析完整版")
    st.markdown(detailed_health_text(es, strength))

with tabs[9]:
    st.header("大师建议完整版")
    top = max(rs.items(), key=lambda x: x[1])[0]
    st.markdown(detailed_master_advice(top, useful, avoid, strength))

with tabs[10]:
    st.header("人生大运周期解读")
    st.dataframe(pd.DataFrame(dys), hide_index=True, use_container_width=True)
    for d in dys:
        if d.get("起始年份"):
            sig_mid = year_signal(bazi, int(d["起始年份"]), d, useful, avoid, int(year))
            st.markdown(detailed_dayun_text(d, bazi, useful, avoid, int(year)))

with tabs[11]:
    st.header("未来十年运势图表")
    chart_df = future_df[["年份", "总分", "事业", "财运", "感情", "健康", "人际"]].set_index("年份")
    st.line_chart(chart_df)
    st.dataframe(future_df[["年份","年龄","流年","大运","总分","倾向","主题","依据"]], hide_index=True, use_container_width=True)

with tabs[12]:
    st.header(f"{int(target_year)}年流年详批（5维度）")
    dim = dimension_scores(bazi, target_sig, useful, avoid)
    c1, c2, c3, c4, c5 = st.columns(5)
    for col, d in zip([c1,c2,c3,c4,c5], DIMENSIONS):
        col.metric(d, dim[d])
    st.markdown(detailed_year_text(int(target_year), target_sig, dim))
    st.dataframe(pd.DataFrame([{"维度": k, "评分": v, "建议": "宜主动推进" if v>=70 else "宜保守控险" if v<=50 else "宜试点观察"} for k,v in dim.items()]), hide_index=True, use_container_width=True)

with tabs[13]:
    st.header(f"{int(target_year)}年九宫飞星风水布局")
    st.caption("此为简化年飞星参考，用于空间和生活习惯提示。")
    st.dataframe(pd.DataFrame(palace), hide_index=True, use_container_width=True)

with tabs[14]:
    st.header(f"{int(target_year)}年12个月行动日历")
    cal_df = pd.DataFrame(calendar)
    st.dataframe(cal_df, hide_index=True, use_container_width=True)
    st.subheader("逐月人话建议")
    for _, row in cal_df.iterrows():
        st.write("- " + detailed_month_advice(row))

with tabs[15]:
    st.header("导出高级报告")
    report = {
        "姓名": name, "性别": gender, "输入时间": local_dt.strftime("%Y-%m-%d %H:%M"),
        "排盘时间": chart_dt.strftime("%Y-%m-%d %H:%M"), "出生地址": address,
        "四柱": bazi["pillars"], "日主": bazi["day_stem"], "身势": strength,
        "强弱分": strength_score, "五行": es, "十神": ts, "关系": rs,
        "喜用": useful, "忌重": avoid, "格局": patterns, "神煞": shen,
        "大运": dys, "出生至今十件应事": rep_years, "未来十年": future,
        "流年五维": {"年份": int(target_year), "总断": target_sig, "五维": dimension_scores(bazi, target_sig, useful, avoid)},
        "九宫飞星": palace, "12个月行动日历": calendar,
        "免责声明": "本报告为传统命理与象征性分析，不替代法律、医学、投资、职业等专业判断。",
    }
    st.download_button("下载 JSON 高级报告", json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8"), f"{name}_高级八字报告_V7.json", "application/json")
