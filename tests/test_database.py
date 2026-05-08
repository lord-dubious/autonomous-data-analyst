"""Tests for DuckDB database interface."""

from __future__ import annotations

import io
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data_analyst.database import DuckDBManager
from data_analyst.models import QueryResult, TableSchema


class TestDuckDBManager:
    """Test suite for DuckDBManager class."""

    def test_init_memory_database(self) -> None:
        """Test creating an in-memory database."""
        db = DuckDBManager()
        assert db.conn is not None
        assert db.db_path == ":memory:"
        db.close()

    def test_list_tables_empty(self, empty_db: DuckDBManager) -> None:
        """Test listing tables in an empty database."""
        tables = empty_db.list_tables()
        assert tables == []

    def test_list_tables_with_data(self, sample_db: DuckDBManager) -> None:
        """Test listing tables in a database with data."""
        tables = sample_db.list_tables()
        assert "sales" in tables

    def test_execute_query_success(self, sample_db: DuckDBManager) -> None:
        """Test successful query execution."""
        result = sample_db.execute_query("SELECT COUNT(*) as cnt FROM sales")

        assert result.success is True
        assert result.data is not None
        assert result.data[0]["cnt"] == 10
        assert result.row_count == 1
        assert result.error is None

    def test_execute_query_failure(self, sample_db: DuckDBManager) -> None:
        """Test failed query execution."""
        result = sample_db.execute_query("SELECT * FROM nonexistent_table")

        assert result.success is False
        assert result.data is None
        assert result.error is not None
        assert "nonexistent_table" in result.error.lower()
        assert result.metadata is not None
        assert result.metadata["boundary"] == "duckdb_query"
        assert result.metadata["degraded"] is True

    def test_execute_query_aggregation(self, sample_db: DuckDBManager) -> None:
        """Test aggregation query."""
        result = sample_db.execute_query(
            "SELECT product, SUM(revenue) as total FROM sales GROUP BY product ORDER BY total DESC"
        )

        assert result.success is True
        assert result.data is not None
        assert len(result.data) == 4  # Widget A, Widget B, Gadget C, Gadget D
        assert result.columns == ["product", "total"]

    def test_get_schema(self, sample_db: DuckDBManager) -> None:
        """Test getting table schema."""
        schema = sample_db.get_schema("sales")

        assert schema is not None
        assert isinstance(schema, TableSchema)
        assert schema.table_name == "sales"
        assert "product" in schema.columns
        assert "revenue" in schema.columns
        assert schema.row_count == 10

    def test_get_schema_nonexistent(self, sample_db: DuckDBManager) -> None:
        """Test getting schema for nonexistent table."""
        schema = sample_db.get_schema("nonexistent_table")
        assert schema is None

    def test_get_sample_data(self, sample_db: DuckDBManager) -> None:
        """Test getting sample data from a table."""
        result = sample_db.get_sample_data("sales", limit=3)

        assert result.success is True
        assert result.data is not None
        assert len(result.data) == 3

    def test_get_statistics(self, sample_db: DuckDBManager) -> None:
        """Test getting statistics for numeric columns."""
        stats = sample_db.get_statistics("sales")

        assert stats is not None
        assert "quantity" in stats
        assert "revenue" in stats
        assert stats["quantity"]["min"] == 40
        assert stats["quantity"]["max"] == 120

    def test_load_csv_from_path(self, empty_db: DuckDBManager, sample_csv_path: Path) -> None:
        """Test loading CSV from file path."""
        success = empty_db.load_csv(sample_csv_path, "test_table")

        assert success is True
        assert empty_db.last_load_metadata["success"] is True
        assert empty_db.last_load_metadata["stage"] == "loaded"
        assert empty_db.last_load_metadata["row_count"] == 3
        assert "test_table" in empty_db.list_tables()

        result = empty_db.execute_query("SELECT COUNT(*) as cnt FROM test_table")
        assert result.data[0]["cnt"] == 3

    def test_load_csv_from_string_io(
        self, empty_db: DuckDBManager, sample_csv_content: str
    ) -> None:
        """Test loading CSV from file-like object."""
        file_obj = io.StringIO(sample_csv_content)
        success = empty_db.load_csv(file_obj, "test_table")

        assert success is True
        assert "test_table" in empty_db.list_tables()

    def test_load_csv_nonexistent_file(self, empty_db: DuckDBManager) -> None:
        """Test loading nonexistent CSV file."""
        success = empty_db.load_csv("/nonexistent/path.csv", "test_table")
        assert success is False
        assert empty_db.last_load_metadata["success"] is False
        assert empty_db.last_load_metadata["stage"] == "read_csv"
        assert empty_db.last_load_metadata["error_type"] == "FileNotFoundError"
        assert "not found" in empty_db.last_load_metadata["error"]

    def test_load_csv_invalid_content_records_metadata(self, empty_db: DuckDBManager) -> None:
        """Test invalid CSV content records failure metadata."""
        success = empty_db.load_csv(io.StringIO(""), "test_table")

        assert success is False
        assert empty_db.last_load_metadata["success"] is False
        assert empty_db.last_load_metadata["stage"] == "load_csv"
        assert empty_db.last_load_metadata["error_type"] is not None

    def test_context_manager(self) -> None:
        """Test using DuckDBManager as a context manager."""
        with DuckDBManager() as db:
            db.conn.execute("CREATE TABLE test (id INTEGER)")
            tables = db.list_tables()
            assert "test" in tables

    def test_column_name_normalization(self, empty_db: DuckDBManager, tmp_path: Path) -> None:
        """Test that column names are normalized (lowercase, underscores)."""
        csv_content = """Product Name,Unit Price,Total Revenue
Widget A,15.00,1500.00
Widget B,25.00,1250.00
"""
        csv_path = tmp_path / "test.csv"
        csv_path.write_text(csv_content)

        empty_db.load_csv(csv_path, "test_table")
        schema = empty_db.get_schema("test_table")

        assert schema is not None
        # Column names should be normalized
        assert "product_name" in schema.columns
        assert "unit_price" in schema.columns
        assert "total_revenue" in schema.columns


class TestQueryResult:
    """Test suite for QueryResult model."""

    def test_success_result(self) -> None:
        """Test creating a successful QueryResult."""
        result = QueryResult(
            success=True,
            data=[{"id": 1, "name": "test"}],
            columns=["id", "name"],
            row_count=1,
        )

        assert result.success is True
        assert result.data is not None
        assert result.error is None

    def test_failure_result(self) -> None:
        """Test creating a failed QueryResult."""
        result = QueryResult(
            success=False,
            error="Table not found",
        )

        assert result.success is False
        assert result.data is None
        assert result.error == "Table not found"


class TestTableSchema:
    """Test suite for TableSchema model."""

    def test_create_schema(self) -> None:
        """Test creating a TableSchema."""
        schema = TableSchema(
            table_name="test_table",
            columns={"id": "INTEGER", "name": "VARCHAR"},
            row_count=100,
        )

        assert schema.table_name == "test_table"
        assert len(schema.columns) == 2
        assert schema.row_count == 100
