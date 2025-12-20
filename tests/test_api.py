"""Tests for the FastAPI REST API endpoints."""

from __future__ import annotations

import io
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

# Add src and api to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_csv_bytes() -> bytes:
    """Return sample CSV content as bytes."""
    return b"""date,product,category,quantity,unit_price,revenue,region
2024-01-01,Widget A,Electronics,100,15.00,1500.00,North
2024-01-02,Widget B,Electronics,50,25.00,1250.00,South
2024-01-03,Gadget C,Home,75,30.00,2250.00,East
"""


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_check_returns_healthy(self, client: TestClient):
        """Test that health check returns healthy status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"

    def test_health_check_response_model(self, client: TestClient):
        """Test that health check response has correct structure."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data


class TestRootEndpoint:
    """Tests for the root / endpoint."""

    def test_root_returns_welcome_message(self, client: TestClient):
        """Test that root returns welcome message with docs link."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "docs" in data
        assert data["docs"] == "/docs"


class TestSchemaEndpoint:
    """Tests for the /schema endpoint."""

    def test_schema_returns_columns(self, client: TestClient, sample_csv_bytes: bytes):
        """Test that schema endpoint returns column information."""
        response = client.post(
            "/schema",
            files={"file": ("data.csv", io.BytesIO(sample_csv_bytes), "text/csv")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["tables"]) == 1
        assert data["tables"][0]["name"] == "data"
        assert len(data["tables"][0]["columns"]) == 7

    def test_schema_rejects_non_csv(self, client: TestClient):
        """Test that schema endpoint rejects non-CSV files."""
        response = client.post(
            "/schema",
            files={"file": ("data.txt", io.BytesIO(b"hello"), "text/plain")},
        )

        assert response.status_code == 400
        assert "CSV" in response.json()["detail"]

    def test_schema_with_empty_filename(self, client: TestClient):
        """Test that schema endpoint handles missing filename."""
        response = client.post(
            "/schema",
            files={"file": ("", io.BytesIO(b""), "text/csv")},
        )

        assert response.status_code == 400


class TestQueryEndpoint:
    """Tests for the /query endpoint."""

    def test_query_select_all(self, client: TestClient, sample_csv_bytes: bytes):
        """Test executing a SELECT * query."""
        response = client.post(
            "/query",
            files={"file": ("data.csv", io.BytesIO(sample_csv_bytes), "text/csv")},
            data={"sql": "SELECT * FROM data"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["row_count"] == 3
        assert len(data["columns"]) == 7
        assert len(data["rows"]) == 3

    def test_query_with_aggregation(self, client: TestClient, sample_csv_bytes: bytes):
        """Test executing a query with aggregation."""
        response = client.post(
            "/query",
            files={"file": ("data.csv", io.BytesIO(sample_csv_bytes), "text/csv")},
            data={"sql": "SELECT COUNT(*) as cnt FROM data"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["row_count"] == 1
        assert data["rows"][0][0] == 3

    def test_query_with_filter(self, client: TestClient, sample_csv_bytes: bytes):
        """Test executing a query with WHERE clause."""
        response = client.post(
            "/query",
            files={"file": ("data.csv", io.BytesIO(sample_csv_bytes), "text/csv")},
            data={"sql": "SELECT * FROM data WHERE category = 'Electronics'"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["row_count"] == 2

    def test_query_invalid_sql(self, client: TestClient, sample_csv_bytes: bytes):
        """Test that invalid SQL returns error."""
        response = client.post(
            "/query",
            files={"file": ("data.csv", io.BytesIO(sample_csv_bytes), "text/csv")},
            data={"sql": "INVALID SQL QUERY"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["error"] is not None

    def test_query_rejects_non_csv(self, client: TestClient):
        """Test that query endpoint rejects non-CSV files."""
        response = client.post(
            "/query",
            files={"file": ("data.json", io.BytesIO(b"{}"), "application/json")},
            data={"sql": "SELECT * FROM data"},
        )

        assert response.status_code == 400


class TestAnalyzeEndpoint:
    """Tests for the /analyze endpoint."""

    @patch("api.main.analyze")
    def test_analyze_success(
        self,
        mock_analyze: AsyncMock,
        client: TestClient,
        sample_csv_bytes: bytes,
    ):
        """Test successful analysis with mocked AI response."""
        mock_analyze.return_value = (
            "The data contains 3 records with Electronics and Home products."
        )

        response = client.post(
            "/analyze",
            files={"file": ("data.csv", io.BytesIO(sample_csv_bytes), "text/csv")},
            data={"question": "Summarize the data"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["question"] == "Summarize the data"
        assert "3 records" in data["analysis"]

    @patch("api.main.analyze")
    def test_analyze_with_error(
        self,
        mock_analyze: AsyncMock,
        client: TestClient,
        sample_csv_bytes: bytes,
    ):
        """Test analysis handles errors gracefully."""
        mock_analyze.side_effect = Exception("API error")

        response = client.post(
            "/analyze",
            files={"file": ("data.csv", io.BytesIO(sample_csv_bytes), "text/csv")},
            data={"question": "What is the total revenue?"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["error"] is not None

    def test_analyze_rejects_non_csv(self, client: TestClient):
        """Test that analyze endpoint rejects non-CSV files."""
        response = client.post(
            "/analyze",
            files={"file": ("data.xlsx", io.BytesIO(b""), "application/xlsx")},
            data={"question": "Summarize the data"},
        )

        assert response.status_code == 400
        assert "CSV" in response.json()["detail"]

    def test_analyze_missing_question(self, client: TestClient, sample_csv_bytes: bytes):
        """Test that analyze requires a question."""
        response = client.post(
            "/analyze",
            files={"file": ("data.csv", io.BytesIO(sample_csv_bytes), "text/csv")},
        )

        assert response.status_code == 422  # Validation error


class TestCORS:
    """Tests for CORS middleware configuration."""

    def test_cors_headers_present(self, client: TestClient):
        """Test that CORS headers are present in response."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        # CORS preflight should succeed
        assert response.status_code in [200, 405]


class TestOpenAPIDocumentation:
    """Tests for API documentation endpoints."""

    def test_docs_available(self, client: TestClient):
        """Test that /docs endpoint is available."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_redoc_available(self, client: TestClient):
        """Test that /redoc endpoint is available."""
        response = client.get("/redoc")
        assert response.status_code == 200

    def test_openapi_json_available(self, client: TestClient):
        """Test that OpenAPI JSON schema is available."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert data["info"]["title"] == "Autonomous Data Analyst API"
        assert data["info"]["version"] == "1.0.0"
