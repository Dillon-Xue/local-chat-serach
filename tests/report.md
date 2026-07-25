# local-chat-search 功能测试报告

- 运行环境: WSL FDE (`python3`)

- 数据源: `/mnt/c/Users/dillon/.workbuddy/projects/**/*.jsonl`

- 当前项目 cwd: `d:/forworkbuddy/2026-07-25-17-18-49`

- 生成时间: 2026-07-25 20:21:50


## 一、动态功能测试 (实跑 search.py)

| 用例 | 覆盖 | 描述 | 命令 | 预期 | 实际 | 结果 |
|------|------|------|------|------|------|------|
| T01 | FR-01, FR-10 | 当前对话·中文关键词 + 摘要预览 | `--query 渐进式 --scope current` | total_results>0 且首条含 summary | hits=10, summary=有 | ✅ PASS |
| T02 | FR-01, NFR-04 | 当前对话·英文关键词 | `--query local-chat-search --scope current` | total_results>0 | hits=10 | ✅ PASS |
| T03 | FR-03 | 当前对话无结果 → 主动给出扩大范围建议 | `--query zzzqqqnopexyz不存在词 --scope current` | total=0 且 expand_suggestion 非空(核心)；单 token 时 suggestions 为空属正常 | total=0, expand=有, sugg=无 | ✅ PASS |
| T04 | FR-04 | 扩大到当前项目 | `--query local-chat-search --scope project` | total_results>0 | hits=10 | ✅ PASS |
| T05 | FR-05, FR-07 | 扩大到所有项目 + 跨项目分组 | `--query 渐进式 --scope all --max-results 8` | total>0 且命中 ≥2 个不同 project_name | hits=8, 项目数=4 -> ['d-forworkbuddy-2026-07-16-13-10-25', 'd-forworkbuddy-2026-07-16-17-15-19', 'd-forworkbuddy-2026-07-25-16-24-19', 'd-forworkbuddy-2026-07-25-17-18-49'] | ✅ PASS |
| T06 | FR-06 | 时间筛选 · today | `--query 搜索 --scope all --time-range today` | 有结果时全部日期 == 2026-07-25 | hits=10, 日期检查=通过 | ✅ PASS |
| T07 | FR-06 | 时间筛选 · yesterday | `--query 搜索 --scope all --time-range yesterday` | 有结果时全部日期 == 2026-07-24 | hits=10, 日期检查=通过 | ✅ PASS |
| T08 | FR-06 | 时间筛选 · this_week | `--query 搜索 --scope all --time-range this_week` | 有结果时全部日期 >= 2026-07-20 | hits=10, 日期检查=通过 | ✅ PASS |
| T09 | FR-06 | 时间筛选 · custom(2026-07-01~31) | `--query 渐进式 --scope all --time-range custom --time-start 2026-07-01 --time-end 2026-07-31` | 有结果时全部日期落在范围内 | hits=10, 日期检查=通过 | ✅ PASS |
| T10 | FR-11 | 排序 · relevance(降序) | `--query 搜索 --scope all --sort-by relevance` | match_score 非严格降序 | hits=10, 序列=降序 [100.0, 100.0, 100.0, 100.0, 100.0] | ✅ PASS |
| T11 | FR-11 | 排序 · time(降序) | `--query 搜索 --scope all --sort-by time` | timestamp 非严格降序 | hits=10, 序列=降序 ['2026-07-25 20:18:07', '2026-07-25 20:17:16', '2026-07-25 20:17:14'] | ✅ PASS |
| T12 | FR-08 | 按会话分组 · session_title 标注 | `--query 渐进式 --scope all --max-results 5` | 命中结果含 session_title 字段 | hits=5, 带标题=5 | ✅ PASS |
| T13 | FR-09 | 代码片段提取/高亮 | `--query git@github.com --scope all --max-results 5` | 至少一条结果提取出 code_snippet | hits=5, 含代码=2 | ✅ PASS |
| T14 | NFR-01 | 响应时间 < 3s (全量扫描) | `--query 搜索 --scope all --max-results 20` | 耗时 < 3.0s | 耗时=1.357s | ✅ PASS |
| T15 | NFR-04 | 英文关键词全量搜索 | `--query python --scope all --max-results 5` | 正常返回(无异常) | hits=5, 异常=否 | ✅ PASS |
| T16 | FR-09(开关) | --no-code 关闭代码片段 | `--query git@github.com --scope all --max-results 5 --no-code` | 所有结果 code_snippet 为 None | hits=5, 含代码=0 | ✅ PASS |
| T17 | FR-03(默认) | 不传 --scope 时默认 current(显示'第 N 轮') | `--query local-chat-search  (无 --scope)` | 首条 position 含 '第' 字(current 格式) | position='第 4 轮' | ✅ PASS |

## 二、静态/说明项

| 项 | 能力 | 结论 | 说明 |
|----|------|------|------|
| FR-02 | 语义搜索(理解意图) | SKIP | v1 未实现。脚本仅做关键词/子串匹配(score_text)。按约定留作 v2(本地 embedding 模型)。 |
| NFR-02 | 只搜索当前用户对话 | PASS(架构保证) | 脚本固定读取 os.path.expanduser('~/.workbuddy')，不接收/不访问其他用户路径。 |
| NFR-03 | 不保存/不传输对话内容 | PASS(静态验证) | 脚本全文无网络关键字(http, requests, socket, urllib, urlopen, aiohttp)，纯本地 stdlib，无外部请求、不写搜索日志。命中=无 |

## 三、汇总

- 动态用例: 17 个，通过 17，失败 0
- 静态/说明项: 3 个
- 总体: ✅ 全部通过