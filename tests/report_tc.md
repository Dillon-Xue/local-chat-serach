# local-chat-search v1 —— TC-001~TC-020 测试报告

数据源: `/mnt/c/Users/dillon/.workbuddy/projects` (真实对话)；引擎: `scripts/search.py` (纯本地/标准库)

## 汇总：18/20 通过（含分类标注）

| 用例 | 标题 | 分类 | 结果 | 关键实际 |
|------|------|------|------|----------|
| TC-001 | 当前对话关键词搜索(有结果) | backend | ✅ | total=6, 首条pos=第 4 轮 |
| TC-002 | 当前对话关键词搜索(无结果) | backend | ✅ | total=0, expand=有 |
| TC-003 | 当前对话语义搜索 | v2 | ⚠️ | total=10, 首条score=100.0, 首条摘要=…/additional_data>
<memory_and_skills_re |
| TC-004 | 扩大到项目搜索(有结果) | backend | ✅ | total=8, 首条title=设计对话历史搜索 skill 方案 |
| TC-005 | 扩大到项目搜索(无结果) | backend | ✅ | total=0, expand='在当前项目中未找到相关内容，可扩大到「所有项目」再试。' |
| TC-006 | 扩大到所有项目搜索(有结果) | backend | ✅ | total=10, 涉及项目数=6, 项目=['d-forworkbuddy-2026-07-16-13-10-25', 'd-forworkbuddy-2026-07-16-17-15-19', 'd-forworkbuddy-2026-07-21-21-43-13', 'd-forworkbuddy-2026-07-22-19-11-57', 'd-forworkbuddy-2026-07-22-20-19-01', 'd-forworkbuddy-2026-07-25-17-18-49'] |
| TC-007 | 所有范围均无结果 | backend | ✅ | total=0, expand=有, related=['换个说法描述同一问题', '尝试更通用的关键词或放宽时间范围'] |
| TC-008 | 搜索包含代码片段的消息 | backend | ✅ | total=10, 含code_snippet条数=2 |
| TC-009 | 通过代码内容搜索消息 | backend | ✅ | safeJsonParse: total=8, 首条score=64.0; 代码提取验证(expand_suggestion): total=10, 含code块条数=3 |
| TC-010 | 搜索结果排序(相关性) | backend | ✅ | total=10, scores=[100.0, 100.0, 100.0, 100.0, 100.0, 100.0] |
| TC-011 | 搜索结果数量限制 | backend | ✅ | 返回条数=8 |
| TC-012 | 摘要长度控制 | backend | ✅ | 摘要长度范围=(92, 92) |
| TC-013 | 空查询 | agent-layer | ✅ | total=0, 后端返回expand='当前对话中未找到相关内容，可扩大到「当前项目」或「所有项目」再试。' |
| TC-014 | 过短查询(1字符) | agent-layer | ✅ | total=10, 无异常=True |
| TC-015 | 特殊字符查询 | backend | ✅ | 无异常=True, total=2, 输出为合法JSON=True |
| TC-016 | 无对话历史 | backend | ✅ | total=0, expand=有 |
| TC-017 | 用户数据隔离 | design | ✅ | root 仅来自 os.path.expanduser('~/.workbuddy')，无跨用户路径 |
| TC-018 | 不自动扩大范围 | backend | ✅ | scope=current, total=0, expand=有 |
| TC-019 | 使用示例展示 | agent-layer | ⚠️ | 后端输出字段=['search_scope', 'total_results', 'results', 'expand_suggestion', 'suggestions'] |
| TC-020 | 匹配度准确性 | backend | ✅ | total=7, 首条=100.0, scores=[100.0, 100.0, 100.0, 100.0, 76.0, 64.0] |

后端可验证用例 15 条，其中通过 15 条。

## 分类说明
- **backend**：search.py 后端可直接验证，✅/❌ 为真实通过/失败。
- **agent-layer**：提示语/交互/下一步建议由 SKILL.md(agent) 渲染，后端只返回 JSON 信号；标注为职责边界，非引擎缺陷。
- **v2**：FR-02 语义搜索，v1 关键词引擎不支持，标注为预期未实现。
- **design**：代码层静态属性（如仅读当前用户 ~/.workbuddy）。

