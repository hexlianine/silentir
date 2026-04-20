from .base import BaseNoter, NoterRegistry
from .json import JsonNoter
from .markdown import MarkdownNoter
from .text import TextNoter


def default_noter_registry() -> NoterRegistry:
    return NoterRegistry([MarkdownNoter(), TextNoter(), JsonNoter()])


__all__ = [
    "BaseNoter",
    "NoterRegistry",
    "MarkdownNoter",
    "TextNoter",
    "JsonNoter",
    "default_noter_registry",
]
