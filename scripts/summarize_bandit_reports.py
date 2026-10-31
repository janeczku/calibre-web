#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Başlangıç (baseline) Bandit JSON raporlarından okunabilir Türkçe özet üretir.

Girdi (değiştirilmez, ham raporlar):
    reports/baseline/bandit-cps.json
    reports/baseline/bandit-entrypoint.json

Çıktı:
    docs/bandit-summary.md

Kullanım:
    python scripts/summarize_bandit_reports.py
    python scripts/summarize_bandit_reports.py --report-dir reports/final --output docs/bandit-final-summary.md
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT_FILES = ("bandit-cps.json", "bandit-entrypoint.json")
LEVELS = ("HIGH", "MEDIUM", "LOW")
LEVEL_ORDER = {level: i for i, level in enumerate(LEVELS)}
THIRD_PARTY_DIRS = ("cps/cw_login/", "cps/cw_advocate/")


def normalize_path(filename: str) -> str:
    path = filename.replace("\\", "/")
    if path.startswith("./"):
        path = path[2:]
    return path


def bandit_version(results) -> str:
    # Bandit, JSON çıktısına sürüm yazmaz; more_info bağlantısındaki
    # dokümantasyon sürümü aracı çalıştıran Bandit sürümünü gösterir.
    versions = {r["more_info"].split("/en/")[1].split("/")[0] for r in results if "/en/" in r["more_info"]}
    return ", ".join(sorted(versions)) or "bilinmiyor"


def load_reports(report_dir: Path):
    results = []
    meta = []
    for name in REPORT_FILES:
        data = json.loads((report_dir / name).read_text(encoding="utf-8"))
        totals = data["metrics"]["_totals"]
        meta.append((name, data["generated_at"], len(data["results"]), totals["loc"],
                     totals["nosec"], len(data["errors"]), bandit_version(data["results"])))
        results.extend(data["results"])
    results.sort(key=lambda r: (LEVEL_ORDER[r["issue_severity"]], LEVEL_ORDER[r["issue_confidence"]],
                                normalize_path(r["filename"]), r["line_number"]))
    return results, meta


def is_third_party(path: str) -> bool:
    return path.startswith(THIRD_PARTY_DIRS)


def build_markdown(results, meta, report_dir: Path) -> str:
    rel_dir = report_dir.relative_to(ROOT).as_posix()
    lines = [
        "# Bandit özeti",
        "",
        f"Bu dosya `scripts/summarize_bandit_reports.py` ile `{rel_dir}/` altındaki ham JSON raporlarından "
        "üretilmiştir; elle düzenlemeyin. Manuel değerlendirme: `docs/review-bandit.md`, "
        "bulgu kaydı: `docs/findings-register.csv`.",
        "",
        "## Rapor bilgileri",
        "",
        "| Rapor | Üretilme zamanı (UTC) | Bulgu | Taranan LOC | `# nosec` | Hata | Bandit sürümü (more_info) |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for name, generated, count, loc, nosec, errors, version in meta:
        lines.append(f"| `{name}` | {generated} | {count} | {loc} | {nosec} | {errors} | {version} |")

    matrix = Counter((r["issue_severity"], r["issue_confidence"]) for r in results)
    lines += [
        "",
        f"Toplam bulgu: **{len(results)}**",
        "",
        "## Önem × güven matrisi",
        "",
        "| Önem \\ Güven | HIGH | MEDIUM | LOW | Toplam |",
        "| --- | --- | --- | --- | --- |",
    ]
    for sev in LEVELS:
        row = [matrix[(sev, conf)] for conf in LEVELS]
        lines.append(f"| {sev} | " + " | ".join(str(v) for v in row) + f" | {sum(row)} |")
    col_totals = [sum(matrix[(sev, conf)] for sev in LEVELS) for conf in LEVELS]
    lines.append("| Toplam | " + " | ".join(str(v) for v in col_totals) + f" | {len(results)} |")

    rules = Counter((r["test_id"], r["test_name"], r["issue_severity"]) for r in results)
    third_party = Counter((r["test_id"], r["test_name"], r["issue_severity"])
                          for r in results if is_third_party(normalize_path(r["filename"])))
    lines += [
        "",
        "## Kural kodu dağılımı",
        "",
        "| Kural | Ad | Önem | Adet | Gömülü üçüncü taraf (K7) |",
        "| --- | --- | --- | --- | --- |",
    ]
    for key in sorted(rules, key=lambda k: (LEVEL_ORDER[k[2]], -rules[k], k[0])):
        lines.append(f"| {key[0]} | `{key[1]}` | {key[2]} | {rules[key]} | {third_party[key]} |")

    lines += [
        "",
        "## Tüm bulgular (önem, güven, dosya sırasıyla)",
        "",
        "| # | Önem | Güven | Kural | Dosya:satır | Bandit mesajı | Not |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for i, r in enumerate(results, 1):
        path = normalize_path(r["filename"])
        note = "Gömülü üçüncü taraf (K7): kapsamda, incelendi, düzeltme yapılmaz." if is_third_party(path) else ""
        text = r["issue_text"].replace("|", "\\|").replace("``", "`")
        lines.append(f"| {i} | {r['issue_severity']} | {r['issue_confidence']} | {r['test_id']} | "
                     f"`{path}:{r['line_number']}` | {text} | {note} |")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--report-dir", default="reports/baseline")
    parser.add_argument("--output", default="docs/bandit-summary.md")
    args = parser.parse_args()

    report_dir = (ROOT / args.report_dir).resolve()
    results, meta = load_reports(report_dir)
    output = ROOT / args.output
    output.write_text(build_markdown(results, meta, report_dir), encoding="utf-8", newline="\n")
    print(f"{output.relative_to(ROOT).as_posix()}: {len(results)} bulgu yazıldı")


if __name__ == "__main__":
    main()
