---
name: local-chat-search
description: 搜索 WorkBuddy 本地对话历史，支持按当前对话/当前项目/所有项目三级渐进式检索、关键词匹配、时间筛选、按会话/项目分组、代码片段高亮、相关性/时间排序。当用户忘记之前讨论过的内容、想查找历史代码片段/方案决策/排查过程，或说"搜一下之前的对话""我之前问过…""之前聊过…""查找历史消息""对话历史搜索""翻翻聊天记录"时触发。只读取本地 ~/.workbuddy/projects 下的对话原文，不发送任何数据到外部。
agent_created: true
---

# Local Chat Search — 对话历史本地搜索

当用户想翻找之前和 agent 讨论过的内容（方案决策、代码片段、排查过程、知识点）时使用。本 skill 直接读取 WorkBuddy 本地的对话原文（`~/.workbuddy/projects/<项目slug>/<conversationId>.jsonl`），**完全本地、不发送任何数据到外部服务**。

## 核心策略：渐进式范围
1. 默认只搜**当前对话**（当前打开的会话）。
2. 当前对话 0 结果时，**主动询问**用户是否扩大到「当前项目」或「所有项目」，绝不擅自扩大。
3. 确认后再搜对应范围；仍 0 结果则给出改写建议。

## 触发即执行（不要先寒暄）
用户说出搜索意图后，立即按下面流程执行。

### Step 1 解析查询
- 提取 `query`（关键词或自然语言）。
- 默认 `scope=current`，`time_range=all`，`sort_by=relevance`，`max_results=10`。

### Step 2 运行检索脚本
用环境里的 managed Python 运行（无则回退 `python3`）：

```bash
"<managed-python>" "<SKILL_DIR>/scripts/search.py" \
  --query "<query>" \
  --scope current \
  --cwd "<当前工作区绝对路径>" \
  [--time-range today|yesterday|this_week|last_week|custom --time-start <YYYY-MM-DD> --time-end <YYYY-MM-DD>] \
  [--sort-by relevance|time] \
  [--max-results 10] \
  [--no-code]
```

脚本输出 JSON 到 stdout，结构见文末「输出约定」。若在本机 WSL/其他环境测试，可用 `--root <workbuddy根目录>` 覆盖默认 `~/.workbuddy`。

### Step 3 渲染结果
若 `total_results > 0`，按设计样例渲染：
- 顶部标题 `## 🔍 对话历史搜索结果`，并注明搜索范围（当前对话 / 当前项目 / 所有项目）与命中数。
- 结果列表表格：`# | 位置/会话 | 项目 | 时间 | 匹配度`。
- 详情区：每条展示 时间、摘要（含匹配上下文）、代码片段（若有，用 ``` 围栏高亮）、命中的高亮词。

### Step 4 当前对话无结果 → 询问扩大
若 `total_results == 0` 且 `scope == current`：
- 输出：`当前对话中未找到相关内容。是否扩大搜索范围？`
- 给出选项：`[ ] 扩大到当前项目` / `[ ] 扩大到所有项目`。
- 用户选择后，以对应 `--scope`（project / all）重新运行 Step 2，并渲染。

### Step 5 仍无结果 → 建议
若扩大后仍为 0：输出「在所有范围内均未找到」，并展示脚本返回的 `suggestions.related_queries` 与 `suggestions.time_range_rewrites`，提示用户换关键词或新开讨论。

## 范围与文件来源（实现说明，agent 无需关心）
- 当前对话：`~/.workbuddy/app/sessions.json` 用 `cwd` 映射到 `conversationId`，定位 `projects/<slug>/<conversationId>.jsonl`。
- 当前项目：`projects/<slug>/*.jsonl`。
- 所有项目：`projects/*/*.jsonl`。
- `<slug>` 由 `cwd` 推导（盘符小写、去 `:`、`\`→`-`）。

## 隐私
仅读取当前用户本地 `~/.workbuddy`，不调用任何网络/外部 API，不保存搜索记录。

## 输出约定（脚本 JSON）
```json
{
  "search_scope": "current|project|all",
  "total_results": 0,
  "results": [
    {
      "session_id": "str",
      "session_title": "str|null",
      "project_name": "str",
      "position": "第 N 轮 | 会话标题",
      "timestamp": "YYYY-MM-DD HH:mm:ss",
      "match_score": 0.0,
      "summary": "str",
      "code_snippet": "str|null",
      "highlight": ["str"]
    }
  ],
  "expand_suggestion": "str|null",
  "suggestions": {"related_queries": ["str"], "time_range_rewrites": ["str"]}
}
```

## 局限说明

- 本 skill 按**关键词**搜索：你提供的词需要出现在历史对话里。它不会按"意思相近"去联想（例如搜"部署"不会自动返回"上线"相关结果）。若 0 命中，请引导用户换关键词或扩大范围。
- 历史数据量很大时，首次「所有项目」检索可能需要几秒，之后复用本地缓存会明显加快。