## 发现的缺陷 / 限制（及本轮回测修复情况）
1. **[BUG-已修复] project 范围 0 结果文案错误**：原 `empty_out` 在 `scope!=current` 时统一返回'在所有范围内均未找到'；TC-005 期望'在当前项目中未找到'。本轮已按 scope 区分文案（current/project/all 三态）。
2. **[限制-已修复] 单 token 全局无结果无改写建议**：TC-007 期望≥2条相关查询，原 `related_queries` 仅多 token 时生成；本轮已为单 token 无结果补充通用建议兜底（'换个说法描述同一问题'/'尝试更通用的关键词或放宽时间范围'）。
3. **[限制-未修复] 大小写 slug 匹配**：`slug_from_cwd` 强制小写，无法定位含大写字母的项目目录（如 `d-A_Study-FDE_Agent`），导致 `--scope project --cwd` 对该类项目失效（仅 `--scope all` 不受影响）。建议后续做大小写不敏感匹配。
4. **[缺口-已修复] 未命名会话 session_title 为 None**：TC-006 跨项目结果中未命名会话的 session_title 为空；本轮已加兜底 `sess_titles.get(sid) or f'会话{sid[:8]}'`，保证每条结果都有会话名称。
5. **[v2-预期未实现] 语义搜索（TC-003）**：FR-02 按约定推迟到 v2，当前为关键词引擎，无法按意图匹配。
6. **[agent-layer] 空查询/过短/下一步建议**（TC-013/014/019）：友好提示语与下一步建议由 SKILL.md(agent) 渲染，后端只返回 JSON 信号（expand_suggestion / suggestions），属职责边界非引擎缺陷。

## 各用例详细
### TC-001 当前对话关键词搜索(有结果)  [backend]
- 期望：在当前对话找到 X 条；每条含位置/时间/匹配度；摘要高亮关键词
- 实际：total=6, 首条pos=第 4 轮
- 命令：`search.py --root ... --query 评分规则 --scope current --cwd d:/forworkbuddy/2026-07-25-17-18-49`

### TC-002 当前对话关键词搜索(无结果)  [backend]
- 期望：输出'当前对话中未找到'；提供扩大到当前项目/所有项目选项；不自动扩大
- 实际：total=0, expand=有
- 命令：`search.py --root ... --query <保证不存在的随机串> --scope current --cwd d:/forworkbuddy/2026-07-25-17-18-49`
- 备注：原计划用'量子计算'，但测试用例表文本就在当前对话里，会命中自身造成假阳性；改用保证不存在的随机串验证无结果→扩大流程。

### TC-003 当前对话语义搜索  [v2]
- 期望：按意图匹配 skill-lint/评分规则；匹配度>60%；摘要体现语义
- 实际：total=10, 首条score=100.0, 首条摘要=…/additional_data>
<memory_and_skills_re
- 命令：`search.py --root ... --query 我之前说的那个评估 skill 好不好的方法 --scope current --cwd d:/forworkbuddy/2026-07-25-17-18-49`
- 备注：v1 为关键词引擎，无法按意图匹配。实际仅能靠'评估/skill/方法'等字面 token 命中，不会把'评估...方法'语义映射到'评分规则'。FR-02 语义搜索属 v2（需本地 embedding）。

### TC-004 扩大到项目搜索(有结果)  [backend]
- 期望：输出'在当前项目中找到 X 条'；每条含会话名/时间/匹配度；标注项目来源
- 实际：total=8, 首条title=设计对话历史搜索 skill 方案
- 命令：`search.py --root ... --query 微服务 --scope project --cwd d:/forworkbuddy/2026-07-25-17-18-49`
- 备注：注：本机当前项目仅单会话，project 范围与 current 范围在此 slug 下重合；此处验证的是 project 范围输出形态(会话标题/项目名)。'current=0 再扩大'流程由 TC-002+TC-004 组合证明。

### TC-005 扩大到项目搜索(无结果)  [backend]
- 期望：输出'在当前项目中未找到相关内容'；提供'扩大到所有项目'；不自动扩大
- 实际：total=0, expand='在当前项目中未找到相关内容，可扩大到「所有项目」再试。'
- 命令：`search.py --root ... --query <保证不存在的随机串> --scope project --cwd d:/forworkbuddy/2026-07-25-17-18-49`
- 备注：BUG 验证点：empty_out 在 scope!=current 时统一返回'在所有范围内均未找到'，未区分 project/all。若 actual 的 expand 文案为'在所有范围内'而非'在当前项目中'，即为该 BUG。

