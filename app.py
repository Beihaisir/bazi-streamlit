
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Tuple, Optional

import pandas as pd
import streamlit as st

try:
    from lunar_python import Solar
    LUNAR_AVAILABLE = True
except Exception:
    Solar = None
    LUNAR_AVAILABLE = False


# ============================================================
# Streamlit 基础配置
# ============================================================

st.set_page_config(
    page_title="八字趋利避害决策系统 V2",
    page_icon="☯️",
    layout="wide"
)


# ============================================================
# 基础常量
# ============================================================

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

BRANCH_HIDDEN_STEMS = {
    "子": ["癸"],
    "丑": ["己", "癸", "辛"],
    "寅": ["甲", "丙", "戊"],
    "卯": ["乙"],
    "辰": ["戊", "乙", "癸"],
    "巳": ["丙", "戊", "庚"],
    "午": ["丁", "己"],
    "未": ["己", "丁", "乙"],
    "申": ["庚", "壬", "戊"],
    "酉": ["辛"],
    "戌": ["戊", "辛", "丁"],
    "亥": ["壬", "甲"],
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

FIVE_RELATIONS = {
    "印": ["正印", "偏印"],
    "比劫": ["比肩", "劫财"],
    "食伤": ["食神", "伤官"],
    "财": ["正财", "偏财"],
    "官杀": ["正官", "七杀"],
}

GOD_TO_RELATION = {
    "正印": "印",
    "偏印": "印",
    "比肩": "比劫",
    "劫财": "比劫",
    "食神": "食伤",
    "伤官": "食伤",
    "正财": "财",
    "偏财": "财",
    "正官": "官杀",
    "七杀": "官杀",
}

RELATION_STRATEGY = {
    "印": {
        "得利方式": "靠学习、资质、贵人、平台、专业背书得利。",
        "风险": "容易依赖、想太多、行动慢、学习成瘾。",
        "建议": "把学习转化为证书、作品、职位、客户或现金流，避免只输入不输出。",
    },
    "比劫": {
        "得利方式": "靠团队、同伴、竞争力、行动力、圈层得利。",
        "风险": "容易合伙分利、同辈消耗、冲动竞争、朋友拖累。",
        "建议": "钱账分明，权责清晰，少做口头承诺，合作必须写清退出机制。",
    },
    "食伤": {
        "得利方式": "靠表达、技术、内容、产品、创意、服务输出得利。",
        "风险": "容易嘴快、叛逆、项目过多、执行分散、顶撞权威。",
        "建议": "把表达变成产品，把技术变成服务，把想法变成可交付结果。",
    },
    "财": {
        "得利方式": "靠资源、项目、市场、交易、资产、商务能力得利。",
        "风险": "容易贪快钱、被项目拖累、现金流紧张、为资源耗神。",
        "建议": "重视现金流、合同、成本、退出机制，不碰看不懂的高收益项目。",
    },
    "官杀": {
        "得利方式": "靠规则、职位、管理、责任、组织、风险控制得利。",
        "风险": "容易被压力、领导、制度、债务、监管或责任压住。",
        "建议": "把压力转化成资质、职位、权责边界和制度优势，不硬扛灰色风险。",
    },
}

DECISION_TYPES = {
    "跳槽/换工作": {
        "main_gods": ["正官", "七杀", "正印", "偏印", "食神", "伤官"],
        "benefit": "职业平台、规则系统、能力输出、身份变化",
        "main_risks": ["官杀压力", "平台不适配", "领导压制", "收入不稳定", "行业判断错误"],
    },
    "创业/做副业": {
        "main_gods": ["食神", "伤官", "正财", "偏财", "比肩", "劫财"],
        "benefit": "能力变现、资源整合、市场扩张、个人品牌",
        "main_risks": ["现金流断裂", "合伙分利", "项目过多", "监管合同风险", "重仓冒进"],
    },
    "投资/买资产": {
        "main_gods": ["正财", "偏财", "正官", "七杀"],
        "benefit": "资产增长、资源配置、财富积累",
        "main_risks": ["贪财破财", "杠杆风险", "信息不对称", "合同风险", "流动性不足"],
    },
    "婚恋/结婚/分手": {
        "main_gods": ["正财", "偏财", "正官", "七杀", "正印", "偏印"],
        "benefit": "亲密关系、资源协同、责任绑定、情感稳定",
        "main_risks": ["控制权冲突", "依赖过重", "现实压力", "第三方干扰", "情绪化决策"],
    },
    "买房/搬家": {
        "main_gods": ["正财", "偏财", "正印", "偏印"],
        "benefit": "稳定性、家庭资产、居住环境、长期安全感",
        "main_risks": ["现金流压力", "贷款压力", "城市选择错误", "家庭意见冲突", "高位接盘"],
    },
    "学习/考证/进修": {
        "main_gods": ["正印", "偏印", "正官", "七杀"],
        "benefit": "资质提升、专业背书、贵人平台、长期护城河",
        "main_risks": ["学习成瘾", "行动延迟", "证书不变现", "机会成本过高"],
    },
    "合作/合伙": {
        "main_gods": ["比肩", "劫财", "正财", "偏财", "食神", "伤官"],
        "benefit": "团队起势、资源互补、渠道扩张、共同变现",
        "main_risks": ["分钱不清", "权责不明", "熟人消耗", "合伙翻脸", "责任转嫁"],
    },
}


# ============================================================
# 八字计算逻辑
# ============================================================

def get_ten_god(day_stem: str, other_stem: str) -> str:
    """
    用日干和目标天干计算十神。
    规则：
    - 同我者：同性比肩，异性劫财
    - 生我者：异性正印，同性偏印
    - 我生者：同性食神，异性伤官
    - 克我者：异性正官，同性七杀
    - 我克者：异性正财，同性偏财
    """
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
    """
    输入类似 甲子，返回 甲, 子。
    """
    if not gz or len(gz) < 2:
        return "", ""
    return gz[0], gz[1]


def safe_call(obj, method_name: str):
    try:
        method = getattr(obj, method_name)
        return method()
    except Exception:
        return None


def build_bazi_from_solar(year: int, month: int, day: int, hour: int, minute: int, second: int):
    if not LUNAR_AVAILABLE:
        raise RuntimeError("未安装 lunar_python。请先执行：pip install lunar-python")

    solar = Solar.fromYmdHms(year, month, day, hour, minute, second)
    lunar = solar.getLunar()
    eight_char = lunar.getEightChar()

    year_gz = eight_char.getYear()
    month_gz = eight_char.getMonth()
    day_gz = eight_char.getDay()
    time_gz = eight_char.getTime()

    pillars = {
        "年柱": year_gz,
        "月柱": month_gz,
        "日柱": day_gz,
        "时柱": time_gz,
    }

    day_stem, day_branch = split_ganzhi(day_gz)

    rows = []
    ten_gods_visible = []
    hidden_rows = []

    for pillar_name, gz in pillars.items():
        stem, branch = split_ganzhi(gz)
        stem_god = "日主" if pillar_name == "日柱" else get_ten_god(day_stem, stem)
        ten_gods_visible.append(stem_god) if stem_god != "日主" else None

        hidden = BRANCH_HIDDEN_STEMS.get(branch, [])
        hidden_gods = []
        for hs in hidden:
            hg = get_ten_god(day_stem, hs)
            hidden_gods.append(f"{hs}{hg}")
            hidden_rows.append(
                {
                    "柱": pillar_name,
                    "地支": branch,
                    "藏干": hs,
                    "藏干十神": hg,
                }
            )

        rows.append(
            {
                "柱": pillar_name,
                "干支": gz,
                "天干": stem,
                "天干五行": STEM_ELEMENT.get(stem, ""),
                "天干阴阳": STEM_YINYANG.get(stem, ""),
                "天干十神": stem_god,
                "地支": branch,
                "藏干": "、".join(hidden),
                "藏干十神": "、".join(hidden_gods),
            }
        )

    # 尝试调用 lunar-python 的附加信息，失败就忽略。
    extra = {
        "公历": solar.toYmdHms(),
        "农历": lunar.toString(),
        "农历完整": lunar.toFullString(),
        "生肖": safe_call(lunar, "getYearShengXiao"),
    }

    return {
        "pillars": pillars,
        "day_stem": day_stem,
        "day_branch": day_branch,
        "rows": rows,
        "hidden_rows": hidden_rows,
        "extra": extra,
    }


def count_ten_gods(rows: List[Dict], hidden_weight: float = 0.35) -> Dict[str, float]:
    counts = {g: 0.0 for g in TEN_GODS}
    for r in rows:
        g = r.get("天干十神")
        if g in counts:
            counts[g] += 1.0

        branch = r.get("地支", "")
        for hs in BRANCH_HIDDEN_STEMS.get(branch, []):
            hg = get_ten_god(rows[2]["天干"], hs) if len(rows) > 2 else None
            if hg in counts:
                counts[hg] += hidden_weight
    return counts


def infer_strength(rows: List[Dict]) -> Tuple[str, int, List[str]]:
    """
    简化版日主强弱评分。
    注意：这不是完整旺衰算法，只用于决策模型初筛。
    """
    if not rows or len(rows) < 4:
        return "未知", 50, ["排盘数据不足。"]

    day_stem = rows[2]["天干"]
    day_el = STEM_ELEMENT[day_stem]
    month_branch = rows[1]["地支"]

    score = 50
    reasons = []

    # 月令藏干包含日主同五行，加分。
    month_hidden = BRANCH_HIDDEN_STEMS.get(month_branch, [])
    month_hidden_elements = [STEM_ELEMENT[h] for h in month_hidden]
    if day_el in month_hidden_elements:
        score += 20
        reasons.append("月令藏干含日主同五行，日主有根。")

    # 天干比印扶身。
    for idx, r in enumerate(rows):
        if idx == 2:
            continue
        g = r["天干十神"]
        if g in ["比肩", "劫财"]:
            score += 10
            reasons.append(f"{r['柱']}天干为{g}，有同类扶身。")
        elif g in ["正印", "偏印"]:
            score += 8
            reasons.append(f"{r['柱']}天干为{g}，有印星生身。")
        elif g in ["正财", "偏财", "正官", "七杀"]:
            score -= 8
            reasons.append(f"{r['柱']}天干为{g}，对日主形成耗克压力。")
        elif g in ["食神", "伤官"]:
            score -= 5
            reasons.append(f"{r['柱']}天干为{g}，日主外泄输出。")

    # 地支藏干粗略评分。
    for r in rows:
        branch = r["地支"]
        for hs in BRANCH_HIDDEN_STEMS.get(branch, []):
            hg = get_ten_god(day_stem, hs)
            if hg in ["比肩", "劫财"]:
                score += 3
            elif hg in ["正印", "偏印"]:
                score += 2
            elif hg in ["正财", "偏财", "正官", "七杀"]:
                score -= 2

    score = max(0, min(100, score))

    if score >= 65:
        strength = "偏强"
    elif score <= 40:
        strength = "偏弱"
    else:
        strength = "中和"

    if not reasons:
        reasons.append("未发现特别强的扶抑信号，暂按中和处理。")

    return strength, score, reasons


def auto_suggest_useful_avoid(day_strength: str, counts: Dict[str, float]) -> Tuple[List[str], List[str], List[str]]:
    """
    简化喜忌建议：
    - 偏强：喜食伤、财、官杀；忌印、比劫过重
    - 偏弱：喜印、比劫；忌财、官杀、食伤过重
    - 中和：按结构流通选，先不给绝对喜忌
    """
    useful = []
    avoid = []
    notes = []

    if day_strength == "偏强":
        useful = ["食神", "伤官", "正财", "偏财", "正官", "七杀"]
        avoid = ["正印", "偏印", "比肩", "劫财"]
        notes.append("日主偏强，原则上喜泄、耗、克，忌继续生扶。")
    elif day_strength == "偏弱":
        useful = ["正印", "偏印", "比肩", "劫财"]
        avoid = ["食神", "伤官", "正财", "偏财", "正官", "七杀"]
        notes.append("日主偏弱，原则上喜生扶，忌过度输出、耗财、受克。")
    else:
        # 中和时，根据明显过旺的十神做风险提示
        useful = []
        avoid = []
        notes.append("日主中和，喜忌不能只靠强弱定，需要结合格局、流通和历史校准。")

    # 如果某类十神特别多，加入风险提示。
    heavy = [g for g, v in counts.items() if v >= 2.0]
    if heavy:
        notes.append("命局中较突出的十神：" + "、".join(heavy) + "。突出不等于一定有利，需要看是否可用。")

    return useful, avoid, notes


# ============================================================
# 决策评分函数
# ============================================================

def parse_gods(raw: str) -> List[str]:
    if not raw:
        return []
    parts = raw.replace("，", ",").replace("、", ",").replace(" ", ",").split(",")
    return [p.strip() for p in parts if p.strip() in TEN_GODS]


def clamp(value: float, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(round(value))))


