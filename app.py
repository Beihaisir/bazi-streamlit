
import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st

try:
    from lunar_python import Solar
    LUNAR_AVAILABLE = True
except Exception:
    Solar = None
    LUNAR_AVAILABLE = False

st.set_page_config(page_title="八字趋利避害决策系统 V3", page_icon="☯️", layout="wide")

# ============================================================
# 基础命理表
# ============================================================

HEAVENLY_STEMS = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
EARTHLY_BRANCHES = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
GANZHI60 = [HEAVENLY_STEMS[i % 10] + EARTHLY_BRANCHES[i % 12] for i in range(60)]

STEM_ELEMENT = {"甲":"木","乙":"木","丙":"火","丁":"火","戊":"土","己":"土","庚":"金","辛":"金","壬":"水","癸":"水"}
STEM_YINYANG = {"甲":"阳","乙":"阴","丙":"阳","丁":"阴","戊":"阳","己":"阴","庚":"阳","辛":"阴","壬":"阳","癸":"阴"}
BRANCH_ELEMENT = {"寅":"木","卯":"木","巳":"火","午":"火","申":"金","酉":"金","亥":"水","子":"水","辰":"土","戌":"土","丑":"土","未":"土"}
BRANCH_YINYANG = {"子":"阳","丑":"阴","寅":"阳","卯":"阴","辰":"阳","巳":"阴","午":"阳","未":"阴","申":"阳","酉":"阴","戌":"阳","亥":"阴"}

BRANCH_HIDDEN_STEMS = {
    "子": [("癸", 1.0)],
    "丑": [("己", 0.6), ("癸", 0.3), ("辛", 0.1)],
    "寅": [("甲", 0.6), ("丙", 0.3), ("戊", 0.1)],
    "卯": [("乙", 1.0)],
    "辰": [("戊", 0.6), ("乙", 0.3), ("癸", 0.1)],
    "巳": [("丙", 0.6), ("戊", 0.3), ("庚", 0.1)],
    "午": [("丁", 0.7), ("己", 0.3)],
    "未": [("己", 0.6), ("丁", 0.3), ("乙", 0.1)],
    "申": [("庚", 0.6), ("壬", 0.3), ("戊", 0.1)],
    "酉": [("辛", 1.0)],
    "戌": [("戊", 0.6), ("辛", 0.3), ("丁", 0.1)],
    "亥": [("壬", 0.7), ("甲", 0.3)],
}

ELEMENT_GENERATES = {"木":"火", "火":"土", "土":"金", "金":"水", "水":"木"}
ELEMENT_CONTROLS = {"木":"土", "土":"水", "水":"火", "火":"金", "金":"木"}

TEN_GODS = ["正印","偏印","比肩","劫财","食神","伤官","正财","偏财","正官","七杀"]
GOD_TO_RELATION = {"正印":"印","偏印":"印","比肩":"比劫","劫财":"比劫","食神":"食伤","伤官":"食伤","正财":"财","偏财":"财","正官":"官杀","七杀":"官杀"}
FIVE_RELATIONS = {"印":["正印","偏印"],"比劫":["比肩","劫财"],"食伤":["食神","伤官"],"财":["正财","偏财"],"官杀":["正官","七杀"]}

# 月令季节权重。用于简化旺衰，不等同于完整调候取用。
SEASON_ELEMENT_POWER = {
    "寅": {"木":1.45,"火":1.10,"土":0.95,"金":0.65,"水":0.85},
    "卯": {"木":1.60,"火":1.10,"土":0.90,"金":0.60,"水":0.80},
    "辰": {"木":1.20,"火":1.00,"土":1.25,"金":0.80,"水":0.90},
    "巳": {"木":0.95,"火":1.55,"土":1.15,"金":0.80,"水":0.55},
    "午": {"木":0.90,"火":1.70,"土":1.20,"金":0.70,"水":0.50},
    "未": {"木":0.85,"火":1.25,"土":1.45,"金":0.85,"水":0.60},
    "申": {"木":0.55,"火":0.70,"土":1.05,"金":1.60,"水":1.10},
    "酉": {"木":0.50,"火":0.65,"土":1.00,"金":1.70,"水":1.05},
    "戌": {"木":0.65,"火":0.85,"土":1.50,"金":1.20,"水":0.70},
    "亥": {"木":1.05,"火":0.55,"土":0.80,"金":0.95,"水":1.55},
    "子": {"木":0.95,"火":0.50,"土":0.75,"金":0.90,"水":1.70},
    "丑": {"木":0.75,"火":0.60,"土":1.45,"金":1.05,"水":1.20},
}

