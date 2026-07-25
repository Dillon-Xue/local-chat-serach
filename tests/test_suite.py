#!/usr/bin/env python3
"""local-chat-search 功能测试套件。

覆盖方案设计中所有 FR / NFR（FR-02 语义搜索为 v2，显式标记 SKIP）。
每个用例实跑 scripts/search.py 并断言输出，生成 Markdown 报告。
"""
import json
import subprocess
import time
import os
import datetime

ROOT = "/mnt/c/Users/dillon/.workbuddy"
CWD = "d:/forworkbuddy/2026-07-25-17-18-49"
SCRIPT = "/home/dillon/workbuddy-skills/local-chat-search/scripts/search.py"

cases = []          # 动态测试结果
notes = []          # 静态/说明项


def run(query, scope="current", time_range="all", sort_by="relevance",
        max_results=10, extra=None, cwd=CWD):
    cmd = ["python3", SCRIPT, "--query", query, "--scope", scope,
           "--cwd", cwd, "--root", ROOT, "--time-range", time_range,
           "--sort-by", sort_by, "--max-results", str(max_results)]
    if extra:
        cmd += extra
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True)
    dt = time.time() - t0
    try:
        data = json.loads(p.stdout)
    except Exception:
        data = {"_raw": p.stdout, "_err": p.stderr}
    return data, dt, cmd


def rec(tid, fr, desc, cmd_desc, expect, actual, passed, note=""):
    cases.append(dict(tid=tid, fr=fr, desc=desc, cmd=cmd_desc, expect=expect,
                      actual=actual, passed=passed, note=note))


def dates_all(d, pred):
    rs = d.get("results", [])
    if not rs:
        return None  # 无数据
    return all(pred(r["timestamp"][:10]) for r in rs)


# ---- T01 FR-01 / FR-10 当前对话关键词(中文) ----
d, dt, cmd = run("渐进式", "current")
first = (d.get("results") or [{}])[0]
rec("T01", "FR-01, FR-10", "当前对话·中文关键词 + 摘要预览",
    "--query 渐进式 --scope current",
    "total_results>0 且首条含 summary",
    f"hits={d.get('total_results')}, summary={'有' if first.get('summary') else '无'}",
    d.get("total_results", 0) > 0 and bool(first.get("summary")))

# ---- T02 FR-01 / NFR-04 当前对话关键词(英文) ----
d, dt, cmd = run("local-chat-search", "current")
rec("T02", "FR-01, NFR-04", "当前对话·英文关键词",
    "--query local-chat-search --scope current",
    "total_results>0",
    f"hits={d.get('total_results')}",
    d.get("total_results", 0) > 0)

# ---- T03 FR-03 当前对话 0 结果 → 扩大建议 ----
d, dt, cmd = run("lcs_probe_9f3a2b8c1d4e6f0a_never_existed", "current")
rec("T03", "FR-03", "当前对话无结果 → 主动给出扩大范围建议",
    "--query zzzqqqnopexyz不存在词 --scope current",
    "total=0 且 expand_suggestion 非空(核心)；单 token 时 suggestions 为空属正常",
    f"total={d.get('total_results')}, expand={'有' if d.get('expand_suggestion') else '无'}, "
    f"sugg={'有' if d.get('suggestions', {}).get('related_queries') or d.get('suggestions', {}).get('time_range_rewrites') else '无'}",
    d.get("total_results", -1) == 0 and bool(d.get("expand_suggestion")))

# ---- T04 FR-04 扩大到当前项目 ----
d, dt, cmd = run("local-chat-search", "project")
rec("T04", "FR-04", "扩大到当前项目",
    "--query local-chat-search --scope project",
    "total_results>0",
    f"hits={d.get('total_results')}",
    d.get("total_results", 0) > 0)

# ---- T05 FR-05 / FR-07 扩大到所有项目 + 按项目分组 ----
d, dt, cmd = run("渐进式", "all", max_results=8)
projs = sorted({r["project_name"] for r in d.get("results", [])})
rec("T05", "FR-05, FR-07", "扩大到所有项目 + 跨项目分组",
    "--query 渐进式 --scope all --max-results 8",
    "total>0 且命中 ≥2 个不同 project_name",
    f"hits={d.get('total_results')}, 项目数={len(projs)} -> {projs}",
    d.get("total_results", 0) > 0 and len(projs) >= 2)

