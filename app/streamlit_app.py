"""Streamlit web application for Autonomous Data Analyst.

This module provides an interactive web interface for data analysis
using DuckDB and optional Gemini-assisted agent responses.

Run with: streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import asyncio
import io
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data_analyst.agent import analyze
from data_analyst.database import DuckDBManager

# Page configuration
st.set_page_config(
    page_title="Autonomous Data Analyst",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


def init_session_state() -> None:
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "db" not in st.session_state:
        st.session_state.db = None
    if "data_loaded" not in st.session_state:
        st.session_state.data_loaded = False
    if "current_data" not in st.session_state:
        st.session_state.current_data = None
    if "table_name" not in st.session_state:
        st.session_state.table_name = "data"


def load_css() -> None:
    """Load custom CSS styles."""
    st.markdown(
        """
        <style>
        .stChatMessage {
            padding: 1rem;
        }
        .main-header {
            font-size: 2.5rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
        }
        .sub-header {
            font-size: 1.1rem;
            color: #666;
            margin-bottom: 2rem;
        }
        .metric-card {
            background-color: #f0f2f6;
            padding: 1rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    """Render the sidebar with file upload and controls."""
    with st.sidebar:
        st.title("📊 Data Analyst")
        st.markdown("---")

        # File upload section
        st.subheader("📁 Data Upload")
        uploaded_file = st.file_uploader(
            "Upload a CSV file",
            type=["csv"],
            help="Upload a CSV file to analyze. The data will be loaded into DuckDB.",
        )

        if uploaded_file is not None and (
            st.session_state.current_data is None
            or uploaded_file.name != st.session_state.get("uploaded_filename")
        ):
            with st.spinner("Loading data..."):
                try:
                    # Reset file position
                    uploaded_file.seek(0)

                    # Read as pandas for preview
                    df = pd.read_csv(uploaded_file)
                    st.session_state.current_data = df

                    # Reset and load into DuckDB
                    uploaded_file.seek(0)
                    st.session_state.db = DuckDBManager()
                    success = st.session_state.db.load_csv(
                        uploaded_file, st.session_state.table_name
                    )

                    if success:
                        st.session_state.data_loaded = True
                        st.session_state.uploaded_filename = uploaded_file.name
                        st.success(f"✅ Loaded {len(df):,} rows")
                    else:
                        st.error("Failed to load data")

                except Exception as e:
                    st.error(f"Error loading file: {e}")

        # Data preview
        if st.session_state.data_loaded and st.session_state.current_data is not None:
            st.markdown("---")
            st.subheader("📋 Data Preview")

            df = st.session_state.current_data
            st.caption(f"**{len(df):,}** rows × **{len(df.columns)}** columns")

            # Show column info
            with st.expander("Column Types"):
                col_info = pd.DataFrame({"Type": df.dtypes.astype(str), "Non-Null": df.count()})
                st.dataframe(col_info, use_container_width=True)

        # Controls section
        st.markdown("---")
        st.subheader("🎛️ Controls")

        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

        if st.button("📥 Export Chat", use_container_width=True) and st.session_state.messages:
            export_chat_history()

        # Sample questions
        if st.session_state.data_loaded:
            st.markdown("---")
            st.subheader("💡 Sample Questions")

            sample_questions = [
                "What columns are in this data?",
                "Show me summary statistics",
                "What are the top 5 values?",
                "Are there any missing values?",
            ]

            for q in sample_questions:
                if st.button(q, key=f"sample_{q}", use_container_width=True):
                    st.session_state.pending_question = q
                    st.rerun()


def export_chat_history() -> None:
    """Export chat history as JSON."""
    if st.session_state.messages:
        export_data = {
            "exported_at": datetime.now().isoformat(),
            "messages": st.session_state.messages,
        }
        json_str = json.dumps(export_data, indent=2, default=str)

        st.sidebar.download_button(
            label="📄 Download JSON",
            data=json_str,
            file_name=f"chat_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
        )


def create_chart(
    df: pd.DataFrame,
    chart_type: str,
    x_col: str,
    y_col: str,
    title: str = "",
    color_col: str | None = None,
) -> go.Figure | None:
    """Create a Plotly chart based on specifications.

    Args:
        df: DataFrame with the data
        chart_type: Type of chart (bar, line, pie, scatter, area)
        x_col: Column for x-axis
        y_col: Column for y-axis
        title: Chart title
        color_col: Optional column for color grouping

    Returns:
        Plotly figure or None if creation fails
    """
    try:
        if chart_type == "bar":
            fig = px.bar(df, x=x_col, y=y_col, color=color_col, title=title)
        elif chart_type == "line":
            fig = px.line(df, x=x_col, y=y_col, color=color_col, title=title)
        elif chart_type == "pie":
            fig = px.pie(df, names=x_col, values=y_col, title=title)
        elif chart_type == "scatter":
            fig = px.scatter(df, x=x_col, y=y_col, color=color_col, title=title)
        elif chart_type == "area":
            fig = px.area(df, x=x_col, y=y_col, color=color_col, title=title)
        else:
            return None

        fig.update_layout(
            template="plotly_white",
            margin={"l": 40, "r": 40, "t": 60, "b": 40},
        )
        return fig

    except Exception:
        return None


def render_data_preview() -> None:
    """Render data preview in an expander."""
    if st.session_state.current_data is not None:
        with st.expander("📊 View Data", expanded=False):
            df = st.session_state.current_data

            # Data preview with pagination
            rows_per_page = 10
            total_pages = (len(df) - 1) // rows_per_page + 1

            col1, col2 = st.columns([3, 1])
            with col2:
                page = st.number_input(
                    "Page",
                    min_value=1,
                    max_value=total_pages,
                    value=1,
                    key="data_page",
                )

            start_idx = (page - 1) * rows_per_page
            end_idx = start_idx + rows_per_page

            st.dataframe(df.iloc[start_idx:end_idx], use_container_width=True, height=300)
            st.caption(f"Showing rows {start_idx + 1}-{min(end_idx, len(df))} of {len(df)}")

            # Quick stats
            st.markdown("#### Quick Statistics")
            numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

            if numeric_cols:
                stats_df = df[numeric_cols].describe().T
                st.dataframe(stats_df, use_container_width=True)

            # Export data
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)

            st.download_button(
                label="📥 Download CSV",
                data=csv_buffer.getvalue(),
                file_name="data_export.csv",
                mime="text/csv",
            )


