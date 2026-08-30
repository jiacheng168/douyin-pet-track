# 🐾 douyin-pet-track · 宠物赛道抖音爆款对标工具

> 一键拉取抖音「宠物赛道」的热榜、搜索、日榜、七日飙升榜，自动筛选宠物向作品，生成可点击跳转的可视化 HTML 对标报告。

---

## 一、项目简介

`douyin-pet-track` 是一个面向**宠物号（养猫 / 养狗 / 异宠）**创作者的抖音选题对标工具。它把「抖音爆款内容专家」流水线的 **阶段①热点捕捉 + 阶段②爆款对标** 沉淀为一条可复用的命令：

- 调用红狐 hub API，拉取 **4 个数据源**（实时热榜 / 宠物关键词搜索 / 动物赛道日榜 / 七日点赞飙升榜）；
- 按可配置的「宠物向」关键词表，从动物赛道里**筛出猫 / 狗 / 异宠相关内容**；
- 输出一份 **带可点击跳转链接的可视化 HTML 报告**（KPI 卡片 + 4 张榜单表 + 宠物向高亮 + 对标锁定 + 选题建议）。

无需写代码、无需登录抖音后台，一条命令拿到「动物赛道里哪些宠物内容正在涨」的答案。

---

## 二、工作流程原理说明

工具严格遵循下图所示的 4 步流程，不篡改环节顺序：

```
┌─────────────────────────────────────────────────────────────┐
│  ① 热点捕捉（看「风往哪吹」）                                  │
│     ├─ 实时全站热榜      hotSpot/getListByPlatform            │
│     └─ 宠物关键词搜索    dy/data/searchWork                  │
├─────────────────────────────────────────────────────────────┤
│  ② 爆款对标（看「谁正在涨」）                                  │
│     ├─ 动物赛道·点赞日榜   dy/search/likesRank               │
│     └─ 动物赛道·七日飙升   dy/search/hotContentRank          │
├─────────────────────────────────────────────────────────────┤
│  ③ 宠物筛选                                                  │
│     └─ 标题命中 pet_filter.keywords → 标记「宠物向」(橙底高亮) │
├─────────────────────────────────────────────────────────────┤
│  ④ 报告生成                                                  │
│     └─ 输出 HTML：KPI + 4表 + 对标锁定 + 选题建议             │
└─────────────────────────────────────────────────────────────┘
```

**关键设计**

1. **双榜交叉逻辑**：日榜代表「已验证的确定性内容」，七日飙升榜代表「正在起量的潜力内容」；报告把「七日飙升榜里的宠物向作品」单独锁定为「优先复刻池」。
2. **宠物向判定**：不依赖抖音官方分类，而是对作品标题做关键词命中（猫 / 狗 / 异宠词表在 `config.yaml` 可改），泛化性强、零额外依赖。
3. **零依赖**：网络层仅用 Python 标准库 `urllib`，无需 `pip install`；`config.yaml` 为可选配置（有 PyYAML 才读取，缺失自动回落内置默认值）。

> 说明：本工具覆盖流水线的 **① 热点捕捉 + ② 爆款对标**；下游的 **③ 文案复刻**（风格仿写 + 违禁词扫雷）与 **④ 效果验证**（发布后追踪飙升榜）由同体系其他技能承接。

---

## 三、功能清单

- ✅ 实时全站热榜抓取（platform=2）
- ✅ 宠物关键词作品搜索（可换「猫咪 / 狗狗 / 布偶猫」等）
- ✅ 动物赛道·点赞日榜抓取
- ✅ 动物赛道·七日点赞飙升榜抓取
- ✅ 宠物向智能筛选（猫 / 狗 / 异宠，关键词可配置）
- ✅ 可视化 HTML 报告：KPI 卡片、4 张榜单表、可点击跳转链接、宠物向橙底高亮、对标锁定区、选题建议
- ✅ 全部参数可配置（搜索词 / 关键词表 / 条数 / 输出路径）
- ✅ 零依赖运行，开箱即用