NAYIN = {
    "甲子":"海中金","乙丑":"海中金","丙寅":"炉中火","丁卯":"炉中火","戊辰":"大林木","己巳":"大林木",
    "庚午":"路旁土","辛未":"路旁土","壬申":"剑锋金","癸酉":"剑锋金","甲戌":"山头火","乙亥":"山头火",
    "丙子":"涧下水","丁丑":"涧下水","戊寅":"城头土","己卯":"城头土","庚辰":"白蜡金","辛巳":"白蜡金",
    "壬午":"杨柳木","癸未":"杨柳木","甲申":"泉中水","乙酉":"泉中水","丙戌":"屋上土","丁亥":"屋上土",
    "戊子":"霹雳火","己丑":"霹雳火","庚寅":"松柏木","辛卯":"松柏木","壬辰":"长流水","癸巳":"长流水",
    "甲午":"砂中金","乙未":"砂中金","丙申":"山下火","丁酉":"山下火","戊戌":"平地木","己亥":"平地木",
    "庚子":"壁上土","辛丑":"壁上土","壬寅":"金箔金","癸卯":"金箔金","甲辰":"覆灯火","乙巳":"覆灯火",
    "丙午":"天河水","丁未":"天河水","戊申":"大驿土","己酉":"大驿土","庚戌":"钗钏金","辛亥":"钗钏金",
    "壬子":"桑柘木","癸丑":"桑柘木","甲寅":"大溪水","乙卯":"大溪水","丙辰":"沙中土","丁巳":"沙中土",
    "戊午":"天上火","己未":"天上火","庚申":"石榴木","辛酉":"石榴木","壬戌":"大海水","癸亥":"大海水",
}

# 十二长生：按日干看地支状态。
CHANG_SHENG = {
    "甲": {"亥":"长生","子":"沐浴","丑":"冠带","寅":"临官","卯":"帝旺","辰":"衰","巳":"病","午":"死","未":"墓","申":"绝","酉":"胎","戌":"养"},
    "乙": {"午":"长生","巳":"沐浴","辰":"冠带","卯":"临官","寅":"帝旺","丑":"衰","子":"病","亥":"死","戌":"墓","酉":"绝","申":"胎","未":"养"},
    "丙": {"寅":"长生","卯":"沐浴","辰":"冠带","巳":"临官","午":"帝旺","未":"衰","申":"病","酉":"死","戌":"墓","亥":"绝","子":"胎","丑":"养"},
    "丁": {"酉":"长生","申":"沐浴","未":"冠带","午":"临官","巳":"帝旺","辰":"衰","卯":"病","寅":"死","丑":"墓","子":"绝","亥":"胎","戌":"养"},
    "戊": {"寅":"长生","卯":"沐浴","辰":"冠带","巳":"临官","午":"帝旺","未":"衰","申":"病","酉":"死","戌":"墓","亥":"绝","子":"胎","丑":"养"},
    "己": {"酉":"长生","申":"沐浴","未":"冠带","午":"临官","巳":"帝旺","辰":"衰","卯":"病","寅":"死","丑":"墓","子":"绝","亥":"胎","戌":"养"},
    "庚": {"巳":"长生","午":"沐浴","未":"冠带","申":"临官","酉":"帝旺","戌":"衰","亥":"病","子":"死","丑":"墓","寅":"绝","卯":"胎","辰":"养"},
    "辛": {"子":"长生","亥":"沐浴","戌":"冠带","酉":"临官","申":"帝旺","未":"衰","午":"病","巳":"死","辰":"墓","卯":"绝","寅":"胎","丑":"养"},
    "壬": {"申":"长生","酉":"沐浴","戌":"冠带","亥":"临官","子":"帝旺","丑":"衰","寅":"病","卯":"死","辰":"墓","巳":"绝","午":"胎","未":"养"},
    "癸": {"卯":"长生","寅":"沐浴","丑":"冠带","子":"临官","亥":"帝旺","戌":"衰","酉":"病","申":"死","未":"墓","午":"绝","巳":"胎","辰":"养"},
}

DECISION_TYPES = {
    "跳槽/换工作": {"main_gods":["正官","七杀","正印","偏印","食神","伤官"],"benefit":"职业平台、规则系统、能力输出、身份变化","main_risks":["官杀压力","平台不适配","领导压制","收入不稳定","行业判断错误"]},
    "创业/做副业": {"main_gods":["食神","伤官","正财","偏财","比肩","劫财"],"benefit":"能力变现、资源整合、市场扩张、个人品牌","main_risks":["现金流断裂","合伙分利","项目过多","监管合同风险","重仓冒进"]},
    "投资/买资产": {"main_gods":["正财","偏财","正官","七杀"],"benefit":"资产增长、资源配置、财富积累","main_risks":["贪财破财","杠杆风险","信息不对称","合同风险","流动性不足"]},
    "婚恋/结婚/分手": {"main_gods":["正财","偏财","正官","七杀","正印","偏印"],"benefit":"亲密关系、资源协同、责任绑定、情感稳定","main_risks":["控制权冲突","依赖过重","现实压力","第三方干扰","情绪化决策"]},
    "买房/搬家": {"main_gods":["正财","偏财","正印","偏印"],"benefit":"稳定性、家庭资产、居住环境、长期安全感","main_risks":["现金流压力","贷款压力","城市选择错误","家庭意见冲突","高位接盘"]},
    "学习/考证/进修": {"main_gods":["正印","偏印","正官","七杀"],"benefit":"资质提升、专业背书、贵人平台、长期护城河","main_risks":["学习成瘾","行动延迟","证书不变现","机会成本过高"]},
    "合作/合伙": {"main_gods":["比肩","劫财","正财","偏财","食神","伤官"],"benefit":"团队起势、资源互补、渠道扩张、共同变现","main_risks":["分钱不清","权责不明","熟人消耗","合伙翻脸","责任转嫁"]},
}