def light_level(score: int) -> Tuple[str, str]:
    if score >= 85:
        return "🟢 绿灯", "可以推进，但必须设置止损线。"
    if score >= 70:
        return "🟡 偏绿", "可以做，但建议分阶段推进，避免一次性重仓。"
    if score >= 55:
        return "🟠 黄灯", "方向未必错，但时机、资源或风险控制不足，适合先准备或小规模试点。"
    return "🔴 红灯", "不建议贸然推进，应延后、缩小规模或换方案。"


def calculate_reality_score(cash_flow, ability, information, support, worst_case) -> int:
    return clamp((cash_flow + ability + information + support + worst_case) / 5)


def calculate_risk_score(stop_loss, contract, backup, small_test, emotion_control) -> int:
    return clamp((stop_loss + contract + backup + small_test + emotion_control) / 5)


def calculate_natal_fit(useful_gods, avoid_gods, decision_type, selected_chain) -> int:
    decision_gods = DECISION_TYPES[decision_type]["main_gods"]

    useful_hit = len(set(useful_gods) & set(decision_gods))
    avoid_hit = len(set(avoid_gods) & set(decision_gods))
    chain_hit = len(set(selected_chain) & set(decision_gods))

    base = 50
    base += useful_hit * 10
    base += chain_hit * 6
    base -= avoid_hit * 12

    return clamp(base)


