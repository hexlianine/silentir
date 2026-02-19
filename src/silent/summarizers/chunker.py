from __future__ import annotations

from dataclasses import dataclass

from ..types import Segment, Transcript


@dataclass
class TranscriptChunk:
    index: int
    start: float
    end: float
    text: str


class TranscriptChunker:
    def __init__(self, *, max_words: int = 1200, overlap_words: int = 120) -> None:
        self.max_words = max_words
        self.overlap_words = overlap_words

    def chunk(self, transcript: Transcript) -> list[TranscriptChunk]:
        chunks: list[TranscriptChunk] = []
        buffer: list[Segment] = []
        buffer_words = 0

        def flush(chunk_idx: int) -> int:
            nonlocal buffer, buffer_words
            if not buffer:
                return chunk_idx
            text = " ".join(seg.text for seg in buffer).strip()
            chunks.append(
                TranscriptChunk(
                    index=chunk_idx,
                    start=buffer[0].start,
                    end=buffer[-1].end,
                    text=text,
                )
            )
            if self.overlap_words <= 0:
                buffer = []
                buffer_words = 0
            else:
                carry: list[Segment] = []
                count = 0
                for seg in reversed(buffer):
                    carry.insert(0, seg)
                    count += self._word_count(seg.text)
                    if count >= self.overlap_words:
                        break
                buffer = carry
                buffer_words = sum(self._word_count(s.text) for s in buffer)
            return chunk_idx + 1

        idx = 0
        for seg in transcript.segments:
            seg_words = self._word_count(seg.text)
            if buffer and buffer_words + seg_words > self.max_words:
                idx = flush(idx)
            buffer.append(seg)
            buffer_words += seg_words

        flush(idx)
        return chunks

    @staticmethod
    def _word_count(text: str) -> int:
        return len(text.split())