RELATION_STRATEGY = {
    "印":{"得利方式":"靠学习、资质、贵人、平台、专业背书得利。","风险":"容易依赖、想太多、行动慢、学习成瘾。","建议":"把学习转化为证书、作品、职位、客户或现金流。"},
    "比劫":{"得利方式":"靠团队、同伴、竞争力、行动力、圈层得利。","风险":"容易合伙分利、同辈消耗、冲动竞争、朋友拖累。","建议":"钱账分明，权责清晰，合作必须写退出机制。"},
    "食伤":{"得利方式":"靠表达、技术、内容、产品、创意、服务输出得利。","风险":"容易嘴快、叛逆、项目过多、执行分散、顶撞权威。","建议":"把表达变成产品，把技术变成服务，把想法变成可交付结果。"},
    "财":{"得利方式":"靠资源、项目、市场、交易、资产、商务能力得利。","风险":"容易贪快钱、被项目拖累、现金流紧张、为资源耗神。","建议":"重视现金流、合同、成本、退出机制。"},
    "官杀":{"得利方式":"靠规则、职位、管理、责任、组织、风险控制得利。","风险":"容易被压力、领导、制度、债务、监管或责任压住。","建议":"把压力转化成资质、职位、权责边界和制度优势。"},
}

# ============================================================
# 真太阳时与排盘函数
# ============================================================

def equation_of_time_minutes(dt: datetime) -> float:
    """近似均时差，单位分钟。用于真太阳时。"""
    n = dt.timetuple().tm_yday
    b = math.radians((360 / 365) * (n - 81))
    return 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)


def true_solar_datetime(local_dt: datetime, longitude: float, timezone_meridian: float = 120.0, use_eot: bool = True) -> Tuple[datetime, float, float]:
    longitude_delta = (longitude - timezone_meridian) * 4.0
    eot = equation_of_time_minutes(local_dt) if use_eot else 0.0
    total = longitude_delta + eot
    return local_dt + timedelta(minutes=total), longitude_delta, eot


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


def split_ganzhi(gz: str) -> Tuple[str, str]:
    return (gz[0], gz[1]) if gz and len(gz) >= 2 else ("", "")