---

## 四、参数说明

### 入参（命令行）

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--key` | string | 否 | `$REDFOX_API_KEY` | 红狐 API Key；缺省读取环境变量 `REDFOX_API_KEY` |
| `--config` | path | 否 | `config.yaml` | 配置文件路径 |
| `--out` | path | 否 | 读 `config.output.default_path` | 输出 HTML 报告路径 |
| `--date` | date | 否 | 昨天 | 数据日期 `YYYY-MM-DD` |
| `--search-kw` | string | 否 | 读 `config.search.keyword` | 搜索关键词（如 `宠物` / `猫咪` / `狗狗`） |
| `--top` | int | 否 | 读 `config.report.top_n` | 各榜单展示条数（≤ 50） |

### 配置项（config.yaml）

| 配置路径 | 说明 |
|----------|------|
| `redfox.api_base` / `*_path` | 红狐 API 域名与 4 个接口路径 |
| `redfox.api_key_env` | 密钥环境变量名（避免明文落盘） |
| `search.keyword` | 默认搜索词 |
| `search.page_size` | 单次搜索返回条数 |
| `pet_filter.enabled` | 是否开启宠物向筛选 |
| `pet_filter.keywords` | 宠物向判定词表（可增删） |
| `report.top_n` | 榜单展示条数 |
| `report.title` / `highlight_label` | 报告标题 / 高亮标注文字 |
| `output.default_path` | 默认输出文件名 |

### 返回 / 输出

- **控制台摘要**：`热榜 N 条 | 搜索 N 条 | 日榜 N（宠物向 N）| 飙升 N（宠物向 N）`
- **HTML 报告文件**：路径由 `--out` 或 `config.output.default_path` 决定，含：
  - KPI 卡片（5 项计数）
  - ① 热点捕捉：实时热榜表 + 宠物搜索表
  - ② 爆款对标：动物日榜表 + 七日飙升表（宠物向橙底高亮）
  - ③ 对标锁定：七日飙升·宠物向 优先复刻池
  - ④ 选题建议

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

### 示例 1：默认跑一遍（搜索词=宠物，昨天数据）

```bash
export REDFOX_API_KEY=ak_xxxx
python main.py
```

输出：`宠物赛道对标报告.html` + 控制台摘要，例如：
```
▶ 数据日期: 2026-08-29 ｜ 搜索词: 宠物 ｜ 榜单条数: 50
✅ 报告已生成: 宠物赛道对标报告.html
   热榜 50 条 | 搜索 20 条 | 日榜 50（宠物向 21）| 飙升 50（宠物向 23）
```

### 示例 2：只看「狗狗」且只要前 30 条

```bash
python main.py --key ak_xxxx --search-kw 狗狗 --top 30 --out 狗狗对标.html
```

### 示例 3：换指定日期

```bash
python main.py --key ak_xxxx --date 2026-08-20
```

更多真实输入/输出演示见 [`examples/`](./examples) 目录。

---

## 七、GitHub 仓库说明

- **仓库地址**：https://github.com/jiacheng168/douyin-pet-track
- **目录结构**：

```
douyin-pet-track/
├── main.py              # 主入口，实现完整工作流程（零依赖）
├── config.yaml          # 可修改参数配置（搜索词/宠物词表/条数/输出）
├── skill.yaml           # 技能元数据（YAML）
├── skill.json           # 技能元数据（JSON）
├── SKILL.md             # WorkBuddy 技能说明
├── README.md            # 本文件
├── LICENSE              # MIT 开源协议
├── .gitignore           # Python 项目忽略规则
└── examples/            # 输入/输出演示案例
    ├── example-1/
    └── example-2/
```

- **版本**：v1.0.0
- **作者**：jiacheng168
- **许可**：MIT

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
