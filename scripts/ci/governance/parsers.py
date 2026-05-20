"""Parsers for governance documents and artifact manifests."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple


COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$")


def normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


@dataclass(frozen=True)
class ChangelogEntry:
    heading: str
    fields: Dict[str, str]


@dataclass(frozen=True)
class ChangelogParseResult:
    entries: List[ChangelogEntry]
    errors: List[str]

    @property
    def commit_shas(self) -> List[str]:
        return [entry.fields["Commit"] for entry in self.entries if "Commit" in entry.fields]


def parse_changelog(
    text: str,
    heading_regex: str,
    required_fields: List[str],
    allowed_types: List[str],
    link_regex: str,
) -> ChangelogParseResult:
    lines = normalize_text(text).split("\n")
    heading_re = re.compile(heading_regex)
    link_re = re.compile(link_regex)

    entries: List[ChangelogEntry] = []
    errors: List[str] = []
    current_heading = ""
    current_fields: Dict[str, str] = {}
    current_field_key = ""

    def flush_entry() -> None:
        nonlocal current_heading, current_fields, current_field_key
        if not current_heading:
            return
        entries.append(ChangelogEntry(heading=current_heading, fields=dict(current_fields)))
        current_heading = ""
        current_fields = {}
        current_field_key = ""

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if line.startswith("## "):
            flush_entry()
            current_heading = stripped
            if not heading_re.match(stripped):
                errors.append(f"line {idx}: invalid changelog heading '{stripped}'")
            continue

        if not current_heading:
            continue

        field_match = re.match(r"^\s*-\s*([^:]+):\s*(.*)$", line)
        if field_match:
            key = field_match.group(1).strip()
            value = field_match.group(2).strip()
            current_fields[key] = value
            current_field_key = key
            continue

        if stripped:
            if current_field_key:
                existing = current_fields.get(current_field_key, "")
                current_fields[current_field_key] = f"{existing}\n{stripped}" if existing else stripped
            else:
                errors.append(f"line {idx}: unexpected non-field content in changelog entry")

    flush_entry()

    if not entries:
        errors.append("no changelog entries found")

    allowed_types_set = {item.strip().lower() for item in allowed_types}
    for entry in entries:
        missing = [field for field in required_fields if field not in entry.fields]
        if missing:
            errors.append(f"entry '{entry.heading}': missing fields: {', '.join(missing)}")
            continue

        commit_value = entry.fields["Commit"].strip()
        if not COMMIT_RE.match(commit_value):
            errors.append(f"entry '{entry.heading}': invalid Commit '{commit_value}'")

        type_value = entry.fields["Type"].strip().lower()
        if type_value not in allowed_types_set:
            errors.append(f"entry '{entry.heading}': invalid Type '{entry.fields['Type']}'")

        link_value = entry.fields["Link"].strip()
        if not link_re.match(link_value):
            errors.append(f"entry '{entry.heading}': invalid Link '{link_value}'")

        for required_text_field in ("Date (UTC)", "Summary", "Rationale"):
            if not entry.fields[required_text_field].strip():
                errors.append(f"entry '{entry.heading}': empty '{required_text_field}'")

    return ChangelogParseResult(entries=entries, errors=errors)


@dataclass(frozen=True)
class DecisionEntry:
    heading: str
    metadata: Dict[str, str]
    sections: Dict[str, str]


@dataclass(frozen=True)
class DecisionsParseResult:
    entries: List[DecisionEntry]
    errors: List[str]


def parse_decisions(
    text: str,
    heading_regex: str,
    required_meta_fields: List[str],
    allowed_statuses: List[str],
    required_sections: List[str],
) -> DecisionsParseResult:
    normalized = normalize_text(text)
    lines = normalized.split("\n")
    heading_re = re.compile(heading_regex)
    errors: List[str] = []
    entries: List[DecisionEntry] = []

    entry_starts: List[Tuple[int, str]] = []
    for index, line in enumerate(lines):
        if line.startswith("## "):
            entry_starts.append((index, line.strip()))

    if not entry_starts:
        return DecisionsParseResult(entries=[], errors=["no decision entries found"])

    for position, (start_idx, heading) in enumerate(entry_starts):
        end_idx = entry_starts[position + 1][0] if position + 1 < len(entry_starts) else len(lines)
        chunk = lines[start_idx:end_idx]
        if not heading_re.match(heading):
            errors.append(f"invalid decision heading '{heading}'")

        metadata: Dict[str, str] = {}
        sections: Dict[str, str] = {}
        current_section = ""

        for line in chunk[1:]:
            section_match = re.match(r"^###\s+(.+)$", line.strip())
            if section_match:
                current_section = section_match.group(1).strip()
                sections.setdefault(current_section, "")
                continue

            meta_match = re.match(r"^([A-Za-z][A-Za-z ]+):\s*(.*)$", line.strip())
            if meta_match and not current_section:
                metadata[meta_match.group(1).strip()] = meta_match.group(2).strip()
                continue

            if current_section and line.strip():
                current = sections.get(current_section, "")
                sections[current_section] = f"{current}\n{line.strip()}" if current else line.strip()

        missing_meta = [field for field in required_meta_fields if field not in metadata]
        if missing_meta:
            errors.append(f"entry '{heading}': missing metadata fields: {', '.join(missing_meta)}")

        status = metadata.get("Status", "").strip().lower()
        if status and status not in {item.lower() for item in allowed_statuses}:
            errors.append(f"entry '{heading}': invalid Status '{metadata.get('Status', '')}'")

        missing_sections = [section for section in required_sections if section not in sections]
        if missing_sections:
            errors.append(f"entry '{heading}': missing sections: {', '.join(missing_sections)}")

        for section_name in required_sections:
            if section_name in sections and not sections[section_name].strip():
                errors.append(f"entry '{heading}': section '{section_name}' is empty")

        entries.append(DecisionEntry(heading=heading, metadata=metadata, sections=sections))

    return DecisionsParseResult(entries=entries, errors=errors)


def extract_headings(text: str) -> List[str]:
    """Return all markdown headings without leading hash symbols."""
    headings: List[str] = []
    for line in normalize_text(text).split("\n"):
        match = re.match(r"^(#+)\s+(.+)$", line.strip())
        if not match:
            continue
        headings.append(match.group(2).strip())
    return headings


def _normalize_heading_for_match(value: str) -> str:
    lowered = value.strip().lower()
    lowered = re.sub(r"^\d+[\.\)]\s*", "", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered


def missing_required_headings(text: str, required_headings: List[str]) -> List[str]:
    actual = [_normalize_heading_for_match(item) for item in extract_headings(text)]
    missing: List[str] = []
    for required in required_headings:
        normalized_required = _normalize_heading_for_match(required)
        if not any(normalized_required in heading for heading in actual):
            missing.append(required)
    return missing


def parse_checksums_file(text: str) -> Tuple[Dict[str, str], List[str]]:
    checksums: Dict[str, str] = {}
    errors: List[str] = []
    for idx, line in enumerate(normalize_text(text).split("\n"), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        match = re.match(r"^([0-9a-f]{64})\s{2}(.+)$", stripped)
        if not match:
            errors.append(f"line {idx}: invalid checksum entry '{line}'")
            continue
        digest, path = match.group(1), match.group(2).strip()
        if path in checksums:
            errors.append(f"line {idx}: duplicate checksum path '{path}'")
            continue
        checksums[path] = digest
    if not checksums:
        errors.append("checksums file contains no entries")
    return checksums, errors