def xunkong(day_gz: str) -> str:
    if day_gz not in GANZHI60:
        return "未知"
    idx = GANZHI60.index(day_gz)
    xun_start = (idx // 10) * 10
    used_branches = [GANZHI60[i][1] for i in range(xun_start, xun_start + 10)]
    missing = [b for b in EARTHLY_BRANCHES if b not in used_branches]
    return "".join(missing)


def simple_shensha(day_stem: str, day_branch: str, year_branch: str, branches: List[str]) -> Dict[str, str]:
    # 常用简表，作为提示项，不作绝对断语。
    taohua_group = {
        "申子辰":"酉", "寅午戌":"卯", "亥卯未":"子", "巳酉丑":"午"
    }
    yima_group = {
        "申子辰":"寅", "寅午戌":"申", "亥卯未":"巳", "巳酉丑":"亥"
    }
    huagai_group = {
        "申子辰":"辰", "寅午戌":"戌", "亥卯未":"未", "巳酉丑":"丑"
    }
    tianyi = {
        "甲":["丑","未"], "乙":["子","申"], "丙":["亥","酉"], "丁":["亥","酉"], "戊":["丑","未"],
        "己":["子","申"], "庚":["丑","未"], "辛":["寅","午"], "壬":["卯","巳"], "癸":["卯","巳"]
    }
    def group_lookup(base_branch, table):
        for group, val in table.items():
            if base_branch in group:
                return val
        return ""
    res = {}
    for base_name, base in [("年支", year_branch), ("日支", day_branch)]:
        peach = group_lookup(base, taohua_group)
        horse = group_lookup(base, yima_group)
        canopy = group_lookup(base, huagai_group)
        res[f"桃花({base_name})"] = f"{peach}，{'命局见' if peach in branches else '命局未见'}"
        res[f"驿马({base_name})"] = f"{horse}，{'命局见' if horse in branches else '命局未见'}"
        res[f"华盖({base_name})"] = f"{canopy}，{'命局见' if canopy in branches else '命局未见'}"
    noble = tianyi.get(day_stem, [])
    res["天乙贵人(日干)"] = "、".join(noble) + ("，命局见" if any(b in branches for b in noble) else "，命局未见")
    return res


def build_bazi(dt_for_chart: datetime):
    if not LUNAR_AVAILABLE:
        raise RuntimeError("未安装 lunar_python。请先执行：pip install lunar-python")
    solar = Solar.fromYmdHms(dt_for_chart.year, dt_for_chart.month, dt_for_chart.day, dt_for_chart.hour, dt_for_chart.minute, dt_for_chart.second)
    lunar = solar.getLunar()
    ec = lunar.getEightChar()
    pillars = {"年柱": ec.getYear(), "月柱": ec.getMonth(), "日柱": ec.getDay(), "时柱": ec.getTime()}
    day_stem, day_branch = split_ganzhi(pillars["日柱"])
    rows = []
    hidden_rows = []
    for pillar, gz in pillars.items():
        stem, branch = split_ganzhi(gz)
        stem_god = "日主" if pillar == "日柱" else get_ten_god(day_stem, stem)
        hidden_text = []
        for hs, weight in BRANCH_HIDDEN_STEMS.get(branch, []):
            hg = get_ten_god(day_stem, hs)
            hidden_text.append(f"{hs}{hg}({weight})")
            hidden_rows.append({"柱": pillar, "地支": branch, "藏干": hs, "权重": weight, "藏干五行": STEM_ELEMENT[hs], "藏干十神": hg})
        rows.append({
            "柱": pillar, "干支": gz, "纳音": NAYIN.get(gz, ""),
            "天干": stem, "天干五行": STEM_ELEMENT.get(stem, ""), "天干阴阳": STEM_YINYANG.get(stem, ""), "天干十神": stem_god,
            "地支": branch, "地支五行": BRANCH_ELEMENT.get(branch, ""), "地支阴阳": BRANCH_YINYANG.get(branch, ""),
            "十二长生": CHANG_SHENG.get(day_stem, {}).get(branch, ""),
            "藏干十神": "、".join(hidden_text),
        })
    branches = [r["地支"] for r in rows]
    extra = {
        "公历排盘时间": solar.toYmdHms(),
        "农历": lunar.toString(),
        "农历完整": lunar.toFullString(),
        "生肖": lunar.getYearShengXiao(),
        "日柱空亡": xunkong(pillars["日柱"]),
        "神煞简表": simple_shensha(day_stem, day_branch, branches[0], branches),
    }
    return {"pillars": pillars, "day_stem": day_stem, "day_branch": day_branch, "rows": rows, "hidden_rows": hidden_rows, "extra": extra}


def count_elements_and_gods(rows: List[Dict], day_stem: str, month_branch: str) -> Tuple[Dict[str, float], Dict[str, float]]:
    elem = {"木":0.0,"火":0.0,"土":0.0,"金":0.0,"水":0.0}
    gods = {g:0.0 for g in TEN_GODS}
    month_power = SEASON_ELEMENT_POWER.get(month_branch, {e:1.0 for e in elem})
    for r in rows:
        stem = r["天干"]
        se = STEM_ELEMENT[stem]
        elem[se] += 1.0 * month_power.get(se, 1.0)
        g = r["天干十神"]
        if g in gods:
            gods[g] += 1.0
        branch = r["地支"]
        for hs, w in BRANCH_HIDDEN_STEMS.get(branch, []):
            he = STEM_ELEMENT[hs]
            elem[he] += w * month_power.get(he, 1.0)
            hg = get_ten_god(day_stem, hs)
            if hg in gods:
                gods[hg] += w
    return elem, gods


def infer_strength(rows: List[Dict], element_counts: Dict[str, float], god_counts: Dict[str, float]) -> Tuple[str, int, List[str]]:
    day_stem = rows[2]["天干"]
    day_el = STEM_ELEMENT[day_stem]
    month_branch = rows[1]["地支"]
    support_elems = [day_el] + [e for e, gen in ELEMENT_GENERATES.items() if gen == day_el]
    support = sum(element_counts[e] for e in support_elems)
    total = sum(element_counts.values()) or 1
    support_ratio = support / total
    score = round(support_ratio * 100)
    reasons = [f"日主五行：{day_el}。同类与印星合计约占 {support_ratio:.1%}。", f"月令：{month_branch}，已按季节权重修正五行强弱。"]
    if score >= 58:
        strength = "偏强"
        reasons.append("扶身力量偏多，原则上宜泄、耗、克来流通。")
    elif score <= 42:
        strength = "偏弱"
        reasons.append("扶身力量偏少，原则上宜印比生扶，不宜过度耗泄克。")
    else:
        strength = "中和"
        reasons.append("扶抑相对平衡，应重点看格局、流通和历史验证。")
    return strength, int(score), reasons


def suggest_useful_avoid(strength: str, god_counts: Dict[str, float]) -> Tuple[List[str], List[str], List[str]]:
    if strength == "偏强":
        useful = ["食神","伤官","正财","偏财","正官","七杀"]
        avoid = ["正印","偏印","比肩","劫财"]
        notes = ["日主偏强：先取泄秀、财耗、官杀约束，使能量流通。"]
    elif strength == "偏弱":
        useful = ["正印","偏印","比肩","劫财"]
        avoid = ["食神","伤官","正财","偏财","正官","七杀"]
        notes = ["日主偏弱：先取印比生扶，避免财官食伤过度消耗。"]
    else:
        useful, avoid = [], []
        notes = ["日主中和：不宜机械定喜忌，建议结合格局、大运和历史事件校准。"]
    heavy = [g for g, v in god_counts.items() if v >= 2.0]
    if heavy:
        notes.append("命局明显突出的十神：" + "、".join(heavy) + "。突出代表主题强，不代表一定有利。")
    return useful, avoid, notes


def detect_basic_patterns(god_counts: Dict[str, float], rows: List[Dict]) -> List[Dict[str, str]]:
    g = god_counts
    patterns = []
    def add(name, desc, risk): patterns.append({"格局/链条": name, "含义": desc, "风险": risk})
    if g["食神"] + g["伤官"] >= 1.5 and g["正财"] + g["偏财"] >= 1.2:
        add("食伤生财", "靠技术、表达、产品、内容、服务输出变现。", "项目过多、现金流波动、重表达轻管理。")
    if g["正官"] + g["七杀"] >= 1.2 and g["正印"] + g["偏印"] >= 1.2:
        add("官印相生/杀印相生", "压力、规则、资质、平台形成上升通道。", "容易依赖组织与证书，行动变慢。")
    if g["正财"] + g["偏财"] >= 1.3 and g["正官"] + g["七杀"] >= 1.0:
        add("财生官杀", "资源、项目、金钱可转化为身份、权责或组织位置。", "责任、合同、监管压力随资源同步上升。")
    if g["比肩"] + g["劫财"] >= 1.8 and g["食神"] + g["伤官"] >= 1.0:
        add("比劫生食伤", "同伴、团队、竞争力可转成输出和市场行动。", "合伙分利、同辈消耗、口舌冲突。")
    if g["食神"] + g["伤官"] >= 1.2 and g["正官"] + g["七杀"] >= 1.2:
        add("食伤制官杀", "用技术、表达、策略处理压力、竞争和风险。", "容易挑战权威，需注意规则边界。")
    if not patterns:
        add("未见明显单一链条", "命局可能更依赖大运、现实环境和历史校准。", "不要用单一十神下结论。")
    return patterns


def luck_direction(gender: str, year_stem: str) -> str:
    # 阳男阴女顺，阴男阳女逆。其他性别不指定时仅给出传统规则提示。
    yy = STEM_YINYANG.get(year_stem, "")
    if gender == "男":
        return "顺行" if yy == "阳" else "逆行"
    if gender == "女":
        return "逆行" if yy == "阳" else "顺行"
    return "未定：传统规则按年干阴阳与性别判顺逆"


def calc_luck_pillars(month_gz: str, direction: str, count: int = 10) -> List[str]:
    if month_gz not in GANZHI60 or direction not in ["顺行","逆行"]:
        return []
    idx = GANZHI60.index(month_gz)
    step = 1 if direction == "顺行" else -1
    return [GANZHI60[(idx + step*i) % 60] for i in range(1, count+1)]

# ============================================================
# 决策函数
# ============================================================

def clamp(x, lo=0, hi=100): return max(lo, min(hi, int(round(x))))

def light_level(score: int) -> Tuple[str, str]:
    if score >= 85: return "🟢 绿灯", "可以推进，但必须设置止损线。"
    if score >= 70: return "🟡 偏绿", "可以做，但建议分阶段推进，避免一次性重仓。"
    if score >= 55: return "🟠 黄灯", "方向未必错，但时机、资源或风险控制不足，适合先准备或小规模试点。"
    return "🔴 红灯", "不建议贸然推进，应延后、缩小规模或换方案。"

def calculate_natal_fit(useful, avoid, decision_type, chain):
    dg = DECISION_TYPES[decision_type]["main_gods"]
    return clamp(50 + len(set(useful)&set(dg))*10 + len(set(chain)&set(dg))*6 - len(set(avoid)&set(dg))*12)

def calculate_trend_score(useful, avoid, decade_god, year_god, decision_type):
    dg = DECISION_TYPES[decision_type]["main_gods"]
    ds = 50 + (25 if decade_god in useful else 0) - (25 if decade_god in avoid else 0) + (15 if decade_god in dg else 0)
    ys = 50 + (25 if year_god in useful else 0) - (25 if year_god in avoid else 0) + (15 if year_god in dg else 0)
    return clamp(ds), clamp(ys)

def avg_score(*vals): return clamp(sum(vals)/len(vals))

def parse_gods(raw: str) -> List[str]:
    parts = str(raw).replace("，", ",").replace("、", ",").replace(" ", ",").split(",")
    return [p.strip() for p in parts if p.strip() in TEN_GODS]

def infer_history_bias(df):
    res = {g:{"好":0,"差":0,"中性":0} for g in TEN_GODS}
    for _, row in df.iterrows():
        outcome = str(row.get("结果", "中性")).strip()
        if outcome not in ["好","差","中性"]: outcome = "中性"
        for god in parse_gods(row.get("相关十神", "")):
            res[god][outcome] += 1
    return res

def history_suggest(bias):
    useful, avoid = [], []
    for god, s in bias.items():
        if s["好"] >= 2 and s["好"] > s["差"]: useful.append(god)
        if s["差"] >= 2 and s["差"] > s["好"]: avoid.append(god)
    return useful, avoid

def risk_checklist(decision_type):
    return DECISION_TYPES[decision_type]["main_risks"] + ["最坏结果是否能承受？", "有没有明确止损线？", "是否可以小规模测试？", "有没有合同/书面边界？", "是否受贪婪、恐惧、面子驱动？"]

def generate_advice(decision_type, useful, avoid, decade_god, year_god, score):
    dg = DECISION_TYPES[decision_type]["main_gods"]
    msg = []
    if score >= 85: msg.append("综合评分高，可以推进，但保留止损和退出机制。")
    elif score >= 70: msg.append("方向可试，建议分阶段、小规模推进。")
    elif score >= 55: msg.append("先做准备、调研、样板或资源谈判，不宜重仓。")
    else: msg.append("当前不宜贸然推进，优先避险、延后或换方案。")
    if decade_god in avoid: msg.append(f"大运主题「{decade_god}」为风险项，长期主线需保守。")
    if year_god in avoid: msg.append(f"流年主题「{year_god}」为风险项，今年尤其要防冲动和合同风险。")
    if decade_god in useful: msg.append(f"大运主题「{decade_god}」为优势项，可作为长期发力点。")
    if year_god in useful: msg.append(f"流年主题「{year_god}」为优势项，可把握阶段机会。")
    conflict = set(dg)&set(avoid)
    support = set(dg)&set(useful)
    if conflict: msg.append("此事项会引动风险十神：" + "、".join(conflict) + "。")
    if support: msg.append("此事项会引动优势十神：" + "、".join(support) + "。")
    return msg

# ============================================================
# 状态初始化
# ============================================================

def init_state():
    if "history_df" not in st.session_state:
        st.session_state.history_df = pd.DataFrame([
            {"年份":2020,"事件":"示例：换工作","结果":"好","相关十神":"正官,正印","备注":"平台变好，收入稳定"},
            {"年份":2022,"事件":"示例：合伙项目","结果":"差","相关十神":"劫财,偏财","备注":"合伙分钱不清，项目亏损"},
        ])
init_state()

st.title("☯️ 八字趋利避害决策系统 V3")
st.caption("修复日期选择；加入真太阳时；补充五行旺衰、藏干权重、纳音、空亡、十二长生、神煞简表、大运方向和决策评分联动。")

with st.expander("使用边界", expanded=True):
    st.markdown("""
    这是决策辅助系统，不是绝对预测器。系统输出用于 **识别长期模式、校准风险、拦截冲动决策**。  
    不替代法律、医学、投资、职业等专业判断。真太阳时采用经度修正 + 均时差近似；不同流派排盘细节可能有差异。
    """)

if not LUNAR_AVAILABLE:
    st.error("缺少依赖 lunar-python。请运行：pip install -r requirements.txt")
    st.stop()

# ============================================================
# 侧边栏：日期改为数字输入，规避 date_input 限制
# ============================================================

st.sidebar.header("一、出生信息")
name = st.sidebar.text_input("姓名/代号", "测试用户")
gender = st.sidebar.selectbox("性别", ["男", "女", "其他/不指定"], index=0)

col_y, col_m, col_d = st.sidebar.columns(3)
year = col_y.number_input("年", min_value=1600, max_value=2200, value=1990, step=1)
month = col_m.number_input("月", min_value=1, max_value=12, value=1, step=1)
day = col_d.number_input("日", min_value=1, max_value=31, value=1, step=1)
col_h, col_min = st.sidebar.columns(2)
hour = col_h.number_input("时", min_value=0, max_value=23, value=8, step=1)
minute = col_min.number_input("分", min_value=0, max_value=59, value=0, step=1)

st.sidebar.markdown("---")
st.sidebar.header("二、真太阳时")
city = st.sidebar.text_input("出生地/城市", "中国大陆")
longitude = st.sidebar.number_input("出生地经度", min_value=73.0, max_value=135.0, value=120.0, step=0.1, help="中国大陆大致范围 73E-135E。东八区标准经线为 120E。")
use_true_solar = st.sidebar.checkbox("启用真太阳时排盘", value=True)
use_eot = st.sidebar.checkbox("加入均时差近似", value=True)
timezone_meridian = st.sidebar.number_input("时区标准经线", min_value=-180.0, max_value=180.0, value=120.0, step=1.0)

st.sidebar.markdown("---")
st.sidebar.header("三、大运流年")
decade_god = st.sidebar.selectbox("当前大运主题十神", TEN_GODS, index=6)
year_god = st.sidebar.selectbox("当前流年主题十神", TEN_GODS, index=7)

st.sidebar.markdown("---")
st.sidebar.header("四、当前决策")
decision_type = st.sidebar.selectbox("要判断的事项", list(DECISION_TYPES.keys()))
decision_desc = st.sidebar.text_area("具体决策描述", "例如：是否要和朋友合伙做一个副业项目？预计投入3万元，三个月内验证。", height=120)

try:
    local_dt = datetime(int(year), int(month), int(day), int(hour), int(minute), 0)
except ValueError as e:
    st.error(f"出生日期无效：{e}。请检查大小月、闰年日期。")
    st.stop()

if use_true_solar:
    chart_dt, lon_delta, eot = true_solar_datetime(local_dt, float(longitude), float(timezone_meridian), use_eot)
else:
    chart_dt, lon_delta, eot = local_dt, 0.0, 0.0

try:
    bazi = build_bazi(chart_dt)
except Exception as e:
    st.error(f"排盘失败：{e}")
    st.stop()

rows = bazi["rows"]
day_stem = bazi["day_stem"]
month_branch = rows[1]["地支"]
element_counts, god_counts = count_elements_and_gods(rows, day_stem, month_branch)
strength, strength_score, strength_reasons = infer_strength(rows, element_counts, god_counts)
auto_useful, auto_avoid, auto_notes = suggest_useful_avoid(strength, god_counts)
patterns = detect_basic_patterns(god_counts, rows)

year_stem, year_branch = split_ganzhi(bazi["pillars"]["年柱"])
month_gz = bazi["pillars"]["月柱"]
direction = luck_direction(gender, year_stem)
luck_pillars = calc_luck_pillars(month_gz, direction) if direction in ["顺行","逆行"] else []

visible_gods = [r["天干十神"] for r in rows if r["天干十神"] != "日主"]
all_auto_gods = []
for r in rows:
    if r["天干十神"] in TEN_GODS: all_auto_gods.append(r["天干十神"])
for hr in bazi["hidden_rows"]:
    all_auto_gods.append(hr["藏干十神"])

# ============================================================
# Tabs
# ============================================================

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["排盘", "旺衰格局", "喜忌校准", "历史校准", "决策评分", "报告导出"])