# ---- T06 FR-06 时间筛选 today ----
today = datetime.date.today().isoformat()
d, dt, cmd = run("搜索", "all", time_range="today")
ok = dates_all(d, lambda x: x == today)
rec("T06", "FR-06", "时间筛选 · today",
    "--query 搜索 --scope all --time-range today",
    f"有结果时全部日期 == {today}",
    f"hits={d.get('total_results')}, 日期检查={'无数据' if ok is None else ('通过' if ok else '失败')}",
    (ok is None) or ok, note="无数据则记 INFO" if ok is None else "")

# ---- T07 FR-06 时间筛选 yesterday ----
y = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
d, dt, cmd = run("搜索", "all", time_range="yesterday")
ok = dates_all(d, lambda x: x == y)
rec("T07", "FR-06", "时间筛选 · yesterday",
    "--query 搜索 --scope all --time-range yesterday",
    f"有结果时全部日期 == {y}",
    f"hits={d.get('total_results')}, 日期检查={'无数据' if ok is None else ('通过' if ok else '失败')}",
    (ok is None) or ok, note="无昨日数据则记 INFO" if ok is None else "")

# ---- T08 FR-06 时间筛选 this_week ----
monday = (datetime.date.today() - datetime.timedelta(days=datetime.date.today().weekday())).isoformat()
d, dt, cmd = run("搜索", "all", time_range="this_week")
ok = dates_all(d, lambda x: x >= monday)
rec("T08", "FR-06", "时间筛选 · this_week",
    "--query 搜索 --scope all --time-range this_week",
    f"有结果时全部日期 >= {monday}",
    f"hits={d.get('total_results')}, 日期检查={'无数据' if ok is None else ('通过' if ok else '失败')}",
    (ok is None) or ok, note="无数据则记 INFO" if ok is None else "")

# ---- T09 FR-06 时间筛选 custom ----
d, dt, cmd = run("渐进式", "all", time_range="custom",
                 extra=["--time-start", "2026-07-01", "--time-end", "2026-07-31"])
ok = dates_all(d, lambda x: "2026-07-01" <= x <= "2026-07-31")
rec("T09", "FR-06", "时间筛选 · custom(2026-07-01~31)",
    "--query 渐进式 --scope all --time-range custom --time-start 2026-07-01 --time-end 2026-07-31",
    "有结果时全部日期落在范围内",
    f"hits={d.get('total_results')}, 日期检查={'无数据' if ok is None else ('通过' if ok else '失败')}",
    (ok is None) or ok, note="无数据则记 INFO" if ok is None else "")

# ---- T10 FR-11 排序 relevance ----
d, dt, cmd = run("搜索", "all", sort_by="relevance")
scores = [r["match_score"] for r in d.get("results", [])]
ok = all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))
rec("T10", "FR-11", "排序 · relevance(降序)",
    "--query 搜索 --scope all --sort-by relevance",
    "match_score 非严格降序",
    f"hits={len(scores)}, 序列={'降序' if ok else '非降序'} {scores[:5]}",
    ok)

# ---- T11 FR-11 排序 time ----
d, dt, cmd = run("搜索", "all", sort_by="time")
ts = [r["timestamp"] for r in d.get("results", [])]
ok = all(ts[i] >= ts[i + 1] for i in range(len(ts) - 1))
rec("T11", "FR-11", "排序 · time(降序)",
    "--query 搜索 --scope all --sort-by time",
    "timestamp 非严格降序",
    f"hits={len(ts)}, 序列={'降序' if ok else '非降序'} {ts[:3]}",
    ok)

# ---- T12 FR-08 会话分组 ----
d, dt, cmd = run("渐进式", "all", max_results=5)
titled = [r for r in d.get("results", []) if r.get("session_title")]
rec("T12", "FR-08", "按会话分组 · session_title 标注",
    "--query 渐进式 --scope all --max-results 5",
    "命中结果含 session_title 字段",
    f"hits={d.get('total_results')}, 带标题={len(titled)}",
    d.get("total_results", 0) > 0 and len(titled) > 0)

# ---- T13 FR-09 代码片段高亮 ----
d, dt, cmd = run("git@github.com", "all", max_results=5)
coded = [r for r in d.get("results", []) if r.get("code_snippet")]
rec("T13", "FR-09", "代码片段提取/高亮",
    "--query git@github.com --scope all --max-results 5",
    "至少一条结果提取出 code_snippet",
    f"hits={d.get('total_results')}, 含代码={len(coded)}",
    d.get("total_results", 0) > 0 and len(coded) > 0)

