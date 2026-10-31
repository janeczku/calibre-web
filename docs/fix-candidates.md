# Düzeltme adayları ve önerilen dağılım

Hazırlayan: Şeyda Altın · Tarih: 31 Ekim 2026 · Durum: **taslak, grupta karar bekliyor** (1 Kasım toplantısı yapılmayacak; karar grupta alınacak)

Kaynaklar:
- `docs/findings-register.csv` içindeki tüm `Gerçek sorun` satırları;
- `docs/review-auth.md` ve `docs/review-file-handling.md` → "Düzeltme önerileri";
- `docs/review-bandit.md` → "B113 düzeltme planı".

K7 klasörlerinden (`cps/cw_login/`, `cps/cw_advocate/`) aday yok. Büyüklükler kodu okuyarak verildi:
- **küçük:** ≤ 5 satır, tek fonksiyon;
- **orta:** 6–40 satır, birden çok yer ya da şablon/i18n etkisi;
- **büyük:** yeni akış, şablon veya veri modeli.

## 1. Aday tablosu

| FIND-ID | Tür | Dosya:satır | Kısa açıklama | Önerilen düzeltme | Büyüklük | Risk | Aynı dosyaya dokunan diğer adaylar |
| --- | --- | --- | --- | --- | --- | --- | --- |
| FIND-010 | güvenlik | `cps/metadata_provider/comicvine.py:53` | `requests.get` zaman aşımı yok (B113) | `timeout=(5, 30)` | küçük (1 satır) | Düşük. `except Exception` Timeout'u yakalıyor, `[]` döner | – |
| FIND-011 | güvenlik | `cps/metadata_provider/google.py:54` | B113 | `timeout=(5, 30)` | küçük (1 satır) | Düşük | – |
| FIND-012 | güvenlik | `cps/metadata_provider/lubimyczytac.py:121` | B113 | `timeout=(5, 30)` | küçük (1 satır) | Düşük | FIND-013 (aynı dosya, aynı PR) |
| FIND-013 | güvenlik | `cps/metadata_provider/lubimyczytac.py:215` | B113, `ThreadPool(processes=10)` içinde | `timeout=(5, 30)` | küçük (1 satır) | Düşük–orta. Paralel isteklerde `None` sonuçları üst seviyede ele alınmalı (plan madde 5) | FIND-012 |
| FIND-014 (+ FIND-085 W3101) | güvenlik | `cps/services/goodreads_support.py:89` | B113. Yazar sayfasından, anonim gezinme açıksa girişsiz de tetiklenebilir | `timeout=(5, 30)`. W3101 de aynı değişiklikle kapanır | küçük (1 satır) | Düşük. `request()` içinde try yok, `get_author_info()` yakalıyor (:139-144) | – |
| FIND-116 | güvenlik | `cps/metadata_provider/amazon.py:61, 121` | `requests.Session` ile zaman aşımsız iki dış istek. Bandit B113 `Session` çağrılarını yakalamıyor; manuel incelemeyle bulundu (araç sınırlılığı) | `timeout=(5, 30)` (B113 ile aynı değer) | küçük (2 satır) | Düşük. İki çağrı da `except Exception` içinde, `[]` döner | `amazon.py`: PEP 8 düzeltmesi (Şeyda) |
| FIND-044 | güvenlik | `cps/constants.py:140` (+ `ub.py:677-689`, `web.py:1442`) | Varsayılan `admin/admin123`, ilk girişte parola değişikliği zorlanmıyor | İlk girişte parola değiştirme zorunluluğu | **büyük** (yeni yönlendirme akışı, durum alanı, şablon) | Yüksek: davranış değişikliği, ilk kurulum akışını etkiler | `web.py`: FIND-126, FIND-150 |
| FIND-126 | güvenlik | `cps/web.py:1428-1438` (`login_post`) | "Parolamı unuttum" var olan ve olmayan kullanıcıya farklı mesaj veriyor: kullanıcı adı tahmin edilebiliyor | Tüm dallarda (başarılı, kullanıcı yok, e-posta ayarsız, hata) mevcut `"New Password was sent to your email address"` mesajı (`web.py:1432`), yeni metin yok; log satırları ayrı kalır | **küçük** (4–6 satır, tek fonksiyon) | Düşük–orta. (1) Yeni metin eklenmez, bkz. bölüm 2. (2) E-posta ayarsızken ya da hata olduğunda kullanıcı hata görmez, log kalır. (3) Zamanlama farkı sürer. Asıl sorun (onaysız sıfırlama) çözülmez, raporda öneri olarak kalır | `web.py`: FIND-150 (1265), FIND-133 (1451, seçilmedi) |
| FIND-049 | kalite | `cps/admin.py:1374, 1377`; `cps/shelf.py:287` | Hata dalında `e.orig` olmayan istisnada AttributeError (500) | `getattr(e, 'orig', e)` | küçük (3 satır, 2 dosya) | Düşük. Yalnızca hata dalı | `admin.py`: FIND-078 (2206), FIND-069 (1169). `shelf.py`: FIND-132 (359, seçilmedi) |
| FIND-056 | kalite | `cps/helper.py:417` | E1305: biçim dizgisinde tek yer tutucu, iki argüman | `"File {}/{} not found on gdrive"` | küçük (1 satır) | Çok düşük (yalnızca log) | `helper.py`: FIND-081 (302), FIND-057/082 (847-850) |
| FIND-057 (+ FIND-082 W0705) | kalite (güvenlik etkili) | `cps/helper.py:847-850` (`save_cover_from_url`) | E0701: wand yokken `MissingDelegateError = BaseException`; SSRF engel istisnası yanlış blokta yakalanıyor | `except UnacceptableAddressException` bloğunu öne al | küçük (3 satır yer değişikliği) | Düşük. Engelleme zaten çalışıyor; düzelen mesaj ve log seviyesi | `helper.py`: FIND-081, FIND-056 |
| FIND-069 | kalite | `admin.py:1169`, `dep_check.py:29, 39`, `kobo.py:1158`, `updater.py:155, 411` | W1514: `open()` encoding'siz | `encoding='utf-8'` (gdrive.py ve gdriveutils.py kapsam dışı, bkz. kayıt) | küçük (6 satır, 4 dosya) | Düşük. Her dosyanın UTF-8 olduğu doğrulanmalı; `admin.py:1169` `client_secrets.json` okuyor (JSON → UTF-8 uygun) | `admin.py`: FIND-049, FIND-078 |
| FIND-078 | kalite | `cps/admin.py:2206` | W0715: `.format` unutulmuş | `", user)"` → `".format(user))"` | küçük (1 satır) | Çok düşük | `admin.py`: FIND-049, FIND-069 |
| FIND-080 (+ FIND-109 E722) | kalite | `cps/file_helper.py:85` | Çıplak `except:` | `except (zipfile.BadZipFile, OSError, ValueError, NotImplementedError):` | küçük (1 satır) | Düşük. Liste K9 denemesiyle doğrulandı; çağıranlarda try yok, kaçan istisna 500 olur | – |
| FIND-081 | kalite | `cps/helper.py:302` (`get_sorted_author`) | W1116: ters `isinstance`; hata işleyicisi kendisi çöküyor | `isinstance(value, list)` | küçük (1 satır) | Düşük | `helper.py`: FIND-056, FIND-057/082 |
| FIND-101 | kalite | `cps/epub.py:119`, `cps/fb2.py:34` | R1732: zip ve dosya açıkça kapatılmıyor | `with` bloğuna al | küçük (epub ~5 satır girinti, fb2 2 satır) | Düşük. `epub_zip` yalnızca `parse_epub_cover`'da kullanılıyor | – |
| PEP 8 (FIND-104 E501, FIND-105 E231, FIND-112 diğer) | PEP 8 | `cps/metadata_provider/amazon.py` (140 satır) | flake8 45 ihlal, 9 tür (E501 19, E251 12, E262 3, E203 3, E261 2, E265 2, E126 2, E225 1, E231 1) | Elle, yalnızca bu dosyada; hedef `flake8 --isolated --select=E,W` = 0 | orta (~35 satır, mekanik) | Düşük. Davranış değişmez; `py_compile` + flake8 + pylint ile doğrulanır | FIND-116 (Dilara, B113 PR'ı). PEP 8 PR'ı ondan sonra gelir |
| FIND-150 | güvenlik | `cps/web.py:1265` (`send_to_ereader`) | Kitap filtresiz `get_book` ile alınıyor; içerik kısıtlaması e-okuyucuya göndermede aşılıyor | `get_filtered_book(book_id, allow_show_archived=True)` | küçük (1 satır) | Düşük. Kitap bulunamazsa mevcut "format not supported" yanıtı | `web.py`: FIND-126 (1428), FIND-133 |
| FIND-151 | güvenlik (düşük) | `cps/editbooks.py:57-64` | Yönetici "yüklemeye izin ver" ayarı sunucuda uygulanmıyor | `role_upload() and config.config_uploading` | küçük (1 satır) | Düşük. Amaçlanan davranış değişikliği | – |
| FIND-152 | kalite (işlev) | `cps/tasks/thumbnail.py:384-386` | GDrive seri küçük resminde bytes `urlopen`'a veriliyor | `io.BytesIO(web_content_link)` | küçük (1–2 satır) | Düşük; yalnızca GDrive kurulumları | – |
| FIND-158 | kalite | `cps/subproc_wrapper.py:28-32` | Windows dalında komutun 0. elemanı tırnaklanmıyor | `subprocess.list2cmdline()` | orta | Orta. Windows'ta davranış değişikliği riski (review-file-handling önceliği düşük) | – |
| FIND-132 | güvenlik (düşük) | `cps/shelf.py:359` | Raf görünürlük kontrolü istisnada `True` döndürüyor (fail-open) | `except` sonrası `return False` | küçük (1 satır) | Düşük | `shelf.py`: FIND-049 (287) |
| FIND-133 | güvenlik (düşük) | `cps/web.py:1451` | Başarısız girişte parola forma geri basılıyor | `render_login(username, "")` | küçük (1 satır) | Düşük | `web.py`: FIND-126, FIND-150 |
| FIND-128 | güvenlik (düşük) | `cps/oauth_bb.py:192` | `/unlink/*` GET ile çalışıyor (CSRF) | `abort(403)` ya da POST'a çevirme (şablon) | küçük–orta | Orta (POST seçeneği şablon değiştirir) | – |
| FIND-127 | güvenlik (düşük) | `cps/main.py:69` | OPDS sınırlamasında günlük limit yok | `"3/minute;40/day"` | küçük (1 satır) | Düşük | – |

`FIND-127`, `FIND-128`, `FIND-132` ve `FIND-133` kayıtta `Düşük öncelikli uyarı` olarak duruyor; `review-auth.md` önerisi oldukları için tabloya alındı. Seçilirlerse kaydı `Gerçek sorun` olarak güncellemek gerekir (bkz. CLAUDE.md "Düzeltme yaparken" madde 1).

## 2. FIND-044 ve FIND-126: büyüklük değerlendirmesi

- **FIND-044 büyük.** Kodu okuyarak:
  - `config_is_initial` yalnızca ilk girişte `False` yapılıyor (`web.py:1442`).
  - Parola değişikliğini zorlamak için kullanıcı başına bir "parola değişmeli" durumu gerekir (`ub.py` veri modeli ya da config).
  - Tüm route'larda bir `before_request` yönlendirmesi ve profil sayfası akışı da eklenmeli.
  - Bu, birden çok dosyada davranış değişikliği demek. Raporda risk ve kurulum önerisi olarak kalsın.
- **FIND-126 küçük.**
  - Değişiklik `login_post` içindeki "forgot" dalında üç `flash` çağrısının hepsinde aynı mesajı kullanmak (4–6 satır).
  - Yeni metin eklenmez. Kullanılacak mesaj, aynı fonksiyonun başarı dalında zaten duran `_(u"New Password was sent to your email address")`, `category="info"` (`web.py:1432`).
    - Bugün meşru kullanıcının gördüğü mesaj değişmez.
    - Var olmayan kullanıcı, e-posta ayarsız (`ret == 2`) ve hata (`ret == 0`) dalları da aynı mesajı gösterir.
    - Fonksiyon her durumda `401` döndürdüğü için HTTP durum kodu da aynı kalır.
  - Bu dallarda parola değişmez: `reset_password` e-posta ayarsızken parolaya dokunmadan döner, hata olduğunda `rollback` yapar. Mesaj kimseyi hesabından etmez.
  - Log satırları ayrı kalır, yöneticinin gerçek durumu görmesi bunlara bağlıdır.
  - Çeviri durumu: bu dizgi 28 dilin 14'ünde çevrili (`tr` çevrilmemiş olanlardan). Değişiklik yeni bir çevrilmemiş metin eklemiyor, mevcut kapsamı koruyor.
  - Değerlendirilen alternatif: `"Success! Confirmation Email has been sent."` (`web.py:1341`, kayıt akışı; 25/28 çevrili). Anlamı parola sıfırlamaya uymuyor (kayıt onayı), bu yüzden seçilmedi.
  - Kapanan sorun kullanıcı adı tahmini. Onaysız parola sıfırlama sorunu kapanmaz; raporda büyük öneri olarak kalır.
  - **Seçim: FIND-126.**
- Alternatif güvenlik adayı gerekmiyor. Yine de yedek olarak **FIND-132** (fail-closed, 1 satır) ya da **FIND-151** (1 satır) kullanılabilir. FIND-151 zaten `Gerçek sorun`. FIND-132 seçilirse önce kayıtta `Gerçek sorun` olarak güncellenmeli.

## 3. Önerilen seçim ve dağılım

| Uygulayan | Adaylar | Dal(lar) | Gözden geçiren |
| --- | --- | --- | --- |
| Dilara Yıldırım | FIND-010–014 (B113; FIND-085 W3101 de kapanır) + FIND-116 (`amazon.py`, aynı `timeout=(5, 30)`) | `fix/find-010` | Hasan Kurt |
| Hasan Kurt | FIND-150; FIND-057 (+082); FIND-080 (+109) | `fix/find-150`, `fix/find-057`, `fix/find-080` | Emre Bulut |
| Emre Bulut | FIND-126; FIND-049 | `fix/find-126`, `fix/find-049` | Şeyda Altın |
| Şeyda Altın | FIND-081 (W1116), FIND-078 (W0715), FIND-056 (E1305), FIND-069 (W1514), FIND-101 (R1732), PEP 8 `amazon.py` | `fix/find-081`, `fix/find-078`, `fix/find-056`, `fix/find-069`, `fix/find-101`, `fix/find-104` | Dilara Yıldırım |

FIND-048 ile ilgili not: FIND-048 `Yanlış pozitif`, düzeltilecek bir şey yok. Emre yalnızca FIND-049'u (iki gerçek `e.orig` hatası) düzeltir. FIND-048 kayıtta olduğu gibi kalır.

## 4. K5 kontrolü

- **Güvenlik (en az 3):**
  - B113 FIND-010–014: 5 bulgu, ayrıca aynı türden manuel FIND-116.
  - FIND-150 ve FIND-126.
  - Toplam **8 bulgu, 3 ayrı sorun türü**. B113 tek başına yetiyor; diğer ikisi çeşitlilik ve yedek sağlıyor.
  - FIND-057 güvenlik etkili ama kalite olarak sayıldı.
- **Kod kalitesi / PEP 8 türü (en az 5):**
  - Şeyda tek başına 5 Pylint türü düzeltiyor: W1116, W0715, E1305, W1514, R1732.
  - Hasan 2 tür düzeltiyor: E0701/W0705 ve W0702/E722.
  - Emre 1 tür düzeltiyor: E1101.
  - `amazon.py`'de 9 flake8 türü var.
  - Toplam **8 Pylint türü + 9 PEP 8 türü**. Yarısı düşse bile hedef karşılanır.
- **Sayım notu:** İkiz uyarılar (W0705, E722, W3101) aynı değişiklikle kapanır. Karşılaştırmada "kapanan" olarak ayrı sayılır, ama ayrı düzeltme sayılmaz.

## 5. Aynı dosyaya dokunan düzeltmeler: birleştirme sırası

Genel kural:
- Her PR birleşmeden önce güncel `project-analysis` ile güncellenir (`git merge project-analysis`).
- Dokunulan dosyada `py_compile` ile ilgili `pylint` ve `flake8` taramaları yeniden çalıştırılır.
- Aynı dosyada bir PR birleşmeden sıradaki birleştirilmez.

| Dosya | Sıra | Gerekçe |
| --- | --- | --- |
| `cps/helper.py` | 1) Hasan `fix/find-057` (847-850) → 2) Şeyda `fix/find-081` (302) → 3) Şeyda `fix/find-056` (417) | Güvenlik etkili değişiklik önce gider. Hunk'lar birbirinden uzak, çakışma beklenmez, ama satır kayması incelemeyi zorlaştırmasın diye sıralı ilerlenir. |
| `cps/web.py` | 1) Hasan `fix/find-150` (1265) → 2) Emre `fix/find-126` (1428-1438) | Tek satırlık olan önce gider. İkisi de güvenlik. |
| `cps/admin.py` | 1) Şeyda `fix/find-078` (2206) → 2) Emre `fix/find-049` (1374-1377, + `shelf.py`) → 3) Şeyda `fix/find-069` (1169 + `dep_check.py`, `kobo.py`, `updater.py`) | Tek satırlıklar önce gider. Dört dosyaya dokunan W1514 en sona kalır. |
| `cps/metadata_provider/amazon.py` | 1) Dilara `fix/find-010` (B113 + FIND-116, :61 ve :121) → 2) Şeyda `fix/find-104` (PEP 8) | Güvenlik düzeltmesi önce gider. PEP 8 PR'ı bu iki satırı da yeniden biçimlendirebilir. |
| `cps/file_helper.py`, `epub.py`, `fb2.py`, diğer `metadata_provider/*`, `goodreads_support.py` | Serbest | Başka seçilmiş aday yok. |

