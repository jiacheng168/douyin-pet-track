# -*- coding: utf-8 -*-
"""
douyin-pet-track —— 宠物赛道抖音爆款对标工具
================================================
一键拉取红狐 API 的：
  ① 实时热榜 (hotSpot/getListByPlatform)
  ② 关键词作品搜索 (dy/data/searchWork)
  ③ 动物赛道·点赞日榜 (dy/search/likesRank)
  ④ 动物赛道·七日点赞飙升榜 (dy/search/hotContentRank)
筛选「宠物向」作品，生成含可点击跳转链接的可视化 HTML 对标报告。

仅依赖标准库（urllib），零额外依赖。
配置从 config.yaml 读取（可选，需 PyYAML；缺失则使用内置默认值）。
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
}


# ---------------- 极简 YAML 解析（仅支持本项目 config.yaml 的子集） ----------------
def _strip_quotes(s):
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("\"", "'"):
        return s[1:-1]
    return s


def _strip_comment(s):
    # 去掉行内注释：首个「空格+#」之后的内容（注释前必有空格）
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
                # 预判下一项是否为 list
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


# ---------------- 四个数据源 ----------------
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
    base = deep_get(cfg, "redfox", "api_base")
    path = deep_get(cfg, "redfox", "weekly_path")
    body = {"source": "宠物对标-skill", "type": "动物", "startTime": date}
    r = call(base + path, body=body, api_key=api_key)
    if r.get("code") != 2000:
        sys.stderr.write(f"[error] 飙升榜接口: code={r.get('code')} msg={r.get('msg')}\n")
        sys.exit(1)
    return r.get("data", {}).get("weeklyRank", [])


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
        elif kind == "weekly":
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


# ---------------- 报告生成 ----------------
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
<div class="note"><b>结论先行：</b>动物赛道里「宠物」是核心内容池。日榜 TOP{len(daily)} 中{pet_label(daily_pet)} 条、七日飙升 TOP{len(weekly)} 中{pet_label(weekly_pet)} 条。优先盯 <b>七日飙升榜里的宠物向作品</b>（正在涨、确定性最高），它们是复刻首选靶子。</div>
<h2>① 热点捕捉</h2>
{table("hot", hot, ["排名","话题（点击跳转）","热度"], "实时全站热榜（橙底=宠物相关）", label)}
{table("search", search, ["作品（点击跳转）","作者","点赞","收藏","评论","分享","发布时间"], "宠物关键词作品搜索 TOP" + str(min(len(search), 20)) + "（按点赞降序）", label)}
<h2>② 爆款对标 · 动物赛道</h2>
{table("daily", daily, ["排名","作品（点击跳转）","作者（粉丝）","收藏","评论","分享","**点赞**","发布时间"], f"动物赛道 点赞日榜 TOP{len(daily)}（橙底={html.escape(label)}）", label)}
{table("weekly", weekly, ["排名","作品（点击跳转）","作者","七日新增收藏","七日新增评论","七日新增分享","**七日新增点赞**","发布时间"], f"动物赛道 七日点赞飙升 TOP{len(weekly)}（橙底={html.escape(label)}）", label)}
<h2>③ 对标锁定 · 正在涨的宠物爆款（优先复刻池）</h2>
<div class="note">以下来自「七日飙升榜·{html.escape(label)}」，代表过去 7 天仍在持续起量的宠物内容，是宠物号最该复刻的方向：</div>
{table("weekly", weekly_pet, ["排名","作品（点击跳转）","作者","七日新增收藏","七日新增评论","七日新增分享","**七日新增点赞**","发布时间"], f"七日飙升 · {html.escape(label)} {len(weekly_pet)} 条", label)}
<h2>④ 给宠物号的对标建议</h2>
<div class="note">
1. <b>题材切口</b>：飙升宠物向高频出现——小奶猫/小狗卖萌、宠物迷惑行为、品种猫狗反差、宠物 meme 小剧场、沉浸式洗护/养宠教程。<br>
2. <b>形态</b>：宠物向爆款以「原声+字幕」轻剧情/记录为主，口播型偏少；口播脚本可叠加「宠物实景画面+痛点口播」，兼顾完播与人设。<br>
3. <b>挂车节奏</b>：爆款宠物内容评论/分享极高（情绪驱动），适合在痛点段自然带出宠物用品。<br>
4. <b>下一步</b>：指定某条对标作品，跑「文案复刻 + 违禁词扫雷」工作流，出可发布文案。
</div>
</div></body></html>"""
    return doc


def pet_label(lst):
    return str(len(lst))


# ---------------- 主流程 ----------------
def main():
    parser = argparse.ArgumentParser(description="宠物赛道抖音爆款对标工具")
    parser.add_argument("--key", default=None, help="红狐 API Key（默认读 config 的 api_key_env 环境变量）")
    parser.add_argument("--config", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml"), help="配置文件路径")
    parser.add_argument("--out", default=None, help="输出 HTML 路径（默认读 config output.default_path）")
    parser.add_argument("--date", default=None, help="数据日期 YYYY-MM-DD（默认昨天）")
    parser.add_argument("--search-kw", default=None, help="搜索关键词（默认读 config search.keyword）")
    parser.add_argument("--top", type=int, default=None, help="榜单条数（最大50，默认读 config report.top_n）")
    args = parser.parse_args()

    cfg = load_config(args.config)

    api_key_env = deep_get(cfg, "redfox", "api_key_env", default="REDFOX_API_KEY")
    api_key = args.key or os.environ.get(api_key_env, "")
    if not api_key:
        sys.stderr.write(f"[error] 未提供 API Key，请用 --key 或环境变量 {api_key_env} 传入\n")
        sys.exit(1)

    search_kw = args.search_kw or deep_get(cfg, "search", "keyword", default="宠物")
    top_n = args.top or deep_get(cfg, "report", "top_n", default=50)
    out_path = args.out or deep_get(cfg, "output", "default_path", default="宠物赛道对标报告.html")
    date = args.date or yesterday()
    pet_kw = deep_get(cfg, "pet_filter", "keywords", default=DEFAULT_CONFIG["pet_filter"]["keywords"])
    pet_enabled = deep_get(cfg, "pet_filter", "enabled", default=True)
    if not pet_enabled:
        pet_kw = []  # 不筛选

    print(f"▶ 数据日期: {date} ｜ 搜索词: {search_kw} ｜ 榜单条数: {top_n}")
    print("▶ 拉取实时热榜…")
    hot = build(fetch_hot(cfg, api_key), "hot", pet_kw)
    print("▶ 宠物搜索作品…")
    search = build(fetch_search(cfg, api_key, kw=search_kw, page_size=top_n)[:20], "search", pet_kw)
    print("▶ 动物赛道日榜…")
    daily = build(fetch_daily(cfg, api_key, date=date)[:top_n], "daily", pet_kw)
    print("▶ 动物赛道七日飙升榜…")
    weekly = build(fetch_weekly(cfg, api_key, date=date)[:top_n], "weekly", pet_kw)

    daily_pet = [d for d in daily if d["pet"]]
    weekly_pet = [d for d in weekly if d["pet"]]
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    doc = build_report(cfg, hot, search, daily, weekly, daily_pet, weekly_pet, now)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(doc)

    print(f"✅ 报告已生成: {out_path}")
    print(f"   热榜 {len(hot)} 条 | 搜索 {len(search)} 条 | 日榜 {len(daily)}（宠物向 {len(daily_pet)}）| 飙升 {len(weekly)}（宠物向 {len(weekly_pet)}）")


if __name__ == "__main__":
    main()
