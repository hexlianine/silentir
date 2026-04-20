from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from silentir.api import generate_notes
from silentir.exceptions import (
    ConfigurationError,
    ModelInferenceError,
    TranscriptExtractionError,
    UnsupportedURLError,
)
from silentir.noters import default_noter_registry


def _sanitize_filename(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    return sanitized.strip("-") or "notes"


def _env_str(key: str, default: str) -> str:
    raw = os.environ.get(key)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip()


def _format_duration(seconds: int | float | None) -> str:
    if seconds is None:
        return "Unknown"
    total_seconds = int(seconds)
    minutes, sec = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{sec:02d}"
    return f"{minutes:d}:{sec:02d}"


def render_app() -> None:
    examples_dir = Path(__file__).resolve().parent
    if str(examples_dir) not in sys.path:
        sys.path.insert(0, str(examples_dir))
    from envdot import load_dotenv_in_directories

    load_dotenv_in_directories(examples_dir.parent, examples_dir)
    try:
        import streamlit as st
    except ModuleNotFoundError as exc:
        raise SystemExit("Streamlit is not installed. Run: uv sync --extra ui") from exc

    st.set_page_config(page_title="Silentir UI", page_icon="M", layout="wide")
    st.title("Silentir")
    st.caption("Generate structured notes from YouTube and Bilibili URLs.")

    if "rendered_note" not in st.session_state:
        st.session_state.rendered_note = None
        st.session_state.output_format = "markdown"
        st.session_state.result = None

    with st.form("note_form", clear_on_submit=False):
        url = st.text_input("Video URL", placeholder="https://www.youtube.com/watch?v=...")
        language = st.text_input("Language", value="auto", help="Use 'auto' to infer language.")

        col1, col2, col3 = st.columns(3)
        with col1:
            provider_policy = st.selectbox(
                "Provider policy",
                options=("local_first", "online_first", "local_only", "online_only"),
                index=0,
            )
        with col2:
            output_format = st.selectbox(
                "Output format",
                options=["markdown", "text", "json"],
                index=0,
            )
        with col3:
            include_timestamps = st.selectbox(
                "Include timestamps",
                options=["section", "point", "none"],
                index=0,
            )

        col4, col5 = st.columns(2)
        with col4:
            local_model = st.text_input(
                "Local model",
                value=_env_str("LOCAL_MODEL", "qwen2.5:7b-instruct"),
            )
            ollama_host = st.text_input(
                "Ollama host",
                value=_env_str("OLLAMA_HOST", "http://localhost:11434"),
            )
        with col5:
            online_model = st.text_input(
                "Online model",
                value=_env_str("ONLINE_MODEL", "qwen/qwen3-235b-a22b-thinking-2507"),
            )
            openai_base_url = st.text_input(
                "OpenAI-compatible base URL",
                value=_env_str("OPENAI_BASE_URL", "https://openrouter.ai/api/v1"),
            )

        col6, col7 = st.columns(2)
        with col6:
            openai_api_key = st.text_input(
                "OpenAI API key",
                type="password",
                value=_env_str("OPENAI_API_KEY", ""),
            )
            write_path = st.text_input("Write path (optional)", value="")
        with col7:
            cookies_path = st.text_input("Cookies path (optional)", value="")

        generate = st.form_submit_button("Generate Notes", type="primary")

    if generate:
        if not url.strip():
            st.error("Please enter a video URL.")
        else:
            with st.spinner("Generating notes..."):
                try:
                    result = generate_notes(
                        url.strip(),
                        language=language.strip() or "auto",
                        output_format=output_format,
                        provider_policy=provider_policy,
                        local_model=local_model.strip() or None,
                        online_model=online_model.strip() or None,
                        ollama_host=ollama_host.strip() or "http://localhost:11434",
                        openai_base_url=openai_base_url.strip() or "https://api.openai.com/v1",
                        openai_api_key=openai_api_key.strip() or None,
                        include_timestamps=include_timestamps,
                        write_path=write_path.strip() or None,
                        cookies_path=cookies_path.strip() or None,
                    )
                except (
                    UnsupportedURLError,
                    ConfigurationError,
                    TranscriptExtractionError,
                    ModelInferenceError,
                ) as exc:
                    import textwrap
                    import traceback

                    formatted_traceback = "".join(
                        traceback.format_exception(type(exc), exc, exc.__traceback__)
                    )
                    st.error(
                        f"**An error occurred:**\n\n"
                        f"**Type:** `{type(exc).__name__}`\n"
                        f"**Message:** {exc}\n\n"
                        f"**Traceback:**\n\n"
                        f"```python\n{textwrap.dedent(formatted_traceback)}\n```"
                    )
                else:
                    rendered_note = default_noter_registry().note(output_format, result)
                    st.session_state.rendered_note = rendered_note
                    st.session_state.output_format = output_format
                    st.session_state.result = result
                    if write_path.strip():
                        st.info(f"Wrote notes to: {write_path.strip()}")

    if st.session_state.result is None or st.session_state.rendered_note is None:
        return

    result = st.session_state.result
    rendered_note = st.session_state.rendered_note
    output_format = st.session_state.output_format

    st.success("Notes generated.")
    st.subheader("Result")

    c1, c2, c3 = st.columns(3)
    c1.metric("Provider", result.provider_used or "Unknown")
    c2.metric("Model", result.model_used or "Unknown")
    c3.metric("Duration", _format_duration(result.duration_sec))

    st.write(f"**Title:** {result.title}")
    st.write(f"**Language:** {result.language}")
    st.write(f"**Transcript source:** {result.transcript_source}")

    if result.warnings:
        st.warning("\n".join(f"- {item}" for item in result.warnings))

    st.subheader("Notes")
    if output_format == "markdown":
        st.markdown(rendered_note)
    elif output_format == "json":
        st.code(rendered_note, language="json")
    else:
        st.text(rendered_note)

    extension = {"markdown": "md", "text": "txt", "json": "json"}[output_format]
    mime = {
        "markdown": "text/markdown",
        "text": "text/plain",
        "json": "application/json",
    }[output_format]
    filename = f"{_sanitize_filename(result.title)}.{extension}"
    st.download_button(
        label="Download notes",
        data=rendered_note,
        file_name=filename,
        mime=mime,
    )


if __name__ == "__main__":
    render_app()