def calculate_trend_score(useful_gods, avoid_gods, decade_god, year_god, decision_type) -> Tuple[int, int]:
    decision_gods = DECISION_TYPES[decision_type]["main_gods"]

    decade_score = 50
    year_score = 50

    if decade_god in useful_gods:
        decade_score += 25
    if decade_god in avoid_gods:
        decade_score -= 25
    if decade_god in decision_gods:
        decade_score += 15

    if year_god in useful_gods:
        year_score += 25
    if year_god in avoid_gods:
        year_score -= 25
    if year_god in decision_gods:
        year_score += 15

    return clamp(decade_score), clamp(year_score)


def infer_history_bias(df: pd.DataFrame) -> Dict[str, Dict[str, int]]:
    result = {god: {"好": 0, "差": 0, "中性": 0} for god in TEN_GODS}
    for _, row in df.iterrows():
        gods = parse_gods(str(row.get("相关十神", "")))
        outcome = str(row.get("结果", "中性")).strip()
        if outcome not in ["好", "差", "中性"]:
            outcome = "中性"
        for god in gods:
            result[god][outcome] += 1
    return result


def generate_history_suggestions(history_bias: Dict[str, Dict[str, int]]) -> Tuple[List[str], List[str]]:
    likely_useful = []
    likely_avoid = []
    for god, stat in history_bias.items():
        good = stat["好"]
        bad = stat["差"]
        if good >= 2 and good > bad:
            likely_useful.append(god)
        if bad >= 2 and bad > good:
            likely_avoid.append(god)
    return likely_useful, likely_avoid


