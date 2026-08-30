# -*- coding: utf-8 -*-
"""
养猫赛道抖音对标工具 (douyin-cat-track)
一键拉取红狐 API 的 实时热榜 / 养猫搜索 / 动物赛道日榜 / 七日飙升榜，
筛选猫向作品并生成含可点击跳转链接的可视化 HTML 报告。
仅依赖标准库 urllib，零额外依赖。
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

HOT_URL = "https://redfox.hk/story/api/hotSpot/getListByPlatform"
SEARCH_URL = "https://redfox.hk/story/api/dy/data/searchWork"
DAILY_URL = "https://redfox.hk/story/api/dy/search/likesRank"
WEEKLY_URL = "https://redfox.hk/story/api/dy/search/hotContentRank"

CAT_KW = ["猫", "橘猫", "布偶", "暹罗", "德文", "英短", "美短", "缅因", "波斯",
          "加菲", "银渐层", "金渐层", "奶猫", "小奶", "小猫", "狸花", "奶牛猫",
          "猫砂", "铲屎", "哈基米", "咪咪", "大橘"]


def yesterday():
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")


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


def fetch_hot(api_key):
    r = call(HOT_URL, params={"platform": 2, "source": "养猫对标-skill"}, api_key=api_key)
    if isinstance(r, dict):
        d = r.get("data")
        if isinstance(d, list):
            return d
        if isinstance(d, dict):
            return d.get("list", [])
    if isinstance(r, list):
        return r
    return []


def fetch_search(api_key, kw="养猫", page_size=50):
    body = {"keyword": kw, "source": "养猫对标-skill", "pageNum": 1, "pageSize": page_size}
    r = call(SEARCH_URL, body=body, api_key=api_key)
    if r.get("code") != 2000:
        sys.stderr.write(f"[error] 搜索接口: code={r.get('code')} msg={r.get('msg')}\n")
        sys.exit(1)
    return r.get("data", {}).get("list", [])


def fetch_daily(api_key, date=None):
    date = date or yesterday()
    body = {"source": "养猫对标-skill", "type": "动物", "startTime": date, "endTime": date}
    r = call(DAILY_URL, body=body, api_key=api_key)
    if r.get("code") != 2000:
        sys.stderr.write(f"[error] 日榜接口: code={r.get('code')} msg={r.get('msg')}\n")
        sys.exit(1)
    return r.get("data", [])


def fetch_weekly(api_key, date=None):
    date = date or yesterday()
    body = {"source": "养猫对标-skill", "type": "动物", "startTime": date}
    r = call(WEEKLY_URL, body=body, api_key=api_key)
    if r.get("code") != 2000:
        sys.stderr.write(f"[error] 飙升榜接口: code={r.get('code')} msg={r.get('msg')}\n")
        sys.exit(1)
    return r.get("data", {}).get("weeklyRank", [])


def is_cat(title):
    return any(k in (title or "") for k in CAT_KW)


def extract_link(cell):
    m = re.search(r"\[(.*?)\]\((.*?)\)", cell)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return (cell or "").strip(), ""


def clean_bold(s):
    return (s or "").replace("**", "").strip()


def build(items, kind):
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
                    "like": like, "cat": is_cat(title), **extra})
    return out


def fmt(v):
    return html.escape(str(v)) if v not in (None, "") else "-"


def row_html(d, kind):
    cls = ' class="cat"' if d["cat"] else ""
    title_cell = f'<a href="{html.escape(d["url"])}" target="_blank">{html.escape(d["title"] or "(无标题)")}</a>'
    if kind == "hot":
        return f'<tr{cls}><td>{html.escape(str(d["rank"]))}</td><td>{title_cell}</td><td>{html.escape(str(d["like"]))}</td></tr>'
    if kind == "search":
        extra = f'<td>{fmt(d.get("collect"))}</td><td>{fmt(d.get("comment"))}</td><td>{fmt(d.get("share"))}</td><td>{fmt(d.get("time"))}</td>'
        return f'<tr{cls}><td>{title_cell}</td><td>{html.escape(str(d["author"]))}</td><td>{fmt(d["like"])}</td>{extra}</tr>'
    extra = f'<td>{fmt(d.get("collect"))}</td><td>{fmt(d.get("comment"))}</td><td>{fmt(d.get("share"))}</td><td><b>{fmt(d["like"])}</b></td><td>{fmt(d.get("time"))}</td>'
    return f'<tr{cls}><td>{html.escape(str(d["rank"]))}</td><td>{title_cell}</td><td>{html.escape(str(d["author"]))}</td>{extra}</tr>'


def table(kind, data, headers, note=""):
    h = "".join(f"<th>{x}</th>" for x in headers)
    body = "\n".join(row_html(d, kind) for d in data)
    return f'<h3>{note}</h3><table><thead><tr>{h}</tr></thead><tbody>{body}</tbody></table>'


def main():
    p = argparse.ArgumentParser(description="养猫赛道抖音对标工具")
    p.add_argument("--key", default=os.environ.get("REDFOX_API_KEY", ""), help="红狐 API Key")
    p.add_argument("--out", default="养猫赛道对标报告.html", help="输出 HTML 路径")
    p.add_argument("--date", default=None, help="数据日期 YYYY-MM-DD（默认昨天）")
    p.add_argument("--search-kw", default="养猫", help="搜索关键词")
    p.add_argument("--top", type=int, default=50, help="榜单条数（最大50）")
    args = p.parse_args()

    if not args.key:
        sys.stderr.write("[error] 未提供 REDFOX_API_KEY，请用 --key 或环境变量传入\n")
        sys.exit(1)

    print("▶ 拉取实时热榜…")
    hot = build(fetch_hot(args.key), "hot")
    print("▶ 养猫搜索作品…")
    search = build(fetch_search(args.key, kw=args.search_kw, page_size=args.top)[:20], "search")
    print("▶ 动物赛道日榜…")
    daily = build(fetch_daily(args.key, date=args.date), "daily")
    print("▶ 动物赛道七日飙升榜…")
    weekly = build(fetch_weekly(args.key, date=args.date), "weekly")

    daily_cat = [d for d in daily if d["cat"]]
    weekly_cat = [d for d in weekly if d["cat"]]
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    doc = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>养猫赛道·抖音热榜+对标报告</title>
<style>
*{{box-sizing:border-box}}
body{{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;margin:0;background:#f3eefe;color:#2a2350;padding:28px}}
.wrap{{max-width:1100px;margin:0 auto;background:#fff;border-radius:16px;padding:32px;box-shadow:0 8px 30px rgba(107,79,187,.12)}}
h1{{color:#6b4fbb;margin:0 0 4px;font-size:26px}}
.sub{{color:#8a82b8;font-size:13px;margin-bottom:20px}}
h2{{color:#6b4fbb;border-left:5px solid #6b4fbb;padding-left:10px;margin-top:32px;font-size:19px}}
h3{{color:#4a3f80;font-size:15px;margin:18px 0 8px}}
table{{width:100%;border-collapse:collapse;font-size:13px;margin-bottom:8px}}
th{{background:#6b4fbb;color:#fff;text-align:left;padding:8px 10px;white-space:nowrap}}
td{{border-bottom:1px solid #eee;padding:7px 10px;vertical-align:top}}
tr.cat{{background:#fff5e6}}
tr.cat td:first-child{{box-shadow:inset 3px 0 0 #ff9f43}}
a{{color:#6b4fbb;text-decoration:none}}
a:hover{{text-decoration:underline}}
.note{{background:#f8f5ff;border-left:4px solid #6b4fbb;padding:12px 16px;border-radius:8px;font-size:13px;line-height:1.7;margin:10px 0}}
.kpi{{display:flex;gap:14px;flex-wrap:wrap;margin:14px 0}}
.kpi div{{background:#f3eefe;border-radius:12px;padding:14px 20px;text-align:center;flex:1;min-width:110px}}
.kpi b{{display:block;font-size:24px;color:#6b4fbb}}
.kpi span{{font-size:12px;color:#8a82b8}}
</style></head><body><div class="wrap">
<h1>🐱 养猫赛道 · 抖音热榜 + 对标报告</h1>
<div class="sub">生成时间 {now} ｜ 数据来源：红狐 hub（热榜 / 搜索 / 动物赛道日榜 / 七日飙升榜）｜ 橙底行 = 猫垂直向内容</div>
<div class="kpi">
<div><b>{len(hot)}</b><span>实时热榜话题</span></div>
<div><b>{len(search)}</b><span>养猫搜索样本</span></div>
<div><b>{len(daily)}</b><span>动物日榜(全)</span></div>
<div><b>{len(daily_cat)}</b><span>日榜·猫向</span></div>
<div><b>{len(weekly_cat)}</b><span>飙升·猫向</span></div>
</div>
<div class="note"><b>结论先行：</b>动物赛道里「猫」是绝对主力。日榜 TOP{len(daily)} 中猫向 <b>{len(daily_cat)}</b> 条、七日飙升 TOP{len(weekly)} 中猫向 <b>{len(weekly_cat)}</b> 条。优先盯 <b>七日飙升榜里的猫向作品</b>（正在涨、确定性最高），它们是复刻首选靶子。</div>
<h2>① 热点捕捉</h2>
{table("hot", hot, ["排名","话题（点击跳转）","热度"], "实时全站热榜（橙底=宠物/猫相关）")}
{table("search", search, ["作品（点击跳转）","作者","点赞","收藏","评论","分享","发布时间"], "养猫关键词作品搜索 TOP20（按点赞降序）")}
<h2>② 爆款对标 · 动物赛道</h2>
{table("daily", daily, ["排名","作品（点击跳转）","作者（粉丝）","收藏","评论","分享","**点赞**","发布时间"], f"动物赛道 点赞日榜 TOP{len(daily)}（橙底=猫向）")}
{table("weekly", weekly, ["排名","作品（点击跳转）","作者","七日新增收藏","七日新增评论","七日新增分享","**七日新增点赞**","发布时间"], f"动物赛道 七日点赞飙升 TOP{len(weekly)}（橙底=猫向）")}
<h2>③ 对标锁定 · 正在涨的猫爆款（优先复刻池）</h2>
<div class="note">以下来自「七日飙升榜·猫向」，代表过去 7 天仍在持续起量的猫内容，是养猫号最该复刻的方向：</div>
{table("weekly", weekly_cat, ["排名","作品（点击跳转）","作者","七日新增收藏","七日新增评论","七日新增分享","**七日新增点赞**","发布时间"], f"七日飙升 · 猫向 {len(weekly_cat)} 条")}
<h2>④ 给养猫号的对标建议</h2>
<div class="note">
1. <b>题材切口</b>：飙升猫向高频出现——小奶猫卖萌、猫咪迷惑行为、橘猫/品种猫反差、猫 meme 小剧场、沉浸式洗猫/养猫教程。<br>
2. <b>形态</b>：猫向爆款以「原声+字幕」轻剧情/萌宠记录为主，口播型偏少；口播脚本可叠加「猫咪实景画面+痛点口播」，兼顾完播与人设。<br>
3. <b>挂车节奏</b>：爆款猫内容评论/分享极高（情绪驱动），适合在痛点段自然带出猫用品。<br>
4. <b>下一步</b>：指定某条对标作品，跑「文案复刻 + 违禁词扫雷」工作流，出可发布文案。
</div>
</div></body></html>"""

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(doc)

    print(f"✅ 报告已生成: {args.out}")
    print(f"   热榜 {len(hot)} 条 | 养猫搜索 {len(search)} 条 | 日榜 {len(daily)}（猫向 {len(daily_cat)}）| 飙升 {len(weekly)}（猫向 {len(weekly_cat)}）")


if __name__ == "__main__":
    main()
