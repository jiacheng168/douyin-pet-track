# 🐾 douyin-pet-track · 宠物赛道抖音爆款内容流水线

> 忠实复刻「抖音爆款内容专家」工作流：**① 热点捕捉 → ② 爆款对标 → ③ 文案复刻（含违禁词扫雷）→ ④ 效果验证**，一条命令跑通宠物号抖音选题到验证的完整闭环。

---

## 一、项目简介

`douyin-pet-track` 是一个面向**宠物号（养猫 / 养狗 / 异宠）**创作者的抖音内容流水线工具。它把「抖音爆款内容专家」流水线的**四个阶段**沉淀为一条可复用的命令：

- **① 热点捕捉**：调用红狐 hub API，拉取实时全站热榜 + 宠物关键词作品搜索；
- **② 爆款对标**：拉取动物赛道·点赞日榜 + 七日点赞飙升榜，按可配置的「宠物向」词表筛出猫/狗/异宠内容，生成可点击跳转的可视化 HTML 对标报告；
- **③ 文案复刻**：蒸馏对标作品结构 + 你的风格分身 → 产出可直接喂给 AI 的「复刻写作提示词」；若提供草稿，顺带跑违禁词扫雷；
- **④ 效果验证**：发布后查每日点赞飙升榜，验证作品是否进榜。

无需写代码、无需登录抖音后台，从「看风向」到「验证数据」一条命令闭环。

---

## 二、工作流程原理说明

工具严格遵循下图所示的 4 阶段流程，不篡改环节顺序（接口与字段约定忠实复刻红狐官方 skill）：

```
┌─────────────────────────────────────────────────────────────┐
│  ① 热点捕捉（看「风往哪吹」）                                  │
│     ├─ 实时全站热榜      hotSpot/getListByPlatform            │
│     └─ 宠物关键词搜索    dy/data/searchWork                  │
├─────────────────────────────────────────────────────────────┤
│  ② 爆款对标（看「谁正在涨」）                                  │
│     ├─ 动物赛道·点赞日榜   dy/search/likesRank               │
│     └─ 动物赛道·七日飙升   dy/search/hotContentRank          │
│                              (source=抖音七日点赞飙升榜-WorkBuddy → weeklyRank) │
├─────────────────────────────────────────────────────────────┤
│  ③ 文案复刻（把爆款「基因」变成你的稿）                         │
│     ├─ 蒸馏对标结构 + 你的风格 → 复刻写作提示词                │
│     └─ 违禁词扫雷         cozeSkill/sensitiveWordSearch      │
├─────────────────────────────────────────────────────────────┤
│  ④ 效果验证（发完看数据）                                      │
│     └─ 每日点赞飙升榜     dy/search/hotContentRank          │
│                              (source=抖音每日点赞飙升榜 → dailyRank)       │
└─────────────────────────────────────────────────────────────┘
```

**关键设计**

1. **双榜交叉逻辑**：日榜代表「已验证的确定性内容」，七日飙升榜代表「正在起量的潜力内容」；报告把「七日飙升榜里的宠物向作品」单独锁定为「优先复刻池」。
2. **宠物向判定**：不依赖抖音官方分类，而是对作品标题做关键词命中（猫/狗/异宠词表在 `config.yaml` 可改），泛化性强、零额外依赖。
3. **同一端点分流**：`hotContentRank` 靠 `source` 字段分流——七日飙升取 `weeklyRank`，每日飙升（效果验证）取 `dailyRank`。
4. **零依赖**：网络层仅用 Python 标准库 `urllib`，无需 `pip install`；`config.yaml` 为可选配置（有 PyYAML 才读取，缺失自动回落内置默认值）。

---

## 三、功能清单

