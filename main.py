# -*- coding: utf-8 -*-
"""
douyin-pet-track —— 宠物赛道抖音爆款内容流水线
=============================================
完整闭环（忠实复刻「抖音爆款内容专家」官方技能工作流）：

  ① 热点捕捉 : 实时热榜(hotSpot/getListByPlatform) + 关键词作品搜索(dy/data/searchWork)
  ② 爆款对标 : 动物赛道·点赞日榜(dy/search/likesRank) + 七日点赞飙升榜(dy/search/hotContentRank→weeklyRank)
  ③ 文案复刻 : 对标作品结构蒸馏 → 复刻写作提示词(multi-copywrite-alchemy) + 违禁词扫雷(cozeSkill/sensitiveWordSearch)
  ④ 效果验证 : 发布后查每日点赞飙升榜(dy/search/hotContentRank→dailyRank) 验证作品是否进榜

三种运行模式（--mode）：
  report    默认，跑 ①② 生成可视化对标 HTML 报告
  replicate 跑 ③ 文案复刻：蒸馏对标结构 + 你的人设风格 → 复刻写作提示词；可接 --script 跑违禁词扫雷
  verify    跑 ④ 效果验证：给定已发布作品，查它是否进入指定日期的每日飙升榜

仅依赖标准库（urllib），零额外依赖。
配置从 config.yaml 读取（可选 PyYAML；缺失则用内置默认值）。
"""
import json
import re
import html
import sys
import os
import argparse
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

# ---------------- 内置默认配置（config.yaml 读取失败时的兜底） ----------------
DEFAULT_CONFIG = {
    "redfox": {
        "api_base": "https://redfox.hk/story/api",
        "api_key_env": "REDFOX_API_KEY",
        "hotspot_path": "/hotSpot/getListByPlatform",
        "search_path": "/dy/data/searchWork",
        "daily_path": "/dy/search/likesRank",
        "weekly_path": "/dy/search/hotContentRank",
        "prohibited_path": "/cozeSkill/sensitiveWordSearch",
    },
    "search": {"keyword": "宠物", "page_size": 50},
    "pet_filter": {
        "enabled": True,
        "keywords": ["猫", "橘猫", "布偶", "英短", "美短", "缅因", "波斯", "加菲",
                      "银渐层", "金渐层", "奶猫", "小猫", "狸花", "奶牛猫", "猫砂",
                      "铲屎", "哈基米", "咪咪", "大橘", "狗", "修勾", "狗狗", "柴犬",
                      "金毛", "柯基", "泰迪", "猫粮", "狗粮", "宠物", "仓鼠", "兔子", "龟"],
    },
    "report": {"top_n": 50, "title": "宠物赛道·抖音热榜+对标报告", "highlight_label": "宠物向"},
    "output": {"default_path": "宠物赛道对标报告.html"},
    "replicate": {
        "track": "动物",
        "style_ref": "",          # 你的风格/人设参考文本文件路径（可选）
        "prompt_out": "复刻写作提示词.md",
    },
    "verify": {
        "track": "动物",
        "out": "效果验证_{date}.md",
    },
    "prohibited_word": {
        "platform": "抖音",
        "source": "抖音违禁词查询-WorkBuddy",
        "max_content_length": 3000,
        "max_total_length": 10000,
    },
}


# ---------------- 极简 YAML 解析（仅支持本项目 config.yaml 的子集） ----------------
def _strip_quotes(s):
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("\"", "'"):
        return s[1:-1]
    return s


def _strip_comment(s):
    idx = s.find(" #")
    if idx != -1:
        s = s[:idx]
    return s


def _coerce(s):
    s = _strip_comment(s)
    s = _strip_quotes(s)
    if s == "":
        return ""
    if s.lower() in ("true", "false"):
        return s.lower() == "true"
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def parse_simple_yaml(text):
    """解析本项目的 config.yaml（嵌套 dict + 简单 list，仅 str/int/float/bool）。"""
    root = {}
    stack = [(-1, root)]
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1]

        if stripped.startswith("- "):
            item = _coerce(stripped[2:])
            if isinstance(parent, list):
                parent.append(item)
            continue

        if ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip()
            if val == "":
                nxt = None
                for n in text.splitlines()[text.splitlines().index(line) + 1:]:
                    if n.strip() and not n.strip().startswith("#"):
                        nxt = n.strip()
                        break
                new = [] if (nxt and nxt.startswith("- ")) else {}
                parent[key] = new
                stack.append((indent, new))
            else:
                parent[key] = _coerce(val)
    return root


