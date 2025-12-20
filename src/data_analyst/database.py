"""DuckDB database interface for SQL analytics.

This module provides a clean interface for loading data into DuckDB
and executing SQL queries with proper error handling.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import BinaryIO

import duckdb
import pandas as pd

from data_analyst.models import QueryResult, TableSchema


class DuckDBManager:
    """Manages DuckDB connections and SQL operations.

    Provides methods for loading CSV data, executing queries,
    and inspecting database schema.

    Attributes:
        conn: The DuckDB connection object.
        db_path: Path to the database file or ":memory:" for in-memory.

    Example:
        >>> db = DuckDBManager()
        >>> db.load_csv("data.csv", "sales")
        True
        >>> result = db.execute_query("SELECT * FROM sales LIMIT 5")
        >>> print(result.data)
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        """Initialize DuckDB connection.

        Args:
            db_path: Path to database file or ":memory:" for in-memory database.
        """
        self.db_path = db_path
        self.conn = duckdb.connect(db_path)
        # Enable case-insensitive column access
        self.conn.execute("SET preserve_insertion_order=true")

    def load_csv(
        self,
        file_source: Path | str | BinaryIO,
        table_name: str,
        *,
        replace: bool = True,
    ) -> bool:
        """Load CSV data into a DuckDB table.

        Args:
            file_source: Path to CSV file, string path, or file-like object.
            table_name: Name of the table to create.
            replace: If True, replace existing table. If False, fail if exists.

        Returns:
            True if successful, False otherwise.

        Example:
            >>> db.load_csv("sales.csv", "sales")
            True
            >>> db.load_csv(uploaded_file, "data")  # From Streamlit
            True
        """
        try:
            # Handle different input types
            if isinstance(file_source, (Path, str)):
                file_path = Path(file_source)
                if not file_path.exists():
                    return False
                df = pd.read_csv(file_path)
            elif hasattr(file_source, "read"):
                # File-like object (e.g., from Streamlit upload)
                content = file_source.read()
                if isinstance(content, bytes):
                    content = content.decode("utf-8")
                df = pd.read_csv(io.StringIO(content))
            else:
                return False

            # Clean column names: lowercase, replace spaces with underscores
            df.columns = [col.lower().replace(" ", "_").replace("-", "_") for col in df.columns]

            # Create or replace table
            if replace:
                self.conn.execute(f"DROP TABLE IF EXISTS {table_name}")

            self.conn.register("temp_df", df)
            self.conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM temp_df")
            self.conn.unregister("temp_df")

            return True

        except Exception:
            return False

    def execute_query(self, sql: str) -> QueryResult:
        """Execute a SQL query and return structured results.

        Args:
            sql: SQL query string to execute.

        Returns:
            QueryResult with success status, data, and metadata.

        Example:
            >>> result = db.execute_query("SELECT COUNT(*) as cnt FROM sales")
            >>> if result.success:
            ...     print(result.data[0]["cnt"])
        """
        try:
            result = self.conn.execute(sql)
            columns = [desc[0] for desc in result.description]
            rows = result.fetchall()

            # Convert to list of dictionaries
            data = [dict(zip(columns, row)) for row in rows]

            return QueryResult(
                success=True,
                data=data,
                columns=columns,
                row_count=len(data),
                error=None,
            )

        except duckdb.Error as e:
            return QueryResult(
                success=False,
                data=None,
                columns=None,
                row_count=0,
                error=str(e),
            )
        except Exception as e:
            return QueryResult(
                success=False,
                data=None,
                columns=None,
                row_count=0,
                error=f"Unexpected error: {e!s}",
            )

    def get_schema(self, table_name: str) -> TableSchema | None:
        """Get schema information for a table.

        Args:
            table_name: Name of the table to inspect.

        Returns:
            TableSchema with column information, or None if table doesn't exist.

        Example:
            >>> schema = db.get_schema("sales")
            >>> print(schema.columns)
            {'date': 'DATE', 'product': 'VARCHAR', 'revenue': 'DOUBLE'}
        """
        try:
            # Get column information
            result = self.conn.execute(f"DESCRIBE {table_name}").fetchall()

            columns = {row[0]: row[1] for row in result}

            # Get row count
            count_result = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
            row_count = count_result[0] if count_result else 0

            return TableSchema(
                table_name=table_name,
                columns=columns,
                row_count=row_count,
            )

        except duckdb.Error:
            return None

    def list_tables(self) -> list[str]:
        """List all tables in the database.

        Returns:
            List of table names.

        Example:
            >>> db.list_tables()
            ['sales', 'products', 'customers']
        """
        try:
            result = self.conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
            ).fetchall()
            return [row[0] for row in result]
        except duckdb.Error:
            return []

    def get_sample_data(self, table_name: str, limit: int = 5) -> QueryResult:
        """Get sample rows from a table.

        Args:
            table_name: Name of the table to sample.
            limit: Maximum number of rows to return.

        Returns:
            QueryResult with sample data.

        Example:
            >>> sample = db.get_sample_data("sales", limit=3)
            >>> print(sample.data)
        """
        return self.execute_query(f"SELECT * FROM {table_name} LIMIT {limit}")

    def get_statistics(self, table_name: str) -> dict | None:
        """Get basic statistics for numeric columns in a table.

        Args:
            table_name: Name of the table to analyze.

        Returns:
            Dictionary with column statistics, or None if failed.

        Example:
            >>> stats = db.get_statistics("sales")
            >>> print(stats["revenue"])
            {'min': 10.0, 'max': 1000.0, 'avg': 250.5}
        """
        try:
            schema = self.get_schema(table_name)
            if not schema:
                return None

            stats: dict = {}
            numeric_types = {"INTEGER", "BIGINT", "DOUBLE", "FLOAT", "DECIMAL"}

            for col_name, col_type in schema.columns.items():
                # Extract base type (handle things like DECIMAL(10,2))
                base_type = col_type.split("(")[0].upper()

                if base_type in numeric_types:
                    result = self.conn.execute(
                        f"SELECT "
                        f"MIN({col_name}) as min_val, "
                        f"MAX({col_name}) as max_val, "
                        f"AVG({col_name}) as avg_val, "
                        f"SUM({col_name}) as sum_val "
                        f"FROM {table_name}"
                    ).fetchone()

                    if result:
                        stats[col_name] = {
                            "min": result[0],
                            "max": result[1],
                            "avg": float(result[2]) if result[2] else None,
                            "sum": result[3],
                        }

            return stats if stats else None

        except duckdb.Error:
            return None

    def close(self) -> None:
        """Close the database connection.

        Should be called when done using the database.
        """
        if self.conn:
            self.conn.close()

    def __enter__(self) -> "DuckDBManager":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - closes connection."""
        self.close()