- ✅ 实时全站热榜抓取（platform=2）
- ✅ 宠物关键词作品搜索（可换「猫咪 / 狗狗 / 布偶猫」等）
- ✅ 动物赛道·点赞日榜抓取
- ✅ 动物赛道·七日点赞飙升榜抓取（官方 source 字段）
- ✅ 宠物向智能筛选（猫 / 狗 / 异宠，关键词可配置）
- ✅ 可视化 HTML 报告：KPI 卡片、榜单表、可点击跳转链接、宠物向橙底高亮、对标锁定区、选题建议
- ✅ **③ 文案复刻**：蒸馏对标结构 + 风格分身 → 复刻写作提示词（multi-copywrite-alchemy 思路）
- ✅ **③ 违禁词扫雷**：调用 `cozeSkill/sensitiveWordSearch`，标记命中词并分类（违禁/敏感/行业违禁）
- ✅ **④ 效果验证**：查每日点赞飙升榜，匹配已发布作品是否进榜
- ✅ 全部参数可配置（搜索词 / 关键词表 / 条数 / 赛道 / 风格参考）
- ✅ 零依赖运行，开箱即用

---

## 四、参数说明

### 入参（命令行）

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--mode` | string | 否 | `report` | 运行模式：`report`(①②报告) / `replicate`(③文案复刻) / `verify`(④效果验证) |
| `--key` | string | 否* | `$REDFOX_API_KEY` | 红狐 API Key；`report`/`verify` 必填，`replicate` 仅带 `--script` 时必填 |
| `--config` | path | 否 | `config.yaml` | 配置文件路径 |
| `--out` | path | 否 | 见各模式 | 输出路径：report=HTML；replicate=提示词md；verify=结果md |
| `--date` | date | 否 | 昨天 | 数据日期 `YYYY-MM-DD` |
| `--search-kw` | string | 否 | 读 `config.search.keyword` | 搜索关键词 |
| `--top` | int | 否 | 读 `config.report.top_n` | 各榜单展示条数（≤ 50） |
| `--topic` | string | 否 | — | `[replicate]` 本次命题主题，如「猫咪半夜跑酷怎么办」 |
| `--benchmark` | string | 否 | — | `[replicate]` 对标标杆文本/链接（粘贴爆款结构或原稿） |
| `--style-ref` | path | 否 | — | `[replicate]` 你的风格/人设参考文本文件路径 |
| `--script` | path | 否 | — | `[replicate]` 已写好的草稿，顺带跑违禁词扫雷 |
| `--track` | string | 否 | 读 `config.verify.track` | `[verify]` 赛道（默认 动物） |
| `--work-title` / `--work-author` / `--work-url` | string | 否 | — | `[verify]` 已发布作品的标题/作者/链接（任一即可匹配） |

### 配置项（config.yaml）

| 配置路径 | 说明 |
|----------|------|
| `redfox.api_base` / `*_path` | 红狐 API 域名与 5 个接口路径（含 `prohibited_path`） |
| `redfox.api_key_env` | 密钥环境变量名（避免明文落盘） |
| `search.keyword` / `search.page_size` | 默认搜索词 / 单次返回条数 |
| `pet_filter.enabled` / `pet_filter.keywords` | 宠物向筛选开关 / 判定词表（可增删） |
| `report.top_n` / `report.title` / `report.highlight_label` | 展示条数 / 标题 / 高亮标注 |
| `replicate.track` / `replicate.style_ref` / `replicate.prompt_out` | 复刻默认赛道 / 风格参考 / 提示词输出 |
| `verify.track` / `verify.out` | 验证默认赛道 / 结果输出模板 |
| `prohibited_word.platform` / `source` / `max_content_length` | 扫雷平台/来源/单次字数上限 |
| `output.default_path` | 默认输出文件名 |

### 返回 / 输出

- **report 模式**：控制台摘要 `热榜 N | 搜索 N | 日榜 N（宠物向 N）| 飙升 N（宠物向 N）` + HTML 报告（KPI + 热榜/搜索/日榜/飙升四表 + 对标锁定池 + 选题建议）。
- **replicate 模式**：控制台预览 + `复刻写作提示词.md`；若带 `--script` 额外生成 `草稿_扫雷.md`（命中词清单 + 标记后文本）。
- **verify 模式**：控制台命中结果 + `效果验证_{date}.md`（已进榜则列排名/新增互动，未进榜则提示排查）。

---

## 五、本地运行部署教程

### 环境要求

- Python 3.8+（仅需标准库，无需 `pip install` 任何包）
- 一个红狐 hub API Key（[获取地址](https://redfox.hk/settings/api-keys?source=github)）

### 步骤

```bash
# 1) 克隆仓库
git clone https://github.com/jiacheng168/douyin-pet-track.git
cd douyin-pet-track

