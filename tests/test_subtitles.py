from silentir.transcribers.subtitles import parse_vtt_text


def test_parse_vtt_text_basic() -> None:
    vtt = """WEBVTT

00:00:00.000 --> 00:00:02.000
Hello world.

00:00:02.000 --> 00:00:05.000
Second line.
"""
    segments = parse_vtt_text(vtt)
    assert len(segments) == 2
    assert segments[0].text == "Hello world."
    assert segments[1].start == 2.0
