# local-chat-search

WorkBuddy skill：在本地搜索你的对话历史（当前对话 / 当前项目 / 所有项目）。

- **纯本地、零网络**：只读 `~/.workbuddy/projects` 下的对话原文，不调用任何外部 API。
- **渐进式范围**：先搜当前对话，无结果再询问是否扩大到当前项目 / 所有项目。
- **能力**：关键词匹配（中英）、时间筛选（今天/昨天/本周/上周/自定义）、按会话/项目分组、代码片段高亮、按相关性/时间排序。
- **隐私**：不保存搜索记录，数据不出本机。

## 安装
把本目录放到 `~/.workbuddy/skills/local-chat-search/`（或任意 WorkBuddy skills 目录）即可。

## 用法
在对话中说“搜索我之前讨论过的 XXX / 翻翻聊天记录 / 我之前问过…”触发；或由 agent 调用 `scripts/search.py`。

```bash
python3 scripts/search.py --query "渐进式搜索" --scope current --cwd "<当前工作区路径>"
# scope: current | project | all
# --time-range today|yesterday|this_week|last_week|custom (配合 --time-start/--time-end)
# --sort-by relevance|time  --max-results 10  --no-code
# 测试可用 --root <workbuddy根目录> 覆盖默认 ~/.workbuddy
```

## 已知限制 / 后续迭代
- 语义搜索（理解意图而非精确词）v1 未实现，后续可接入本地 embedding 模型（离线）。
- “所有项目”为流式逐文件扫描，通常 <3s；后续可加本地索引进一步加速。
