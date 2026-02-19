"""Basic Usage"""

from silent import generate_notes

if __name__ == "__main__":
    result = generate_notes(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        language="auto",
        provider_policy="local_first",
        include_timestamps="section",
    )
    print(result.note_markdown)
