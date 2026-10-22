"""
RV32I Coverage Reporter
Generates comprehensive Terminal, Markdown, and Interactive HTML Reports
for Functional (Architectural ISA) and Structural Coverage (Verilator Native Line/Toggle/Branch/Expr
and Cocotb Structural Monitors).
"""

import os
import re
import json
import yaml
import subprocess
from pathlib import Path
from cocotb_coverage.coverage import coverage_db


def load_functional_summary_from_yaml(yaml_path):
    """Loads merged functional coverage metrics from a YAML file."""
    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)
    summary = {"groups": {}}
    for k, v in data.items():
        if isinstance(v, dict) and "coverage" in v and "size" in v:
            summary["groups"][k] = {
                "coverage": v["coverage"],
                "size": v["size"],
                "percentage": round(v.get("cover_percentage", 0.0), 2),
                "hits": v.get("bins:_hits", {})
            }
    return summary


def parse_verilator_summary(dat_path):
    """Parses native Verilator coverage report using verilator_coverage --report hier."""
    posix_path = Path(dat_path).as_posix()
    if not Path(posix_path).exists():
        return None

    env = os.environ.copy()
    env["PATH"] = "C:\\msys64\\usr\\bin;C:\\msys64\\ucrt64\\bin;" + env.get("PATH", "")

    cmd = f"verilator_coverage --report hier {posix_path}"
    res = subprocess.run(cmd, capture_output=True, text=True, shell=True, env=env)
    if res.returncode != 0:
        return None

    summary = {"overall": {}, "hierarchy": {}, "units": {}}
    section = None
    current_node = None

    for line in res.stdout.splitlines():
        line_s = line.strip()
        if not line_s:
            continue
        if line_s == "Hierarchy Coverage Summary:":
            section = "hierarchy"
            continue
        elif line_s == "Design Unit Coverage Summary:":
            section = "units"
            continue

        m_metric = re.match(r"^(line|toggle|branch|expr|fsm_state|fsm_arc)\s*:\s*([\d\.]+)%\s*\(\s*(\d+)/\s*(\d+)\)", line_s)
        if m_metric:
            m_type, pct, hits, total = m_metric.groups()
            entry = {"percentage": float(pct), "hits": int(hits), "total": int(total)}
            if current_node is not None:
                current_node[m_type] = entry
            continue

        if section in ("hierarchy", "units"):
            node_name = line_s
            summary[section][node_name] = {}
            current_node = summary[section][node_name]

    # Extract overall TOP coverage
    top_hier = summary.get("hierarchy", {}).get("TOP", {})
    summary["overall"] = top_hier
    return summary


