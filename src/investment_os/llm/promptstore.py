"""Versioned prompt registry.

Prompts are files named ``<name>@v<version>.md`` under ``prompts/`` — reviewed
in PRs like code, referenced by version in stored recommendations, never
inline strings (docs/fase-6, coding standards: "prompt sebagai artefak
berversi").
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_PROMPT_FILE_RE = re.compile(r"^(?P<name>[a-z0-9_-]+)@v(?P<version>\d+)\.md$")


class PromptNotFoundError(LookupError):
    pass


@dataclass(frozen=True)
class PromptTemplate:
    name: str
    version: int
    text: str

    @property
    def tag(self) -> str:
        return f"{self.name}@v{self.version}"

    def render(self, **fields: str) -> str:
        return self.text.format(**fields)


class PromptStore:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._cache: dict[tuple[str, int | None], PromptTemplate] = {}

    def get(self, name: str, version: int | None = None) -> PromptTemplate:
        """Load a prompt by name; latest version when none is pinned."""
        key = (name, version)
        if key in self._cache:
            return self._cache[key]

        candidates: list[tuple[int, Path]] = []
        if self._root.is_dir():
            for path in self._root.iterdir():
                match = _PROMPT_FILE_RE.match(path.name)
                if match and match.group("name") == name:
                    candidates.append((int(match.group("version")), path))

        if version is not None:
            candidates = [c for c in candidates if c[0] == version]
        if not candidates:
            wanted = f"{name}@v{version}" if version else name
            raise PromptNotFoundError(f"prompt '{wanted}' tidak ditemukan di {self._root}")

        chosen_version, path = max(candidates, key=lambda c: c[0])
        template = PromptTemplate(name=name, version=chosen_version, text=path.read_text())
        self._cache[key] = template
        return template