def generate_advice(decision_type, useful_gods, avoid_gods, decade_god, year_god, score) -> List[str]:
    advice = []
    decision_gods = DECISION_TYPES[decision_type]["main_gods"]

    if score >= 85:
        advice.append("当前综合评分较高，可以推进，但不要取消止损线。")
    elif score >= 70:
        advice.append("方向可以尝试，但建议用小规模试点验证，不要一次性投入全部资源。")
    elif score >= 55:
        advice.append("建议先准备、谈资源、做样板或收集信息，暂不适合重大承诺。")
    else:
        advice.append("当前不适合贸然推进，优先规避损失，延后或换方案更稳。")

    if decade_god in avoid_gods:
        advice.append(f"当前大运主题「{decade_god}」落在你的忌神里，十年主线对这类事项容易有阻力。")
    elif decade_god in useful_gods:
        advice.append(f"当前大运主题「{decade_god}」落在你的喜用神里，长期方向有加分。")

    if year_god in avoid_gods:
        advice.append(f"今年流年主题「{year_god}」是风险点，今年不宜冲动、重仓、签死合同。")
    elif year_god in useful_gods:
        advice.append(f"今年流年主题「{year_god}」有利，可以把握机会，但仍需现实条件配合。")

    conflict = set(decision_gods) & set(avoid_gods)
    if conflict:
        advice.append(f"这个决策会引动你的忌神：{', '.join(conflict)}。需要重点做风险隔离。")

    support = set(decision_gods) & set(useful_gods)
    if support:
        advice.append(f"这个决策会引动你的优势十神：{', '.join(support)}。可以围绕这些优势设计执行方案。")

    return advice


