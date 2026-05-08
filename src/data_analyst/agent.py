"""Pydantic AI agent helpers for data analysis.

The agent can use Gemini through Pydantic AI when credentials and network access
are available. Helper functions expose explicit degraded metadata when the model
call fails or external service access is unavailable.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from dotenv import load_dotenv
from pydantic_ai import Agent

from data_analyst.database import DuckDBManager
from data_analyst.tools import (
    describe_table,
    execute_sql,
    get_column_statistics,
    get_sample_rows,
    list_available_tables,
)

if TYPE_CHECKING:
    from pydantic_ai import AgentRunResult

# Load environment variables
load_dotenv()

# System prompt for the data analyst agent
SYSTEM_PROMPT = """You are a data analysis assistant that can call DuckDB tools.
Your role is to help users inspect CSV-backed data through natural language.

## Your Capabilities
- Execute SQL queries on DuckDB (PostgreSQL-like syntax)
- Summarize observed data patterns and trends
- Provide caveated observations and recommendations
- Suggest appropriate visualizations

## Workflow
1. ALWAYS start by listing available tables using list_available_tables
2. Describe the table schema to understand the columns and data types
3. Get sample data to understand the content
4. Plan your analysis approach
5. Execute SQL queries to answer the user's question
6. Provide clear explanations and insights

## SQL Guidelines
- Use DuckDB SQL syntax (similar to PostgreSQL)
- Always verify table and column names exist before querying
- Use appropriate aggregations (SUM, AVG, COUNT, etc.)
- Handle NULL values appropriately
- Use LIMIT for large result sets

## Response Guidelines
- Explain your analysis step by step
- Highlight key insights and patterns
- Suggest follow-up questions when relevant
- Recommend appropriate chart types for visualization:
  - Bar charts: comparing categories
  - Line charts: trends over time
  - Pie charts: proportions/percentages
  - Scatter plots: correlations between variables

## Error Handling
- If a query fails, explain the error and try an alternative approach
- If data is missing or unexpected, acknowledge and adapt
- Always provide helpful suggestions even when analysis is limited

Remember: Be concise but thorough. Base conclusions on tool results and state limits clearly."""


@dataclass
class AgentAnalysisResult:
    """Result wrapper for agent runs with explicit external-service metadata."""

    success: bool
    output: str
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def create_agent(model_name: str | None = None) -> Agent[DuckDBManager, str]:
    """Create and configure the data analyst agent.

    Args:
        model_name: Optional model name override. Defaults to gemini-2.5-flash.

    Returns:
        Configured Pydantic AI agent with all tools registered.

    Example:
        >>> agent = create_agent()
        >>> result = await agent.run("What are the total sales?", deps=db)
    """
    # Use provided model name or default to Gemini 2.5 Flash
    model = model_name or os.getenv("MODEL_NAME", "google-gla:gemini-2.5-flash")

    # Create the agent
    agent = Agent(
        model,
        deps_type=DuckDBManager,
        system_prompt=SYSTEM_PROMPT,
        retries=2,
    )

    # Register tools
    agent.tool(execute_sql)
    agent.tool(describe_table)
    agent.tool(list_available_tables)
    agent.tool(get_sample_rows)
    agent.tool(get_column_statistics)

    return agent


# Default agent instance
_default_agent: Agent[DuckDBManager, str] | None = None


def get_agent() -> Agent[DuckDBManager, str]:
    """Get or create the default agent instance.

    Returns:
        The default agent instance.
    """
    global _default_agent
    if _default_agent is None:
        _default_agent = create_agent()
    return _default_agent


async def analyze(
    db: DuckDBManager,
    question: str,
    *,
    agent: Agent[DuckDBManager, str] | None = None,
) -> str:
    """Analyze data using the AI agent.

    This is the main entry point for running data analysis.

    Args:
        db: DuckDB manager with loaded data.
        question: Natural language question about the data.
        agent: Optional custom agent instance. Uses default if not provided.

    Returns:
        The agent's analysis response as a string.

    Example:
        >>> db = DuckDBManager()
        >>> db.load_csv("sales.csv", "data")
        >>> response = await analyze(db, "What is the total revenue by product?")
        >>> print(response)
    """
    run_agent = agent or get_agent()

    result: AgentRunResult[str] = await run_agent.run(question, deps=db)
    return result.output


async def analyze_with_metadata(
    db: DuckDBManager,
    question: str,
    *,
    agent: Agent[DuckDBManager, str] | None = None,
) -> AgentAnalysisResult:
    """Analyze data and return explicit success/error metadata.

    This preserves the original ``analyze`` function while giving API callers a
    non-throwing boundary for Gemini/Pydantic AI failures.
    """
    model_name = os.getenv("MODEL_NAME", "google-gla:gemini-2.5-flash")
    metadata: dict[str, Any] = {
        "service": "pydantic_ai",
        "model": model_name,
        "degraded": False,
    }

    try:
        output = await analyze(db, question, agent=agent)
    except Exception as exc:
        metadata.update(
            {
                "degraded": True,
                "error_type": type(exc).__name__,
                "boundary": "agent_run",
            }
        )
        return AgentAnalysisResult(
            success=False,
            output="",
            error="Agent analysis failed before producing a response",
            metadata=metadata,
        )

    return AgentAnalysisResult(success=True, output=output, metadata=metadata)


def analyze_sync(
    db: DuckDBManager,
    question: str,
    *,
    agent: Agent[DuckDBManager, str] | None = None,
) -> str:
    """Synchronous version of analyze for non-async contexts.

    Args:
        db: DuckDB manager with loaded data.
        question: Natural language question about the data.
        agent: Optional custom agent instance. Uses default if not provided.

    Returns:
        The agent's analysis response as a string.

    Example:
        >>> db = DuckDBManager()
        >>> db.load_csv("sales.csv", "data")
        >>> response = analyze_sync(db, "What is the total revenue?")
    """
    run_agent = agent or get_agent()

    result = run_agent.run_sync(question, deps=db)
    return result.output
