# Bandit özeti

Bu dosya `scripts/summarize_bandit_reports.py` ile `reports/baseline/` altındaki ham JSON raporlarından üretilmiştir; elle düzenlemeyin. Manuel değerlendirme: `docs/review-bandit.md`, bulgu kaydı: `docs/findings-register.csv`.

## Rapor bilgileri

| Rapor | Üretilme zamanı (UTC) | Bulgu | Taranan LOC | `# nosec` | Hata | Bandit sürümü (more_info) |
| --- | --- | --- | --- | --- | --- | --- |
| `bandit-cps.json` | 2026-10-28T12:12:14Z | 42 | 31571 | 10 | 0 | 1.9.4 |
| `bandit-entrypoint.json` | 2026-10-28T12:12:14Z | 1 | 26 | 0 | 0 | 1.9.4 |

Toplam bulgu: **43**

## Önem × güven matrisi

| Önem \ Güven | HIGH | MEDIUM | LOW | Toplam |
| --- | --- | --- | --- | --- |
| HIGH | 0 | 0 | 0 | 0 |
| MEDIUM | 8 | 1 | 5 | 14 |
| LOW | 19 | 10 | 0 | 29 |
| Toplam | 27 | 11 | 5 | 43 |

## Kural kodu dağılımı

| Kural | Ad | Önem | Adet | Gömülü üçüncü taraf (K7) |
| --- | --- | --- | --- | --- |
| B113 | `request_without_timeout` | MEDIUM | 5 | 0 |
| B704 | `markupsafe_markup_xss` | MEDIUM | 4 | 0 |
| B103 | `set_bad_file_permissions` | MEDIUM | 2 | 0 |
| B104 | `hardcoded_bind_all_interfaces` | MEDIUM | 1 | 0 |
| B307 | `blacklist` | MEDIUM | 1 | 0 |
| B310 | `blacklist` | MEDIUM | 1 | 0 |
| B101 | `assert_used` | LOW | 12 | 9 |
| B105 | `hardcoded_password_string` | LOW | 8 | 0 |
| B110 | `try_except_pass` | LOW | 4 | 0 |
| B107 | `hardcoded_password_default` | LOW | 1 | 0 |
| B112 | `try_except_continue` | LOW | 1 | 0 |
| B403 | `blacklist` | LOW | 1 | 1 |
| B404 | `blacklist` | LOW | 1 | 0 |
| B606 | `start_process_with_no_shell` | LOW | 1 | 0 |

## Tüm bulgular (önem, güven, dosya sırasıyla)