def generate_text_summary(func_summary, struct_summary, verilator_summary=None):
    """Generates an ANSI terminal-formatted summary report."""
    lines = []
    lines.append("=" * 78)
    lines.append("           RV32I COMPREHENSIVE COVERAGE REPORT (VERIFICATION CLOSURE)")
    lines.append("=" * 78)

    # 1. Functional Coverage
    lines.append("\n[1] FUNCTIONAL COVERAGE (ARCHITECTURAL ISA & CORNER CASES)")
    lines.append("-" * 78)
    lines.append(f"{'CoverGroup / CoverPoint':<45} {'Hits':<10} {'Total':<10} {'Coverage':<10}")
    lines.append("-" * 78)

    func_groups = func_summary.get("groups", {})
    total_f_cov = 0
    total_f_size = 0

    for key, data in sorted(func_groups.items()):
        cov = data["coverage"]
        size = data["size"]
        pct = data["percentage"]
        indent = "  " * key.count(".")
        short_name = key.split(".")[-1]
        display_name = f"{indent}{short_name}"
        lines.append(f"{display_name:<45} {cov:<10} {size:<10} {pct:>6.2f}%")
        
        if "." not in key:
            total_f_cov = cov
            total_f_size = size

    total_f_pct = round(total_f_cov / total_f_size * 100.0, 2) if total_f_size > 0 else 0.0
    lines.append("-" * 78)
    lines.append(f"{'TOTAL FUNCTIONAL COVERAGE':<45} {total_f_cov:<10} {total_f_size:<10} {total_f_pct:>6.2f}%")

    # 2. Native Verilator Structural Coverage
    if verilator_summary and verilator_summary.get("overall"):
        v_over = verilator_summary["overall"]
        lines.append("\n[2] NATIVE VERILATOR STRUCTURAL COVERAGE (COMPILER-INSTRUMENTED)")
        lines.append("-" * 78)
        lines.append(f"{'Metric Type':<45} {'Hits':<10} {'Total':<10} {'Coverage':<10}")
        lines.append("-" * 78)
        for m in ["branch", "line", "toggle", "expr"]:
            if m in v_over:
                v = v_over[m]
                name = f"Verilator {m.capitalize()} Coverage"
                lines.append(f"{name:<45} {v['hits']:<10} {v['total']:<10} {v['percentage']:>6.2f}%")

        lines.append("-" * 78)
        lines.append("Design Unit Breakdown:")
        for uname, udata in sorted(verilator_summary.get("units", {}).items()):
            l_str = f"Line: {udata['line']['percentage']:.1f}%" if 'line' in udata else "Line: N/A"
            t_str = f"Toggle: {udata['toggle']['percentage']:.1f}%" if 'toggle' in udata else "Toggle: N/A"
            b_str = f"Branch: {udata['branch']['percentage']:.1f}%" if 'branch' in udata else "Branch: N/A"
            lines.append(f"  {uname:<20} {b_str:<18} {l_str:<18} {t_str}")

    # 3. Cocotb Structural Coverage
    lines.append("\n[3] COCOTB STRUCTURAL COVERAGE (RTL TOGGLES & MUX DECISIONS)")
    lines.append("-" * 78)
    toggle = struct_summary.get("toggle", {})
    t_hits = toggle.get("hit_transitions", 0)
    t_tot = toggle.get("total_transitions", 0)
    t_pct = toggle.get("percentage", 0.0)
    lines.append(f"{'Signal Toggle Transitions':<45} {t_hits:<10} {t_tot:<10} {t_pct:>6.2f}%")

    dec = struct_summary.get("decision", {})
    d_hits = dec.get("hit_decisions", 0)
    d_tot = dec.get("total_decisions", 0)
    d_pct = dec.get("percentage", 0.0)
    lines.append(f"{'Control / Mux Decision States':<45} {d_hits:<10} {d_tot:<10} {d_pct:>6.2f}%")

    # Overall Combined Metric
    combined_score = round((total_f_pct * 0.6) + (t_pct * 0.2) + (d_pct * 0.2), 2)
    lines.append("=" * 78)
    lines.append(f"  COMBINED VERIFICATION SCORE: {combined_score:.2f}%")
    status = "CLOSED (100% FUNCTIONAL MET)" if total_f_pct >= 100.0 else "OPEN (HOLES REMAINING)"
    lines.append(f"  VERIFICATION LOOP STATUS:    {status}")
    lines.append("=" * 78)

    return "\n".join(lines)