with tab1:
    st.header("一、排盘结果")
    c1, c2, c3 = st.columns(3)
    c1.metric("本地钟表时间", local_dt.strftime("%Y-%m-%d %H:%M"))
    c2.metric("排盘采用时间", chart_dt.strftime("%Y-%m-%d %H:%M"))
    c3.metric("真太阳时修正", f"{(chart_dt-local_dt).total_seconds()/60:.1f} 分钟")
    st.caption(f"经度修正 {lon_delta:.1f} 分钟；均时差 {eot:.1f} 分钟。")

    p1, p2, p3, p4 = st.columns(4)
    for col, name_p in zip([p1,p2,p3,p4], ["年柱","月柱","日柱","时柱"]):
        col.metric(name_p, bazi["pillars"][name_p])
    st.dataframe(pd.DataFrame(rows), use_container_width=True)
    st.subheader("地支藏干")
    st.dataframe(pd.DataFrame(bazi["hidden_rows"]), use_container_width=True)
    st.subheader("附加信息")
    st.json(bazi["extra"])

with tab2:
    st.header("二、五行旺衰、格局链条、大运")
    st.subheader("五行强弱统计")
    elem_df = pd.DataFrame([{"五行":k,"季节修正权重":round(v,2)} for k,v in element_counts.items()]).sort_values("季节修正权重", ascending=False)
    st.dataframe(elem_df, use_container_width=True)
    st.bar_chart(elem_df.set_index("五行"))

    st.subheader("十神分布")
    god_df = pd.DataFrame([{"十神":k,"权重":round(v,2),"关系":GOD_TO_RELATION[k]} for k,v in god_counts.items()]).sort_values("权重", ascending=False)
    st.dataframe(god_df, use_container_width=True)

    st.subheader("简化日主强弱")
    c1, c2 = st.columns([1,2])
    c1.metric("系统判断", strength)
    c1.progress(strength_score/100)
    c1.write(f"扶身分：{strength_score}/100")
    for r in strength_reasons:
        c2.write("- " + r)

    st.subheader("格局/能力链条提示")
    st.dataframe(pd.DataFrame(patterns), use_container_width=True)

    st.subheader("大运方向与大运柱")
    st.write(f"传统顺逆：**{direction}**。规则：阳男阴女顺，阴男阳女逆。")
    if luck_pillars:
        st.dataframe(pd.DataFrame([{"序号":i+1,"大运柱":gz,"纳音":NAYIN.get(gz,"")} for i,gz in enumerate(luck_pillars)]), use_container_width=True)
    st.caption("注意：V3 先给出大运顺逆和大运柱序列；精确起运岁数需结合出生到节气的时差，后续可继续升级。")

