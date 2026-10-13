"""Skill library loader for progressive disclosure.

Loads skill library content from disk with support for the hierarchical
structure used in PIMS skill libraries:

    skill_library/
        SKILL.md           -- Main index (table catalog, coordination rules)
        dep_map.md         -- Cross-table dependency graph
        table_refs/        -- Per-table reference documents
            BUY.md, SELL.md, CAPS.md, ...
        procedures/        -- Step-by-step operation procedures
            capacity.md, blending.md, price_change.md, ...
        experience/        -- Expert patterns and pitfalls
            patterns.md, ...
        equipment_refs/    -- Equipment-specific references
            DHT.md, ...

Usage::

    from skillrefine.skill_loader import load_skill_library, load_skill

    # Load the full library index
    lib = load_skill_library(Path("skill_libraries/SKILL_REFINED"))
    print(lib["index"])         # SKILL.md content
    print(lib["table_refs"])    # List of available table references

    # Load a specific skill on demand
    content = load_skill(Path("skill_libraries/SKILL_REFINED"), "BUY")
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional


# Subdirectories that contain skill documents
SKILL_SUBDIRS = ("table_refs", "procedures", "experience", "equipment_refs", "submodel")

# Maximum content length for individual skill files (characters)
MAX_SKILL_CONTENT_LENGTH = 8000


def load_skill_library(skill_dir: Path) -> Dict[str, Any]:
    """Load a skill library's index and metadata from disk.

    Reads the main SKILL.md index and enumerates available documents
    in each subdirectory without loading their full content. This
    supports progressive disclosure: the agent sees the index first
    and requests specific skills on demand via ``load_skill()``.

    Args:
        skill_dir: Path to the skill library root directory.
            If a ``skill/`` subdirectory exists, it is used as the
            effective root.

    Returns:
        Dictionary with keys:
            - ``"index"``: Content of SKILL.md (main skill definition)
            - ``"dep_map"``: Content of dep_map.md (dependency graph), or None
            - ``"table_refs"``: List of available table reference names
            - ``"procedures"``: List of available procedure names
            - ``"experience"``: List of available experience document names
            - ``"equipment_refs"``: List of available equipment reference names
            - ``"all_skills"``: Flat list of all available skill names
            - ``"root_dir"``: Resolved root directory path

    Raises:
        FileNotFoundError: If ``skill_dir`` does not exist.
    """
    skill_dir = Path(skill_dir)

    if not skill_dir.exists():
        raise FileNotFoundError(f"Skill library directory not found: {skill_dir}")

    # Check for nested skill/ subdirectory
    effective_root = skill_dir / "skill" if (skill_dir / "skill").is_dir() else skill_dir

    result: Dict[str, Any] = {
        "index": "",
        "dep_map": None,
        "table_refs": [],
        "procedures": [],
        "experience": [],
        "equipment_refs": [],
        "all_skills": [],
        "root_dir": str(effective_root),
    }

    # Load main index (SKILL.md)
    skill_md = effective_root / "SKILL.md"
    if skill_md.exists():
        result["index"] = skill_md.read_text(encoding="utf-8")

    # Load dependency map
    dep_map = effective_root / "dep_map.md"
    if dep_map.exists():
        result["dep_map"] = dep_map.read_text(encoding="utf-8")

    # Enumerate subdirectories
    all_skills: List[str] = []
    for subdir_name in SKILL_SUBDIRS:
        subdir_path = effective_root / subdir_name
        if subdir_path.is_dir():
            md_files = sorted(subdir_path.glob("*.md"))
            names = [f.stem for f in md_files]
            result[subdir_name] = names
            all_skills.extend(names)

    # Also include root-level .md files (excluding SKILL.md and dep_map.md)
    root_docs = [
        f.stem
        for f in effective_root.glob("*.md")
        if f.stem not in ("SKILL", "dep_map")
    ]
    if root_docs:
        result["root_docs"] = root_docs
        all_skills.extend(root_docs)

    result["all_skills"] = sorted(set(all_skills))

    return result


def load_skill(
    skill_dir: Path,
    skill_name: str,
    max_length: int = MAX_SKILL_CONTENT_LENGTH,
) -> str:
    """Load a specific skill document by name.

    Searches for the skill in subdirectories (table_refs, procedures,
    experience, equipment_refs, submodel) and the root level. Supports
    both exact name and case-insensitive matching.

    Args:
        skill_dir: Path to the skill library root directory.
        skill_name: Name of the skill to load (without ``.md`` extension).
            Supports path-style names like ``"submodel/reformer_type"``.
        max_length: Maximum content length to return (characters).

    Returns:
        Skill document content, truncated to ``max_length``.
        Returns an empty string if the skill is not found.
    """
    skill_dir = Path(skill_dir)

    if not skill_dir.exists():
        return ""

    # Check for nested skill/ subdirectory
    effective_root = skill_dir / "skill" if (skill_dir / "skill").is_dir() else skill_dir

    # Handle path-style names (e.g., "submodel/reformer_type")
    if "/" in skill_name:
        direct = effective_root / f"{skill_name}.md"
        if direct.exists():
            return direct.read_text(encoding="utf-8")[:max_length]

    # Search subdirectories (exact match first, then case-insensitive)
    for subdir_name in SKILL_SUBDIRS:
        subdir_path = effective_root / subdir_name
        if not subdir_path.is_dir():
            continue

        # Exact match
        candidate = subdir_path / f"{skill_name}.md"
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")[:max_length]

        # Uppercase match
        candidate = subdir_path / f"{skill_name.upper()}.md"
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")[:max_length]

        # Case-insensitive match
        name_lower = skill_name.lower()
        for md_file in subdir_path.glob("*.md"):
            if md_file.stem.lower() == name_lower:
                return md_file.read_text(encoding="utf-8")[:max_length]

    # Check root level
    candidate = effective_root / f"{skill_name}.md"
    if candidate.exists():
        return candidate.read_text(encoding="utf-8")[:max_length]

    candidate = effective_root / f"{skill_name.upper()}.md"
    if candidate.exists():
        return candidate.read_text(encoding="utf-8")[:max_length]

    # Fuzzy fallback: find files whose name contains the skill name
    name_lower = skill_name.lower()
    matches = sorted(effective_root.rglob(f"*{name_lower}*.md"))
    if matches:
        combined: List[str] = []
        total_len = 0
        for m in matches[:5]:
            content = m.read_text(encoding="utf-8")
            entry = f"--- {m.stem} ---\n{content}"
            if total_len + len(entry) > max_length:
                remaining = max_length - total_len
                if remaining > 100:
                    combined.append(entry[:remaining] + "...")
                break
            combined.append(entry)
            total_len += len(entry)
        return "\n\n".join(combined)

    return ""


def load_skill_index(skill_dir: Path) -> str:
    """Load just the SKILL.md index document.

    Args:
        skill_dir: Path to the skill library root directory.

    Returns:
        SKILL.md content, or empty string if not found.
    """
    skill_dir = Path(skill_dir)
    if not skill_dir.exists():
        return ""

    effective_root = skill_dir / "skill" if (skill_dir / "skill").is_dir() else skill_dir

    skill_md = effective_root / "SKILL.md"
    if skill_md.exists():
        return skill_md.read_text(encoding="utf-8")
    return ""


def load_dependency_map(skill_dir: Path) -> str:
    """Load the cross-table dependency map.

    Args:
        skill_dir: Path to the skill library root directory.

    Returns:
        dep_map.md content, or empty string if not found.
    """
    skill_dir = Path(skill_dir)
    if not skill_dir.exists():
        return ""

    effective_root = skill_dir / "skill" if (skill_dir / "skill").is_dir() else skill_dir

    dep_map = effective_root / "dep_map.md"
    if dep_map.exists():
        return dep_map.read_text(encoding="utf-8")
    return ""


def list_available_skills(skill_dir: Path) -> Dict[str, List[str]]:
    """List all available skills organized by subdirectory.

    Args:
        skill_dir: Path to the skill library root directory.

    Returns:
        Dictionary mapping subdirectory names to lists of skill names.
    """
    skill_dir = Path(skill_dir)
    if not skill_dir.exists():
        return {}

    effective_root = skill_dir / "skill" if (skill_dir / "skill").is_dir() else skill_dir

    result: Dict[str, List[str]] = {}
    for subdir_name in SKILL_SUBDIRS:
        subdir_path = effective_root / subdir_name
        if subdir_path.is_dir():
            result[subdir_name] = sorted(
                f.stem for f in subdir_path.glob("*.md")
            )

    return result


def build_skill_summary(skill_dir: Path) -> str:
    """Build a concise summary of available skills for the agent system prompt.

    Creates a text summary listing the main index content and available
    skill documents, suitable for inclusion in an LLM system prompt.

    Args:
        skill_dir: Path to the skill library root directory.

    Returns:
        Formatted summary string.
    """
    lib = load_skill_library(skill_dir)

    lines: List[str] = []

    # Index summary (first 500 chars)
    if lib["index"]:
        lines.append("## Skill Index (SKILL.md)")
        lines.append(lib["index"][:500])
        lines.append("")

    # Available skills by category
    categories = {
        "table_refs": "Table References",
        "procedures": "Procedures",
        "experience": "Experience Documents",
        "equipment_refs": "Equipment References",
    }

    for key, label in categories.items():
        items = lib.get(key, [])
        if items:
            lines.append(f"## {label}")
            lines.append(", ".join(items))
            lines.append("")

    if lib.get("dep_map"):
        lines.append("## Dependency Map")
        lines.append("")

    return "\n".join(lines)