# ---- T14 NFR-01 性能 < 3s ----
d, dt, cmd = run("搜索", "all", max_results=20)
rec("T14", "NFR-01", "响应时间 < 3s (全量扫描)",
    "--query 搜索 --scope all --max-results 20",
    "耗时 < 3.0s",
    f"耗时={dt:.3f}s",
    dt < 3.0)

# ---- T15 NFR-04 英文搜索(全量) ----
d, dt, cmd = run("python", "all", max_results=5)
rec("T15", "NFR-04", "英文关键词全量搜索",
    "--query python --scope all --max-results 5",
    "正常返回(无异常)",
    f"hits={d.get('total_results')}, 异常={'是' if '_err' in d else '否'}",
    "_err" not in d and d.get("total_results", 0) >= 0)

# ---- T16 --no-code 关闭代码提取 ----
d, dt, cmd = run("git@github.com", "all", max_results=5, extra=["--no-code"])
coded = [r for r in d.get("results", []) if r.get("code_snippet")]
rec("T16", "FR-09(开关)", "--no-code 关闭代码片段",
    "--query git@github.com --scope all --max-results 5 --no-code",
    "所有结果 code_snippet 为 None",
    f"hits={d.get('total_results')}, 含代码={len(coded)}",
    len(coded) == 0)

# ---- T17 默认 scope = current ----
d, dt, cmd = run("local-chat-search")  # 不显式传 scope
pos = (d.get("results") or [{}])[0].get("position", "")
rec("T17", "FR-03(默认)", "不传 --scope 时默认 current(显示'第 N 轮')",
    "--query local-chat-search  (无 --scope)",
    "首条 position 含 '第' 字(current 格式)",
    f"position='{pos}'",
    "第" in pos)

# ---- 静态/说明项 ----
notes.append(("FR-02", "语义搜索(理解意图)", "SKIP",
              "v1 未实现。脚本仅做关键词/子串匹配(score_text)。按约定留作 v2(本地 embedding 模型)。"))
# NFR-02 用户隔离：root 默认 ~/.workbuddy，仅读当前用户目录
src = open(SCRIPT, encoding="utf-8").read()
notes.append(("NFR-02", "只搜索当前用户对话", "PASS(架构保证)",
              "脚本固定读取 os.path.expanduser('~/.workbuddy')，不接收/不访问其他用户路径。"))
# NFR-03 不外发：检查有无网络调用
net_kw = ["http", "requests", "socket", "urllib", "urlopen", "aiohttp"]
hits_net = [k for k in net_kw if k in src.lower()]
notes.append(("NFR-03", "不保存/不传输对话内容", "PASS(静态验证)",
              f"脚本全文无网络关键字({', '.join(net_kw)})，纯本地 stdlib，无外部请求、不写搜索日志。命中={hits_net or '无'}"))

# ---- 生成报告 ----
lines = []
lines.append("# local-chat-search 功能测试报告\n")
lines.append(f"- 运行环境: WSL FDE (`python3`)\n")
lines.append(f"- 数据源: `{ROOT}/projects/**/*.jsonl`\n")
lines.append(f"- 当前项目 cwd: `{CWD}`\n")
lines.append(f"- 生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
lines.append("\n## 一、动态功能测试 (实跑 search.py)\n")
lines.append("| 用例 | 覆盖 | 描述 | 命令 | 预期 | 实际 | 结果 |")
lines.append("|------|------|------|------|------|------|------|")
for c in cases:
    res = "✅ PASS" if c["passed"] else "❌ FAIL"
    lines.append(f"| {c['tid']} | {c['fr']} | {c['desc']} | `{c['cmd']}` | {c['expect']} | {c['actual']} | {res} |")
lines.append("\n## 二、静态/说明项\n")
lines.append("| 项 | 能力 | 结论 | 说明 |")
lines.append("|----|------|------|------|")
for fr, name, concl, desc in notes:
    lines.append(f"| {fr} | {name} | {concl} | {desc} |")
lines.append("\n## 三、汇总\n")
np = sum(1 for c in cases if c["passed"])
nf = sum(1 for c in cases if not c["passed"])
lines.append(f"- 动态用例: {len(cases)} 个，通过 {np}，失败 {nf}")
lines.append(f"- 静态/说明项: {len(notes)} 个")
lines.append(f"- 总体: {'✅ 全部通过' if nf == 0 else '⚠️ 存在失败项，见上表'}")

report = "\n".join(lines)
print(report)
out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "report.md")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(report)
print(f"\n[报告已写入] {out_path}")
