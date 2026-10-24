#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Başlangıç (baseline) Pylint ve flake8 (PEP 8) raporlarından okunabilir
Türkçe özet dokümanları üretir.

Girdi (değiştirilmez, ham raporlar):
    reports/baseline/pylint.txt
    reports/baseline/pep8.txt

Çıktı:
    docs/pylint-baseline-summary.md
    docs/pep8-baseline-summary.md

Kullanım:
    python scripts/summarize_baseline_reports.py
    (son taramadan sonra aynı mantıkla reports/final/ için ayrı bir
     çalıştırma/kopya gerekir; bu betik şimdilik yalnızca baseline içindir.)
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYLINT_REPORT = ROOT / "reports" / "baseline" / "pylint.txt"
PEP8_REPORT = ROOT / "reports" / "baseline" / "pep8.txt"
PYLINT_SUMMARY = ROOT / "docs" / "pylint-baseline-summary.md"
PEP8_SUMMARY = ROOT / "docs" / "pep8-baseline-summary.md"

CATEGORY_NAMES = {
    "C": "convention",
    "R": "refactor",
    "W": "warning",
    "E": "error",
    "F": "fatal",
    "I": "information",
}

# Pylint mesaj satırı: <dosya>:<satır>:<sütun>: <KOD>: <mesaj> (<sembol>)
PYLINT_LINE_RE = re.compile(
    r"^(?P<file>.+?):(?P<line>\d+):(?P<col>\d+):\s+(?P<code>[A-Z]\d{4}):\s+(?P<rest>.*)$"
)
SYMBOL_RE = re.compile(r"\(([\w-]+)\)\s*$")
SCORE_RE = re.compile(r"rated at (-?\d+(?:\.\d+)?)/10")

# flake8 detay satırı: <dosya>:<satır>:<sütun>: <KOD> <mesaj>
PEP8_DETAIL_RE = re.compile(
    r"^(?P<file>.+?):(?P<line>\d+):(?P<col>\d+):\s+(?P<code>[EWF]\d+)\s+(?P<message>.*)$"
)
# flake8 --statistics satırı: "<adet>     <KOD> <mesaj>" (dosya/satır/sütun yok)
PEP8_STAT_RE = re.compile(r"^\s*(?P<count>\d+)\s+(?P<code>[EWF]\d+)\s+(?P<message>.*)$")

LDAP_FILE_MARKER = "simpleldap"


def parse_pylint(text: str):
    score = None
    m = SCORE_RE.search(text)
    if m:
        score = float(m.group(1))

    category_counts = Counter()
    code_counts = Counter()
    code_symbol = {}
    file_counts = Counter()
    e0401_occurrences = []
    e0611_occurrences = []

    for raw_line in text.splitlines():
        m = PYLINT_LINE_RE.match(raw_line)
        if not m:
            continue
        file_ = m.group("file")
        code = m.group("code")
        rest = m.group("rest")
        category = code[0]
        category_counts[category] += 1
        code_counts[code] += 1
        file_counts[file_] += 1

        sym_m = SYMBOL_RE.search(rest)
        symbol = sym_m.group(1) if sym_m else code_symbol.get(code, "-")
        if code not in code_symbol or code_symbol[code] == "-":
            code_symbol[code] = symbol

        if code == "E0401":
            e0401_occurrences.append((file_, m.group("line"), rest))
        elif code == "E0611":
            e0611_occurrences.append((file_, m.group("line"), rest))

    return {
        "score": score,
        "category_counts": category_counts,
        "code_counts": code_counts,
        "code_symbol": code_symbol,
        "file_counts": file_counts,
        "e0401": e0401_occurrences,
        "e0611": e0611_occurrences,
    }


