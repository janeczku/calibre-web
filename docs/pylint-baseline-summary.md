# Pylint başlangıç taraması — özet

Bu dosya, `reports/baseline/pylint.txt` ham raporundan `scripts/summarize_baseline_reports.py` ile üretilmiştir. Ham rapor değiştirilmemiştir.

**Pylint puanı:** 6.42/10

## Kategori dağılımı

| Kategori | Kod öneki | Adet |
| --- | --- | --- |
| error | E | 324 |
| warning | W | 454 |
| refactor | R | 537 |
| convention | C | 2646 |
| information | I | 38 |
| **Toplam** | | **3999** |

## En sık 20 mesaj kodu

| Kod | Açıklama (sembol) | Adet |
| --- | --- | --- |
| C0301 | line-too-long | 911 |
| C0116 | missing-function-docstring | 779 |
| C0209 | consider-using-f-string | 303 |
| E0611 | no-name-in-module | 252 |
| C0103 | invalid-name | 209 |
| C0411 | wrong-import-order | 105 |
| R1705 | no-else-return | 96 |
| C0114 | missing-module-docstring | 92 |
| C0115 | missing-class-docstring | 90 |
| W0718 | broad-exception-caught | 83 |
| W1406 | redundant-u-string-prefix | 69 |
| R1734 | use-list-literal | 65 |
| R0912 | too-many-branches | 63 |
| R0401 | cyclic-import | 43 |
| W0719 | broad-exception-raised | 42 |
| E1101 | no-member | 39 |
| I1101 | c-extension-no-member | 38 |
| C0415 | import-outside-toplevel | 37 |
| C0121 | singleton-comparison | 35 |
| W0511 | fixme | 34 |

## Dosya başına en çok uyarı alan 10 dosya

| Dosya | Uyarı adedi |
| --- | --- |
| `cps\admin.py` | 336 |
| `cps\web.py` | 333 |
| `cps\editbooks.py` | 255 |
| `cps\helper.py` | 218 |
| `cps\db.py` | 212 |
| `cps\gdriveutils.py` | 195 |
| `cps\kobo.py` | 194 |
| `cps\ub.py` | 178 |
| `cps\opds.py` | 110 |
| `cps\shelf.py` | 110 |

## Ortamdan kaynaklanan mesajlar (güvenlik/kod kalitesi bulgusu SAYILMAZ)

CLAUDE.md madde 9: import/bağımlılık hataları (`E0401 import-error` vb.) güvenlik bulgusu sayılmaz; ortam sorunu olarak burada ve `docs/environment-notes.md` içinde kayıtlıdır. `E0611 no-name-in-module` da aynı tabloda, kaynağı ayrıştırılmış biçimde gösterilir.

### E0401 — import-error

| Dosya | Satır | LDAP ile ilgili mi? | Mesaj |
| --- | --- | --- | --- |
| `cps\services\simpleldap.py` | 21 | Evet (flask_simpleldap eksik) | Unable to import 'flask_simpleldap' (import-error) |
| `cps\services\simpleldap.py` | 22 | Evet (flask_simpleldap eksik) | Unable to import 'flask_simpleldap' (import-error) |

### E0611 — no-name-in-module

Toplam 252 adet. Bunlardan **2** adedi LDAP modülünde (`cps/services/simpleldap.py`, `flask_simpleldap` eksik olduğu için modül tam çözümlenemiyor); kalan **250** adedi LDAP ile ilgisizdir ve `cps/__init__.py` içinde alt modüllerin paket özniteliği olarak çalışma zamanında (dynamic attribute) atanmasından kaynaklanır — Pylint'in statik analizinin bu örüntüyü çözememesi bilinen bir kısıttır, kod hatası veya güvenlik açığı değildir.

LDAP dışı E0611 uyarılarının göründüğü dosya sayısı: 62 (liste `reports/baseline/pylint.txt` içinde `E0611` aranarak görülebilir; ayrıntı burada tekrarlanmamıştır).

