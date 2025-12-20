"""Autonomous Data Analyst - Core Library.

This package provides the core functionality for the AI-powered data analyst:
- Pydantic models for type-safe data structures
- DuckDB database interface for SQL analytics
- Pydantic AI agent for natural language analysis
- Tools for agent operations
"""

from data_analyst.models import (
    AnalysisPlan,
    AnalysisResponse,
    ChartSpec,
    QueryResult,
    TableSchema,
)
from data_analyst.database import DuckDBManager
from data_analyst.agent import (
    analyze,
    analyze_sync,
    create_agent,
    get_agent,
)

__all__ = [
    # Models
    "AnalysisPlan",
    "AnalysisResponse",
    "ChartSpec",
    "QueryResult",
    "TableSchema",
    # Database
    "DuckDBManager",
    # Agent
    "analyze",
    "analyze_sync",
    "create_agent",
    "get_agent",
]

__version__ = "1.0.0"