def parse_pep8(text: str):
    file_counts = Counter()
    stat_counts = []  # (count, code, message) kaynak sırası korunur
    total_detail_lines = 0

    lines = text.splitlines()
    for raw_line in lines:
        detail_m = PEP8_DETAIL_RE.match(raw_line)
        if detail_m:
            file_counts[detail_m.group("file")] += 1
            total_detail_lines += 1
            continue
        stat_m = PEP8_STAT_RE.match(raw_line)
        if stat_m:
            stat_counts.append(
                (int(stat_m.group("count")), stat_m.group("code"), stat_m.group("message"))
            )

    total_from_stats = sum(c for c, _, _ in stat_counts)
    return {
        "file_counts": file_counts,
        "stat_counts": stat_counts,
        "total_detail_lines": total_detail_lines,
        "total_from_stats": total_from_stats,
    }


def is_ldap_related(file_path: str) -> bool:
    return LDAP_FILE_MARKER in file_path.replace("\\", "/").lower()


def render_pylint_summary(data: dict) -> str:
    lines = []
    lines.append("# Pylint başlangıç taraması — özet")
    lines.append("")
    lines.append(
        "Bu dosya, `reports/baseline/pylint.txt` ham raporundan "
        "`scripts/summarize_baseline_reports.py` ile üretilmiştir. "
        "Ham rapor değiştirilmemiştir."
    )
    lines.append("")
    lines.append(f"**Pylint puanı:** {data['score']:.2f}/10")
    lines.append("")

    lines.append("## Kategori dağılımı")
    lines.append("")
    lines.append("| Kategori | Kod öneki | Adet |")
    lines.append("| --- | --- | --- |")
    total = sum(data["category_counts"].values())
    for cat in ["E", "F", "W", "R", "C", "I"]:
        count = data["category_counts"].get(cat, 0)
        if count == 0 and cat not in data["category_counts"]:
            continue
        lines.append(f"| {CATEGORY_NAMES[cat]} | {cat} | {count} |")
    lines.append(f"| **Toplam** | | **{total}** |")
    lines.append("")

    lines.append("## En sık 20 mesaj kodu")
    lines.append("")
    lines.append("| Kod | Açıklama (sembol) | Adet |")
    lines.append("| --- | --- | --- |")
    for code, count in data["code_counts"].most_common(20):
        symbol = data["code_symbol"].get(code, "-")
        lines.append(f"| {code} | {symbol} | {count} |")
    lines.append("")

    lines.append("## Dosya başına en çok uyarı alan 10 dosya")
    lines.append("")
    lines.append("| Dosya | Uyarı adedi |")
    lines.append("| --- | --- |")
    for file_, count in data["file_counts"].most_common(10):
        lines.append(f"| `{file_}` | {count} |")
    lines.append("")

    lines.append("## Ortamdan kaynaklanan mesajlar (güvenlik/kod kalitesi bulgusu SAYILMAZ)")
    lines.append("")
    lines.append(
        "CLAUDE.md madde 9: import/bağımlılık hataları (`E0401 import-error` vb.) "
        "güvenlik bulgusu sayılmaz; ortam sorunu olarak burada ve "
        "`docs/environment-notes.md` içinde kayıtlıdır. `E0611 no-name-in-module` "
        "da aynı tabloda, kaynağı ayrıştırılmış biçimde gösterilir."
    )
    lines.append("")
    lines.append("### E0401 — import-error")
    lines.append("")
    if data["e0401"]:
        lines.append("| Dosya | Satır | LDAP ile ilgili mi? | Mesaj |")
        lines.append("| --- | --- | --- | --- |")
        for file_, line_no, rest in data["e0401"]:
            ldap_flag = "Evet (flask_simpleldap eksik)" if is_ldap_related(file_) else "Hayır"
            lines.append(f"| `{file_}` | {line_no} | {ldap_flag} | {rest} |")
    else:
        lines.append("Bulunamadı.")
    lines.append("")

    lines.append("### E0611 — no-name-in-module")
    lines.append("")
    ldap_e0611 = [o for o in data["e0611"] if is_ldap_related(o[0])]
    other_e0611 = [o for o in data["e0611"] if not is_ldap_related(o[0])]
    lines.append(
        f"Toplam {len(data['e0611'])} adet. Bunlardan **{len(ldap_e0611)}** adedi "
        f"LDAP modülünde (`cps/services/simpleldap.py`, `flask_simpleldap` eksik "
        "olduğu için modül tam çözümlenemiyor); kalan "
        f"**{len(other_e0611)}** adedi LDAP ile ilgisizdir ve `cps/__init__.py` "
        "içinde alt modüllerin paket özniteliği olarak çalışma zamanında "
        "(dynamic attribute) atanmasından kaynaklanır — Pylint'in statik "
        "analizinin bu örüntüyü çözememesi bilinen bir kısıttır, kod hatası "
        "veya güvenlik açığı değildir."
    )
    lines.append("")
    affected_files = sorted({o[0] for o in other_e0611})
    lines.append(
        f"LDAP dışı E0611 uyarılarının göründüğü dosya sayısı: {len(affected_files)} "
        "(liste `reports/baseline/pylint.txt` içinde `E0611` aranarak görülebilir; "
        "ayrıntı burada tekrarlanmamıştır)."
    )
    lines.append("")

    return "\n".join(lines) + "\n"


