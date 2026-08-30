---
name: douyin-pet-track
description: 宠物赛道抖音爆款对标工具——一键拉取红狐 API 的实时热榜 / 宠物关键词搜索 / 动物赛道日榜 / 七日飙升榜，自动筛选宠物向作品并生成含可点击跳转链接的可视化 HTML 对标报告。当用户要做宠物号（养猫/养狗/异宠）抖音选题对标、爆款分析、热点捕捉，或想看「动物赛道里哪些宠物内容正在涨」时使用。
---

# 宠物赛道抖音爆款对标工具 (douyin-pet-track)

把「抖音爆款内容专家」流水线的 **阶段①热点捕捉 + 阶段②爆款对标** 沉淀为一条可复用的命令：
自动拉取红狐 API 的 4 个数据源 → 筛选宠物向作品 → 输出可点击跳转的可视化 HTML 对标报告。

## 使用方式

```bash
# 基础用法（密钥走环境变量或 --key）
python main.py --key ak_xxxx --out 报告.html

# 改搜索词 / 日期 / 条数（均可不改代码，改 config.yaml 也行）
python main.py --key ak_xxxx --search-kw 狗狗 --date 2026-08-29 --top 30

# 密钥也可放环境变量，省去 --key
export REDFOX_API_KEY=ak_xxxx
python main.py
```

- 零额外依赖（仅标准库 urllib）；`config.yaml` 可选（有 PyYAML 才读取，缺失则用内置默认值）。
- 输出：控制台打印「热榜/搜索/日榜(宠物向)/飙升(宠物向)」条数摘要 + 一份 HTML 报告（含 KPI 卡片、4 张榜单表、宠物向高亮橙底行、对标锁定与选题建议）。

## 数据源（红狐 hub）

| 环节 | 接口 | 说明 |
|------|------|------|
| ① 热点捕捉 | `hotSpot/getListByPlatform` | 实时全站热榜 |
| ① 热点捕捉 | `dy/data/searchWork` | 宠物关键词作品搜索 |
| ② 爆款对标 | `dy/search/likesRank` | 动物赛道·点赞日榜 |
| ② 爆款对标 | `dy/search/hotContentRank` | 动物赛道·七日点赞飙升榜 |

## 可配置项（config.yaml）

- `search.keyword`：搜索词（默认「宠物」，可改「猫咪」「狗狗」）
- `pet_filter.keywords`：宠物向判定词表（猫/狗/异宠，可自行增删）
- `report.top_n`：榜单展示条数（≤50）
- `output.default_path`：默认输出文件名

## 说明

本技能聚焦「捕捉 + 对标」两端；下游的 **阶段③文案复刻**（风格仿写 + 违禁词扫雷）与 **阶段④效果验证**（发布后追踪飙升榜）由同体系其他技能承接。