def generate_risk_checklist(decision_type: str) -> List[str]:
    base = [
        "最坏结果是否能承受？",
        "有没有明确止损线？",
        "有没有备用方案？",
        "是否因为贪婪、恐惧、面子或情绪在做决定？",
        "是否可以先小规模测试，而不是一次性重仓？",
    ]
    return DECISION_TYPES[decision_type]["main_risks"] + base


def init_state():
    if "history_df" not in st.session_state:
        st.session_state.history_df = pd.DataFrame(
            [
                {"年份": 2020, "事件": "示例：换工作", "结果": "好", "相关十神": "正官,正印", "备注": "平台变好，收入稳定"},
                {"年份": 2022, "事件": "示例：合伙项目", "结果": "差", "相关十神": "劫财,偏财", "备注": "合伙分钱不清，项目亏损"},
            ]
        )


# ============================================================
# 页面
# ============================================================

init_state()

st.title("☯️ 八字趋利避害决策系统 V2")
st.caption("自动排盘版：输入公历出生时间，自动生成四柱、十神、简化日主强弱，并接入决策评分。")

with st.expander("使用边界", expanded=True):
    st.markdown(
        """
        这个程序不是绝对预测器，而是 **命理结构 + 现实条件 + 风险控制 + 历史校准** 的决策辅助工具。

        建议用法：  
        - 用它识别长期模式  
        - 用它做重大决策前的风险审查  
        - 用它记录历史事件并持续校准  
        - 不要用它替代法律、医学、投资、职业等专业判断
        """
    )

if not LUNAR_AVAILABLE:
    st.error("当前环境未安装 lunar_python。请先执行：pip install lunar-python")
    st.stop()


# ============================================================
# 侧边栏
# ============================================================

st.sidebar.header("一、出生信息")

name = st.sidebar.text_input("姓名/代号", value="测试用户")
gender = st.sidebar.selectbox("性别", ["男", "女", "其他/不指定"], index=0)

birth_date = st.sidebar.date_input("公历出生日期", value=datetime(1990, 1, 1).date())
birth_time = st.sidebar.time_input("出生时间", value=datetime(1990, 1, 1, 8, 0).time())

birthplace = st.sidebar.text_input("出生地/备注", value="未填写")
use_true_solar_time = st.sidebar.checkbox("使用真太阳时修正", value=False)
longitude = st.sidebar.number_input("出生地经度，仅真太阳时预留", min_value=-180.0, max_value=180.0, value=120.0, step=0.1)

st.sidebar.caption("V2 先预留真太阳时入口；当前排盘仍按输入的本地钟表时间计算。")

st.sidebar.markdown("---")
st.sidebar.header("二、大运流年")

decade_god = st.sidebar.selectbox("当前大运主题十神", TEN_GODS, index=6)
year_god = st.sidebar.selectbox("当前流年主题十神", TEN_GODS, index=7)

st.sidebar.markdown("---")
st.sidebar.header("三、当前决策")

decision_type = st.sidebar.selectbox("你要判断的事项", list(DECISION_TYPES.keys()))

