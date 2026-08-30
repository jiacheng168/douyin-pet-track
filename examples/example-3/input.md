# 示例 3 · 闭环演示（③ 文案复刻 + ④ 效果验证）

> 本示例为「完整闭环」的调用演示。其中的复刻提示词与验证结果均为**说明性样例**，展示工具在对应模式下会产出什么；真实运行需配置 `REDFOX_API_KEY` 并传入真实对标/作品信息。

## 运行命令

```bash
# ③ 文案复刻：把一条动物赛道爆款的结构，蒸馏成你的复刻写作提示词
python main.py --mode replicate \
  --topic "猫咪半夜跑酷怎么办" \
  --benchmark "我家猫凌晨三点满屋跑酷，我崩溃了，直到发现是这个原因" \
  --style-ref 我的风格.md

# ③ 写完草稿顺带扫雷
python main.py --mode replicate --key $REDFOX_API_KEY --script 我的口播稿.txt

# ④ 效果验证：发完后查是否进入每日飙升榜
python main.py --mode verify --key $REDFOX_API_KEY \
  --work-title "我家猫凌晨跑酷怎么办" --date 2026-08-30 --track 动物
```

## 输入说明

- `--topic`：本次想做的命题（新角度，不照抄标杆）。
- `--benchmark`：从 report 模式「对标锁定池」里挑一条正在涨的宠物爆款，粘贴其标题/原稿/结构。
- `--style-ref`：你的风格/人设参考文本（如「喵叔阿布」口播基调：温和、不凶相、邀请式评论引导）。
- `--script`：AI 按提示词写好的草稿，交给工具跑违禁词扫雷。
- `--work-title` / `--date` / `--track`：发布后用于和每日飙升榜匹配。
