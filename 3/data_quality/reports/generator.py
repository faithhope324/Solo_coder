import os
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..core.config import CheckResult, CheckStatus, ReportConfig


class ReportGenerator:
    def __init__(self, report_config: ReportConfig = None):
        self.report_config = report_config or ReportConfig()

    def generate(
        self,
        results: List[CheckResult],
        summary: Dict[str, Any],
        output_path: Optional[str] = None,
    ) -> str:
        if not results:
            raise ValueError("No check results to generate report from")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_format = self.report_config.output_format.lower()
        base_path = output_path or self.report_config.output_path

        os.makedirs(base_path, exist_ok=True)

        if output_format == "html":
            file_path = os.path.join(base_path, f"data_quality_report_{timestamp}.html")
            content = self._generate_html(results, summary)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
        elif output_format == "json":
            file_path = os.path.join(base_path, f"data_quality_report_{timestamp}.json")
            content = self._generate_json(results, summary)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")

        return file_path

    def _generate_html(
        self,
        results: List[CheckResult],
        summary: Dict[str, Any],
    ) -> str:
        generation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        all_passed = summary.get("all_passed", False)
        overall_status = "PASS" if all_passed else "FAIL"
        status_color = "#28a745" if all_passed else "#dc3545"

        html_parts = [
            self._get_html_header(),
            self._get_overview_section(generation_time, overall_status, status_color, summary),
        ]

        if self.report_config.include_charts:
            html_parts.append(self._get_chart_section(summary))

        html_parts.append(self._get_results_section(results))
        html_parts.append(self._get_html_footer())

        return "\n".join(html_parts)

    def _get_html_header(self) -> str:
        return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Data Quality Report</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: #f5f7fa;
            color: #333;
            line-height: 1.6;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }
        .header h1 { font-size: 28px; margin-bottom: 10px; }
        .header .time { font-size: 14px; opacity: 0.9; }
        .overall-status {
            text-align: center;
            padding: 40px;
            background: white;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        }
        .status-badge {
            display: inline-block;
            padding: 12px 40px;
            font-size: 28px;
            font-weight: bold;
            border-radius: 50px;
            margin-bottom: 20px;
        }
        .status-pass { background: #d4edda; color: #155724; }
        .status-fail { background: #f8d7da; color: #721c24; }
        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .metric-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }
        .metric-value {
            font-size: 36px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .metric-label {
            font-size: 14px;
            color: #666;
        }
        .section {
            background: white;
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        }
        .section h2 {
            font-size: 20px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
            display: flex;
            align-items: center;
        }
        .section h2::before {
            content: '';
            width: 6px;
            height: 24px;
            background: #667eea;
            margin-right: 12px;
            border-radius: 3px;
        }
        .chart-container {
            height: 300px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .pie-chart {
            width: 250px;
            height: 250px;
            border-radius: 50%;
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .chart-legend {
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-top: 20px;
        }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .legend-color {
            width: 16px;
            height: 16px;
            border-radius: 3px;
        }
        .results-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        .results-table th,
        .results-table td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        .results-table th {
            background: #f8f9fa;
            font-weight: 600;
            color: #495057;
        }
        .results-table tr:hover {
            background: #f8f9fa;
        }
        .status-indicator {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        .status-indicator.pass { background: #d4edda; color: #155724; }
        .status-indicator.fail { background: #f8d7da; color: #721c24; }
        .status-indicator.warning { background: #fff3cd; color: #856404; }
        .status-indicator.error { background: #f3e5f5; color: #6a1b9a; }
        .details-panel {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            margin-top: 10px;
            font-size: 14px;
        }
        .details-panel h4 { margin-bottom: 10px; color: #495057; }
        .details-panel pre {
            background: white;
            padding: 10px;
            border-radius: 5px;
            overflow-x: auto;
            white-space: pre-wrap;
            word-break: break-all;
        }
        .footer {
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
"""

    def _get_overview_section(
        self,
        generation_time: str,
        overall_status: str,
        status_color: str,
        summary: Dict[str, Any],
    ) -> str:
        total_checks = summary.get("total_checks", 0)
        passed_count = summary.get("passed_count", 0)
        failed_count = summary.get("failed_count", 0)
        error_count = summary.get("error_count", 0)
        status_counts = summary.get("status_counts", {})

        pass_percent = (passed_count / total_checks * 100) if total_checks > 0 else 0
        status_class = "status-pass" if overall_status == "PASS" else "status-fail"

        return f"""
        <div class="header">
            <h1>📊 Data Quality Report</h1>
            <div class="time">Report generated at: {generation_time}</div>
        </div>

        <div class="overall-status">
            <div class="status-badge {status_class}">{overall_status}</div>
            <h3>Overall Data Quality Status</h3>
            <div class="metrics">
                <div class="metric-card">
                    <div class="metric-value" style="color: #667eea;">{total_checks}</div>
                    <div class="metric-label">Total Checks</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" style="color: #28a745;">{passed_count}</div>
                    <div class="metric-label">Passed</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" style="color: #ffc107;">{failed_count}</div>
                    <div class="metric-label">Warnings/Failed</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" style="color: #dc3545;">{error_count}</div>
                    <div class="metric-label">Errors</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" style="color: #17a2b8;">{pass_percent:.1f}%</div>
                    <div class="metric-label">Pass Rate</div>
                </div>
            </div>
        </div>
"""

    def _get_chart_section(self, summary: Dict[str, Any]) -> str:
        status_counts = summary.get("status_counts", {})
        pass_count = status_counts.get("PASS", 0)
        warning_count = status_counts.get("WARNING", 0)
        fail_count = status_counts.get("FAIL", 0)
        error_count = status_counts.get("ERROR", 0)
        total = pass_count + warning_count + fail_count + error_count

        if total == 0:
            return ""

        pass_deg = pass_count / total * 360 if total > 0 else 0
        warning_deg = warning_count / total * 360 if total > 0 else 0
        fail_deg = fail_count / total * 360 if total > 0 else 0
        error_deg = error_count / total * 360 if total > 0 else 0

        colors = {
            "PASS": "#28a745",
            "WARNING": "#ffc107",
            "FAIL": "#dc3545",
            "ERROR": "#6f42c1",
        }

        conic_gradient = (
            f"conic-gradient("
            f"#28a745 0deg {pass_deg}deg, "
            f"#ffc107 {pass_deg}deg {pass_deg + warning_deg}deg, "
            f"#dc3545 {pass_deg + warning_deg}deg {pass_deg + warning_deg + fail_deg}deg, "
            f"#6f42c1 {pass_deg + warning_deg + fail_deg}deg 360deg"
            f")"
        )

        legend_items = []
        if pass_count > 0:
            legend_items.append(f'<div class="legend-item"><div class="legend-color" style="background: #28a745;"></div><span>Pass ({pass_count})</span></div>')
        if warning_count > 0:
            legend_items.append(f'<div class="legend-item"><div class="legend-color" style="background: #ffc107;"></div><span>Warning ({warning_count})</span></div>')
        if fail_count > 0:
            legend_items.append(f'<div class="legend-item"><div class="legend-color" style="background: #dc3545;"></div><span>Fail ({fail_count})</span></div>')
        if error_count > 0:
            legend_items.append(f'<div class="legend-item"><div class="legend-color" style="background: #6f42c1;"></div><span>Error ({error_count})</span></div>')

        return f"""
        <div class="section">
            <h2>Results Overview</h2>
            <div class="chart-container">
                <div class="pie-chart" style="background: {conic_gradient};"></div>
            </div>
            <div class="chart-legend">
                {''.join(legend_items)}
            </div>
        </div>
"""

    def _get_results_section(self, results: List[CheckResult]) -> str:
        rows = []
        for result in results:
            status_class = result.status.value.lower()
            details_html = ""

            if result.details or result.errors:
                details_parts = []
                if result.details:
                    try:
                        details_json = json.dumps(result.details, ensure_ascii=False, indent=2)
                        details_parts.append(f"<h4>Details:</h4><pre>{details_json}</pre>")
                    except Exception:
                        details_parts.append(f"<h4>Details:</h4><pre>{str(result.details)}</pre>")
                if result.errors:
                    errors_str = "\n".join(result.errors)
                    details_parts.append(f"<h4>Errors:</h4><pre>{errors_str}</pre>")
                details_html = f'<div class="details-panel">{"".join(details_parts)}</div>'

            row = f"""
                <tr>
                    <td><strong>{result.check_name}</strong></td>
                    <td>{result.check_type}</td>
                    <td><span class="status-indicator {status_class}">{result.status.value}</span></td>
                    <td>{result.actual_value}</td>
                    <td>{result.expected_value}</td>
                    <td>{result.execution_time_ms:.2f}ms</td>
                </tr>
                <tr>
                    <td colspan="6">
                        <p><strong>Message:</strong> {result.message}</p>
                        {details_html}
                    </td>
                </tr>
"""
            rows.append(row)

        return f"""
        <div class="section">
            <h2>Detailed Results</h2>
            <table class="results-table">
                <thead>
                    <tr>
                        <th>Check Name</th>
                        <th>Type</th>
                        <th>Status</th>
                        <th>Actual</th>
                        <th>Expected</th>
                        <th>Time</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
"""

    def _get_html_footer(self) -> str:
        return """
        <div class="footer">
            <p>Generated by Data Quality Platform</p>
        </div>
    </div>
</body>
</html>
"""

    def _generate_json(
        self,
        results: List[CheckResult],
        summary: Dict[str, Any],
    ) -> Dict[str, Any]:
        results_json = []
        for result in results:
            results_json.append({
                "check_name": result.check_name,
                "check_type": result.check_type,
                "status": result.status.value,
                "message": result.message,
                "actual_value": result.actual_value,
                "expected_value": result.expected_value,
                "details": result.details,
                "timestamp": result.timestamp,
                "execution_time_ms": result.execution_time_ms,
                "errors": result.errors,
            })

        summary_serializable = dict(summary)
        if "failed_checks" in summary_serializable:
            summary_serializable["failed_checks"] = [
                {
                    "check_name": r.check_name,
                    "status": r.status.value,
                    "message": r.message,
                }
                for r in summary_serializable["failed_checks"]
            ]
        if "error_checks" in summary_serializable:
            summary_serializable["error_checks"] = [
                {
                    "check_name": r.check_name,
                    "status": r.status.value,
                    "message": r.message,
                }
                for r in summary_serializable["error_checks"]
            ]

        return {
            "report_generated_at": datetime.now().isoformat(),
            "summary": summary_serializable,
            "results": results_json,
        }