with tab3:
    st.header("三、喜忌与能力链条校准")
    st.info("；".join(auto_notes))
    col1, col2 = st.columns(2)
    with col1:
        useful_gods = st.multiselect("最终采用的喜用神/优势十神", TEN_GODS, default=auto_useful)
    with col2:
        avoid_gods = st.multiselect("最终采用的忌神/风险十神", TEN_GODS, default=auto_avoid)
    selected_chain = st.multiselect("命局中较顺的能力链条", TEN_GODS, default=[g for g in all_auto_gods if g in auto_useful][:3] or visible_gods[:2])
    st.subheader("五类关系策略")
    st.dataframe(pd.DataFrame([{"关系":k, "包含十神":"、".join(FIVE_RELATIONS[k]), **v} for k,v in RELATION_STRATEGY.items()]), use_container_width=True)
    info = DECISION_TYPES[decision_type]
    st.subheader("当前决策引动主题")
    st.write(f"**{decision_type}**：{info['benefit']}")
    st.write("主要十神：" + "、".join(info["main_gods"]))
    st.write("主要风险：" + "、".join(info["main_risks"]))

with tab4:
    st.header("四、历史事件校准")
    st.markdown("记录过去重大事件，用结果反推哪些十神对你更像优势或风险。建议至少 8-10 条。")
    edited = st.data_editor(st.session_state.history_df, num_rows="dynamic", use_container_width=True, column_config={
        "年份": st.column_config.NumberColumn("年份", min_value=1600, max_value=2200),
        "结果": st.column_config.SelectboxColumn("结果", options=["好","差","中性"]),
        "相关十神": st.column_config.TextColumn("相关十神，例如：正财,劫财"),
    })
    st.session_state.history_df = edited
    bias = infer_history_bias(edited)
    hu, ha = history_suggest(bias)
    bias_df = pd.DataFrame([{"十神":g, **s, "判断":"偏优势" if s["好"]>s["差"] else "偏风险" if s["差"]>s["好"] else "暂不明确"} for g,s in bias.items() if sum(s.values())>0])
    if len(bias_df): st.dataframe(bias_df, use_container_width=True)
    st.success("历史偏优势：" + ("、".join(hu) if hu else "暂不明显"))
    st.error("历史偏风险：" + ("、".join(ha) if ha else "暂不明显"))

