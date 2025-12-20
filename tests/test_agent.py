"""Tests for Pydantic AI agent functionality.

Note: These tests use pytest-recording to record/replay API calls,
making them deterministic and fast after the first run.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data_analyst.agent import analyze_sync, create_agent
from data_analyst.database import DuckDBManager
from data_analyst.models import AnalysisPlan, AnalysisResponse, ChartSpec


class TestAgentCreation:
    """Test suite for agent creation and configuration."""

    def test_create_agent_default_model(self) -> None:
        """Test creating an agent with default model."""
        agent = create_agent()
        assert agent is not None
        assert agent.deps_type is DuckDBManager

    def test_create_agent_custom_model(self) -> None:
        """Test creating an agent with custom model."""
        agent = create_agent(model_name="google-gla:gemini-1.5-flash")
        assert agent is not None


class TestAgentTools:
    """Test suite for agent tool functionality."""

    def test_tools_registered(self) -> None:
        """Test that all expected tools are registered."""
        agent = create_agent()

        # Get registered tool names
        tool_names = [tool.name for tool in agent._function_tools.values()]

        # Verify expected tools are present
        assert "execute_sql" in tool_names
        assert "describe_table" in tool_names
        assert "list_available_tables" in tool_names
        assert "get_sample_rows" in tool_names
        assert "get_column_statistics" in tool_names


class TestModels:
    """Test suite for Pydantic models."""

    def test_analysis_plan_creation(self) -> None:
        """Test creating an AnalysisPlan."""
        plan = AnalysisPlan(
            objective="Find top products by revenue",
            steps=["Query products", "Aggregate revenue", "Sort by total"],
            sql_query="SELECT product, SUM(revenue) FROM sales GROUP BY product",
            reasoning="Aggregation provides the totals needed",
        )

        assert plan.objective == "Find top products by revenue"
        assert len(plan.steps) == 3
        assert "SELECT" in plan.sql_query

    def test_chart_spec_creation(self) -> None:
        """Test creating a ChartSpec."""
        spec = ChartSpec(
            chart_type="bar",
            title="Revenue by Product",
            x_column="product",
            y_column="revenue",
            description="Bar chart showing revenue per product",
        )

        assert spec.chart_type == "bar"
        assert spec.x_column == "product"
        assert spec.color_column is None

    def test_analysis_response_creation(self) -> None:
        """Test creating an AnalysisResponse."""
        response = AnalysisResponse(
            summary="Analysis complete",
            insights=["Revenue is highest in North", "Widget A is top seller"],
            follow_up_questions=["Why is North performing well?"],
        )

        assert len(response.insights) == 2
        assert len(response.query_results) == 0
        assert len(response.chart_specs) == 0


# Pytest-recording decorated tests (for integration with LLM)
# These tests will record API responses on first run
# and replay them on subsequent runs


@pytest.mark.skip(reason="Requires GEMINI_API_KEY and network access")
class TestAgentIntegration:
    """Integration tests for the AI agent.

    These tests require a valid GEMINI_API_KEY environment variable.
    They are skipped by default to allow CI to run without credentials.

    To run these tests locally:
        GEMINI_API_KEY=your_key pytest tests/test_agent.py -k "Integration" --run-integration
    """

    @pytest.mark.vcr
    def test_agent_lists_tables(self, sample_db: DuckDBManager) -> None:
        """Test that agent can list tables."""
        response = analyze_sync(sample_db, "What tables are available?")

        assert response is not None
        assert "sales" in response.lower()

    @pytest.mark.vcr
    def test_agent_describes_schema(self, sample_db: DuckDBManager) -> None:
        """Test that agent can describe table schema."""
        response = analyze_sync(sample_db, "What columns are in the sales table?")

        assert response is not None
        # Should mention some columns
        assert any(col in response.lower() for col in ["product", "revenue", "quantity", "date"])

    @pytest.mark.vcr
    def test_agent_executes_aggregation(self, sample_db: DuckDBManager) -> None:
        """Test that agent can execute aggregation queries."""
        response = analyze_sync(sample_db, "What is the total revenue by product?")

        assert response is not None
        # Should mention products and revenue
        assert any(
            keyword in response.lower() for keyword in ["widget", "gadget", "revenue", "total"]
        )

    @pytest.mark.vcr
    def test_agent_handles_invalid_question(self, sample_db: DuckDBManager) -> None:
        """Test that agent handles invalid questions gracefully."""
        response = analyze_sync(sample_db, "What is the color of the sky in the data?")

        assert response is not None
        # Should indicate the data doesn't contain this information
        assert len(response) > 0