decision_desc = st.sidebar.text_area(
    "具体决策描述",
    value="例如：是否要和朋友合伙做一个副业项目？预计投入3万元，三个月内验证。",
    height=120
)


# ============================================================
# 自动排盘
# ============================================================

dt = datetime.combine(birth_date, birth_time)

try:
    bazi = build_bazi_from_solar(dt.year, dt.month, dt.day, dt.hour, dt.minute, 0)
except Exception as e:
    st.error(f"排盘失败：{e}")
    st.stop()

bazi_rows = bazi["rows"]
bazi_df = pd.DataFrame(bazi_rows)
hidden_df = pd.DataFrame(bazi["hidden_rows"])
counts = count_ten_gods(bazi_rows)
auto_strength, strength_score, strength_reasons = infer_strength(bazi_rows)
auto_useful, auto_avoid, auto_notes = auto_suggest_useful_avoid(auto_strength, counts)

visible_gods = [r["天干十神"] for r in bazi_rows if r["天干十神"] != "日主"]
hidden_gods = []
for hr in bazi["hidden_rows"]:
    hidden_gods.append(hr["藏干十神"])
all_gods_auto = [g for g in visible_gods + hidden_gods if g in TEN_GODS]


# ============================================================
# Tabs
# ============================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "自动排盘",
    "喜忌校准",
    "历史校准",
    "决策评分",
    "报告导出"
])


with tab1:
    st.header("一、自动排盘结果")

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

    st.subheader("四柱与十神")
    st.dataframe(bazi_df, use_container_width=True)

    st.subheader("地支藏干")
    st.dataframe(hidden_df, use_container_width=True)

    st.subheader("简化日主强弱")
    cc1, cc2 = st.columns(2)
    with cc1:
        st.metric("系统判断", auto_strength)
        st.progress(strength_score / 100)
        st.write(f"强弱分：{strength_score}/100")
    with cc2:
        st.write("判断依据：")
        for reason in strength_reasons:
            st.write(f"- {reason}")

    st.subheader("十神分布")
    count_df = pd.DataFrame(
        [{"十神": g, "权重计数": round(v, 2), "关系类别": GOD_TO_RELATION[g]} for g, v in counts.items()]
    )
    st.dataframe(count_df.sort_values("权重计数", ascending=False), use_container_width=True)

    st.subheader("农历与附加信息")
    st.json(bazi["extra"])


with tab2:
    st.header("二、喜忌与能力链条校准")

    st.markdown(
        """
        系统会根据简化强弱给出初始喜忌，但这不是最终结论。  
        你可以结合实际经历手动修正。真正用于决策时，建议以“历史校准后的喜忌”为准。
        """
    )

    st.info("系统初步建议：" + "；".join(auto_notes))

    col_a, col_b = st.columns(2)
    with col_a:
        useful_gods = st.multiselect(
            "最终采用的喜用神/优势十神",
            TEN_GODS,
            default=auto_useful[:]
        )
    with col_b:
        avoid_gods = st.multiselect(
            "最终采用的忌神/风险十神",
            TEN_GODS,
            default=auto_avoid[:]
        )

    selected_chain = st.multiselect(
        "命局中较顺的能力链条",
        TEN_GODS,
        default=[g for g in all_gods_auto if g in auto_useful][:3] or visible_gods[:2]
    )

    st.subheader("五类关系解释")
    rows = []
    for relation, gods in FIVE_RELATIONS.items():
        strategy = RELATION_STRATEGY[relation]
        rows.append(
            {
                "关系": relation,
                "包含十神": "、".join(gods),
                "得利方式": strategy["得利方式"],
                "主要风险": strategy["风险"],
                "策略建议": strategy["建议"],
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True)

    st.subheader("当前决策对应的命理主题")
    info = DECISION_TYPES[decision_type]
    st.write(f"**事项类型：** {decision_type}")
    st.write(f"**主要引动十神：** {'、'.join(info['main_gods'])}")
    st.write(f"**可能收益：** {info['benefit']}")
    st.write(f"**主要风险：** {'、'.join(info['main_risks'])}")


with tab3:
    st.header("三、历史事件校准")

    st.markdown(
        """
        如果某些十神在过去多次对应好结果，可暂定为优势；  
        如果某些十神多次对应坏结果，应列入风险。  
        建议至少记录 8-10 条重大事件。
        """
    )

    edited_df = st.data_editor(
        st.session_state.history_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "年份": st.column_config.NumberColumn("年份", min_value=1900, max_value=2100),
            "结果": st.column_config.SelectboxColumn("结果", options=["好", "差", "中性"]),
            "相关十神": st.column_config.TextColumn("相关十神，例如：正财,劫财"),
        },
    )
    st.session_state.history_df = edited_df

    history_bias = infer_history_bias(edited_df)
    likely_useful, likely_avoid = generate_history_suggestions(history_bias)

    bias_rows = []
    for god, stat in history_bias.items():
        total = stat["好"] + stat["差"] + stat["中性"]
        if total > 0:
            bias_rows.append(
                {
                    "十神": god,
                    "好结果次数": stat["好"],
                    "差结果次数": stat["差"],
                    "中性次数": stat["中性"],
                    "初步判断": (
                        "偏优势" if stat["好"] > stat["差"]
                        else "偏风险" if stat["差"] > stat["好"]
                        else "暂不明确"
                    ),
                }
            )

    if bias_rows:
        st.dataframe(pd.DataFrame(bias_rows), use_container_width=True)
    else:
        st.info("还没有足够历史事件。")

    c1, c2 = st.columns(2)
    with c1:
        st.success("历史上可能偏优势的十神：" + ("、".join(likely_useful) if likely_useful else "暂不明显"))
    with c2:
        st.error("历史上可能偏风险的十神：" + ("、".join(likely_avoid) if likely_avoid else "暂不明显"))


