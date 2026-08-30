---
name: douyin-pet-track
description: 宠物赛道抖音爆款内容全闭环工具——忠实复刻「抖音爆款内容专家」工作流：① 热点捕捉 ② 爆款对标 ③ 文案复刻（含违禁词扫雷）④ 效果验证。当用户要做宠物号（养猫/养狗/异宠）抖音选题对标、爆款分析、复刻爆款文案、或验证已发作品数据表现时使用。
---

# 宠物赛道抖音爆款内容流水线 (douyin-pet-track)

把「抖音爆款内容专家」流水线的 **四个阶段** 沉淀为一条可复用的命令，形成完整闭环：

- **① 热点捕捉**：实时全站热榜 + 宠物关键词作品搜索
- **② 爆款对标**：动物赛道·点赞日榜 + 七日点赞飙升榜，自动筛宠物向，生成可视化 HTML 报告
- **③ 文案复刻**：蒸馏对标作品结构 + 你的风格分身 → 复刻写作提示词；可接草稿跑违禁词扫雷
- **④ 效果验证**：发布后查每日点赞飙升榜，验证作品是否进榜

## 使用方式

```bash
# ①+② 生成对标报告（默认模式）
python main.py --key ak_xxxx --out 报告.html
python main.py --key ak_xxxx --search-kw 狗狗 --date 2026-08-29 --top 30

# ③ 文案复刻：蒸馏对标结构 + 你的风格 → 复刻写作提示词
python main.py --mode replicate --topic "猫咪半夜跑酷怎么办" --benchmark "（粘贴对标爆款的原稿或结构）" --style-ref 我的风格.md
# ③ 若已写好草稿，顺带跑违禁词扫雷（此时需要 --key）
python main.py --mode replicate --key ak_xxxx --script 我的口播稿.txt

# ④ 效果验证：查已发布作品是否进入每日飙升榜
python main.py --mode verify --key ak_xxxx --work-title "我家猫凌晨跑酷怎么办" --date 2026-08-30 --track 动物
```

- 零额外依赖（仅标准库 urllib）；`config.yaml` 可选（有 PyYAML 才读取，缺失则用内置默认值）。
- 密钥：report / verify 必填，replicate 仅带 `--script` 扫雷时必填；支持 `--key` 或环境变量 `REDFOX_API_KEY`。

## 数据源（红狐 hub，接口与字段约定忠实复刻官方 skill）

| 环节 | 接口 | source 字段 | 返回数据键 |
|------|------|------|------|
| ① 热点捕捉 | `hotSpot/getListByPlatform` | — | 实时全站热榜 |
| ① 热点捕捉 | `dy/data/searchWork` | — | 宠物关键词作品搜索 |
| ② 爆款对标 | `dy/search/likesRank` | — | 动物赛道·点赞日榜 |
| ② 爆款对标 | `dy/search/hotContentRank` | `抖音七日点赞飙升榜-WorkBuddy` | `weeklyRank`（七日飙升） |
| ③ 文案复刻·扫雷 | `cozeSkill/sensitiveWordSearch` | `抖音违禁词查询-WorkBuddy` | 标记后内容 + 命中词 |
| ④ 效果验证 | `dy/search/hotContentRank` | `抖音每日点赞飙升榜` | `dailyRank`（每日飙升） |

> 注：`hotContentRank` 同一端点靠 `source` 字段分流——七日飙升取 `weeklyRank`，每日飙升取 `dailyRank`。

## 可配置项（config.yaml）

- `search.keyword`：搜索词（默认「宠物」，可改「猫咪」「狗狗」）
- `pet_filter.keywords`：宠物向判定词表（猫/狗/异宠，可自行增删）
- `report.top_n`：榜单展示条数（≤50）
- `replicate.track` / `replicate.style_ref`：复刻默认赛道 / 风格参考文件
- `verify.track`：效果验证默认赛道
- `prohibited_word.*`：违禁词扫雷平台/来源/单次字数上限
- `output.default_path`：默认输出文件名

## 说明

本技能是「抖音爆款内容专家」流水线的**完整闭环实现**：阶段①+②对标出报告、阶段③复刻出文案（含扫雷）、阶段④验证数据。复用红狐官方 skill 的接口与字段约定，业务逻辑与原流程一致。
