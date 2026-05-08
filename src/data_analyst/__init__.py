"""Autonomous Data Analyst - Core Library.

This package provides core functionality for CSV-backed analysis:
- Pydantic models for type-safe data structures
- DuckDB database interface for SQL analytics
- Pydantic AI agent helpers for optional natural language analysis
- Tools for agent operations
"""

from data_analyst.agent import (
    AgentAnalysisResult,
    analyze,
    analyze_sync,
    analyze_with_metadata,
    create_agent,
    get_agent,
)
from data_analyst.database import DuckDBManager
from data_analyst.models import (
    AnalysisPlan,
    AnalysisResponse,
    ChartSpec,
    QueryResult,
    TableSchema,
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
    "AgentAnalysisResult",
    "analyze",
    "analyze_with_metadata",
    "analyze_sync",
    "create_agent",
    "get_agent",
]

__version__ = "1.0.0"