with tab4:
    st.header("四、决策评分")

    # 如果用户没有进入 tab2，变量仍可能未定义。这里兜底。
    if "useful_gods" not in locals():
        useful_gods = auto_useful
    if "avoid_gods" not in locals():
        avoid_gods = auto_avoid
    if "selected_chain" not in locals():
        selected_chain = [g for g in all_gods_auto if g in auto_useful][:3]

    st.subheader("现实条件评分")
    st.caption("0 表示很差，100 表示很好。")

    r1, r2, r3, r4, r5 = st.columns(5)

    with r1:
        cash_flow = st.slider("现金流承受力", 0, 100, 70)
    with r2:
        ability = st.slider("能力匹配度", 0, 100, 75)
    with r3:
        information = st.slider("信息充分度", 0, 100, 60)
    with r4:
        support = st.slider("外部支持", 0, 100, 50)
    with r5:
        worst_case = st.slider("最坏结果承受度", 0, 100, 65)

    st.subheader("风险控制评分")

    k1, k2, k3, k4, k5 = st.columns(5)

    with k1:
        stop_loss = st.slider("止损线清晰度", 0, 100, 60)
    with k2:
        contract = st.slider("合同/规则清晰度", 0, 100, 55)
    with k3:
        backup = st.slider("备用方案", 0, 100, 50)
    with k4:
        small_test = st.slider("是否可小规模试点", 0, 100, 80)
    with k5:
        emotion_control = st.slider("情绪控制", 0, 100, 70)

    natal_fit = calculate_natal_fit(useful_gods, avoid_gods, decision_type, selected_chain)
    decade_score, year_score = calculate_trend_score(useful_gods, avoid_gods, decade_god, year_god, decision_type)
    reality_score = calculate_reality_score(cash_flow, ability, information, support, worst_case)
    risk_score = calculate_risk_score(stop_loss, contract, backup, small_test, emotion_control)

    total_score = clamp(
        natal_fit * 0.25
        + decade_score * 0.20
        + year_score * 0.15
        + reality_score * 0.25
        + risk_score * 0.15
    )

    light, conclusion = light_level(total_score)

    s1, s2, s3, s4, s5, s6 = st.columns(6)
    with s1:
        st.metric("命局适配", natal_fit)
    with s2:
        st.metric("大运趋势", decade_score)
    with s3:
        st.metric("流年触发", year_score)
    with s4:
        st.metric("现实条件", reality_score)
    with s5:
        st.metric("风险控制", risk_score)
    with s6:
        st.metric("总分", total_score)

    st.subheader(f"最终判断：{light}")
    st.write(conclusion)
    st.progress(total_score / 100)

    st.subheader("行动建议")
    for item in generate_advice(decision_type, useful_gods, avoid_gods, decade_god, year_god, total_score):
        st.write(f"- {item}")

    st.subheader("风险清单")
    for item in generate_risk_checklist(decision_type):
        st.checkbox(item, value=False)

    st.subheader("模型解释")
    st.markdown(
        f"""
        当前决策：**{decision_type}**

        决策描述：

        > {decision_desc}

        这个事项主要引动：**{", ".join(DECISION_TYPES[decision_type]["main_gods"])}**

        当前大运主题：**{decade_god}**  
        当前流年主题：**{year_god}**

        日主强弱：**{auto_strength}**  
        系统强弱分：**{strength_score}/100**

        如果大运、流年和你的喜用神一致，说明这件事有阶段性助力。  
        如果它们落入忌神，则代表同类事件容易放大风险，需要保守处理。
        """
    )


