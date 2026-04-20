from silentir.summarizers.chunker import TranscriptChunker
from silentir.types import Segment, Transcript


def test_chunk_transcript_splits_large_input() -> None:
    segments = [
        Segment(start=0.0, end=1.0, text="one " * 100),
        Segment(start=1.0, end=2.0, text="two " * 100),
        Segment(start=2.0, end=3.0, text="three " * 100),
    ]
    transcript = Transcript(language="en", source="subtitle", segments=segments)
    chunks = TranscriptChunker(max_words=150, overlap_words=20).chunk(transcript)
    assert len(chunks) >= 2
    assert chunks[0].start == 0.0
    assert chunks[-1].end == 3.0
