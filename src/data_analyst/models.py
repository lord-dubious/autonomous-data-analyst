"""Pydantic models for type-safe data structures.

These models ensure structured, validated responses from the AI agent
and provide clear interfaces for data exchange between components.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class QueryResult(BaseModel):
    """Result of a SQL query execution.

    Represents the outcome of executing a SQL query against DuckDB,
    including the data, metadata, and any errors that occurred.
    """

    success: bool = Field(description="Whether the query executed successfully")
    data: list[dict] | None = Field(
        default=None, description="Query results as list of row dictionaries"
    )
    columns: list[str] | None = Field(default=None, description="Column names in result order")
    row_count: int = Field(default=0, description="Number of rows returned")
    error: str | None = Field(default=None, description="Error message if query failed")
    metadata: dict[str, Any] | None = Field(
        default=None, description="Optional execution metadata for diagnostics and degraded states"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": True,
                    "data": [
                        {"product": "Widget A", "revenue": 1500.0},
                        {"product": "Widget B", "revenue": 2300.0},
                    ],
                    "columns": ["product", "revenue"],
                    "row_count": 2,
                    "error": None,
                    "metadata": {"source": "duckdb"},
                }
            ]
        }
    }


class TableSchema(BaseModel):
    """Schema information for a database table.

    Contains column names and their data types for a table in the database.
    """

    table_name: str = Field(description="Name of the table")
    columns: dict[str, str] = Field(description="Mapping of column names to their data types")
    row_count: int = Field(default=0, description="Number of rows in the table")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "table_name": "sales",
                    "columns": {
                        "date": "DATE",
                        "product": "VARCHAR",
                        "quantity": "INTEGER",
                        "revenue": "DOUBLE",
                    },
                    "row_count": 1000,
                }
            ]
        }
    }


class ChartSpec(BaseModel):
    """Specification for generating a chart visualization.

    Defines the type and configuration of a chart to be rendered
    based on query results.
    """

    chart_type: Literal["bar", "line", "pie", "scatter", "area"] = Field(
        description="Type of chart to generate"
    )
    title: str = Field(description="Chart title")
    x_column: str = Field(description="Column name for x-axis")
    y_column: str = Field(description="Column name for y-axis")
    color_column: str | None = Field(default=None, description="Optional column for color grouping")
    description: str = Field(description="Brief description of what the chart shows")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "chart_type": "bar",
                    "title": "Revenue by Product",
                    "x_column": "product",
                    "y_column": "revenue",
                    "color_column": "category",
                    "description": "Bar chart showing total revenue for each product",
                }
            ]
        }
    }


class AnalysisPlan(BaseModel):
    """Structured plan for data analysis.

    Represents the agent's plan for analyzing data, including
    the objective, steps, and SQL query to execute.
    """

    objective: str = Field(description="Clear statement of what we're trying to find or analyze")
    steps: list[str] = Field(description="List of steps to achieve the objective")
    sql_query: str = Field(description="SQL query to execute for the analysis")
    reasoning: str = Field(description="Explanation of why this approach was chosen")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "objective": "Find the top 5 products by total revenue",
                    "steps": [
                        "Aggregate revenue by product",
                        "Sort by total revenue descending",
                        "Limit to top 5 results",
                    ],
                    "sql_query": "SELECT product, SUM(revenue) as total_revenue FROM sales GROUP BY product ORDER BY total_revenue DESC LIMIT 5",
                    "reasoning": "Using GROUP BY to aggregate sales by product, then sorting to get the highest performers",
                }
            ]
        }
    }


class AnalysisResponse(BaseModel):
    """Complete analysis response from the AI agent.

    Contains the full analysis including summary, insights,
    query results, and visualization recommendations.
    """

    summary: str = Field(description="Brief summary of the analysis findings")
    insights: list[str] = Field(description="Key insights discovered from the data")
    query_results: list[QueryResult] = Field(
        default_factory=list, description="Results from executed queries"
    )
    chart_specs: list[ChartSpec] = Field(
        default_factory=list, description="Recommended chart specifications"
    )
    follow_up_questions: list[str] = Field(
        default_factory=list,
        description="Suggested follow-up questions for deeper analysis",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "summary": "Revenue is highest in the North region, driven primarily by Widget A sales.",
                    "insights": [
                        "North region accounts for 45% of total revenue",
                        "Widget A is the top-selling product by revenue",
                        "Q4 shows 20% growth compared to Q3",
                    ],
                    "query_results": [],
                    "chart_specs": [],
                    "follow_up_questions": [
                        "What factors drive Widget A's success?",
                        "Why is the South region underperforming?",
                    ],
                }
            ]
        }
    }