with tab5:
    st.header("五、导出分析报告")

    # 兜底
    if "useful_gods" not in locals():
        useful_gods = auto_useful
    if "avoid_gods" not in locals():
        avoid_gods = auto_avoid
    if "selected_chain" not in locals():
        selected_chain = [g for g in all_gods_auto if g in auto_useful][:3]

    natal_fit = calculate_natal_fit(useful_gods, avoid_gods, decision_type, selected_chain)
    decade_score, year_score = calculate_trend_score(useful_gods, avoid_gods, decade_god, year_god, decision_type)

    # 如果没有进评分页，给默认值。
    reality_score = 64
    risk_score = 63

    total_score = clamp(
        natal_fit * 0.25
        + decade_score * 0.20
        + year_score * 0.15
        + reality_score * 0.25
        + risk_score * 0.15
    )

    light, conclusion = light_level(total_score)

    history_bias = infer_history_bias(st.session_state.history_df)
    likely_useful, likely_avoid = generate_history_suggestions(history_bias)

    report = {
        "姓名/代号": name,
        "性别": gender,
        "出生信息": {
            "公历": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "出生地备注": birthplace,
            "真太阳时修正": use_true_solar_time,
            "经度": longitude,
        },
        "四柱": bazi["pillars"],
        "日主": {
            "日干": bazi["day_stem"],
            "日支": bazi["day_branch"],
            "系统强弱": auto_strength,
            "强弱分": strength_score,
            "判断依据": strength_reasons,
        },
        "十神表": bazi_rows,
        "十神分布": counts,
        "系统建议": {
            "初步喜用神": auto_useful,
            "初步忌神": auto_avoid,
            "说明": auto_notes,
        },
        "最终采用": {
            "喜用神": useful_gods,
            "忌神": avoid_gods,
            "能力链条": selected_chain,
        },
        "当前大运": decade_god,
        "当前流年": year_god,
        "决策类型": decision_type,
        "决策描述": decision_desc,
        "评分": {
            "命局适配": natal_fit,
            "大运趋势": decade_score,
            "流年触发": year_score,
            "现实条件": reality_score,
            "风险控制": risk_score,
            "总分": total_score,
        },
        "最终判断": light,
        "结论": conclusion,
        "行动建议": generate_advice(decision_type, useful_gods, avoid_gods, decade_god, year_god, total_score),
        "风险清单": generate_risk_checklist(decision_type),
        "历史校准": {
            "可能优势十神": likely_useful,
            "可能风险十神": likely_avoid,
        },
        "边界声明": "本报告为决策辅助，不替代法律、医学、投资、职业等专业判断。",
    }

    report_text = json.dumps(report, ensure_ascii=False, indent=2)

    st.code(report_text, language="json")

    st.download_button(
        label="下载 JSON 报告",
        data=report_text.encode("utf-8"),
        file_name=f"{name}_八字决策报告_V2.json",
        mime="application/json",
    )

    csv_data = st.session_state.history_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="下载历史事件 CSV",
        data=csv_data,
        file_name=f"{name}_历史事件.csv",
        mime="text/csv",
    )