| # | Önem | Güven | Kural | Dosya:satır | Bandit mesajı | Not |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | MEDIUM | HIGH | B307 | `cps/dep_check.py:48` | Use of possibly insecure function - consider using safer ast.literal_eval. |  |
| 2 | MEDIUM | HIGH | B704 | `cps/editbooks.py:125` | Potential XSS with `markupsafe.Markup` detected. Do not use `Markup` on untrusted data. |  |
| 3 | MEDIUM | HIGH | B704 | `cps/editbooks.py:706` | Potential XSS with `markupsafe.Markup` detected. Do not use `Markup` on untrusted data. |  |
| 4 | MEDIUM | HIGH | B704 | `cps/editbooks.py:884` | Potential XSS with `markupsafe.Markup` detected. Do not use `Markup` on untrusted data. |  |
| 5 | MEDIUM | HIGH | B704 | `cps/editbooks.py:1344` | Potential XSS with `markupsafe.Markup` detected. Do not use `Markup` on untrusted data. |  |
| 6 | MEDIUM | HIGH | B103 | `cps/server.py:129` | Chmod setting a permissive mask 0o660 on file (unix_socket_file). |  |
| 7 | MEDIUM | HIGH | B103 | `cps/server.py:271` | Chmod setting a permissive mask 0o660 on file (unix_socket_file). |  |
| 8 | MEDIUM | HIGH | B310 | `cps/tasks/thumbnail.py:386` | Audit url open for permitted schemes. Allowing use of file:/ or custom schemes is often unexpected. |  |
| 9 | MEDIUM | MEDIUM | B104 | `cps/server.py:138` | Possible binding to all interfaces. |  |
| 10 | MEDIUM | LOW | B113 | `cps/metadata_provider/comicvine.py:53` | Call to requests without timeout |  |
| 11 | MEDIUM | LOW | B113 | `cps/metadata_provider/google.py:54` | Call to requests without timeout |  |
| 12 | MEDIUM | LOW | B113 | `cps/metadata_provider/lubimyczytac.py:121` | Call to requests without timeout |  |
| 13 | MEDIUM | LOW | B113 | `cps/metadata_provider/lubimyczytac.py:215` | Call to requests without timeout |  |
| 14 | MEDIUM | LOW | B113 | `cps/services/goodreads_support.py:89` | Call to requests without timeout |  |
| 15 | LOW | HIGH | B110 | `cps.py:61` | Try, Except, Pass detected. |  |
| 16 | LOW | HIGH | B112 | `cps/admin.py:1081` | Try, Except, Continue detected. |  |
| 17 | LOW | HIGH | B101 | `cps/cw_advocate/addrvalidator.py:243` | Use of assert detected. The enclosed code will be removed when compiling to optimised byte code. | Gömülü üçüncü taraf (K7): kapsamda, incelendi, düzeltme yapılmaz. |
| 18 | LOW | HIGH | B403 | `cps/cw_advocate/api.py:31` | Consider possible security implications associated with pickle module. | Gömülü üçüncü taraf (K7): kapsamda, incelendi, düzeltme yapılmaz. |
| 19 | LOW | HIGH | B101 | `cps/cw_advocate/connection.py:63` | Use of assert detected. The enclosed code will be removed when compiling to optimised byte code. | Gömülü üçüncü taraf (K7): kapsamda, incelendi, düzeltme yapılmaz. |
| 20 | LOW | HIGH | B101 | `cps/cw_advocate/connection.py:184` | Use of assert detected. The enclosed code will be removed when compiling to optimised byte code. | Gömülü üçüncü taraf (K7): kapsamda, incelendi, düzeltme yapılmaz. |
| 21 | LOW | HIGH | B101 | `cps/cw_advocate/connection.py:185` | Use of assert detected. The enclosed code will be removed when compiling to optimised byte code. | Gömülü üçüncü taraf (K7): kapsamda, incelendi, düzeltme yapılmaz. |
| 22 | LOW | HIGH | B101 | `cps/cw_advocate/connectionpool.py:26` | Use of assert detected. The enclosed code will be removed when compiling to optimised byte code. | Gömülü üçüncü taraf (K7): kapsamda, incelendi, düzeltme yapılmaz. |
| 23 | LOW | HIGH | B101 | `cps/cw_advocate/connectionpool.py:27` | Use of assert detected. The enclosed code will be removed when compiling to optimised byte code. | Gömülü üçüncü taraf (K7): kapsamda, incelendi, düzeltme yapılmaz. |
| 24 | LOW | HIGH | B101 | `cps/cw_advocate/connectionpool.py:28` | Use of assert detected. The enclosed code will be removed when compiling to optimised byte code. | Gömülü üçüncü taraf (K7): kapsamda, incelendi, düzeltme yapılmaz. |
| 25 | LOW | HIGH | B101 | `cps/cw_advocate/connectionpool.py:29` | Use of assert detected. The enclosed code will be removed when compiling to optimised byte code. | Gömülü üçüncü taraf (K7): kapsamda, incelendi, düzeltme yapılmaz. |
| 26 | LOW | HIGH | B101 | `cps/cw_advocate/poolmanager.py:58` | Use of assert detected. The enclosed code will be removed when compiling to optimised byte code. | Gömülü üçüncü taraf (K7): kapsamda, incelendi, düzeltme yapılmaz. |
| 27 | LOW | HIGH | B110 | `cps/error_handler.py:72` | Try, Except, Pass detected. |  |
| 28 | LOW | HIGH | B404 | `cps/subproc_wrapper.py:21` | Consider possible security implications associated with the subprocess module. |  |
| 29 | LOW | HIGH | B101 | `cps/tornado_wsgi.py:86` | Use of assert detected. The enclosed code will be removed when compiling to optimised byte code. |  |
| 30 | LOW | HIGH | B101 | `cps/tornado_wsgi.py:111` | Use of assert detected. The enclosed code will be removed when compiling to optimised byte code. |  |
| 31 | LOW | HIGH | B101 | `cps/tornado_wsgi.py:112` | Use of assert detected. The enclosed code will be removed when compiling to optimised byte code. |  |
| 32 | LOW | HIGH | B110 | `cps/ub.py:766` | Try, Except, Pass detected. |  |
| 33 | LOW | HIGH | B110 | `cps/ub.py:771` | Try, Except, Pass detected. |  |
| 34 | LOW | MEDIUM | B105 | `cps/admin.py:1643` | Possible hardcoded password: '' |  |
| 35 | LOW | MEDIUM | B105 | `cps/kobo.py:1266` | Possible hardcoded password: 'https://www.kobo.com/passwordretrieval.html' |  |
| 36 | LOW | MEDIUM | B105 | `cps/kobo.py:1281` | Possible hardcoded password: 'https://storeapi.kobo.com/v1/auth/rakuten_token_exchange' |  |
| 37 | LOW | MEDIUM | B606 | `cps/server.py:317` | Starting a process without a shell. |  |
| 38 | LOW | MEDIUM | B105 | `cps/services/simpleldap.py:101` | Possible hardcoded password: '' |  |
| 39 | LOW | MEDIUM | B105 | `cps/services/simpleldap.py:104` | Possible hardcoded password: '' |  |
| 40 | LOW | MEDIUM | B105 | `cps/services/simpleldap.py:108` | Possible hardcoded password: '' |  |
| 41 | LOW | MEDIUM | B105 | `cps/ub.py:668` | Possible hardcoded password: '' |  |
| 42 | LOW | MEDIUM | B105 | `cps/usermanagement.py:71` | Possible hardcoded password: '' |  |
| 43 | LOW | MEDIUM | B107 | `cps/web.py:1366` | Possible hardcoded password: '' |  |
