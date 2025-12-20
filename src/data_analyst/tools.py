"""Agent tools for data analysis operations.

This module provides the tools that the Pydantic AI agent uses
to interact with the database and analyze data.
"""

from pydantic_ai import RunContext

from data_analyst.database import DuckDBManager
from data_analyst.models import QueryResult, TableSchema


async def execute_sql(
    ctx: RunContext[DuckDBManager],
    sql: str,
) -> QueryResult:
    """Execute a SQL query on the database.

    Use this tool to run SQL queries against the loaded data.
    DuckDB uses PostgreSQL-like SQL syntax.

    Args:
        ctx: Runtime context containing the database manager.
        sql: The SQL query to execute.

    Returns:
        QueryResult with the query results or error message.

    Example queries:
        - SELECT * FROM data LIMIT 10
        - SELECT product, SUM(revenue) FROM data GROUP BY product
        - SELECT date, COUNT(*) FROM data GROUP BY date ORDER BY date
    """
    return ctx.deps.execute_query(sql)


async def describe_table(
    ctx: RunContext[DuckDBManager],
    table_name: str,
) -> TableSchema | dict:
    """Get the schema of a database table.

    Use this tool to understand the structure of a table before querying.
    Returns column names and their data types.

    Args:
        ctx: Runtime context containing the database manager.
        table_name: Name of the table to describe.

    Returns:
        TableSchema with column information, or error dict if table doesn't exist.
    """
    schema = ctx.deps.get_schema(table_name)
    if schema:
        return schema
    return {"error": f"Table '{table_name}' not found"}


async def list_available_tables(
    ctx: RunContext[DuckDBManager],
) -> list[str]:
    """List all available tables in the database.

    Use this tool first to see what data is available before querying.

    Args:
        ctx: Runtime context containing the database manager.

    Returns:
        List of table names in the database.
    """
    return ctx.deps.list_tables()


async def get_sample_rows(
    ctx: RunContext[DuckDBManager],
    table_name: str,
    num_rows: int = 5,
) -> QueryResult:
    """Get sample rows from a table.

    Use this tool to preview what the data looks like before
    writing complex queries.

    Args:
        ctx: Runtime context containing the database manager.
        table_name: Name of the table to sample.
        num_rows: Number of rows to return (default 5, max 20).

    Returns:
        QueryResult with sample data.
    """
    # Limit to reasonable range
    num_rows = min(max(1, num_rows), 20)
    return ctx.deps.get_sample_data(table_name, limit=num_rows)


async def get_column_statistics(
    ctx: RunContext[DuckDBManager],
    table_name: str,
) -> dict:
    """Get statistics for numeric columns in a table.

    Use this tool to understand the distribution of numeric data
    (min, max, average, sum) before detailed analysis.

    Args:
        ctx: Runtime context containing the database manager.
        table_name: Name of the table to analyze.

    Returns:
        Dictionary with statistics for each numeric column.
    """
    stats = ctx.deps.get_statistics(table_name)
    if stats:
        return stats
    return {"error": f"Could not get statistics for '{table_name}'"}
