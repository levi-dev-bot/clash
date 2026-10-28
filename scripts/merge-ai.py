#!/usr/bin/env python3
"""
merge-ai.py —— 每日自动生成 AI.list(AI 服务风控严名单,Clash classical 域名部分)

合并逻辑:
  1. ai-core.list   手工核心(2026-10-27 定稿 171 条),原样保底,不做任何过滤
  2. L1 VPSDance    rules/clash/global.yaml(境外聚合版)
  3. L2 Repcz/Tool  mihomo/Rules/AI.list 差集
  过滤(只作用于 L1/L2 上游层,核心层不受影响):
  - exclude-cn.list 命中(精确或子域)即剔除
  - 国内域名后缀(.cn/.com.cn 等)剔除
  - 非域名规则(PROCESS-NAME/IP-CIDR/IP-ASN)不进本文件 → 归 AI-IP.list 或删除

输出: AI.list(classical: DOMAIN-SUFFIX / DOMAIN / DOMAIN-KEYWORD)
规则: - 有变化才写文件;L1 拉取失败整次跳过(exit 1),保留旧文件。
"""
import io
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

L1_URLS = [
    "https://raw.githubusercontent.com/VPSDance/ai-proxy-rules/main/rules/clash/global.yaml",
    "https://ghproxy.net/https://raw.githubusercontent.com/VPSDance/ai-proxy-rules/main/rules/clash/global.yaml",
]
L2_URLS = [
    "https://raw.githubusercontent.com/Repcz/Tool/master/mihomo/Rules/AI.list",
    "https://ghproxy.net/https://raw.githubusercontent.com/Repcz/Tool/master/mihomo/Rules/AI.list",
]

CN_SUFFIXES = (".cn", ".com.cn", ".net.cn", ".org.cn", ".gov.cn")
DOM_TYPES = ("DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD")

OUT = os.path.join(REPO_DIR, "AI.list")


def fetch(urls):
    for u in urls:
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "levi-dev-bot/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                if r.status == 200:
                    return r.read().decode("utf-8", "replace")
        except Exception as e:
            print(f"  [warn] {u} -> {e}", file=sys.stderr)
    return None


def parse_core(text):
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 2 and parts[0] in DOM_TYPES:
            out.append((parts[0], parts[1]))
    return out


def parse_l1(text):
    """YAML payload: `  - DOMAIN-SUFFIX,foo.com`"""
    out = []
    for m in re.finditer(r"^\s*-\s*(DOMAIN(?:-SUFFIX|-KEYWORD)?),(\S+)\s*$", text, re.M):
        out.append((m.group(1), m.group(2)))
    return out


def parse_l2(text):
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 2 and parts[0] in DOM_TYPES:
            out.append((parts[0], parts[1]))
    return out


def is_cn_domain(dom):
    return dom.lower().endswith(CN_SUFFIXES)


def is_excluded(dom, excl):
    d = dom.lower()
    if d in excl:
        return True
    return any(d.endswith("." + e) for e in excl)


def main():
    ts = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")

    with io.open(os.path.join(REPO_DIR, "ai-core.list"), encoding="utf-8") as f:
        core_rules = parse_core(f.read())
    with io.open(os.path.join(REPO_DIR, "exclude-cn.list"), encoding="utf-8") as f:
        excl = {
            ln.strip().lower() for ln in f
            if ln.strip() and not ln.strip().startswith("#")
        }

    l1_raw = fetch(L1_URLS)
    if l1_raw is None:
        print("[fatal] L1(VPSDance) 拉取失败,保留旧 AI.list", file=sys.stderr)
        sys.exit(1)
    l2_raw = fetch(L2_URLS)
    if l2_raw is None:
        print("[warn] L2(Repcz) 拉取失败,本轮只用 L1", file=sys.stderr)
    l1 = parse_l1(l1_raw)
    l2 = parse_l2(l2_raw) if l2_raw else []

    seen = set()
    final = []

    for typ, val in core_rules:  # 1) 核心层原样保底
        seen.add((typ, val))
        final.append((typ, val, "core"))

    def add_upstream(typ, val, layer):  # 2/3) 上游层过滤
        if (typ, val) in seen:
            return
        dom = val.lower()
        if is_excluded(dom, excl) or is_cn_domain(dom):
            return
        seen.add((typ, val))
        final.append((typ, val, layer))

    for typ, val in l1:
        add_upstream(typ, val, "l1")
    for typ, val in l2:
        add_upstream(typ, val, "l2")

    lines = [
        "# AI.list —— AI 服务风控严名单(域名部分)",
        "# 格式: Clash / mihomo classical(DOMAIN-SUFFIX / DOMAIN / DOMAIN-KEYWORD)",
        "# 数据源: ai-core.list(手工核心,保底) + VPSDance/ai-proxy-rules(global 境外聚合)",
        "#         + Repcz/Tool(AI) 补充;国内 AI 服务商由 exclude-cn.list 剔除",
        f"# 生成: {ts}  共 {len(final)} 条(核心 {len(core_rules)} / L1 新增 {sum(1 for x in final if x[2]=='l1')} / L2 新增 {sum(1 for x in final if x[2]=='l2')})",
        "# 由 scripts/merge-ai.py 每日 04:00 自动生成,勿手改本文件;补条目请改 ai-core.list",
        "#",
        "# 用法一(subconverter / Clash-LIAN.ini): ruleset=AI,<本文件URL>",
        "# 用法二(mihomo rule-providers): behavior: classical + format: text",
        "# 配套 IP 规则见 AI-IP.list。本文件不含策略名,策略由规则引用处指定。",
        "",
    ]
    for typ, val, _ in final:
        lines.append(f"{typ},{val}")
    new_text = "\n".join(lines) + "\n"

    ok = True
    for typ, val in core_rules:
        if f"{typ},{val}" not in new_text:
            ok = False
            print(f"[fatal] 核心条目丢失: {typ},{val}", file=sys.stderr)
    if len(final) < len(core_rules) or len(final) < 150:
        ok = False
        print(f"[fatal] 生成条数异常: {len(final)}", file=sys.stderr)
    if not ok:
        sys.exit(1)

    old = None
    if os.path.exists(OUT):
        with io.open(OUT, encoding="utf-8") as f:
            old = f.read()
    if old == new_text:
        print(f"[ok] 无变化,不提交(共 {len(final)} 条)")
        return
    with io.open(OUT, "w", encoding="utf-8") as f:
        f.write(new_text)
    l1n = sum(1 for x in final if x[2] == "l1")
    l2n = sum(1 for x in final if x[2] == "l2")
    print(f"[ok] 已写入: {len(final)} 条(核心 {len(core_rules)} / L1 新增 {l1n} / L2 新增 {l2n})")


if __name__ == "__main__":
    main()
