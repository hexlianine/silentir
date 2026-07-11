from __future__ import annotations

import json
import subprocess
from types import SimpleNamespace

import pytest

from silentir.exceptions import TranscriptExtractionError
from silentir.recorders.bilibili import BilibiliRecorder
from silentir.types import VideoMetadata

# --------------------------------------------------------------------------- #
# supports()
# --------------------------------------------------------------------------- #


def test_supports_bilibili_hosts():
    r = BilibiliRecorder()
    assert r.supports("https://www.bilibili.com/video/BV1xx411c7mD")
    assert r.supports("https://bilibili.com/video/BV1xx411c7mD")
    assert r.supports("https://m.bilibili.com/video/BV1xx411c7mD")
    assert r.supports("https://b23.tv/abc123")


def test_supports_rejects_other_hosts():
    r = BilibiliRecorder()
    assert not r.supports("https://youtube.com/watch?v=abc")
    assert not r.supports("https://youtu.be/abc")
    assert not r.supports("https://example.com")


# --------------------------------------------------------------------------- #
# backend validation
# --------------------------------------------------------------------------- #


def test_default_backend_is_auto():
    assert BilibiliRecorder()._backend == "auto"


def test_invalid_backend_raises():
    with pytest.raises(ValueError):
        BilibiliRecorder(backend="nope")


# --------------------------------------------------------------------------- #
# payload helpers
# --------------------------------------------------------------------------- #


def _payload(
    *,
    available: bool = True,
    items: list | None = None,
    title: str = "测试视频",
    duration: int = 679,
    ok: bool = True,
) -> dict:
    if not ok:
        return {
            "ok": False,
            "schema_version": "1",
            "error": {"code": "upstream_error", "message": "boom"},
        }
    if items is None:
        items = [
            {"from": 0.0, "to": 2.5, "content": "你好"},
            {"from": 2.5, "to": 5.0, "content": "世界"},
        ]
    return {
        "ok": True,
        "schema_version": "1",
        "data": {
            "video": {"title": title, "duration_seconds": duration, "duration": "11:19"},
            "subtitle": {
                "available": available,
                "format": "timeline",
                "items": items,
                "text": "",
            },
            "warnings": [],
        },
    }


def _proc(payload: dict, *, returncode: int = 0, stderr: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=returncode, stdout=json.dumps(payload), stderr=stderr)


def _install_bili(
    monkeypatch,
    *,
    available: bool = True,
    payload: dict | None = None,
    returncode: int = 0,
    stderr: str = "",
    runner=None,
) -> None:
    """Wire `bili` as installed and make subprocess.run return the given payload."""
    monkeypatch.setattr(
        "silentir.recorders.bilibili.shutil.which",
        lambda cmd: "/usr/local/bin/bili" if available and cmd == "bili" else None,
    )
    if available:
        if runner is None:
            resolved_payload = payload or _payload()

            def runner(*a, **k):
                return _proc(resolved_payload, returncode=returncode, stderr=stderr)

        monkeypatch.setattr("silentir.recorders.bilibili.subprocess.run", runner)


def _install_fallback(monkeypatch) -> dict:
    """Stub BaseRecorder.record so the yt-dlp fallback path is observable."""
    calls = {"count": 0}

    def fake_record(self, url, *, language=None, cookies_path=None):
        calls["count"] += 1
        return (
            VideoMetadata(url=url, title="ytdlp", duration_sec=None, platform="bilibili"),
            None,
            ["yt-dlp warning"],
        )

    monkeypatch.setattr("silentir.recorders.base.BaseRecorder.record", fake_record)
    return calls


# --------------------------------------------------------------------------- #
# bili success path
# --------------------------------------------------------------------------- #


def test_bili_success_uses_subtitle(monkeypatch):
    _install_bili(monkeypatch, payload=_payload())
    r = BilibiliRecorder(backend="auto")
    metadata, transcript, warnings = r.record("https://b23.tv/abc")

    assert metadata.title == "测试视频"
    assert metadata.duration_sec == 679
    assert metadata.platform == "bilibili"
    assert metadata.url == "https://b23.tv/abc"
    assert transcript is not None
    assert transcript.source == "subtitle"
    assert transcript.language == "zh"
    assert [s.text for s in transcript.segments] == ["你好", "世界"]
    assert transcript.segments[0].start == 0.0
    assert transcript.segments[1].end == 5.0
    assert warnings == []


def test_bili_passes_full_url_to_cli(monkeypatch):
    captured = {}

    def fake_run(cmd, **kw):
        captured["cmd"] = cmd
        return _proc(_payload())

    _install_bili(monkeypatch, runner=fake_run)
    url = "https://www.bilibili.com/video/BV1xx411c7mD"
    BilibiliRecorder().record(url)

    assert captured["cmd"] == ["bili", "video", url, "--subtitle-timeline", "--json"]


def test_bili_no_subtitle_returns_none(monkeypatch):
    _install_bili(monkeypatch, payload=_payload(available=False, items=[]))
    metadata, transcript, warnings = BilibiliRecorder().record("https://b23.tv/abc")

    assert transcript is None
    assert "no subtitles" in warnings[0]


