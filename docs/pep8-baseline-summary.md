# flake8 (PEP 8) başlangıç taraması — özet

Bu dosya, `reports/baseline/pep8.txt` ham raporundan `scripts/summarize_baseline_reports.py` ile üretilmiştir. Ham rapor değiştirilmemiştir. Komut: `flake8 --isolated --select=E,W --statistics --count cps.py cps`.

**Toplam ihlal sayısı:** 3409

## En sık E/W kodları

| Kod | Açıklama | Adet |
| --- | --- | --- |
| E501 | line too long (81 > 79 characters) | 2879 |
| E221 | multiple spaces before operator | 63 |
| E231 | missing whitespace after ',' | 63 |
| E128 | continuation line under-indented for visual indent | 56 |
| E302 | expected 2 blank lines, found 1 | 33 |
| W503 | line break before binary operator | 28 |
| E127 | continuation line over-indented for visual indent | 26 |
| E126 | continuation line over-indented for hanging indent | 22 |
| W504 | line break after binary operator | 21 |
| E226 | missing whitespace around arithmetic operator | 20 |
| E225 | missing whitespace around operator | 19 |
| E712 | comparison to True should be 'if cond is True:' or 'if cond:' | 18 |
| E711 | comparison to None should be 'if cond is None:' | 17 |
| E303 | too many blank lines (2) | 15 |
| E251 | unexpected spaces around keyword / parameter equals | 13 |
| E265 | block comment should start with '# ' | 12 |
| E222 | multiple spaces after operator | 11 |
| E261 | at least two spaces before inline comment | 11 |
| W391 | blank line at end of file | 10 |
| E275 | missing whitespace after keyword | 9 |
| W291 | trailing whitespace | 9 |
| W293 | blank line contains whitespace | 6 |
| E117 | over-indented (comment) | 5 |
| E203 | whitespace before ',' | 5 |
| E262 | inline comment should start with '# ' | 5 |
| E121 | continuation line under-indented for hanging indent | 4 |
| E241 | multiple spaces after ',' | 3 |
| E713 | test for membership should be 'not in' | 3 |
| E123 | closing bracket does not match indentation of opening bracket's line | 2 |
| E124 | closing bracket does not match visual indentation | 2 |
| E129 | visually indented line with same indent as next logical line | 2 |
| E202 | whitespace before ')' | 2 |
| E252 | missing whitespace around parameter equals | 2 |
| E305 | expected 2 blank lines after class or function definition, found 1 | 2 |
| E306 | expected 1 blank line before a nested definition, found 0 | 2 |
| E402 | module level import not at top of file | 2 |
| E731 | do not assign a lambda expression, use a def | 2 |
| E111 | indentation is not a multiple of 4 | 1 |
| E301 | expected 1 blank line, found 0 | 1 |
| E722 | do not use bare 'except' | 1 |
| E741 | ambiguous variable name 'l' | 1 |
| W292 | no newline at end of file | 1 |

## En çok ihlal içeren 10 dosya

| Dosya | İhlal adedi |
| --- | --- |
| `cps\web.py` | 398 |
| `cps\admin.py` | 337 |
| `cps\editbooks.py` | 290 |
| `cps\kobo.py` | 240 |
| `cps\helper.py` | 210 |
| `cps\db.py` | 163 |
| `cps\opds.py` | 107 |
| `cps\shelf.py` | 98 |
| `cps\updater.py` | 85 |
| `cps\constants.py` | 81 |

