from __future__ import annotations

import os
from pathlib import Path

from silentir.recorders.file import FileRecorder


def test_supports_existing_file(tmp_path):
    video = tmp_path / "lecture.mp4"
    video.write_bytes(b"\x00" * 16)
    recorder = FileRecorder()
    assert recorder.supports(str(video)) is True


def test_supports_video_extension_even_if_missing():
    recorder = FileRecorder()
    assert recorder.supports("/tmp/nonexistent_video.mp4") is True
    assert recorder.supports("/tmp/nonexistent_video.mkv") is True
    assert recorder.supports("/tmp/nonexistent_video.webm") is True


def test_supports_rejects_urls():
    recorder = FileRecorder()
    assert recorder.supports("https://youtube.com/watch?v=abc") is False
    assert recorder.supports("http://bilibili.com/video/BV123") is False


def test_supports_rejects_unknown_extension():
    recorder = FileRecorder()
    assert recorder.supports("/tmp/notes.txt") is False


def test_record_returns_metadata_and_no_transcript(tmp_path):
    video = tmp_path / "my_lecture.mp4"
    video.write_bytes(b"\x00" * 16)
    recorder = FileRecorder()

    metadata, transcript, warnings = recorder.record(str(video))

    assert metadata.title == "my_lecture"
    assert metadata.platform == "local"
    assert metadata.duration_sec is None
    assert transcript is None
    assert len(warnings) > 0


def test_download_audio_returns_path(tmp_path):
    video = tmp_path / "talk.mp4"
    video.write_bytes(b"\x00" * 16)
    recorder = FileRecorder()

    audio_path, temp_dir = recorder.download_audio(str(video))
    assert os.path.basename(audio_path) == "talk.mp4"
    assert os.path.exists(audio_path)
    temp_dir.cleanup()


def test_download_audio_missing_file_raises():
    recorder = FileRecorder()
    import pytest

    with pytest.raises(FileNotFoundError):
        recorder.download_audio("/tmp/does_not_exist_12345.mp4")


def test_record_with_real_video():
    # Use the sample video generated in tests/resources
    video_path = str(Path(__file__).parent / "resources" / "sample_video.mp4")

    # Ensure the file exists
    assert os.path.exists(video_path)

    recorder = FileRecorder()
    metadata, transcript, warnings = recorder.record(video_path)

    assert metadata.title == "sample_video"
    assert metadata.platform == "local"
    assert transcript is None
    assert "no subtitles" in warnings[0].lower()

    # Test download_audio with real file
    audio_path, temp_dir = recorder.download_audio(video_path)
    try:
        assert os.path.basename(audio_path) == "sample_video.mp4"
        assert os.path.exists(audio_path)
        # Verify it's either a symlink or a copy
        assert os.path.getsize(audio_path) == os.path.getsize(video_path)
    finally:
        temp_dir.cleanup()