with tab5:
    st.header("五、决策评分")
    if "useful_gods" not in locals(): useful_gods = auto_useful
    if "avoid_gods" not in locals(): avoid_gods = auto_avoid
    if "selected_chain" not in locals(): selected_chain = [g for g in all_auto_gods if g in auto_useful][:3]

    st.subheader("现实条件评分")
    r1,r2,r3,r4,r5 = st.columns(5)
    cash_flow = r1.slider("现金流承受力",0,100,70)
    ability = r2.slider("能力匹配度",0,100,75)
    information = r3.slider("信息充分度",0,100,60)
    support = r4.slider("外部支持",0,100,50)
    worst_case = r5.slider("最坏结果承受度",0,100,65)
    st.subheader("风险控制评分")
    k1,k2,k3,k4,k5 = st.columns(5)
    stop_loss = k1.slider("止损线清晰度",0,100,60)
    contract = k2.slider("合同/规则清晰度",0,100,55)
    backup = k3.slider("备用方案",0,100,50)
    small_test = k4.slider("小规模试点",0,100,80)
    emotion = k5.slider("情绪控制",0,100,70)

    natal_fit = calculate_natal_fit(useful_gods, avoid_gods, decision_type, selected_chain)
    decade_score, year_score = calculate_trend_score(useful_gods, avoid_gods, decade_god, year_god, decision_type)
    reality_score = avg_score(cash_flow, ability, information, support, worst_case)
    risk_score = avg_score(stop_loss, contract, backup, small_test, emotion)
    total = clamp(natal_fit*0.25 + decade_score*0.20 + year_score*0.15 + reality_score*0.25 + risk_score*0.15)
    light, conclusion = light_level(total)
    cols = st.columns(6)
    for col, label, val in zip(cols, ["命局适配","大运趋势","流年触发","现实条件","风险控制","总分"], [natal_fit,decade_score,year_score,reality_score,risk_score,total]):
        col.metric(label, val)
    st.subheader(f"最终判断：{light}")
    st.write(conclusion)
    st.progress(total/100)
    st.subheader("行动建议")
    for a in generate_advice(decision_type, useful_gods, avoid_gods, decade_god, year_god, total): st.write("- " + a)
    st.subheader("风险清单")
    for item in risk_checklist(decision_type): st.checkbox(item, value=False)

