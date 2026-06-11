"""Tests for the comparison reporter."""

import json
import pytest
from src.pg_compare.comparator import ComparisonResult, Difference, DifferenceType
from src.pg_compare.reporter import ComparisonReporter


@pytest.fixture
def sample_result():
    """Create a sample comparison result for testing."""
    return ComparisonResult(
        source_name="db1@localhost",
        target_name="db2@localhost",
        differences=[
            Difference(
                object_type="table",
                path="public.new_table",
                diff_type=DifferenceType.ADDED,
                target_value={"owner": "postgres"},
            ),
            Difference(
                object_type="table",
                path="public.old_table",
                diff_type=DifferenceType.REMOVED,
                source_value={"owner": "postgres"},
            ),
            Difference(
                object_type="column",
                path="public.users.email",
                diff_type=DifferenceType.MODIFIED,
                source_value={"data_type": "varchar(100)"},
                target_value={"data_type": "varchar(255)"},
                details={"modified_attributes": {"data_type": {"source": "varchar(100)", "target": "varchar(255)"}}},
            ),
        ],
    )


@pytest.fixture
def empty_result():
    """Create an empty comparison result."""
    return ComparisonResult(
        source_name="db1@localhost",
        target_name="db2@localhost",
        differences=[],
    )


class TestConsoleReport:
    """Tests for console report generation."""
    
    def test_contains_header(self, sample_result):
        """Should contain header with database names."""
        reporter = ComparisonReporter(sample_result)
        report = reporter.to_console()
        
        assert "PostgreSQL Database Comparison Report" in report
        assert "db1@localhost" in report
        assert "db2@localhost" in report
    
    def test_contains_summary(self, sample_result):
        """Should contain summary statistics."""
        reporter = ComparisonReporter(sample_result)
        report = reporter.to_console()
        
        assert "SUMMARY" in report
        assert "Total differences: 3" in report
        assert "Added" in report
        assert "Removed" in report
        assert "Modified" in report
    
    def test_contains_details(self, sample_result):
        """Should contain difference details."""
        reporter = ComparisonReporter(sample_result)
        report = reporter.to_console()
        
        assert "DETAILS" in report
        assert "public.new_table" in report
        assert "public.old_table" in report
        assert "public.users.email" in report
    
    def test_empty_result_message(self, empty_result):
        """Should show no differences message for empty result."""
        reporter = ComparisonReporter(empty_result)
        report = reporter.to_console()
        
        assert "No differences found" in report
    
    def test_verbose_mode(self, sample_result):
        """Verbose mode should include more details."""
        reporter = ComparisonReporter(sample_result)
        
        brief = reporter.to_console(verbose=False)
        verbose = reporter.to_console(verbose=True)
        
        # Verbose should have more content
        assert len(verbose) >= len(brief)


class TestJsonReport:
    """Tests for JSON report generation."""
    
    def test_valid_json(self, sample_result):
        """Should produce valid JSON."""
        reporter = ComparisonReporter(sample_result)
        report = reporter.to_json()
        
        # Should parse without error
        data = json.loads(report)
        
        assert "meta" in data
        assert "summary" in data
        assert "differences" in data
    
    def test_contains_meta(self, sample_result):
        """Should contain meta information."""
        reporter = ComparisonReporter(sample_result)
        data = json.loads(reporter.to_json())
        
        assert data["meta"]["source"] == "db1@localhost"
        assert data["meta"]["target"] == "db2@localhost"
        assert "generated_at" in data["meta"]
    
    def test_contains_summary(self, sample_result):
        """Should contain summary statistics."""
        reporter = ComparisonReporter(sample_result)
        data = json.loads(reporter.to_json())
        
        assert data["summary"]["total_differences"] == 3
        assert data["summary"]["added"] == 1
        assert data["summary"]["removed"] == 1
        assert data["summary"]["modified"] == 1
    
    def test_contains_differences(self, sample_result):
        """Should contain all differences."""
        reporter = ComparisonReporter(sample_result)
        data = json.loads(reporter.to_json())
        
        assert len(data["differences"]) == 3
        
        paths = [d["path"] for d in data["differences"]]
        assert "public.new_table" in paths
        assert "public.old_table" in paths
        assert "public.users.email" in paths
    
    def test_pretty_format(self, sample_result):
        """Pretty format should have indentation."""
        reporter = ComparisonReporter(sample_result)
        
        pretty = reporter.to_json(pretty=True)
        compact = reporter.to_json(pretty=False)
        
        # Pretty should be longer due to whitespace
        assert len(pretty) > len(compact)
        assert "\n" in pretty


class TestHtmlReport:
    """Tests for HTML report generation."""
    
    def test_valid_html(self, sample_result):
        """Should produce valid HTML structure."""
        reporter = ComparisonReporter(sample_result)
        report = reporter.to_html()
        
        assert "<!DOCTYPE html>" in report
        assert "<html>" in report
        assert "</html>" in report
        assert "<head>" in report
        assert "<body>" in report
    
    def test_contains_title(self, sample_result):
        """Should contain title."""
        reporter = ComparisonReporter(sample_result)
        report = reporter.to_html()
        
        assert "<title>" in report
        assert "Comparison Report" in report
    
    def test_contains_styles(self, sample_result):
        """Should contain CSS styles."""
        reporter = ComparisonReporter(sample_result)
        report = reporter.to_html()
        
        assert "<style>" in report
        assert ".added" in report
        assert ".removed" in report
        assert ".modified" in report
    
    def test_contains_differences_table(self, sample_result):
        """Should contain differences in a table."""
        reporter = ComparisonReporter(sample_result)
        report = reporter.to_html()
        
        assert "<table>" in report
        assert "public.new_table" in report


class TestMarkdownReport:
    """Tests for Markdown report generation."""
    
    def test_contains_header(self, sample_result):
        """Should contain Markdown header."""
        reporter = ComparisonReporter(sample_result)
        report = reporter.to_markdown()
        
        assert "# PostgreSQL Database Comparison Report" in report
    
    def test_contains_summary_table(self, sample_result):
        """Should contain summary as Markdown table."""
        reporter = ComparisonReporter(sample_result)
        report = reporter.to_markdown()
        
        assert "| Change Type | Count |" in report
        assert "|-------------|-------|" in report
    
    def test_contains_differences_list(self, sample_result):
        """Should contain differences as list."""
        reporter = ComparisonReporter(sample_result)
        report = reporter.to_markdown()
        
        assert "- ➕" in report  # Added
        assert "- ➖" in report  # Removed
        assert "- 🔄" in report  # Modified
    
    def test_uses_code_formatting(self, sample_result):
        """Should use code formatting for paths."""
        reporter = ComparisonReporter(sample_result)
        report = reporter.to_markdown()
        
        assert "`public.new_table`" in report