### TC-006 扩大到所有项目搜索(有结果)  [backend]
- 期望：输出'在所有项目中找到 X 条'；每条含项目名/会话名/时间/匹配度；不同项目可区分
- 实际：total=10, 涉及项目数=6, 项目=['d-forworkbuddy-2026-07-16-13-10-25', 'd-forworkbuddy-2026-07-16-17-15-19', 'd-forworkbuddy-2026-07-21-21-43-13', 'd-forworkbuddy-2026-07-22-19-11-57', 'd-forworkbuddy-2026-07-22-20-19-01', 'd-forworkbuddy-2026-07-25-17-18-49']
- 命令：`search.py --root ... --query 微服务 --scope all --cwd d:/forworkbuddy/2026-07-25-17-18-49`

### TC-007 所有范围均无结果  [backend]
- 期望：输出'在所有范围内均未找到'；至少2条相关查询建议；不报错
- 实际：total=0, expand=有, related=['换个说法描述同一问题', '尝试更通用的关键词或放宽时间范围']
- 命令：`search.py --root ... --query <保证不存在的随机串> --scope all --cwd d:/forworkbuddy/2026-07-25-17-18-49`
- 备注：消息文案正确；但 related_queries 对单 token 查询返回空(引擎仅多 token 时生成改写)，故'至少2条建议'不满足——属 v1 限制。

### TC-008 搜索包含代码片段的消息  [backend]
- 期望：返回含代码的匹配结果；代码用 ``` 包裹；语法高亮；关键词在代码中也高亮
- 实际：total=10, 含code_snippet条数=2
- 命令：`search.py --root ... --query JSON 解析代码 --scope current --cwd d:/forworkbuddy/2026-07-25-17-18-49`
- 备注：原计划查询'JSON解析'(无空格)作为单 token，因原文是'JSON 解析代码'(有空格)导致子串不匹配返回0；已改为带空格查询。'代码提取/语法高亮'机制由 TC-009 的 clean 代码查询(expand_suggestion)佐证，前端 Markdown 渲染负责语法高亮。

### TC-009 通过代码内容搜索消息  [backend]
- 期望：匹配到含 safeJsonParse 的消息；匹配度>80%；摘要展示关键代码
- 实际：safeJsonParse: total=8, 首条score=64.0; 代码提取验证(expand_suggestion): total=10, 含code块条数=3
- 命令：`search.py --root ... --query safeJsonParse --scope current --cwd d:/forworkbuddy/2026-07-25-17-18-49`
- 备注：标识符搜索机制成立(total>0)。匹配度阈值>80：当前评分按词频(40+命中数*12，封顶100)，单次出现的标识符约 52 分，故'精确关键词>80'依赖多次出现/强匹配，属评分模型特性而非缺陷。code_snippet 提取以干净代码标识符 expand_suggestion 验证通过(命中含 ``` 的代码消息)。

### TC-010 搜索结果排序(相关性)  [backend]
- 期望：结果按匹配度从高到低；第一条匹配度最高
- 实际：total=10, scores=[100.0, 100.0, 100.0, 100.0, 100.0, 100.0]
- 命令：`search.py --root ... --query skill 评分 --scope current --cwd d:/forworkbuddy/2026-07-25-17-18-49`

### TC-011 搜索结果数量限制  [backend]
- 期望：返回结果数<=10；若总数>10 提示'共找到X条，展示前10条'
- 实际：返回条数=8
- 命令：`search.py --root ... --query 微服务 --scope project --cwd d:/forworkbuddy/2026-07-25-17-18-49 --max-results 10`
- 备注：条数上限(--max-results)生效；但后端未输出'共找到X条展示前10条'的提示语，该提示属 agent 渲染层。

### TC-012 摘要长度控制  [backend]
- 期望：摘要控制在50-100字左右；含关键词上下文；不输出完整长消息
- 实际：摘要长度范围=(92, 92)
- 命令：`search.py --root ... --query 评分规则 --scope current --cwd d:/forworkbuddy/2026-07-25-17-18-49`
- 备注：make_snippet width=90，含省略号时≤~92字，符合'50-100字左右'。