def generate_html_report(func_summary, struct_summary, output_path, verilator_summary=None):
    """Generates a rich, interactive HTML coverage dashboard."""
    func_groups = func_summary.get("groups", {})
    toggle = struct_summary.get("toggle", {})
    dec = struct_summary.get("decision", {})

    root_func = func_groups.get("rv32i", {"coverage": 0, "size": 1, "percentage": 0.0})
    f_pct = root_func["percentage"]
    t_pct = toggle.get("percentage", 0.0)
    d_pct = dec.get("percentage", 0.0)
    combined = round((f_pct * 0.6) + (t_pct * 0.2) + (d_pct * 0.2), 1)

    v_over = verilator_summary.get("overall", {}) if verilator_summary else {}
    v_line = v_over.get("line", {}).get("percentage", 0.0)
    v_branch = v_over.get("branch", {}).get("percentage", 0.0)
    v_toggle = v_over.get("toggle", {}).get("percentage", 0.0)

    # Build Functional Rows
    func_rows = []
    for k, v in sorted(func_groups.items()):
        if k == "rv32i":
            continue
        level = k.count(".")
        indent = "&nbsp;&nbsp;&nbsp;&nbsp;" * (level - 1)
        name = k.split(".")[-1]
        pct = v["percentage"]
        color = "#10b981" if pct >= 100.0 else ("#f59e0b" if pct >= 75.0 else "#ef4444")
        func_rows.append(f"""
        <tr>
            <td style="font-family: monospace;">{indent}<b>{name}</b> <span style="color:#64748b; font-size:12px;">({k})</span></td>
            <td>{v['coverage']} / {v['size']}</td>
            <td>
                <div style="background:#e2e8f0; border-radius:4px; height:12px; width:120px; overflow:hidden; display:inline-block; vertical-align:middle; margin-right:8px;">
                    <div style="background:{color}; width:{pct}%; height:100%;"></div>
                </div>
                <span style="font-weight:600; color:{color};">{pct:.1f}%</span>
            </td>
        </tr>
        """)

    # Build Verilator Unit Rows
    verilator_rows = []
    if verilator_summary:
        for uname, udata in sorted(verilator_summary.get("units", {}).items()):
            l_val = udata.get("line", {}).get("percentage", None)
            b_val = udata.get("branch", {}).get("percentage", None)
            t_val = udata.get("toggle", {}).get("percentage", None)

            l_str = f"{l_val:.1f}%" if l_val is not None else "N/A"
            b_str = f"{b_val:.1f}%" if b_val is not None else "N/A"
            t_str = f"{t_val:.1f}%" if t_val is not None else "N/A"

            b_color = "#10b981" if (b_val is not None and b_val >= 100) else "#3b82f6"
            verilator_rows.append(f"""
            <tr>
                <td style="font-family: monospace;"><b>{uname}</b></td>
                <td><span style="color:{b_color}; font-weight:700;">{b_str}</span></td>
                <td>{l_str}</td>
                <td>{t_str}</td>
            </tr>
            """)

    # Build Signal Toggle Rows
    toggle_rows = []
    for sig, sdata in sorted(toggle.get("signals", {}).items()):
        pct = sdata["percentage"]
        color = "#10b981" if pct >= 90.0 else ("#f59e0b" if pct >= 60.0 else "#ef4444")
        toggle_rows.append(f"""
        <tr>
            <td style="font-family: monospace;"><b>{sig}</b></td>
            <td>{sdata['hits']} / {sdata['total']}</td>
            <td>
                <div style="background:#e2e8f0; border-radius:4px; height:12px; width:120px; overflow:hidden; display:inline-block; vertical-align:middle; margin-right:8px;">
                    <div style="background:{color}; width:{pct}%; height:100%;"></div>
                </div>
                <span style="font-weight:600; color:{color};">{pct:.1f}%</span>
            </td>
        </tr>
        """)

    # Build Decision Rows
    dec_rows = []
    for cname, cdata in sorted(dec.get("controls", {}).items()):
        pct = cdata["percentage"]
        color = "#10b981" if pct >= 100.0 else ("#f59e0b" if pct >= 75.0 else "#ef4444")
        unhit_str = ", ".join(str(u) for u in cdata.get("unhit", [])) if cdata.get("unhit") else "None"
        dec_rows.append(f"""
        <tr>
            <td style="font-family: monospace;"><b>{cname}</b></td>
            <td>{cdata['hits']} / {cdata['total']}</td>
            <td>
                <div style="background:#e2e8f0; border-radius:4px; height:12px; width:120px; overflow:hidden; display:inline-block; vertical-align:middle; margin-right:8px;">
                    <div style="background:{color}; width:{pct}%; height:100%;"></div>
                </div>
                <span style="font-weight:600; color:{color};">{pct:.1f}%</span>
            </td>
            <td style="color: {'#ef4444' if unhit_str != 'None' else '#10b981'}; font-family: monospace; font-size:12px;">{unhit_str}</td>
        </tr>
        """)

    verilator_card = ""
    if verilator_summary and v_over:
        verilator_card = f"""
            <div class="card">
                <div class="card-title">Verilator Native Structural</div>
                <div class="card-value" style="color: #06b6d4;">{v_branch:.1f}% Branch</div>
                <div class="card-sub">{v_line:.1f}% Line • {v_toggle:.1f}% Toggle</div>
            </div>
        """

    verilator_section = ""
    if verilator_rows:
        verilator_section = f"""
        <div class="section">
            <h2 class="section-title">2. Verilator Compiler Structural Coverage by Design Unit</h2>
            <table>
                <thead>
                    <tr>
                        <th>Design Unit</th>
                        <th>Branch Coverage</th>
                        <th>Line Coverage</th>
                        <th>Toggle Coverage</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(verilator_rows)}
                </tbody>
            </table>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>RV32I Coverage & Verification Dashboard</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #f8fafc; color: #1e293b; margin: 0; padding: 24px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: #0f172a; color: white; padding: 24px 32px; border-radius: 12px; margin-bottom: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }}
        .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-bottom: 24px; }}
        .card {{ background: white; padding: 20px; border-radius: 10px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
        .card-title {{ font-size: 13px; text-transform: uppercase; color: #64748b; font-weight: 700; letter-spacing: 0.5px; }}
        .card-value {{ font-size: 30px; font-weight: 800; margin: 8px 0; }}
        .card-sub {{ font-size: 13px; color: #94a3b8; }}
        .section {{ background: white; border-radius: 10px; border: 1px solid #e2e8f0; padding: 24px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
        .section-title {{ font-size: 18px; font-weight: 700; margin-top: 0; margin-bottom: 16px; border-bottom: 2px solid #f1f5f9; padding-bottom: 8px; }}
        table {{ width: 100%; border-collapse: collapse; text-align: left; }}
        th, td {{ padding: 10px 14px; border-bottom: 1px solid #f1f5f9; font-size: 14px; }}
        th {{ background: #f8fafc; color: #475569; font-weight: 600; }}
        tr:hover {{ background: #f8fafc; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 style="margin:0 0 8px 0; font-size: 26px;">RV32I Verification Closure & Coverage Dashboard</h1>
            <p style="margin:0; opacity: 0.8; font-size: 14px;">Single-Cycle RISC-V Integer Core • Native Verilator & Cocotb Metrics</p>
        </div>

        <div class="cards">
            <div class="card">
                <div class="card-title">Functional Coverage</div>
                <div class="card-value" style="color: {'#10b981' if f_pct >= 100 else '#f59e0b'};">{f_pct:.1f}%</div>
                <div class="card-sub">{root_func['coverage']} / {root_func['size']} ISA CoverPoints & Bins Hit</div>
            </div>
            {verilator_card}
            <div class="card">
                <div class="card-title">Signal Toggle Coverage</div>
                <div class="card-value" style="color: #3b82f6;">{t_pct:.1f}%</div>
                <div class="card-sub">{toggle.get('hit_transitions',0)} / {toggle.get('total_transitions',0)} Bit Transitions</div>
            </div>
            <div class="card">
                <div class="card-title">Verification Loop Status</div>
                <div class="card-value" style="font-size: 22px; color: {'#10b981' if f_pct >= 100 else '#f59e0b'};">
                    {'LOOP CLOSED' if f_pct >= 100 else 'OPEN HOLES'}
                </div>
                <div class="card-sub">Combined Quality Index: <b>{combined:.1f}%</b></div>
            </div>
        </div>

        <div class="section">
            <h2 class="section-title">1. Functional & Architectural Coverage Groups</h2>
            <table>
                <thead>
                    <tr>
                        <th>Category / CoverPoint</th>
                        <th>Bins Hit / Total</th>
                        <th>Coverage Percentage</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(func_rows)}
                </tbody>
            </table>
        </div>

        {verilator_section}

        <div class="section">
            <h2 class="section-title">3. Multiplexer & Control Path Decisions</h2>
            <table>
                <thead>
                    <tr>
                        <th>Control Signal</th>
                        <th>Decisions Hit / Total</th>
                        <th>Percentage</th>
                        <th>Unhit Decisions</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(dec_rows)}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2 class="section-title">4. Structural Signal Toggle Transitions</h2>
            <table>
                <thead>
                    <tr>
                        <th>Signal / Bus Name</th>
                        <th>Toggled Transitions</th>
                        <th>Toggle Percentage</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(toggle_rows)}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)


def generate_markdown_summary(func_summary, struct_summary, output_path, verilator_summary=None):
    """Exports a markdown summary document suitable for Git and documentation."""
    func_groups = func_summary.get("groups", {})
    toggle = struct_summary.get("toggle", {})
    dec = struct_summary.get("decision", {})
    root_func = func_groups.get("rv32i", {"coverage": 0, "size": 1, "percentage": 0.0})

    md = []
    md.append("# RV32I Verification & Coverage Summary\n")
    md.append(f"**Verification Status:** {'✅ **LOOP CLOSED (100% Functional Coverage Met)**' if root_func['percentage'] >= 100.0 else '⚠️ **OPEN (Gaps Remaining)**'}\n")
    md.append("## High-Level Metrics\n")
    md.append(f"* **Functional (ISA) Coverage:** {root_func['percentage']:.2f}% ({root_func['coverage']} / {root_func['size']} bins)")
    
    if verilator_summary and verilator_summary.get("overall"):
        vo = verilator_summary["overall"]
        md.append(f"* **Verilator Branch Coverage:** {vo.get('branch',{}).get('percentage', 0.0):.2f}% ({vo.get('branch',{}).get('hits',0)} / {vo.get('branch',{}).get('total',0)} branches)")
        md.append(f"* **Verilator Line Coverage:** {vo.get('line',{}).get('percentage', 0.0):.2f}% ({vo.get('line',{}).get('hits',0)} / {vo.get('line',{}).get('total',0)} lines)")
        md.append(f"* **Verilator Signal Toggle Coverage:** {vo.get('toggle',{}).get('percentage', 0.0):.2f}% ({vo.get('toggle',{}).get('hits',0)} / {vo.get('toggle',{}).get('total',0)} toggles)")

    md.append(f"* **Cocotb Signal Toggle Coverage:** {toggle.get('percentage', 0.0):.2f}% ({toggle.get('hit_transitions',0)} / {toggle.get('total_transitions',0)} transitions)")
    md.append(f"* **Control/Mux Decision Coverage:** {dec.get('percentage', 0.0):.2f}% ({dec.get('hit_decisions',0)} / {dec.get('total_decisions',0)} states)\n")

    if verilator_summary and verilator_summary.get("units"):
        md.append("## Verilator Structural Coverage by Design Unit\n")
        md.append("| Design Unit | Branch Coverage | Line Coverage | Toggle Coverage |")
        md.append("| :--- | :---: | :---: | :---: |")
        for uname, udata in sorted(verilator_summary["units"].items()):
            b_str = f"{udata['branch']['percentage']:.1f}%" if 'branch' in udata else "N/A"
            l_str = f"{udata['line']['percentage']:.1f}%" if 'line' in udata else "N/A"
            t_str = f"{udata['toggle']['percentage']:.1f}%" if 'toggle' in udata else "N/A"
            md.append(f"| `{uname}` | {b_str} | {l_str} | {t_str} |")
        md.append("")

    md.append("## Functional Coverage Breakdown\n")
    md.append("| CoverGroup | Hit / Total | Percentage |")
    md.append("| :--- | :---: | :---: |")
    for k, v in sorted(func_groups.items()):
        if k == "rv32i":
            continue
        indent = "&nbsp;&nbsp;" * (k.count(".") - 1)
        name = k.split(".")[-1]
        md.append(f"| {indent}`{name}` | {v['coverage']} / {v['size']} | {v['percentage']:.2f}% |")

    md.append("\n## Control Decision Breakdown\n")
    md.append("| Control Signal | Hits / Total | Percentage | Unhit States |")
    md.append("| :--- | :---: | :---: | :--- |")
    for cname, cdata in sorted(dec.get("controls", {}).items()):
        unhit_str = ", ".join(str(u) for u in cdata.get("unhit", [])) if cdata.get("unhit") else "None"
        md.append(f"| `{cname}` | {cdata['hits']} / {cdata['total']} | {cdata['percentage']:.2f}% | `{unhit_str}` |")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