# 2)（可选）如需用 config.yaml 自定义参数，安装 PyYAML
pip install pyyaml
#    不装也能跑，会用脚本内置默认值

# 3) 配置密钥（二选一）
export REDFOX_API_KEY=ak_你的key        # 方式A：环境变量
python main.py                          # 直接用

# 或方式B：命令行传入
python main.py --key ak_你的key --out 报告.html
```

> 注：若脚本报 `curl` / 网络相关错误，多为沙箱代理证书问题；在普通本机直接运行不受影响。

---

## 六、使用示例

### 示例 1：①+② 默认跑一遍（搜索词=宠物，昨天数据）

```bash
export REDFOX_API_KEY=ak_xxxx
python main.py
```

输出：`宠物赛道对标报告.html` + 控制台摘要。

### 示例 2：只看「狗狗」且只要前 30 条

```bash
python main.py --key ak_xxxx --search-kw 狗狗 --top 30 --out 狗狗对标.html
```

### 示例 3：③ 文案复刻 —— 对标结构 + 你的风格 → 复刻提示词

```bash
python main.py --mode replicate \
  --topic "猫咪半夜跑酷怎么办" \
  --benchmark "（粘贴一条对标爆款的原稿或结构）" \
  --style-ref 我的风格.md
# 产出：复刻写作提示词.md（把这份提示词丢给任意 AI 即可写稿）
```

### 示例 4：③ 写完草稿顺带扫雷

```bash
python main.py --mode replicate --key ak_xxxx --script 我的口播稿.txt
# 产出：我的口播稿_扫雷.md（命中词清单 + 标记后文本）
```

### 示例 5：④ 效果验证 —— 查作品是否进每日飙升榜

```bash
python main.py --mode verify --key ak_xxxx \
  --work-title "我家猫凌晨跑酷怎么办" --date 2026-08-30 --track 动物
# 命中则打印排名与新增互动；未命中则提示排查
```

更多真实输入/输出演示见 [`examples/`](./examples) 目录。

---

## 七、GitHub 仓库说明

- **仓库地址**：https://github.com/jiacheng168/douyin-pet-track
- **目录结构**：

```
douyin-pet-track/
├── main.py              # 主入口，实现完整 4 阶段工作流程（零依赖）
├── config.yaml          # 可修改参数配置（搜索词/宠物词表/条数/赛道/风格）
├── skill.yaml           # 技能元数据（YAML）
├── skill.json           # 技能元数据（JSON）
├── SKILL.md             # WorkBuddy 技能说明
├── README.md            # 本文件
├── LICENSE              # MIT 开源协议
├── .gitignore           # Python 项目忽略规则
└── examples/            # 输入/输出演示案例
    ├── example-1/        # report 模式：默认宠物全量
    ├── example-2/        # report 模式：狗狗搜索，top30
    └── example-3/        # 闭环示例：③复刻提示词 + ④效果验证
```

- **版本**：v1.1.0
- **作者**：jiacheng168
- **许可**：MIT

> 本项目为「抖音爆款内容专家」流水线的完整闭环开源实现，接口与字段约定忠实复刻红狐官方 skill。

---

## 八、开源许可

本项目基于 **MIT License** 开源，详见 [LICENSE](./LICENSE)。

```
MIT License
Copyright (c) 2026 jiacheng168

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction...
```

你可以自由使用、修改、分发本工具，包括商业用途，只需保留版权声明。
