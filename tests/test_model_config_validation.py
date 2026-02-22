from __future__ import annotations

import pytest

from silent.api import generate_notes
from silent.exceptions import ConfigurationError


def test_generate_notes_requires_at_least_one_model() -> None:
    with pytest.raises(ConfigurationError, match="At least one model must be configured"):
        generate_notes(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            local_model=None,
            online_model=None,
        )
