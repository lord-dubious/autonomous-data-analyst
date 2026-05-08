"""FastAPI REST API for CSV-backed DuckDB analysis.

This module provides endpoints for CSV upload, DuckDB queries, and optional
Gemini-assisted analysis through the project agent.

Run with: uvicorn api.main:app --reload
"""

from __future__ import annotations

import io
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data_analyst.agent import analyze_with_metadata
from data_analyst.database import DuckDBManager
from data_analyst.models import QueryResult, TableSchema

logger = logging.getLogger(__name__)


# Response models
class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(description="Service status")
    version: str = Field(description="API version")


class AnalysisRequest(BaseModel):
    """Analysis request body."""

    question: str = Field(description="Natural language question about the data")


class AnalysisResponse(BaseModel):
    """Analysis response."""

    success: bool = Field(description="Whether analysis succeeded")
    question: str = Field(description="Original question")
    analysis: str = Field(description="AI-generated analysis")
    error: str | None = Field(default=None, description="Error message if failed")
    metadata: dict[str, Any] | None = Field(
        default=None, description="Load and agent metadata for degraded or failed responses"
    )


class SchemaResponse(BaseModel):
    """Schema response."""

    success: bool = Field(description="Whether schema retrieval succeeded")
    tables: list[TableSchema] = Field(description="List of table schemas")
    error: str | None = Field(default=None, description="Error message if failed")
    metadata: dict[str, Any] | None = Field(
        default=None, description="Load/schema metadata for degraded or failed responses"
    )


class QueryRequest(BaseModel):
    """SQL query request."""

    sql: str = Field(description="SQL query to execute")


# Lifespan context manager
@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan handler."""
    # Startup
    yield
    # Shutdown


# Create FastAPI app
app = FastAPI(
    title="Autonomous Data Analyst API",
    description="""
    CSV analysis API using DuckDB and optional Google Gemini assistance.

    ## Features

    - **Natural Language Analysis**: Ask questions about your data when Gemini is configured
    - **SQL Execution**: Run SQL queries directly on uploaded data
    - **Schema Inspection**: View the structure of your data

    Gemini responses depend on external service availability and may be incomplete.
    DuckDB queries operate on the uploaded CSV loaded into a temporary table named `data`.

    ## Usage

    1. Upload a CSV file to `/upload`
    2. Ask questions with `/analyze`
    3. Or execute SQL directly with `/query`
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
async def root():
    """Redirect to docs."""
    return JSONResponse(content={"message": "Welcome to the CSV analysis API", "docs": "/docs"})


def _exception_metadata(boundary: str, exc: Exception) -> dict[str, Any]:
    """Return response-safe metadata for an exception boundary."""
    return {
        "boundary": boundary,
        "degraded": True,
        "error_type": type(exc).__name__,
    }


def _load_failure_metadata(db: DuckDBManager, boundary: str) -> dict[str, Any]:
    """Return response-safe metadata for CSV load failures."""
    return {
        "boundary": boundary,
        "degraded": True,
        "load": db.last_load_metadata,
    }


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Health check endpoint.

    Returns the service status and version.
    """
    return HealthResponse(status="healthy", version="1.0.0")


@app.post("/analyze", response_model=AnalysisResponse, tags=["Analysis"])
async def analyze_data(
    file: Annotated[UploadFile, File(description="CSV file to analyze")],
    question: Annotated[str, Form(description="Question about the data")],
):
    """Analyze uploaded data with natural language.

    Upload a CSV file and ask a question about the data.
    Gemini-assisted analysis runs when the configured agent call succeeds.

    **Example Questions:**
    - "What is the total revenue by product?"
    - "Show me the trend of sales over time"
    - "Which region has the best performance?"
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    db = DuckDBManager()
    try:
        # Read file content
        content = await file.read()
        file_obj = io.BytesIO(content)

        # Load into DuckDB
        success = db.load_csv(file_obj, "data")

        if not success:
            logger.warning("CSV load failed during analyze: %s", db.last_load_metadata)
            return AnalysisResponse(
                success=False,
                question=question,
                analysis="",
                error="Failed to load CSV file",
                metadata=_load_failure_metadata(db, "csv_load"),
            )

        # Run analysis
        result = await analyze_with_metadata(db, question)
        if not result.success:
            logger.warning("Agent analysis failed: %s", result.metadata)
            return AnalysisResponse(
                success=False,
                question=question,
                analysis="",
                error=result.error,
                metadata=result.metadata,
            )

        return AnalysisResponse(
            success=True,
            question=question,
            analysis=result.output,
            error=None,
            metadata={"load": db.last_load_metadata, "agent": result.metadata},
        )

    except Exception as exc:
        logger.warning("Analyze endpoint failed at API boundary: %s", type(exc).__name__)
        return AnalysisResponse(
            success=False,
            question=question,
            analysis="",
            error="Analysis request failed",
            metadata=_exception_metadata("api_analyze", exc),
        )
    finally:
        db.close()


