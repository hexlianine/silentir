from silentir.noters.markdown import MarkdownNoter
from silentir.types import NoteResult


def test_markdown_renderer_appends_newline() -> None:
    result = NoteResult(
        url="u",
        title="t",
        language="en",
        note_markdown="## Overview\nHello",
        transcript_source="subtitle",
        provider_used="local",
        model_used="m",
        duration_sec=10,
        warnings=[],
    )
    out = MarkdownNoter().note(result)
    assert out.endswith("\n")
    assert "## Overview" in out
