# 示例 2：狗狗定向 + 限定条数与日期

## 输入（执行的命令）

```bash
export REDFOX_API_KEY=ak_xxxx
python main.py \
  --search-kw 狗狗 \
  --top 30 \
  --date 2026-08-28 \
  --out examples/example-2/output.html
```

| 参数 | 取值 | 说明 |
|------|------|------|
| `--search-kw` | `狗狗` | 覆盖 config 默认「宠物」，只看狗向搜索 |
| `--top` | `30` | 各榜单展示前 30 条 |
| `--date` | `2026-08-28` | 指定历史日期 |
| `--out` | `examples/example-2/output.html` | 输出路径 |

## 输出（output.html）

- 文件：`examples/example-2/output.html`（约 47 KB）
- 控制台摘要：`热榜 50 条 | 搜索 20 条 | 日榜 30（宠物向 20）| 飙升 30（宠物向 26）`
- 与示例 1 的区别：搜索词改为「狗狗」、榜单仅取前 30、数据锚定 2026-08-28；可看到狗狗向内容在动物赛道中的占比与具体爆款样本。

> 提示：以上任意参数都可在不改代码的情况下，通过命令行或 `config.yaml` 调整。
