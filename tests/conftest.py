"""Pytest configuration and fixtures for the test suite."""

from __future__ import annotations

import sys
from collections.abc import Generator
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data_analyst.database import DuckDBManager


@pytest.fixture
def sample_db() -> Generator[DuckDBManager, None, None]:
    """Create a test database with sample sales data.

    Yields:
        DuckDBManager instance with sample data loaded.
    """
    db = DuckDBManager()

    # Create sample sales table
    db.conn.execute(
        """
        CREATE TABLE sales (
            date DATE,
            product VARCHAR,
            category VARCHAR,
            quantity INTEGER,
            unit_price DECIMAL(10, 2),
            revenue DECIMAL(10, 2),
            region VARCHAR,
            salesperson VARCHAR
        )
        """
    )

    # Insert sample data
    db.conn.execute(
        """
        INSERT INTO sales VALUES
            ('2024-01-01', 'Widget A', 'Electronics', 100, 15.00, 1500.00, 'North', 'Alice'),
            ('2024-01-02', 'Widget B', 'Electronics', 50, 25.00, 1250.00, 'South', 'Bob'),
            ('2024-01-03', 'Gadget C', 'Home', 75, 30.00, 2250.00, 'East', 'Charlie'),
            ('2024-01-04', 'Widget A', 'Electronics', 120, 15.00, 1800.00, 'West', 'Diana'),
            ('2024-01-05', 'Gadget D', 'Home', 60, 45.00, 2700.00, 'North', 'Alice'),
            ('2024-01-06', 'Widget B', 'Electronics', 80, 25.00, 2000.00, 'South', 'Bob'),
            ('2024-01-07', 'Widget A', 'Electronics', 90, 15.00, 1350.00, 'East', 'Charlie'),
            ('2024-01-08', 'Gadget C', 'Home', 40, 30.00, 1200.00, 'West', 'Diana'),
            ('2024-01-09', 'Gadget D', 'Home', 55, 45.00, 2475.00, 'North', 'Alice'),
            ('2024-01-10', 'Widget B', 'Electronics', 95, 25.00, 2375.00, 'South', 'Bob')
        """
    )

    yield db

    db.close()


@pytest.fixture
def empty_db() -> Generator[DuckDBManager, None, None]:
    """Create an empty test database.

    Yields:
        Empty DuckDBManager instance.
    """
    db = DuckDBManager()
    yield db
    db.close()


@pytest.fixture
def sample_csv_path(tmp_path: Path) -> Path:
    """Create a temporary CSV file for testing.

    Args:
        tmp_path: pytest temporary directory fixture.

    Returns:
        Path to the created CSV file.
    """
    csv_content = """date,product,category,quantity,unit_price,revenue,region
2024-01-01,Widget A,Electronics,100,15.00,1500.00,North
2024-01-02,Widget B,Electronics,50,25.00,1250.00,South
2024-01-03,Gadget C,Home,75,30.00,2250.00,East
"""
    csv_path = tmp_path / "test_data.csv"
    csv_path.write_text(csv_content)
    return csv_path


@pytest.fixture
def sample_csv_content() -> str:
    """Return sample CSV content as a string.

    Returns:
        CSV content string.
    """
    return """date,product,category,quantity,unit_price,revenue,region
2024-01-01,Widget A,Electronics,100,15.00,1500.00,North
2024-01-02,Widget B,Electronics,50,25.00,1250.00,South
2024-01-03,Gadget C,Home,75,30.00,2250.00,East
"""
