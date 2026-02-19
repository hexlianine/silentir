from __future__ import annotations


class PromptBuilder:
    def chunk_system_prompt(self, language: str) -> str:
        return (
            "You are an expert assistant that summarizes transcript chunks faithfully. "
            "Keep concrete facts. Avoid hallucinations. "
            f"Output in {language}."
        )

    def chunk_user_prompt(self, chunk_text: str, start_sec: float, end_sec: float) -> str:
        return (
            f"Chunk timestamp window: {start_sec:.1f}s to {end_sec:.1f}s\n"
            "Create a concise bullet summary of this chunk with important details and decisions:\n\n"
            f"{chunk_text}"
        )

    def merge_system_prompt(self, language: str, include_timestamps: str) -> str:
        ts_instruction = {
            "section": "Include section-level timestamps.",
            "point": "Include timestamps for every key point.",
            "none": "Do not include timestamps.",
        }.get(include_timestamps, "Include section-level timestamps.")

        return (
            "You are an expert technical note writer. "
            "Compose clean, readable Markdown with the exact sections: "
            "Overview, Key Points, Actionable Items, Timestamped Sections. "
            f"{ts_instruction} Output in {language}."
        )

    def merge_user_prompt(self, chunk_summaries: list[str]) -> str:
        joined = "\n\n".join(
            f"Chunk {idx + 1}:\n{summary}" for idx, summary in enumerate(chunk_summaries)
        )
        return (
            "Merge these chunk summaries into a single high-quality note document. "
            "Keep it faithful, avoid repeating points, and preserve major details.\n\n"
            f"{joined}"
        )
