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

CLAUDE.md madde 9: import/bağımlılık hataları (`E0401 import-error` vb.) güvenlik bulgusu sayılmaz; ortam sorunu olarak burada ve `docs/environment-notes.md` içinde kayıtlıdır. `E0611 no-name-in-module` uyarıları da burada, Pylint'in bildirdiği modüle göre gruplanarak gösterilir.

### E0401 — import-error

| Dosya | Satır | LDAP ile ilgili mi? | Mesaj |
| --- | --- | --- | --- |
| `cps\services\simpleldap.py` | 21 | Evet (flask_simpleldap eksik) | Unable to import 'flask_simpleldap' (import-error) |
| `cps\services\simpleldap.py` | 22 | Evet (flask_simpleldap eksik) | Unable to import 'flask_simpleldap' (import-error) |

### E0611 — no-name-in-module

Toplam 252 adet. Pylint'in bildirdiği modüle göre dağılım:

| Modül | Adet | Dosya sayısı | Neden | Değerlendirme |
| --- | --- | --- | --- | --- |
| `cps` | 250 | 62 | `cps/__init__.py` alt modülleri ve servis örneklerini paket özniteliği olarak atıyor (dinamik atama); astroid bu örüntüyü çözemiyor | Yanlış pozitif adayı |
| `lxml.etree` | 1 | 1 | `lxml.etree` derlenmiş bir C uzantısı; astroid içini göremiyor, `ParserError` kurulu ortamda mevcut | Yanlış pozitif adayı |
| `cps.cw_advocate` | 1 | 1 | Gömülü üçüncü taraf kodda (K7) `from . import cw_advocate`; pakette `cw_advocate` adlı bir alt modül yok | Hata adayı (K7, düzeltilmez); 1. kişi `docs/pylint-findings` işinde doğrulayıp kayıtta gerekçelendirecek |

`cps/services/simpleldap.py` içindeki 2 E0611 uyarısı da `cps` modülü grubundadır (`constants`, `logger` gibi paket öznitelikleri); LDAP paketinin eksikliğiyle ilgisi yoktur.

`cps` dışındaki uyarılar:

- `cps\clean_html.py:20` — No name 'ParserError' in module 'lxml.etree' (no-name-in-module)
- `cps\cw_advocate\api.py:175` — No name 'cw_advocate' in module 'cps.cw_advocate' (no-name-in-module)

