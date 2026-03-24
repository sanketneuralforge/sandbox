# observability/dashboard.py

from pathlib import Path
from observability.tracer import Tracer
from observability.metrics import MetricsStore
from datetime import datetime

def generate_dashboard(output_path: str = "observability/dashboard.html"):
    tracer = Tracer()
    metrics = MetricsStore()

    traces = tracer.load_traces(limit=20)
    aggregates = metrics.compute_aggregates()

    html = _build_html(traces, aggregates)

    with open(output_path, "w") as f:
        f.write(html)

    print(f"Dashboard generated: {output_path}")
    return output_path

def _build_html(traces: list, aggregates: dict) -> str:
    # Metrics cards
    def pct(v): return f"{v:.0%}" if v else "0%"
    def ms(v): return f"{v:.0f}ms" if v else "0ms"

    metric_cards = ""
    if aggregates:
        metrics_data = [
            ("Total Runs",       aggregates.get("total_runs", 0),          ""),
            ("Completion Rate",  pct(aggregates.get("completion_rate")),    ""),
            ("Cache Hit Rate",   pct(aggregates.get("cache_hit_rate")),     ""),
            ("RAG Hit Rate",     pct(aggregates.get("rag_hit_rate")),       ""),
            ("Error Rate",       pct(aggregates.get("error_rate")),         "warn"),
            ("HITL Rate",        pct(aggregates.get("hitl_rate")),          ""),
            ("Tool Error Rate",  pct(aggregates.get("tool_error_rate")),    "warn"),
            ("Latency p50",      ms(aggregates.get("latency_p50_ms")),      ""),
            ("Latency p95",      ms(aggregates.get("latency_p95_ms")),      "warn"),
            ("Avg Tool Calls",   f"{aggregates.get('avg_tool_calls', 0):.1f}", ""),
        ]
        for label, value, cls in metrics_data:
            color = "#f59e0b" if cls == "warn" else "#6366f1"
            metric_cards += f"""
            <div style="background:#1e1e2e;border-radius:8px;padding:16px;
                        border-left:3px solid {color}">
                <div style="color:#888;font-size:11px;margin-bottom:4px">{label}</div>
                <div style="color:#fff;font-size:20px;font-weight:500">{value}</div>
            </div>"""

    # Verdict distribution
    verdict_dist = aggregates.get("verdict_distribution", {})
    verdict_html = ""
    verdict_colors = {
        "FALSE": "#ef4444", "TRUE": "#22c55e",
        "MISLEADING": "#f59e0b", "UNVERIFIABLE": "#6b7280"
    }
    for verdict, count in verdict_dist.items():
        color = verdict_colors.get(verdict, "#888")
        verdict_html += f"""
        <span style="background:{color}22;color:{color};padding:4px 10px;
                     border-radius:12px;font-size:12px;margin-right:8px">
            {verdict}: {count}
        </span>"""

    # Trace rows
    trace_rows = ""
    for trace in traces:
        status_color = "#22c55e" if trace["status"] == "success" else "#ef4444"
        verdict = trace.get("final_verdict") or "—"
        verdict_color = verdict_colors.get(verdict, "#888")
        duration = f"{trace.get('duration_ms', 0):.0f}ms"
        cache = "✓ cache" if trace.get("cache_hit") else ""
        rag = f"↑ {trace['rag_hits']} RAG" if trace.get("rag_hits") else ""
        claim_short = trace["claim"][:60] + "..." if len(trace["claim"]) > 60 else trace["claim"]
        span_count = len(trace.get("spans", []))

        # Span detail rows
        span_html = ""
        for span in trace.get("spans", []):
            span_status = "✓" if span["status"] == "success" else "✗"
            span_color = "#22c55e" if span["status"] == "success" else "#ef4444"
            span_html += f"""
            <tr style="font-size:11px;color:#888">
                <td style="padding:4px 8px;padding-left:32px">
                    <span style="color:{span_color}">{span_status}</span>
                    [{span['agent']}] {span['name']}
                </td>
                <td style="padding:4px 8px;color:#666">{span['duration_ms']:.0f}ms</td>
                <td colspan="4"></td>
            </tr>"""

        trace_rows += f"""
        <tr style="border-bottom:1px solid #2a2a3e;cursor:pointer"
            onclick="this.nextElementSibling.style.display=
                     this.nextElementSibling.style.display=='none'?'':'none'">
            <td style="padding:10px 8px">
                <span style="color:{status_color}">●</span>
                <code style="color:#a78bfa;font-size:11px;margin-left:6px">
                    {trace['trace_id']}
                </code>
            </td>
            <td style="padding:10px 8px;color:#ccc;max-width:300px;
                       overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
                {claim_short}
            </td>
            <td style="padding:10px 8px">
                <span style="background:{verdict_color}22;color:{verdict_color};
                             padding:2px 8px;border-radius:10px;font-size:11px">
                    {verdict}
                </span>
            </td>
            <td style="padding:10px 8px;color:#888;font-size:12px">{duration}</td>
            <td style="padding:10px 8px;font-size:11px">
                <span style="color:#22c55e">{cache}</span>
                <span style="color:#6366f1;margin-left:6px">{rag}</span>
            </td>
            <td style="padding:10px 8px;color:#666;font-size:11px">
                {span_count} spans
            </td>
        </tr>
        <tr style="display:none;background:#13131f">
            <td colspan="6">{span_html and f'<table style="width:100%">{span_html}</table>' or ''}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Epistemic Auditor — Observability Dashboard</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0f0f1a; color: #ccc; font-family: system-ui, sans-serif;
          padding: 24px; }}
  h1 {{ color: #fff; font-size: 20px; font-weight: 500; margin-bottom: 4px; }}
  h2 {{ color: #888; font-size: 13px; font-weight: 400; margin-bottom: 24px; }}
  h3 {{ color: #aaa; font-size: 13px; font-weight: 500; margin-bottom: 12px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  tr:hover {{ background: #1a1a2e !important; }}
  code {{ font-family: monospace; }}
</style>
</head>
<body>
<h1>Epistemic Auditor</h1>
<h2>Observability Dashboard — generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</h2>

<h3>System Metrics (last 100 runs)</h3>
<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:32px">
    {metric_cards}
</div>

<div style="margin-bottom:24px">
    <h3>Verdict Distribution</h3>
    <div style="margin-top:8px">{verdict_html or '<span style="color:#666">No data yet</span>'}</div>
</div>

<h3>Recent Traces (click to expand spans)</h3>
<div style="background:#13131f;border-radius:8px;overflow:hidden">
<table>
<thead>
<tr style="border-bottom:1px solid #2a2a3e">
    <th style="padding:10px 8px;color:#666;font-size:11px;
               text-align:left;font-weight:400">TRACE ID</th>
    <th style="padding:10px 8px;color:#666;font-size:11px;
               text-align:left;font-weight:400">CLAIM</th>
    <th style="padding:10px 8px;color:#666;font-size:11px;
               text-align:left;font-weight:400">VERDICT</th>
    <th style="padding:10px 8px;color:#666;font-size:11px;
               text-align:left;font-weight:400">DURATION</th>
    <th style="padding:10px 8px;color:#666;font-size:11px;
               text-align:left;font-weight:400">FLAGS</th>
    <th style="padding:10px 8px;color:#666;font-size:11px;
               text-align:left;font-weight:400">SPANS</th>
</tr>
</thead>
<tbody>
    {trace_rows or
     '<tr><td colspan="6" style="padding:24px;text-align:center;color:#444">'
     'No traces yet. Run an audit first.</td></tr>'}
</tbody>
</table>
</div>
</body>
</html>"""