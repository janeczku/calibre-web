#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Taranan kapsamın (cps/ ve cps.py) büyüklüğünü ölçer: dosya sayısı, toplam
satır sayısı, kod satırı sayısı (boş satırlar ve tek satırlık `#` yorumları
hariç) ve en büyük 10 dosya.

Yöntem (basit, şeffaf bir sezgisel; AST tabanlı değildir):
    - Boş satır: strip() sonrası uzunluğu 0 olan satır.
    - Yorum satırı: strip() sonrası `#` ile başlayan satır.
    - Kod satırı: yukarıdakilerin dışında kalan her satır (çok satırlı
      docstring/string içerikleri de kod satırı sayılır; bunları ayıklamak
      AST gerektirir ve bu betiğin kapsamı dışıdır).

Kullanım:
    python scripts/project_size_stats.py
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGETS = [ROOT / "cps.py", ROOT / "cps"]


def iter_py_files():
    for target in TARGETS:
        if target.is_file() and target.suffix == ".py":
            yield target
        elif target.is_dir():
            for path in sorted(target.rglob("*.py")):
                yield path


def count_lines(path: Path):
    total = 0
    code = 0
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0, 0
    for raw_line in text.splitlines():
        total += 1
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        code += 1
    return total, code


def main() -> None:
    rows = []
    for path in iter_py_files():
        total, code = count_lines(path)
        rel = path.relative_to(ROOT).as_posix()
        rows.append((rel, total, code))

    file_count = len(rows)
    total_lines = sum(r[1] for r in rows)
    total_code_lines = sum(r[2] for r in rows)

    print(f"Dosya sayisi: {file_count}")
    print(f"Toplam satir: {total_lines}")
    print(f"Kod satiri (bos/yorum haric): {total_code_lines}")
    print()
    print("En buyuk 10 dosya (toplam satira gore):")
    for rel, total, code in sorted(rows, key=lambda r: r[1], reverse=True)[:10]:
        print(f"  {rel}\ttoplam={total}\tkod={code}")


if __name__ == "__main__":
    main()