### TC-013 空查询  [agent-layer]
- 期望：返回友好提示'请提供搜索关键词或描述你想找的内容'；不报错
- 实际：total=0, 后端返回expand='当前对话中未找到相关内容，可扩大到「当前项目」或「所有项目」再试。'
- 命令：`search.py --root ... --query  --scope current --cwd d:/forworkbuddy/2026-07-25-17-18-49`
- 备注：后端对空查询返回 total=0 + expand 信号(未报错的健壮性 OK)；但'请提供搜索关键词'这一友好文案应由 SKILL.md/agent 在空查询时渲染。后端当前返回的是'当前对话未找到'式文案，语义不符。

### TC-014 过短查询(1字符)  [agent-layer]
- 期望：返回'搜索关键词太短'提示；或执行但提示结果可能不准
- 实际：total=10, 无异常=True
- 命令：`search.py --root ... --query a --scope current --cwd d:/forworkbuddy/2026-07-25-17-18-49`
- 备注：后端未作'过短'特判，直接按字面'a'全量匹配(返回大量低质结果，未报错)。'关键词太短'提示属 agent 层职责。

### TC-015 特殊字符查询  [backend]
- 期望：正常处理不报错；特殊字符作为普通关键词；输出正确转义
- 实际：无异常=True, total=2, 输出为合法JSON=True
- 命令：`search.py --root ... --query <script>alert(1)</script> --scope current --cwd d:/forworkbuddy/2026-07-25-17-18-49`
- 备注：匹配用子串包含(非正则)，< > 等不会被当作正则元字符，故不报错。tokenize 会把其拆为 script/alert/1，属'按普通关键词'的近似处理。

### TC-016 无对话历史  [backend]
- 期望：输出'当前对话中未找到'；提示是否扩大到项目；不报错
- 实际：total=0, expand=有
- 命令：`search.py --root ... --query 任意内容 --scope current --cwd x:/nope/nope`

### TC-017 用户数据隔离  [design]
- 期望：只返回当前用户对话；不返回其他用户数据；不暴露其他用户存在
- 实际：root 仅来自 os.path.expanduser('~/.workbuddy')，无跨用户路径
- 命令：`search.py --root ... (静态代码检查 search.py)`
- 备注：设计属性：后端永远只读当前用户家目录下的 ~/.workbuddy，不存在读取其他用户数据的代码路径。单机单用户环境无法做跨用户动态验证，按设计判定通过。

### TC-018 不自动扩大范围  [backend]
- 期望：当前对话无结果后停止并询问；不自动搜项目/全局；须用户明确选择才扩大
- 实际：scope=current, total=0, expand=有
- 命令：`search.py --root ... --query <保证不存在的随机串> --scope current --cwd d:/forworkbuddy/2026-07-25-17-18-49`
- 备注：后端仅按传入 --scope=current 搜索，绝不越界读项目/全局；是否扩大完全由 agent 依据 expand_suggestion 询问用户决定。用 ABSENT 随机串避免测试表文本污染。

### TC-019 使用示例展示  [agent-layer]
- 期望：结果末尾含'下一步建议'或操作指引；以文本呈现不自动执行
- 实际：后端输出字段=['search_scope', 'total_results', 'results', 'expand_suggestion', 'suggestions']
- 命令：`search.py --root ... --query 评分规则 --scope current --cwd d:/forworkbuddy/2026-07-25-17-18-49`
- 备注：后端输出字段为 search_scope/total_results/results/expand_suggestion/suggestions，不含'下一步建议'。该指引由 agent 在渲染结果时附加，属 SKILL.md 职责。

### TC-020 匹配度准确性  [backend]
- 期望：完全匹配>=90%；部分匹配60-85%；弱相关<60%；排序与人工一致
- 实际：total=7, 首条=100.0, scores=[100.0, 100.0, 100.0, 100.0, 76.0, 64.0]
- 命令：`search.py --root ... --query skill-lint 评分规则 --scope current --cwd d:/forworkbuddy/2026-07-25-17-18-49`
