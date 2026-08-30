# 示例 1：默认跑全量宠物对标

## 输入（执行的命令）

```bash
export REDFOX_API_KEY=ak_xxxx        # 红狐 API Key（环境变量）
python main.py --out examples/example-1/output.html
```

| 参数 | 取值 | 来源 |
|------|------|------|
| `--key` | 环境变量 `REDFOX_API_KEY` | 环境变量 |
| `--search-kw` | `宠物` | config.yaml `search.keyword` |
| `--date` | `2026-08-29`（昨天） | 默认 |
| `--top` | `50` | config.yaml `report.top_n` |
| `--out` | `examples/example-1/output.html` | 显式指定 |

## 输出（output.html）

- 文件：`examples/example-1/output.html`（约 65 KB）
- 控制台摘要：`热榜 50 条 | 搜索 20 条 | 日榜 50（宠物向 35）| 飙升 50（宠物向 38）`
- 报告含：KPI 卡片 + 实时热榜表 + 宠物搜索表 + 动物日榜表 + 七日飙升表（宠物向橙底高亮）+ 七日飙升·宠物向优先复刻池 + 选题建议。
- 用浏览器打开 `output.html` 即可查看，所有作品标题均为可点击跳转链接。
