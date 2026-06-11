"""Report generators for comparison results."""

import json
from datetime import datetime
from typing import Optional, TextIO
from pathlib import Path
from .comparator import ComparisonResult, DifferenceType


class ComparisonReporter:
    """Generate reports from comparison results."""
    
    def __init__(self, result: ComparisonResult):
        self.result = result
    
    def to_console(self, verbose: bool = False) -> str:
        """Generate a console-friendly report."""
        lines = []
        
        # Header
        lines.append("=" * 70)
        lines.append("PostgreSQL Database Comparison Report")
        lines.append("=" * 70)
        lines.append(f"Source: {self.result.source_name}")
        lines.append(f"Target: {self.result.target_name}")
        lines.append(f"Generated: {datetime.now().isoformat()}")
        lines.append("")
        
        # Summary
        lines.append("-" * 70)
        lines.append("SUMMARY")
        lines.append("-" * 70)
        
        if not self.result.has_differences:
            lines.append("✓ No differences found - databases are identical")
        else:
            lines.append(f"Total differences: {len(self.result.differences)}")
            lines.append(f"  - Added (in target only):   {self.result.added_count}")
            lines.append(f"  - Removed (in source only): {self.result.removed_count}")
            lines.append(f"  - Modified:                 {self.result.modified_count}")
            lines.append("")
            
            # Summary by object type
            summary = self.result.summary()
            lines.append("By object type:")
            for obj_type, counts in sorted(summary.items()):
                total = sum(counts.values())
                lines.append(f"  {obj_type}: {total} difference(s)")
        
        lines.append("")
        
        # Details
        if self.result.has_differences:
            lines.append("-" * 70)
            lines.append("DETAILS")
            lines.append("-" * 70)
            
            # Group by object type
            by_type = {}
            for diff in self.result.differences:
                if diff.object_type not in by_type:
                    by_type[diff.object_type] = []
                by_type[diff.object_type].append(diff)
            
            for obj_type in sorted(by_type.keys()):
                diffs = by_type[obj_type]
                lines.append("")
                lines.append(f"### {obj_type.upper()} ({len(diffs)})")
                
                for diff in sorted(diffs, key=lambda d: d.path):
                    if diff.diff_type == DifferenceType.ADDED:
                        lines.append(f"  [+] {diff.path}")
                        if verbose and diff.target_value:
                            lines.append(f"      Value: {self._format_value(diff.target_value)}")
                    elif diff.diff_type == DifferenceType.REMOVED:
                        lines.append(f"  [-] {diff.path}")
                        if verbose and diff.source_value:
                            lines.append(f"      Value: {self._format_value(diff.source_value)}")
                    else:
                        lines.append(f"  [~] {diff.path}")
                        if diff.details.get("modified_attributes"):
                            for attr, values in diff.details["modified_attributes"].items():
                                lines.append(f"      {attr}:")
                                lines.append(f"        source: {values['source']}")
                                lines.append(f"        target: {values['target']}")
        
        lines.append("")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def to_json(self, pretty: bool = True) -> str:
        """Generate a JSON report."""
        report = {
            "meta": {
                "source": self.result.source_name,
                "target": self.result.target_name,
                "generated_at": datetime.now().isoformat(),
            },
            "summary": {
                "total_differences": len(self.result.differences),
                "added": self.result.added_count,
                "removed": self.result.removed_count,
                "modified": self.result.modified_count,
                "by_type": self.result.summary(),
            },
            "differences": [
                {
                    "object_type": d.object_type,
                    "path": d.path,
                    "diff_type": d.diff_type.value,
                    "source_value": self._serialize_value(d.source_value),
                    "target_value": self._serialize_value(d.target_value),
                    "details": d.details,
                }
                for d in self.result.differences
            ],
        }
        
        if pretty:
            return json.dumps(report, indent=2, default=str)
        return json.dumps(report, default=str)
    
    def to_html(self) -> str:
        """Generate an HTML report."""
        html_parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "<meta charset='UTF-8'>",
            "<title>PostgreSQL Database Comparison Report</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 20px; }",
            "h1 { color: #333; }",
            ".summary { background: #f5f5f5; padding: 15px; border-radius: 5px; }",
            ".added { color: #28a745; }",
            ".removed { color: #dc3545; }",
            ".modified { color: #fd7e14; }",
            "table { border-collapse: collapse; width: 100%; margin-top: 20px; }",
            "th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
            "th { background-color: #4CAF50; color: white; }",
            "tr:nth-child(even) { background-color: #f2f2f2; }",
            ".details { font-size: 0.9em; color: #666; }",
            "</style>",
            "</head>",
            "<body>",
            "<h1>PostgreSQL Database Comparison Report</h1>",
            f"<p><strong>Source:</strong> {self.result.source_name}</p>",
            f"<p><strong>Target:</strong> {self.result.target_name}</p>",
            f"<p><strong>Generated:</strong> {datetime.now().isoformat()}</p>",
            "<div class='summary'>",
            "<h2>Summary</h2>",
        ]
        
        if not self.result.has_differences:
            html_parts.append("<p>✓ No differences found - databases are identical</p>")
        else:
            html_parts.extend([
                f"<p>Total differences: <strong>{len(self.result.differences)}</strong></p>",
                "<ul>",
                f"<li class='added'>Added (in target only): {self.result.added_count}</li>",
                f"<li class='removed'>Removed (in source only): {self.result.removed_count}</li>",
                f"<li class='modified'>Modified: {self.result.modified_count}</li>",
                "</ul>",
            ])
        
        html_parts.append("</div>")
        
        # Details table
        if self.result.has_differences:
            html_parts.extend([
                "<h2>Differences</h2>",
                "<table>",
                "<tr><th>Type</th><th>Object</th><th>Change</th><th>Details</th></tr>",
            ])
            
            for diff in sorted(self.result.differences, key=lambda d: (d.object_type, d.path)):
                diff_class = diff.diff_type.value
                symbol = {"added": "+", "removed": "-", "modified": "~"}[diff.diff_type.value]
                
                details_html = ""
                if diff.diff_type == DifferenceType.MODIFIED and diff.details.get("modified_attributes"):
                    details_lines = []
                    for attr, values in diff.details["modified_attributes"].items():
                        details_lines.append(f"<strong>{attr}</strong>: {values['source']} → {values['target']}")
                    details_html = "<br>".join(details_lines)
                
                html_parts.append(
                    f"<tr class='{diff_class}'>"
                    f"<td>{diff.object_type}</td>"
                    f"<td>{diff.path}</td>"
                    f"<td>[{symbol}] {diff.diff_type.value}</td>"
                    f"<td class='details'>{details_html}</td>"
                    "</tr>"
                )
            
            html_parts.append("</table>")
        
        html_parts.extend([
            "</body>",
            "</html>",
        ])
        
        return "\n".join(html_parts)
    
    def to_markdown(self) -> str:
        """Generate a Markdown report."""
        lines = [
            "# PostgreSQL Database Comparison Report",
            "",
            f"- **Source:** {self.result.source_name}",
            f"- **Target:** {self.result.target_name}",
            f"- **Generated:** {datetime.now().isoformat()}",
            "",
            "## Summary",
            "",
        ]
        
        if not self.result.has_differences:
            lines.append("✅ No differences found - databases are identical")
        else:
            lines.extend([
                f"Total differences: **{len(self.result.differences)}**",
                "",
                f"| Change Type | Count |",
                f"|-------------|-------|",
                f"| Added | {self.result.added_count} |",
                f"| Removed | {self.result.removed_count} |",
                f"| Modified | {self.result.modified_count} |",
                "",
                "### By Object Type",
                "",
            ])
            
            summary = self.result.summary()
            for obj_type, counts in sorted(summary.items()):
                total = sum(counts.values())
                lines.append(f"- **{obj_type}**: {total} difference(s)")
        
        # Details
        if self.result.has_differences:
            lines.extend(["", "## Details", ""])
            
            by_type = {}
            for diff in self.result.differences:
                if diff.object_type not in by_type:
                    by_type[diff.object_type] = []
                by_type[diff.object_type].append(diff)
            
            for obj_type in sorted(by_type.keys()):
                diffs = by_type[obj_type]
                lines.extend([f"### {obj_type.title()}", ""])
                
                for diff in sorted(diffs, key=lambda d: d.path):
                    if diff.diff_type == DifferenceType.ADDED:
                        lines.append(f"- ➕ `{diff.path}`")
                    elif diff.diff_type == DifferenceType.REMOVED:
                        lines.append(f"- ➖ `{diff.path}`")
                    else:
                        lines.append(f"- 🔄 `{diff.path}`")
                        if diff.details.get("modified_attributes"):
                            for attr, values in diff.details["modified_attributes"].items():
                                lines.append(f"  - {attr}: `{values['source']}` → `{values['target']}`")
                
                lines.append("")
        
        return "\n".join(lines)
    
    def save(self, path: Path, format: str = "auto"):
        """Save report to file."""
        if format == "auto":
            suffix = path.suffix.lower()
            format = {
                ".json": "json",
                ".html": "html",
                ".htm": "html",
                ".md": "markdown",
                ".txt": "console",
            }.get(suffix, "console")
        
        content = {
            "json": self.to_json,
            "html": self.to_html,
            "markdown": self.to_markdown,
            "console": self.to_console,
        }[format]()
        
        path.write_text(content)
    
    def _format_value(self, value) -> str:
        """Format a value for console output."""
        if isinstance(value, dict):
            return json.dumps(value, default=str)
        return str(value)
    
    def _serialize_value(self, value):
        """Serialize a value for JSON output."""
        if isinstance(value, (list, dict, str, int, float, bool, type(None))):
            return value
        return str(value)