def test_bili_empty_items_returns_none(monkeypatch):
    _install_bili(monkeypatch, payload=_payload(available=True, items=[]))
    metadata, transcript, warnings = BilibiliRecorder().record("https://b23.tv/abc")

    assert transcript is None
    assert "no subtitles" in warnings[0]


# --------------------------------------------------------------------------- #
# fallback to yt-dlp (backend=auto)
# --------------------------------------------------------------------------- #


def test_bili_returncode_failure_falls_back(monkeypatch):
    calls = _install_fallback(monkeypatch)
    _install_bili(monkeypatch, payload=_payload(), returncode=1, stderr="boom")

    metadata, transcript, warnings = BilibiliRecorder(backend="auto").record("https://b23.tv/abc")

    assert calls["count"] == 1
    assert metadata.title == "ytdlp"
    assert any("bilibili-cli unavailable" in w for w in warnings)


def test_bili_envelope_error_falls_back(monkeypatch):
    calls = _install_fallback(monkeypatch)
    _install_bili(monkeypatch, payload=_payload(ok=False))

    metadata, transcript, warnings = BilibiliRecorder(backend="auto").record("https://b23.tv/abc")

    assert calls["count"] == 1
    assert any("bilibili-cli unavailable" in w for w in warnings)


def test_bili_non_json_falls_back(monkeypatch):
    calls = _install_fallback(monkeypatch)
    monkeypatch.setattr("silentir.recorders.bilibili.shutil.which", lambda c: "/usr/local/bin/bili")
    monkeypatch.setattr(
        "silentir.recorders.bilibili.subprocess.run",
        lambda *a, **k: SimpleNamespace(returncode=0, stdout="not json", stderr=""),
    )

    metadata, transcript, warnings = BilibiliRecorder(backend="auto").record("https://b23.tv/abc")

    assert calls["count"] == 1
    assert any("non-JSON" in w for w in warnings)


def test_bili_timeout_falls_back(monkeypatch):
    calls = _install_fallback(monkeypatch)
    monkeypatch.setattr("silentir.recorders.bilibili.shutil.which", lambda c: "/usr/local/bin/bili")

    def raise_timeout(*a, **k):
        raise subprocess.TimeoutExpired(cmd="bili", timeout=60)

    monkeypatch.setattr("silentir.recorders.bilibili.subprocess.run", raise_timeout)

    metadata, transcript, warnings = BilibiliRecorder(backend="auto").record("https://b23.tv/abc")

    assert calls["count"] == 1
    assert any("timed out" in w for w in warnings)


def test_bili_not_installed_falls_back(monkeypatch):
    calls = _install_fallback(monkeypatch)
    monkeypatch.setattr("silentir.recorders.bilibili.shutil.which", lambda c: None)

    metadata, transcript, warnings = BilibiliRecorder(backend="auto").record("https://b23.tv/abc")

    assert calls["count"] == 1
    assert not any("bilibili-cli unavailable" in w for w in warnings)


def test_backend_ytdlp_skips_bili(monkeypatch):
    calls = _install_fallback(monkeypatch)
    run_calls = {"count": 0}

    def counting_run(*a, **k):
        run_calls["count"] += 1
        return _proc(_payload())

    _install_bili(monkeypatch, runner=counting_run)

    metadata, transcript, warnings = BilibiliRecorder(backend="ytdlp").record("https://b23.tv/abc")

    assert calls["count"] == 1
    assert run_calls["count"] == 0
    assert metadata.title == "ytdlp"


# --------------------------------------------------------------------------- #
# backend=bili (strict, no fallback)
# --------------------------------------------------------------------------- #


def test_backend_bili_not_installed_raises(monkeypatch):
    monkeypatch.setattr("silentir.recorders.bilibili.shutil.which", lambda c: None)
    r = BilibiliRecorder(backend="bili")
    with pytest.raises(TranscriptExtractionError, match="not found"):
        r.record("https://b23.tv/abc")


def test_backend_bili_failure_raises(monkeypatch):
    _install_bili(monkeypatch, payload=_payload(), returncode=1, stderr="boom")
    r = BilibiliRecorder(backend="bili")
    with pytest.raises(TranscriptExtractionError, match="fallback is disabled"):
        r.record("https://b23.tv/abc")


# --------------------------------------------------------------------------- #
# payload parsing helpers
# --------------------------------------------------------------------------- #


def test_metadata_duration_fallback_when_missing_or_non_int():
    assert BilibiliRecorder._metadata_from_payload("u", {"title": "t"}).duration_sec is None
    bad = BilibiliRecorder._metadata_from_payload("u", {"title": "t", "duration_seconds": "100"})
    assert bad.duration_sec is None
    good = BilibiliRecorder._metadata_from_payload("u", {"title": "t", "duration_seconds": 100})
    assert good.duration_sec == 100
    assert good.title == "t"


def test_transcript_skips_empty_content():
    sub = {
        "available": True,
        "items": [
            {"from": 0, "to": 1, "content": ""},
            {"from": 1, "to": 2, "content": "hi"},
        ],
    }
    t = BilibiliRecorder._transcript_from_payload(sub)
    assert t is not None
    assert len(t.segments) == 1
    assert t.segments[0].text == "hi"


def test_transcript_unavailable_returns_none():
    assert BilibiliRecorder._transcript_from_payload({"available": False, "items": []}) is None
