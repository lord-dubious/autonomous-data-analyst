"""FastAPI REST API for Autonomous Data Analyst.

This module provides a REST API for data analysis using the AI agent.

Run with: uvicorn api.main:app --reload
"""

from __future__ import annotations

import io
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data_analyst.agent import analyze
from data_analyst.database import DuckDBManager
from data_analyst.models import QueryResult, TableSchema


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


class SchemaResponse(BaseModel):
    """Schema response."""

    success: bool = Field(description="Whether schema retrieval succeeded")
    tables: list[TableSchema] = Field(description="List of table schemas")
    error: str | None = Field(default=None, description="Error message if failed")


class QueryRequest(BaseModel):
    """SQL query request."""

    sql: str = Field(description="SQL query to execute")


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    yield
    # Shutdown


# Create FastAPI app
app = FastAPI(
    title="Autonomous Data Analyst API",
    description="""
    AI-powered data analysis API using Google Gemini and DuckDB.

    ## Features

    - **Natural Language Analysis**: Ask questions about your data in plain English
    - **SQL Execution**: Run SQL queries directly on uploaded data
    - **Schema Inspection**: View the structure of your data

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
    return JSONResponse(
        content={"message": "Welcome to Autonomous Data Analyst API", "docs": "/docs"}
    )


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
    The AI agent will analyze the data and provide insights.

    **Example Questions:**
    - "What is the total revenue by product?"
    - "Show me the trend of sales over time"
    - "Which region has the best performance?"
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    try:
        # Read file content
        content = await file.read()
        file_obj = io.BytesIO(content)

        # Load into DuckDB
        db = DuckDBManager()
        success = db.load_csv(file_obj, "data")

        if not success:
            return AnalysisResponse(
                success=False,
                question=question,
                analysis="",
                error="Failed to load CSV file",
            )

        # Run analysis
        result = await analyze(db, question)

        db.close()

        return AnalysisResponse(
            success=True,
            question=question,
            analysis=result,
            error=None,
        )

    except Exception as e:
        return AnalysisResponse(
            success=False,
            question=question,
            analysis="",
            error=str(e),
        )


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

    try:
        # Read file content
        content = await file.read()
        file_obj = io.BytesIO(content)

        # Load into DuckDB
        db = DuckDBManager()
        success = db.load_csv(file_obj, "data")

        if not success:
            return QueryResult(
                success=False,
                error="Failed to load CSV file",
            )

        # Execute query
        result = db.execute_query(sql)

        db.close()

        return result

    except Exception as e:
        return QueryResult(
            success=False,
            error=str(e),
        )


@app.post("/schema", response_model=SchemaResponse, tags=["Analysis"])
async def get_schema(
    file: Annotated[UploadFile, File(description="CSV file to inspect")],
):
    """Get the schema of uploaded data.

    Upload a CSV file to see its column names and data types.
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    try:
        # Read file content
        content = await file.read()
        file_obj = io.BytesIO(content)

        # Load into DuckDB
        db = DuckDBManager()
        success = db.load_csv(file_obj, "data")

        if not success:
            return SchemaResponse(
                success=False,
                tables=[],
                error="Failed to load CSV file",
            )

        # Get schema
        schema = db.get_schema("data")

        db.close()

        if schema:
            return SchemaResponse(
                success=True,
                tables=[schema],
                error=None,
            )
        else:
            return SchemaResponse(
                success=False,
                tables=[],
                error="Failed to get schema",
            )

    except Exception as e:
        return SchemaResponse(
            success=False,
            tables=[],
            error=str(e),
        )