def load_config(path):
    if not path or not os.path.exists(path):
        return dict(DEFAULT_CONFIG)
    try:
        import yaml  # type: ignore
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or dict(DEFAULT_CONFIG)
    except ImportError:
        with open(path, "r", encoding="utf-8") as f:
            return parse_simple_yaml(f.read())
    except Exception as e:
        sys.stderr.write(f"[warn] 读取 config.yaml 失败，使用内置默认配置: {e}\n")
        return dict(DEFAULT_CONFIG)


def deep_get(d, *keys, default=None):
    for k in keys:
        if not isinstance(d, dict) or k not in d:
            return default
        d = d[k]
    return d


# ---------------- 网络层 ----------------
def call(url, body=None, params=None, api_key=""):
    headers = {
        "X-API-KEY": api_key,
        "REDFOX_API_KEY": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req = Request(url, data=data, headers=headers, method="POST")
    else:
        if params:
            url = url + "?" + urlencode(params)
        req = Request(url, headers=headers, method="GET")
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        sys.stderr.write(f"[error] HTTP {e.code}: {e.read().decode('utf-8','replace')}\n")
        sys.exit(1)
    except URLError as e:
        sys.stderr.write(f"[error] 网络请求失败: {e.reason}\n")
        sys.exit(1)


def yesterday():
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")


# ---------------- 四个数据源（阶段①+②） ----------------
def fetch_hot(cfg, api_key):
    base = deep_get(cfg, "redfox", "api_base")
    path = deep_get(cfg, "redfox", "hotspot_path")
    r = call(base + path, params={"platform": 2, "source": "宠物对标-skill"}, api_key=api_key)
    if isinstance(r, dict):
        d = r.get("data")
        if isinstance(d, list):
            return d
        if isinstance(d, dict):
            return d.get("list", [])
    if isinstance(r, list):
        return r
    return []


def fetch_search(cfg, api_key, kw, page_size):
    base = deep_get(cfg, "redfox", "api_base")
    path = deep_get(cfg, "redfox", "search_path")
    body = {"keyword": kw, "source": "宠物对标-skill", "pageNum": 1, "pageSize": page_size}
    r = call(base + path, body=body, api_key=api_key)
    if r.get("code") != 2000:
        sys.stderr.write(f"[error] 搜索接口: code={r.get('code')} msg={r.get('msg')}\n")
        sys.exit(1)
    return r.get("data", {}).get("list", [])


def fetch_daily(cfg, api_key, date):
    base = deep_get(cfg, "redfox", "api_base")
    path = deep_get(cfg, "redfox", "daily_path")
    body = {"source": "宠物对标-skill", "type": "动物", "startTime": date, "endTime": date}
    r = call(base + path, body=body, api_key=api_key)
    if r.get("code") != 2000:
        sys.stderr.write(f"[error] 日榜接口: code={r.get('code')} msg={r.get('msg')}\n")
        sys.exit(1)
    return r.get("data", [])


def fetch_weekly(cfg, api_key, date):
    """阶段② 爆款对标：七日点赞飙升榜 —— 官方 source 字符串 + data.weeklyRank"""
    base = deep_get(cfg, "redfox", "api_base")
    path = deep_get(cfg, "redfox", "weekly_path")
    body = {"source": "抖音七日点赞飙升榜-WorkBuddy", "type": "动物", "startTime": date}
    r = call(base + path, body=body, api_key=api_key)
    if r.get("code") != 2000:
        sys.stderr.write(f"[error] 七日飙升榜接口: code={r.get('code')} msg={r.get('msg')}\n")
        sys.exit(1)
    return r.get("data", {}).get("weeklyRank", [])


def fetch_daily_surge(cfg, api_key, date, track="动物"):
    """阶段④ 效果验证：每日点赞飙升榜 —— 官方 source 字符串 + data.dailyRank"""
    base = deep_get(cfg, "redfox", "api_base")
    path = deep_get(cfg, "redfox", "weekly_path")  # 同一端点 hotContentRank
    body = {"source": "抖音每日点赞飙升榜"}
    if track and track != "全部":
        body["type"] = track
    body["startTime"] = date
    r = call(base + path, body=body, api_key=api_key)
    if r.get("code") != 2000:
        sys.stderr.write(f"[error] 每日飙升榜接口: code={r.get('code')} msg={r.get('msg')}\n")
        sys.exit(1)
    return r.get("data", {}).get("dailyRank", [])


# ---------------- 归一化 + 筛选 ----------------
def is_pet(title, pet_kw):
    return any(k in (title or "") for k in pet_kw)


def build(items, kind, pet_kw):
    out = []
    for it in items:
        if kind == "hot":
            title, url = it.get("title", ""), it.get("url", "")
            rank, author, like = it.get("index", ""), "-", it.get("hotCount", "")
            extra = {}
        elif kind == "search":
            title, url = it.get("content", ""), it.get("opusUrl", "")
            rank, author = "", it.get("authorName", "")
            like = it.get("likeCount", "")
            extra = {"collect": it.get("collectCount", ""), "comment": it.get("commentCount", ""),
                     "share": it.get("shareCount", ""), "time": it.get("publishTime", "")}
        elif kind == "daily":
            title, url = it.get("title", ""), it.get("workUrl", "")
            rank, author = it.get("rank", ""), it.get("accountName", "")
            like = it.get("likeCount", "")
            extra = {"collect": it.get("collectCount", ""), "comment": it.get("commentCount", ""),
                     "share": it.get("shareCount", ""), "time": it.get("publishTime", "")}
        elif kind in ("weekly", "surge"):
            title, url = it.get("aweme_desc", ""), it.get("share_url", "")
            rank, author = it.get("rank", ""), it.get("user_nickname", "")
            like = it.get("add_digg_count", "")
            extra = {"collect": it.get("add_collect_count", ""), "comment": it.get("add_comment_count", ""),
                     "share": it.get("add_share_count", ""), "time": it.get("create_time_str", "")}
        out.append({"rank": rank, "title": title, "url": url, "author": author,
                    "like": like, "pet": is_pet(title, pet_kw), **extra})
    return out


def fmt(v):
    return html.escape(str(v)) if v not in (None, "") else "-"


def row_html(d, kind, label):
    cls = ' class="pet"' if d["pet"] else ""
    title_cell = f'<a href="{html.escape(d["url"])}" target="_blank">{html.escape(d["title"] or "(无标题)")}</a>'
    if kind == "hot":
        return f'<tr{cls}><td>{html.escape(str(d["rank"]))}</td><td>{title_cell}</td><td>{html.escape(str(d["like"]))}</td></tr>'
    if kind == "search":
        extra = f'<td>{fmt(d.get("collect"))}</td><td>{fmt(d.get("comment"))}</td><td>{fmt(d.get("share"))}</td><td>{fmt(d.get("time"))}</td>'
        return f'<tr{cls}><td>{title_cell}</td><td>{html.escape(str(d["author"]))}</td><td>{fmt(d["like"])}</td>{extra}</tr>'
    extra = f'<td>{fmt(d.get("collect"))}</td><td>{fmt(d.get("comment"))}</td><td>{fmt(d.get("share"))}</td><td><b>{fmt(d["like"])}</b></td><td>{fmt(d.get("time"))}</td>'
    return f'<tr{cls}><td>{html.escape(str(d["rank"]))}</td><td>{title_cell}</td><td>{html.escape(str(d["author"]))}</td>{extra}</tr>'


def table(kind, data, headers, note, label):
    h = "".join(f"<th>{x}</th>" for x in headers)
    body = "\n".join(row_html(d, kind, label) for d in data)
    return f'<h3>{note}</h3><table><thead><tr>{h}</tr></thead><tbody>{body}</tbody></table>'


def pet_label(lst):
    return str(len(lst))


# ---------------- 报告生成（阶段①+②） ----------------
def build_report(cfg, hot, search, daily, weekly, daily_pet, weekly_pet, now):
    top_n = deep_get(cfg, "report", "top_n", default=50)
    title = deep_get(cfg, "report", "title", default="宠物赛道·抖音热榜+对标报告")
    label = deep_get(cfg, "report", "highlight_label", default="宠物向")
    doc = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
*{{box-sizing:border-box}}
body{{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;margin:0;background:#eef6ff;color:#1f2d3d;padding:28px}}
.wrap{{max-width:1100px;margin:0 auto;background:#fff;border-radius:16px;padding:32px;box-shadow:0 8px 30px rgba(47,128,237,.12)}}
h1{{color:#2f80ed;margin:0 0 4px;font-size:26px}}
.sub{{color:#7a8aa0;font-size:13px;margin-bottom:20px}}
h2{{color:#2f80ed;border-left:5px solid #2f80ed;padding-left:10px;margin-top:32px;font-size:19px}}
h3{{color:#2a4a6b;font-size:15px;margin:18px 0 8px}}
table{{width:100%;border-collapse:collapse;font-size:13px;margin-bottom:8px}}
th{{background:#2f80ed;color:#fff;text-align:left;padding:8px 10px;white-space:nowrap}}
td{{border-bottom:1px solid #eee;padding:7px 10px;vertical-align:top}}
tr.pet{{background:#fff7e6}}
tr.pet td:first-child{{box-shadow:inset 3px 0 0 #ff9f43}}
a{{color:#2f80ed;text-decoration:none}}
a:hover{{text-decoration:underline}}
.note{{background:#f1f7ff;border-left:4px solid #2f80ed;padding:12px 16px;border-radius:8px;font-size:13px;line-height:1.7;margin:10px 0}}
.kpi{{display:flex;gap:14px;flex-wrap:wrap;margin:14px 0}}
.kpi div{{background:#eef6ff;border-radius:12px;padding:14px 20px;text-align:center;flex:1;min-width:110px}}
.kpi b{{display:block;font-size:24px;color:#2f80ed}}
.kpi span{{font-size:12px;color:#7a8aa0}}
</style></head><body><div class="wrap">
<h1>🐾 {html.escape(title)}</h1>
<div class="sub">生成时间 {now} ｜ 数据来源：红狐 hub（热榜 / 搜索 / 动物赛道日榜 / 七日飙升榜）｜ 橙底行 = {html.escape(label)}内容</div>
<div class="kpi">
<div><b>{len(hot)}</b><span>实时热榜话题</span></div>
<div><b>{len(search)}</b><span>宠物搜索样本</span></div>
<div><b>{len(daily)}</b><span>动物日榜(全)</span></div>
<div><b>{len(daily_pet)}</b><span>日榜·{html.escape(label)}</span></div>
<div><b>{len(weekly_pet)}</b><span>飙升·{html.escape(label)}</span></div>
</div>
<div class="note"><b>结论先行：</b>动物赛道里「宠物」是核心内容池。日榜 TOP{len(daily)} 中{pet_label(daily_pet)} 条、七日飙升 TOP{len(weekly)} 中{pet_label(weekly_pet)} 条。优先盯 <b>七日飙升榜里的宠物向作品</b>（正在涨、确定性最高），它们是复刻首选靶子。下一阶段跑 <code>--mode replicate</code> 出可发布文案。</div>
<h2>① 热点捕捉</h2>
{table("hot", hot, ["排名","话题（点击跳转）","热度"], "实时全站热榜（橙底=宠物相关）", label)}
{table("search", search, ["作品（点击跳转）","作者","点赞","收藏","评论","分享","发布时间"], "宠物关键词作品搜索 TOP" + str(min(len(search), 20)) + "（按点赞降序）", label)}
<h2>② 爆款对标 · 动物赛道</h2>
{table("daily", daily, ["排名","作品（点击跳转）","作者（粉丝）","收藏","评论","分享","**点赞**","发布时间"], f"动物赛道 点赞日榜 TOP{len(daily)}（橙底={html.escape(label)}）", label)}
{table("weekly", weekly, ["排名","作品（点击跳转）","作者","七日新增收藏","七日新增评论","七日新增分享","**七日新增点赞**","发布时间"], f"动物赛道 七日点赞飙升 TOP{len(weekly)}（橙底={html.escape(label)}）", label)}
<h2>对标锁定池 · 正在涨的宠物爆款（优先复刻靶子）</h2>
<div class="note">以下来自「七日飙升榜·{html.escape(label)}」，代表过去 7 天仍在持续起量的宠物内容，是宠物号最该复刻的方向。复制标题/链接，作为 <code>--mode replicate --benchmark</code> 的输入。</div>
{table("weekly", weekly_pet, ["排名","作品（点击跳转）","作者","七日新增收藏","七日新增评论","七日新增分享","**七日新增点赞**","发布时间"], f"七日飙升 · {html.escape(label)} {len(weekly_pet)} 条", label)}
<h2>给宠物号的对标建议</h2>
<div class="note">
1. <b>题材切口</b>：飙升宠物向高频出现——小奶猫/小狗卖萌、宠物迷惑行为、品种猫狗反差、宠物 meme 小剧场、沉浸式洗护/养宠教程。<br>
2. <b>形态</b>：宠物向爆款以「原声+字幕」轻剧情/记录为主，口播型偏少；口播脚本可叠加「宠物实景画面+痛点口播」，兼顾完播与人设。<br>
3. <b>挂车节奏</b>：爆款宠物内容评论/分享极高（情绪驱动），适合在痛点段自然带出宠物用品。<br>
4. <b>下一步（闭环）</b>：指定某条对标作品 → <code>--mode replicate</code> 出复刻文案（含违禁词扫雷）→ 发布 → <code>--mode verify</code> 验证是否进每日飙升榜。
</div>
</div></body></html>"""
    return doc


# ---------------- 阶段③：文案复刻（蒸馏 + 违禁词扫雷） ----------------
def build_replicate_prompt(benchmark_text, style_text, topic, track):
    """忠实复刻 multi-copywrite-alchemy 的产出：把对标作品结构 + 你的风格 → 一份可直接喂给 AI 的「复刻写作提示词」。"""
    bench = (benchmark_text or "").strip()
    style = (style_text or "").strip()
    topic = (topic or "").strip()

    style_block = ""
    if style:
        style_block = f"""
## 你的风格分身（必须严格贴合，不要跑偏）
{style}
"""

    prompt = f"""# 宠物赛道抖音文案 · 复刻写作任务

## 0. 角色与目标
你是一名宠物赛道（抖音）短视频脚本写手。目标：基于下方「对标标杆」的爆款结构，结合「你的风格分身」，写一篇**新命题**的宠物口播/口播+实景脚本，做到「像那个爆款的基因，但是你自己的声音」。

## 1. 对标标杆拆解（从真实爆款中提取，不可照抄文案，只学结构）
{bench or '（未提供标杆文本，请依据「{track}」赛道近期爆款共性：强钩子开场、真实痛点共鸣、轻量解法、情绪化结尾、自然挂车）'}

请先自行把标杆拆成以下维度（写稿前在心里过一遍）：
- **钩子类型**：0-3s 用什么冲突/反差/疑问把人留住？
- **痛点锚点**：戳的是养宠人的哪种真实情绪（自责/怕/孤独/又气又舍不得）？
- **解法走向**：给的是哪三步/哪个具体动作？人格线何时出现？
- **结尾设计**：评论引导是邀请式而非命令式；下期预告是否留悬念？
- **情绪曲线**：温和路线，禁凶相/瞪眼/指责感。
- **挂车节奏**：用品在哪一拍自然出现，第一人称「我家猫在用」式归属。

## 2. 本次命题
- 赛道：{track}
- 主题：{topic or '（请补充：你想做的宠物选题，例如「猫咪半夜跑酷怎么办」）'}

{style_block}
## 3. 输出格式（复制即可拍）
按 3-5 段情绪层次拆解，每段含：
- 【画面提示词】这段配什么宠物实景/字幕
- 【语气标签】如 (无奈笑) (轻声) (认真) (自嘲)
- 【台词】带语气标签的口播稿

结尾必须含：①邀请式评论引导（来评论区跟我聊聊…）②下期悬念预告（指向下一篇真实主题）。
严禁：效果提升承诺、命令式评论指令、「橱窗」一词、固化表情模板。
"""
    return prompt


WORD_RE = re.compile(r'<span class="([^"]*)">([^<]*)</span>')
WORD_TYPE = {
    "banned-word": "违禁词",
    "sensitive-word": "敏感词",
    "industry-banned-word": "行业违禁词",
}


def scan_prohibited_words(cfg, api_key, text):
    """忠实复刻 douyin-prohibited-word：调用 cozeSkill/sensitiveWordSearch 扫雷。
    返回 (marked_text, words) —— marked_text 把命中词标成【词】(类型)，words 为去重后的 (词,类型) 列表。"""
    base = deep_get(cfg, "redfox", "api_base")
    path = deep_get(cfg, "redfox", "prohibited_path")
    platform = deep_get(cfg, "prohibited_word", "platform", default="抖音")
    source = deep_get(cfg, "prohibited_word", "source", default="抖音违禁词查询-WorkBuddy")
    max_len = deep_get(cfg, "prohibited_word", "max_content_length", default=3000)

    text = text or ""
    # 超长则按长度切块扫描（忠实复刻 MAX_CONTENT_LENGTH 限制）
    chunks = []
    if len(text) > max_len:
        for i in range(0, len(text), max_len):
            chunks.append(text[i:i + max_len])
    else:
        chunks = [text] if text else []

    seen = {}
    marked_parts = []
    for ch in chunks:
        if not ch.strip():
            marked_parts.append(ch)
            continue
        body = {"content": ch, "platform": platform, "source": source}
        r = call(base + path, body=body, api_key=api_key)
        if r.get("code") != 2000:
            sys.stderr.write(f"[error] 违禁词接口: code={r.get('code')} msg={r.get('msg')}\n")
            sys.exit(1)
        content = (r.get("data") or {}).get("content", ch)
        for cls, word in WORD_RE.findall(content):
            w = word.strip()
            if not w:
                continue
            # 英文误报过滤（忠实复刻原 skill 的处理）
            if re.match(r'^[a-zA-Z]+$', w) and len(w) <= 2:
                continue
            t = WORD_TYPE.get(cls, "敏感词")
            if w not in seen:
                seen[w] = t
        # 转成纯文本标记：把 span 换成【词】(类型)
        plain = WORD_RE.sub(lambda m: f"【{m.group(2)}】({WORD_TYPE.get(m.group(1),'敏感词')})", content)
        marked_parts.append(plain)

    words = [(w, t) for w, t in seen.items()]
    return "\n".join(marked_parts), words


# ---------------- 阶段④：效果验证 ----------------
def verify_work(surge_items, work_title="", work_author="", work_url=""):
    """在每日飙升榜里匹配已发布作品，返回命中项或 None。"""
    def norm(s):
        return (s or "").strip().lower()
    t, a, u = norm(work_title), norm(work_author), norm(work_url)
    for it in surge_items:
        title = norm(it.get("aweme_desc", ""))
        author = norm(it.get("user_nickname", ""))
        url = norm(it.get("share_url", ""))
        if (t and t in title) or (a and a == author) or (u and u in url):
            return it
    return None


# ---------------- 模式入口 ----------------
def cmd_report(args, cfg, api_key, pet_kw):
    search_kw = args.search_kw or deep_get(cfg, "search", "keyword", default="宠物")
    top_n = args.top or deep_get(cfg, "report", "top_n", default=50)
    out_path = args.out or deep_get(cfg, "output", "default_path", default="宠物赛道对标报告.html")
    date = args.date or yesterday()
    pet_enabled = deep_get(cfg, "pet_filter", "enabled", default=True)
    if not pet_enabled:
        pet_kw = []

    print(f"▶ 数据日期: {date} ｜ 搜索词: {search_kw} ｜ 榜单条数: {top_n}")
    print("▶ ① 拉取实时热榜…")
    hot = build(fetch_hot(cfg, api_key), "hot", pet_kw)
    print("▶ ① 宠物搜索作品…")
    search = build(fetch_search(cfg, api_key, kw=search_kw, page_size=top_n)[:20], "search", pet_kw)
    print("▶ ② 动物赛道日榜…")
    daily = build(fetch_daily(cfg, api_key, date=date)[:top_n], "daily", pet_kw)
    print("▶ ② 动物赛道七日飙升榜…")
    weekly = build(fetch_weekly(cfg, api_key, date=date)[:top_n], "weekly", pet_kw)

    daily_pet = [d for d in daily if d["pet"]]
    weekly_pet = [d for d in weekly if d["pet"]]
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    doc = build_report(cfg, hot, search, daily, weekly, daily_pet, weekly_pet, now)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(doc)

    print(f"✅ 报告已生成: {out_path}")
    print(f"   热榜 {len(hot)} 条 | 搜索 {len(search)} 条 | 日榜 {len(daily)}（宠物向 {len(daily_pet)}）| 飙升 {len(weekly)}（宠物向 {len(weekly_pet)}）")


def cmd_replicate(args, cfg, api_key, pet_kw):
    track = deep_get(cfg, "replicate", "track", default="动物")
    style_ref = args.style_ref or deep_get(cfg, "replicate", "style_ref", default="")
    topic = args.topic or ""
    benchmark = args.benchmark or ""

    style_text = ""
    if style_ref and os.path.exists(style_ref):
        style_text = open(style_ref, "r", encoding="utf-8").read()
    elif style_ref:
        sys.stderr.write(f"[warn] 风格参考文件不存在: {style_ref}，忽略\n")

    prompt = build_replicate_prompt(benchmark, style_text, topic, track)
    out = args.out or deep_get(cfg, "replicate", "prompt_out", default="复刻写作提示词.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(prompt)
    print(f"✅ 复刻写作提示词已生成: {out}")
    print("──── 提示词预览（前 600 字）────")
    print(prompt[:600])

    # 若提供了草稿，跑违禁词扫雷（阶段③第二环）
    if args.script and os.path.exists(args.script):
        script_text = open(args.script, "r", encoding="utf-8").read()
        print(f"\n▶ ③ 违禁词扫雷：{args.script}")
        marked, words = scan_prohibited_words(cfg, api_key, script_text)
        scan_out = args.script_out or (os.path.splitext(args.script)[0] + "_扫雷.md")
        with open(scan_out, "w", encoding="utf-8") as f:
            f.write("# 违禁词扫雷报告\n\n")
            f.write(f"扫描时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"命中词数：{len(words)}\n\n")
            if words:
                f.write("## 命中词清单\n")
                for w, t in words:
                    f.write(f"- 【{w}】 ({t})\n")
            else:
                f.write("✅ 未发现违禁/敏感词。\n")
            f.write("\n## 标记后文本\n\n")
            f.write(marked + "\n")
        print(f"   命中 {len(words)} 个词，详情见: {scan_out}")
        for w, t in words:
            print(f"   - 【{w}】 ({t})")
    elif args.script:
        sys.stderr.write(f"[warn] 草稿文件不存在: {args.script}，跳过扫雷\n")


def cmd_verify(args, cfg, api_key, pet_kw):
    date = args.date or yesterday()
    track = args.track or deep_get(cfg, "verify", "track", default="动物")
    print(f"▶ ④ 效果验证：查 {date} {track} 每日点赞飙升榜…")
    surge = build(fetch_daily_surge(cfg, api_key, date=date, track=track), "surge", pet_kw)
    print(f"   榜单共 {len(surge)} 条")
    hit = verify_work(surge, work_title=args.work_title, work_author=args.work_author, work_url=args.work_url)
    out_tpl = deep_get(cfg, "verify", "out", default="效果验证_{date}.md")
    out = args.out or out_tpl.format(date=date)
    if hit:
        lines = [
            f"# 效果验证结果 · {date} {track} 每日飙升榜",
            "",
            f"✅ **已进榜**",
            f"- 排名：{hit.get('rank','-')}",
            f"- 作品：{hit.get('aweme_desc','-')}",
            f"- 作者：{hit.get('user_nickname','-')}",
            f"- 新增点赞：{hit.get('add_digg_count','-')}",
            f"- 新增评论：{hit.get('add_comment_count','-')}",
            f"- 新增收藏：{hit.get('add_collect_count','-')}",
            f"- 新增分享：{hit.get('add_share_count','-')}",
            f"- 发布时间：{hit.get('create_time_str','-')}",
        ]
        print("\n".join(lines))
    else:
        lines = [
            f"# 效果验证结果 · {date} {track} 每日飙升榜",
            "",
            "❌ **未进入当日每日飙升榜**",
            f"查询条件：日期={date}，赛道={track}",
            f"匹配项：标题='{args.work_title}' / 作者='{args.work_author}' / URL='{args.work_url}'",
            "建议：检查发布时间是否满 24h、互动增速是否达标，或隔日再查。",
        ]
        print("\n".join(lines))
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\n✅ 验证结果已写入: {out}")


# ---------------- 主流程 ----------------
def main():
    parser = argparse.ArgumentParser(description="宠物赛道抖音爆款内容流水线（①热点捕捉 ②爆款对标 ③文案复刻 ④效果验证）")
    parser.add_argument("--mode", default="report", choices=["report", "replicate", "verify"],
                        help="运行模式：report(默认,①②报告) / replicate(③文案复刻) / verify(④效果验证)")
    parser.add_argument("--key", default=None, help="红狐 API Key（默认读 config 的 api_key_env 环境变量）")
    parser.add_argument("--config", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml"), help="配置文件路径")
    parser.add_argument("--out", default=None, help="输出路径（report=HTML；replicate=提示词md；verify=结果md）")
    parser.add_argument("--date", default=None, help="数据日期 YYYY-MM-DD（默认昨天）")
    parser.add_argument("--search-kw", default=None, help="搜索关键词（默认读 config search.keyword）")
    parser.add_argument("--top", type=int, default=None, help="榜单条数（最大50，默认读 config report.top_n）")
    # replicate 专用
    parser.add_argument("--topic", default=None, help="[replicate] 本次命题主题")
    parser.add_argument("--benchmark", default=None, help="[replicate] 对标标杆文本/链接（粘贴爆款结构或原稿）")
    parser.add_argument("--style-ref", default=None, help="[replicate] 你的风格/人设参考文本文件路径（可选）")
    parser.add_argument("--script", default=None, help="[replicate] 已写好的草稿文件路径，顺便跑违禁词扫雷")
    parser.add_argument("--script-out", default=None, help="[replicate] 扫雷报告输出路径")
    # verify 专用
    parser.add_argument("--track", default=None, help="[verify] 赛道（默认读 config verify.track）")
    parser.add_argument("--work-title", default=None, help="[verify] 已发布作品标题（用于匹配）")
    parser.add_argument("--work-author", default=None, help="[verify] 已发布作品作者（用于匹配）")
    parser.add_argument("--work-url", default=None, help="[verify] 已发布作品链接（用于匹配）")
    args = parser.parse_args()

    cfg = load_config(args.config)
    api_key_env = deep_get(cfg, "redfox", "api_key_env", default="REDFOX_API_KEY")
    api_key = args.key or os.environ.get(api_key_env, "")

    # API Key 仅在这些场景必填：report/verify 需拉数据；replicate 带 --script 扫雷需扫雷接口
    need_key = (args.mode in ("report", "verify")) or (args.mode == "replicate" and args.script)
    if need_key and not api_key:
        sys.stderr.write(f"[error] 未提供 API Key，请用 --key 或环境变量 {api_key_env} 传入\n")
        sys.exit(1)

    pet_kw = deep_get(cfg, "pet_filter", "keywords", default=DEFAULT_CONFIG["pet_filter"]["keywords"])

    if args.mode == "report":
        cmd_report(args, cfg, api_key, pet_kw)
    elif args.mode == "replicate":
        cmd_replicate(args, cfg, api_key, pet_kw)
    elif args.mode == "verify":
        cmd_verify(args, cfg, api_key, pet_kw)


if __name__ == "__main__":
    main()