with tab6:
    st.header("六、报告导出")
    if "useful_gods" not in locals(): useful_gods = auto_useful
    if "avoid_gods" not in locals(): avoid_gods = auto_avoid
    if "selected_chain" not in locals(): selected_chain = [g for g in all_auto_gods if g in auto_useful][:3]
    natal_fit = calculate_natal_fit(useful_gods, avoid_gods, decision_type, selected_chain)
    decade_score, year_score = calculate_trend_score(useful_gods, avoid_gods, decade_god, year_god, decision_type)
    total = clamp(natal_fit*0.25 + decade_score*0.20 + year_score*0.15 + 64*0.25 + 63*0.15)
    light, conclusion = light_level(total)
    report = {
        "姓名/代号": name,
        "性别": gender,
        "出生地": city,
        "本地时间": local_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "排盘时间": chart_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "真太阳时": {"启用": use_true_solar, "经度": longitude, "经度修正分钟": lon_delta, "均时差分钟": eot},
        "四柱": bazi["pillars"],
        "日主": {"日干": day_stem, "日支": bazi["day_branch"], "强弱": strength, "扶身分": strength_score, "依据": strength_reasons},
        "五行统计": element_counts,
        "十神统计": god_counts,
        "格局链条": patterns,
        "附加信息": bazi["extra"],
        "大运": {"方向": direction, "大运柱序列": luck_pillars},
        "最终采用": {"喜用神": useful_gods, "忌神": avoid_gods, "能力链条": selected_chain},
        "决策": {"类型": decision_type, "描述": decision_desc, "当前大运十神": decade_god, "当前流年十神": year_god},
        "评分": {"命局适配": natal_fit, "大运趋势": decade_score, "流年触发": year_score, "总分估算": total},
        "最终判断": light,
        "结论": conclusion,
        "边界声明": "本报告为命理与现实风险结合的决策辅助，不替代专业意见。"
    }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    st.code(text, language="json")
    st.download_button("下载 JSON 报告", data=text.encode("utf-8"), file_name=f"{name}_八字决策报告_V3.json", mime="application/json")
    st.download_button("下载历史事件 CSV", data=st.session_state.history_df.to_csv(index=False).encode("utf-8-sig"), file_name=f"{name}_历史事件.csv", mime="text/csv")