def render_pep8_summary(data: dict) -> str:
    lines = []
    lines.append("# flake8 (PEP 8) başlangıç taraması — özet")
    lines.append("")
    lines.append(
        "Bu dosya, `reports/baseline/pep8.txt` ham raporundan "
        "`scripts/summarize_baseline_reports.py` ile üretilmiştir. "
        "Ham rapor değiştirilmemiştir. Komut: "
        "`flake8 --isolated --select=E,W --statistics --count cps.py cps`."
    )
    lines.append("")
    lines.append(f"**Toplam ihlal sayısı:** {data['total_from_stats']}")
    if data["total_from_stats"] != data["total_detail_lines"]:
        lines.append(
            f"\n> Uyarı: istatistik toplamı ({data['total_from_stats']}) ile "
            f"satır bazlı ihlal sayısı ({data['total_detail_lines']}) eşleşmiyor; "
            "ham rapor elle kontrol edilmeli."
        )
    lines.append("")

    lines.append("## En sık E/W kodları")
    lines.append("")
    lines.append("| Kod | Açıklama | Adet |")
    lines.append("| --- | --- | --- |")
    for count, code, message in sorted(data["stat_counts"], key=lambda t: t[0], reverse=True):
        lines.append(f"| {code} | {message} | {count} |")
    lines.append("")

    lines.append("## En çok ihlal içeren 10 dosya")
    lines.append("")
    lines.append("| Dosya | İhlal adedi |")
    lines.append("| --- | --- |")
    for file_, count in data["file_counts"].most_common(10):
        lines.append(f"| `{file_}` | {count} |")
    lines.append("")

    return "\n".join(lines) + "\n"


def main() -> None:
    pylint_text = PYLINT_REPORT.read_text(encoding="utf-8", errors="replace")
    pep8_text = PEP8_REPORT.read_text(encoding="utf-8", errors="replace")

    pylint_data = parse_pylint(pylint_text)
    pep8_data = parse_pep8(pep8_text)

    PYLINT_SUMMARY.write_text(render_pylint_summary(pylint_data), encoding="utf-8", newline="\n")
    PEP8_SUMMARY.write_text(render_pep8_summary(pep8_data), encoding="utf-8", newline="\n")

    # ASCII-only konsol çıktısı: Windows PowerShell varsayılan cp1252 konsol
    # kodlamasında Türkçe karakterler UnicodeEncodeError verebilir; dosyalar
    # zaten yukarıda UTF-8 olarak doğru şekilde yazıldı.
    print(f"Written: {PYLINT_SUMMARY.relative_to(ROOT)}")
    print(f"Written: {PEP8_SUMMARY.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