Takvim: PR'lar 2–5 Kasım arasında açılıp birleşir, 6 Kasım'da dosya bazlı tekrar tarama yapılır, 7 Kasım'da son taramalar çalıştırılır. 8 Kasım'dan sonra `cps/` değiştiren PR birleştirilmez. Son taramayı düzeltmeyi yapmayan bir üye kontrol eder.

## 6. Açık konular

1. **FIND-116 (karar verildi).** `amazon.py:61, 121`'deki zaman aşımsız `session.get` çağrıları kayda Manuel satır olarak eklendi. B113 PR'ına aynı değerle girecek. Raporda araç sınırlılığı örneği olarak anılacak: Bandit `requests.Session` çağrılarını yakalamıyor.
2. **FIND-126 mesajı (karar verildi).** Yeni metin eklenmiyor. Mevcut ve kısmen çevrili `"New Password was sent to your email address"` mesajı kullanılıyor (bkz. bölüm 2).
3. Bu dağılımda Şeyda'da 6 PR var. Gerekirse PEP 8 `amazon.py` yerine daha küçük olan `jinjia.py` (16 ihlal) kullanılabilir.

## 7. Gruba atılacak özet

```
Düzeltme adayları hazır: docs/fix-candidates.md (taslak, onayınızı bekliyor).
Öneri:
• Dilara: B113 FIND-010–014 + FIND-116 (amazon.py) (timeout=(5, 30), 7 satır) → gözden geçiren Hasan
• Hasan: FIND-150 (send_to_ereader filtresi), FIND-057 (helper.py except sırası), FIND-080 (file_helper bare except) → gözden geçiren Emre
• Emre: FIND-126 (forgot dallarında mevcut "New Password was sent…" mesajı, yeni metin yok, 4–6 satır) + FIND-049 (e.orig hatası) → gözden geçiren Şeyda
• Şeyda: W1116, W0715, E1305, W1514, R1732 + amazon.py PEP 8 → gözden geçiren Dilara
FIND-044 büyük (yeni parola değiştirme akışı) → raporda risk/öneri olarak kalır; FIND-126 küçük olduğu için seçildi.
K5: güvenlik 8 bulgu (B113 ×5, 116, 150, 126); kalite 8 Pylint + 9 PEP 8 türü → hedef karşılanıyor.
Birleştirme sırası:
• helper.py: Hasan 057 → Şeyda 081 → 056
• web.py: Hasan 150 → Emre 126
• admin.py: Şeyda 078 → Emre 049 → Şeyda 069
• amazon.py: Dilara B113 → Şeyda PEP 8
Her PR'dan önce project-analysis ile güncelleyin; py_compile + dosya bazlı pylint/flake8/bandit sonucunu PR'a yazın.
Takvim: PR'lar 2–5 Kasım, dosya bazlı tarama 6 Kasım, son tarama 7 Kasım, kod dondurma 8 Kasım.
Not: amazon.py'de Bandit'in görmediği 2 zaman aşımsız session.get kayda FIND-116 olarak eklendi (araç sınırlılığı); Dilara'nın B113 PR'ına giriyor.
İtirazı olan yarın öğlene kadar yazsın; yoksa bu dağılımla başlıyoruz.
```