def render_chat_message(message: dict[str, Any]) -> None:
    """Render a single chat message with formatting."""
    role = message["role"]
    content = message["content"]

    with st.chat_message(role):
        st.markdown(content)

        # If there's chart data, render the chart
        if "chart" in message:
            chart_spec = message["chart"]
            if st.session_state.current_data is not None:
                fig = create_chart(
                    st.session_state.current_data,
                    chart_spec.get("type", "bar"),
                    chart_spec.get("x"),
                    chart_spec.get("y"),
                    chart_spec.get("title", ""),
                    chart_spec.get("color"),
                )
                if fig:
                    st.plotly_chart(fig, use_container_width=True)


async def process_question(question: str) -> str:
    """Process a user question using the configured analysis agent.

    Args:
        question: The user's natural language question

    Returns:
        The agent's response as a string
    """
    if st.session_state.db is None:
        return "Please upload a CSV file first to analyze data."

    try:
        response = await analyze(st.session_state.db, question)
        return response
    except Exception as e:
        return f"Error analyzing data: {e!s}"


def render_main_chat() -> None:
    """Render the main chat interface."""
    # Header
    st.markdown(
        '<p class="main-header">📊 Autonomous Data Analyst</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="sub-header">Upload a CSV and ask questions about your data using natural language.</p>',
        unsafe_allow_html=True,
    )

    # Data preview section
    if st.session_state.data_loaded:
        render_data_preview()

    # Chat messages
    st.markdown("---")

    for message in st.session_state.messages:
        render_chat_message(message)

    # Handle pending question from sidebar
    pending = st.session_state.get("pending_question")
    if pending:
        st.session_state.pending_question = None
        process_and_display_question(pending)

    # Chat input
    if question := st.chat_input(
        "Ask a question about your data...",
        disabled=not st.session_state.data_loaded,
    ):
        process_and_display_question(question)


def process_and_display_question(question: str) -> None:
    """Process a question and display the response."""
    # Add user message
    st.session_state.messages.append({"role": "user", "content": question})

    with st.chat_message("user"):
        st.markdown(question)

    # Get agent response
    with st.chat_message("assistant"):
        with st.spinner("Analyzing..."):
            response = asyncio.run(process_question(question))

        st.markdown(response)

        # Add assistant message
        st.session_state.messages.append({"role": "assistant", "content": response})


def render_welcome_message() -> None:
    """Render welcome message when no data is loaded."""
    st.markdown(
        """
        ## Welcome! 👋

        To get started:

        1. **Upload a CSV file** using the sidebar on the left
        2. **Ask questions** about your data in natural language
        3. **Review analysis** generated from DuckDB queries and optional Gemini assistance

        ### Example Questions

        Once you upload data, you can ask questions like:

        - "What are the total sales by region?"
        - "Show me the trend of revenue over time"
        - "Which product has the highest quantity sold?"
        - "Are there any outliers in the data?"
        - "Give me a summary of all numeric columns"

        ### Features

        - 🤖 **Natural Language Queries** - Ask questions in plain English
        - 📈 **Auto-Generated Charts** - Visualizations based on your data
        - 💾 **Export Results** - Download data and chat history
        - 🔄 **Conversation History** - Track your analysis session
        """
    )


def main() -> None:
    """Main application entry point."""
    init_session_state()
    load_css()
    render_sidebar()

    if st.session_state.data_loaded:
        render_main_chat()
    else:
        render_welcome_message()


if __name__ == "__main__":
    main()
