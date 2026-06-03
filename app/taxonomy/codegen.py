"""
Generates the frontend TypeScript taxonomy file from Python source.
Run this whenever the Python taxonomy changes:

    python -m app.taxonomy.codegen

Output: frontend/src/lib/taxonomy.generated.ts

The frontend NEVER edits this file manually.
The Python file is always the source of truth.
"""
from __future__ import annotations
import sys
from pathlib import Path

from app.taxonomy.medical_history import (
    MEDICAL_HISTORY_TAXONOMY,
    DENTAL_RELEVANT_QUESTIONS,
)
from app.taxonomy.examination import ON_EXAMINATION_TAXONOMY, EXAM_GROUPS
from app.taxonomy.clinical import (
    DENTAL_PROBLEM_TAXONOMY,
    DENTAL_DIAGNOSIS_TAXONOMY,
    DENTAL_INVESTIGATION_TAXONOMY,
    DENTAL_TREATMENT_TAXONOMY,
)


def _ts_string(s: str) -> str:
    return f'"{s}"'


def _ts_string_list(items: list[str], indent: int = 2) -> str:
    pad = " " * indent
    inner = (",\n" + pad + "    ").join(_ts_string(i) for i in items)
    return f"[\n{pad}    {inner},\n{pad}]"


def generate() -> str:
    lines: list[str] = []
    lines.append("// AUTO-GENERATED — DO NOT EDIT")
    lines.append("// Source of truth: app/taxonomy/ (Python)")
    lines.append("// Regenerate:  python -m app.taxonomy.codegen")
    lines.append("")
    lines.append('import type { MedicalHistoryItem, ExamItem } from "./taxonomy.types"')
    lines.append("")

    # MEDICAL HISTORY TAXONOMY
    lines.append("export const MEDICAL_HISTORY_TAXONOMY: Record<string, MedicalHistoryItem[]> = {")
    for category, items in MEDICAL_HISTORY_TAXONOMY.items():
        lines.append(f'  {_ts_string(category)}: [')
        for item in items:
            lines.append(
                f'    {{ id: {_ts_string(item.id)}, '
                f'label: {_ts_string(item.label)}, '
                f'type: "{item.type}" }},'
            )
        lines.append("  ],")
    lines.append("}")
    lines.append("")

    # DENTAL RELEVANT QUESTIONS
    lines.append("export const DENTAL_RELEVANT_QUESTIONS: MedicalHistoryItem[] = [")
    for q in DENTAL_RELEVANT_QUESTIONS:
        lines.append(
            f'  {{ id: {_ts_string(q.id)}, '
            f'label: {_ts_string(q.label)}, '
            f'type: "{q.type}" }},'
        )
    lines.append("]")
    lines.append("")
    lines.append(
        "export const ALL_MEDICAL_ITEMS = [\n"
        "  ...Object.values(MEDICAL_HISTORY_TAXONOMY).flat(),\n"
        "  ...DENTAL_RELEVANT_QUESTIONS,\n"
        "]"
    )
    lines.append("")

    # ON EXAMINATION TAXONOMY
    lines.append("export const ON_EXAMINATION_TAXONOMY: Record<string, ExamItem[]> = {")
    for category, fields in ON_EXAMINATION_TAXONOMY.items():
        lines.append(f'  {_ts_string(category)}: [')
        for f in fields:
            parts = [
                f'id: {_ts_string(f.id)}',
                f'label: {_ts_string(f.label)}',
                f'type: "{f.type}"',
            ]
            if f.options:
                opts = ", ".join(_ts_string(o) for o in f.options)
                parts.append(f'options: [{opts}]')
            lines.append(f'    {{ {", ".join(parts)} }},')
        lines.append("  ],")
    lines.append("}")
    lines.append("")

    # EXAM GROUPS
    lines.append("export const EXAM_GROUPS = [")
    for group in EXAM_GROUPS:
        cats = ", ".join(_ts_string(c) for c in group["categories"])
        lines.append(
            f'  {{ title: {_ts_string(group["title"])}, '
            f'categories: [{cats}] }},'
        )
    lines.append("]")
    lines.append("")

    # PROBLEM / FINDING TAXONOMY
    lines.append("export const DENTAL_PROBLEM_TAXONOMY: Record<string, string[]> = {")
    for cat, names in DENTAL_PROBLEM_TAXONOMY.items():
        lines.append(f'  {_ts_string(cat)}: {_ts_string_list(names)},')
    lines.append("}")
    lines.append("")

    # DIAGNOSIS TAXONOMY
    lines.append("export const DENTAL_DIAGNOSIS_TAXONOMY: Record<string, string[]> = {")
    for cat, names in DENTAL_DIAGNOSIS_TAXONOMY.items():
        lines.append(f'  {_ts_string(cat)}: {_ts_string_list(names)},')
    lines.append("}")
    lines.append("")

    # INVESTIGATION TAXONOMY
    lines.append("export const DENTAL_INVESTIGATION_TAXONOMY: Record<string, string[]> = {")
    for cat, names in DENTAL_INVESTIGATION_TAXONOMY.items():
        lines.append(f'  {_ts_string(cat)}: {_ts_string_list(names)},')
    lines.append("}")
    lines.append("")

    # TREATMENT TAXONOMY
    lines.append("export const DENTAL_TREATMENT_TAXONOMY: Record<string, string[]> = {")
    for cat, names in DENTAL_TREATMENT_TAXONOMY.items():
        lines.append(f'  {_ts_string(cat)}: {_ts_string_list(names)},')
    lines.append("}")
    lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    output_path = Path(
        sys.argv[1] if len(sys.argv) > 1
        else "frontend/src/lib/taxonomy.generated.ts"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    content = generate()
    output_path.write_text(content)
    print(f"Generated {output_path} ({len(content)} bytes)")