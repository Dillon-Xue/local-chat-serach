# local-chat-search

## 1. Skill 定位

local-chat-search 是一个 **WorkBuddy 本地对话历史搜索** skill。它让你在 WorkBuddy 内部快速找回自己过去聊过的内容——包括当前对话、当前工作区项目、以及所有项目。

定位关键词：**本地优先、隐私优先、零网络、纯标准库**。它不调用任何外部 API，也不把你的对话发往任何服务器，是 WorkBuddy 的"本地记忆检索层"。

## 2. 解决什么问题

- **忘了之前的结论**：一场对话聊了上百轮，或者跨多个项目协作后，你很难记起"当时是怎么决定这个方案的""那个 bug 之前是怎么修的"。
- **手动翻 JSONL 很痛苦**：WorkBuddy 的对话原文以明文 JSONL 存在磁盘上，靠人肉翻找效率极低。
- **隐私顾虑**：不希望把私人对话上传到云端做检索。

本 skill 用一行命令（或由 agent 自动调用）即可在本地完成**范围可控、关键词可检索、带时间筛选与代码高亮**的历史检索，且不留下任何搜索痕迹。

## 3. 功能

- **渐进式范围检索**：`current`（当前对话）/ `project`（当前项目）/ `all`（所有项目）三级，由近及远。
- **关键词匹配**：支持中英文关键词；项目目录 slug 采用"原样精确 → 转小写精确 → 明确未找到"三级 fallback 定位，兼容大小写不一致的项目目录。
- **时间筛选**：`today` / `yesterday` / `this_week` / `last_week` / `custom`（可配 `--time-start`/`--time-end`）。
- **分组与上下文**：结果按会话/项目分组，标注"第 N 轮"与精确时间戳。
- **代码高亮**：自动从消息中提取 ``` 代码块，便于复看当时的实现片段。
- **相关性 / 时间排序**：按 `--sort-by relevance|time` 切换。
- **零结果引导**：无命中时给出"扩大范围"建议与查询改写、时间范围改写提示，帮助继续探索。
- **隐私保障**：纯本地只读，不保存搜索记录，数据不出本机。

## 4. 使用场景与命令

**典型场景**

- 忘了之前怎么解决某个报错 → 在当前对话/项目内搜关键词。
- 跨项目找之前写过的方案或脚本 → `scope=all` 全局搜。
- 只想看最近一周里讨论过的某个主题 → 配合 `--time-range this_week`。
- 让 agent 自己判断"用户是不是在问历史内容"并自动调用检索。

**命令**

由 agent 调用 `scripts/search.py`，或手动执行：

```bash
python3 scripts/search.py --query "渐进式搜索" --scope current --cwd "<当前工作区路径>"

# --scope         current | project | all
# --time-range    all | today | yesterday | this_week | last_week | custom
# --time-start / --time-end   自定义时间范围（YYYY-MM-DD），配合 custom
# --sort-by       relevance | time
# --max-results   返回条数，默认 10
# --no-code       不提取代码片段
# --root          <workbuddy根目录>，覆盖默认 ~/.workbuddy（多用于测试）
```

输出为标准 JSON（`search_scope` / `total_results` / `results` / 建议字段），便于 agent 解析后呈现给用户。

## 5. 项目架构

```
local-chat-search/
├── SKILL.md            # skill 编排：触发条件、范围递进策略、agent 调用约定
├── scripts/
│   └── search.py       # 纯标准库后端（stdio：参数入，JSON 出）
├── README.md           # 本文档
├── .gitignore          # 忽略 tests/、__pycache__/
└── tests/              # 本地测试套件（仅本地，不进 git）
    ├── test_suite.py   # 17 个动态用例（FR/NFR 覆盖）
    └── tc_cases.py     # 用户用例 TC-001~020 回测
```

**`scripts/search.py` 关键模块**

- `slug_from_cwd(cwd)`：工作区路径 → 项目目录 slug（去掉盘符冒号、`/` `\` 转 `-`）。
- `find_project_dir(root, slug)`：三级 fallback 定位 `projects/<slug>` 真实目录；返回 `realpath` 以还原磁盘真实大小写。
- `iter_files(root, scope, cwd)`：按 `current`/`project`/`all` 产出待检索的 `.jsonl` 文件。
- `load_parsed(fp)`：解析单行 JSONL 为 `(ts, text, role)`；带 temp 缓存索引（按 mtime+size 失效）与行预筛，全量扫描 < 3s。
- `score_text` / `make_snippet` / `highlight`：相关性评分、摘要截取、关键词高亮。
- `main()`：参数解析 → 检索 → 排序 → 输出 JSON。

**数据存储**

WorkBuddy 对话原文位于 `~/.workbuddy/projects/<slug>/<conversationId>.jsonl`，每行一条消息（含 `type`、`role`、`timestamp`、`content` 等）。本 skill 只读取这些文件，不做任何写入。