@app.post("/query", response_model=QueryResult, tags=["Analysis"])
async def execute_query(
    file: Annotated[UploadFile, File(description="CSV file to query")],
    sql: Annotated[str, Form(description="SQL query to execute")],
):
    """Execute a SQL query on uploaded data.

    Upload a CSV file and run a SQL query against it.
    The data is loaded into a table called 'data'.

    **Example Queries:**
    - `SELECT * FROM data LIMIT 10`
    - `SELECT product, SUM(revenue) FROM data GROUP BY product`
    - `SELECT COUNT(*) FROM data WHERE region = 'North'`
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    db = DuckDBManager()
    try:
        # Read file content
        content = await file.read()
        file_obj = io.BytesIO(content)

        # Load into DuckDB
        success = db.load_csv(file_obj, "data")

        if not success:
            logger.warning("CSV load failed during query: %s", db.last_load_metadata)
            return QueryResult(
                success=False,
                error="Failed to load CSV file",
                metadata=_load_failure_metadata(db, "csv_load"),
            )

        # Execute query
        result = db.execute_query(sql)
        result.metadata = {
            **(result.metadata or {}),
            "load": db.last_load_metadata,
        }

        return result

    except Exception as exc:
        logger.warning("Query endpoint failed at API boundary: %s", type(exc).__name__)
        return QueryResult(
            success=False,
            error="Query request failed",
            metadata=_exception_metadata("api_query", exc),
        )
    finally:
        db.close()


@app.post("/schema", response_model=SchemaResponse, tags=["Analysis"])
async def get_schema(
    file: Annotated[UploadFile, File(description="CSV file to inspect")],
):
    """Get the schema of uploaded data.

    Upload a CSV file to see its column names and data types.
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    db = DuckDBManager()
    try:
        # Read file content
        content = await file.read()
        file_obj = io.BytesIO(content)

        # Load into DuckDB
        success = db.load_csv(file_obj, "data")

        if not success:
            logger.warning("CSV load failed during schema: %s", db.last_load_metadata)
            return SchemaResponse(
                success=False,
                tables=[],
                error="Failed to load CSV file",
                metadata=_load_failure_metadata(db, "csv_load"),
            )

        # Get schema
        schema = db.get_schema("data")

        if schema:
            return SchemaResponse(
                success=True,
                tables=[schema],
                error=None,
                metadata={"load": db.last_load_metadata},
            )
        else:
            return SchemaResponse(
                success=False,
                tables=[],
                error="Failed to get schema",
                metadata={"boundary": "schema_lookup", "degraded": True},
            )

    except Exception as exc:
        logger.warning("Schema endpoint failed at API boundary: %s", type(exc).__name__)
        return SchemaResponse(
            success=False,
            tables=[],
            error="Schema request failed",
            metadata=_exception_metadata("api_schema", exc),
        )
    finally:
        db.close()
