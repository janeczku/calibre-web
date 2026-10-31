# Bandit bulguları — manuel değerlendirme notları (hazırlayan: 3. kişi — Emre Bulut; gözden geçiren: 1. kişi — Şeyda Altın)

- **Kapsam:** `cps/` ve `cps.py` (K1). Ham raporlar: `reports/baseline/bandit-cps.json`, `reports/baseline/bandit-entrypoint.json`.
- **Otomatik özet:** `docs/bandit-summary.md` (`scripts/summarize_bandit_reports.py` ile üretilir).
- **Bulgu kaydı:** `docs/findings-register.csv` → FIND-001 … FIND-044.
- **Yöntem:** Her uyarının satırı ve çağrıldığı yer kodda okundu. Girdinin nereden geldiğine (HTTP isteği mi, yapılandırma mı, sabit mi) ve hangi yetkiyle ulaşılabildiğine bakıldı. Uygulama çalıştırılmadı (K2), yani sonuçlar kod okumasına dayanır. CLAUDE.md madde 8 gereği hiçbir uyarı, kodla gerekçelendirilmeden "açık" sayılmadı.
- **İnceleyen:** 3. kişi (Emre Bulut). Kayıtta `inceleyen = Emre Bulut`; `gozden_geciren` FIND-001…043 için `Şeyda Altın` (PR #4 incelemesi), FIND-044 için `-` (karar `review-auth.md` PR'ında verilecek, gözden geçiren orada yazılacak). Yetki bulguları başlangıçta 3. kişiye atanmıştı; rol düzeltmesiyle (Emre Bulut = 3. kişi) inceleyen ve gözden geçiren aynı kişi olacağı için 1. kişiye alındı (`inceleyen ≠ gozden_geciren`). Bulgu kaydının sahibi 2. kişidir (Dilara Yıldırım).

## 1. Başlangıç raporunun Bandit sürümü (K8)

Geçerli baseline (`reports/baseline/bandit-cps.json`, `bandit-entrypoint.json`) **Bandit 1.9.4** ile, CLAUDE.md'deki komut ve parametrelerle, kod değişikliğinden önce üretilmiştir (`generated_at` 2026-10-28T12:12:14Z). `cps/` için 42, `cps.py` için 1 bulgu; LOC / `# nosec` / hata: 31571 / 10 / 0.

**Arka plan:** İlk başlangıç raporları yanlışlıkla Bandit 1.8.6 ile üretilmişti (kök neden: Windows dışı (macOS) ortamda sürüm belirtilmeden kurulum; o anki Python sürümü kayıtlı değil). Kurulum sonrası tutarlılık kontrolünde aynı commit (`6e840ac…`) ve aynı parametrelerle 1.9.4 kullanıldığında `cps/` için 3 ek B105 bulgusu çıktı: `cps/kobo.py:1266`, `cps/kobo.py:1281` ve `cps/usermanagement.py:71` (FIND-035, FIND-036, FIND-042). Diğer bulgular birebir aynıydı; fark kod değişikliğinden değil sürümden kaynaklanıyordu.

**Karar (K8, ekip onayı 28 Ekim 2026):** Baseline 1.9.4 ile yeniden üretildi; orijinal 1.8.6 raporları `evidence/bandit-1.8.6-original/` altında saklanıyor. Bu, "baseline yeniden üretilmez" kuralına tek seferlik istisnadır. Başlangıç ve son tarama artık aynı Bandit sürümüyle yapıldığı için `bandit-comparison.md` içinde ayrı bir "sürüm farkı" satırına gerek yoktur. Bundan sonraki tüm Bandit çalıştırmaları yalnızca `requirements-lock.txt` ile kurulmuş `.venv` içinde yapılır ve çalıştırmadan önce `python -m bandit --version` çıktısının 1.9.4 olduğu kontrol edilir.

Bulgu kaydı, geçerli baseline'daki 43 Bandit bulgusunu ve 1 manuel bulguyu kapsar.

## 2. Sonuç özeti

| Doğrulama sonucu | Adet | Bulgular |
| --- | --- | --- |
| Gerçek sorun | 5 | FIND-010…014 (B113, zaman aşımı olmayan dış HTTP istekleri) |
| Düşük öncelikli uyarı | 7 | FIND-001 (B307), FIND-009 (B104), FIND-015, 016, 027, 032, 033 (B110/B112) |
| Yanlış pozitif | 31 | Bunların 10'u gömülü üçüncü taraf kod (`cps/cw_advocate/`, K7) |
| İnceleniyor (manuel) | 1 | FIND-044 (`# nosec` ile susturulmuş varsayılan admin parolası) |
| **Toplam** | **44** | 43 Bandit + 1 manuel |

Önem dağılımı (araç): HIGH 0 · MEDIUM 14 · LOW 29. Tüm MEDIUM bulgular (ders maddesi 4) aşağıda kod parçasıyla incelendi.

## 3. MEDIUM önemli bulgular

### FIND-001 — B307 `eval` · `cps/dep_check.py:48` (`load_dependencies`) · MEDIUM/HIGH

```python
res = re.match(r'(.*?)([<=>\s]+)([\d\.]+),?\s?([<=>\s]+)?([\d\.]+)?(?:\s?;\s?'
               r'(?:(python_version)\s?([<=>]+)\s?\'([\d\.]+)\'|' ...
if not eval(str(sys.version_info[0]) + "." + "{:02d}".format(sys.version_info[1]) +
            res.group(7) + val[0] + "." + "{:02d}".format(int(val[1]))):
```

- **Kontrol edildi:** `eval` metninin parçalarının nereden geldiği.
- **Gözlem:** Girdi, kurulum dizinindeki `requirements.txt` ve `optional-requirements.txt` dosyalarıdır, HTTP girdisi değildir. Regex, operatörü `[<=>]+`, sürümü `[\d.]+` ile sınırlar; `int()` dönüşümü de var. Üretilen ifade her zaman `3.12>=3.10` biçiminde bir karşılaştırmadır.
- **Sonuç:** Sömürülebilir açık yok. **Düşük öncelikli uyarı.** Yine de `eval` gereksiz.
- **Önerilen düzeltme:** `sys.version_info[:2]` ile `(int, int)` demeti karşılaştırması ve `operator.ge/gt/le/lt/eq`. Davranış korunur ve uyarı gerçekten kapanır. **K5 için güçlü aday.**

### FIND-002, 003, 005 — B704 `Markup` · `cps/editbooks.py:125, 706, 1344` · MEDIUM/HIGH

```python
modify_date |= edit_book_comments(Markup(to_save.get('comments')).unescape(), book)   # 706
...
def edit_book_comments(comments, book):
    if comments:
        comments = clean_string(comments, book.id)    # cps/clean_html.py → nh3.clean(...)
```

- **Kontrol edildi:** `Markup` sonucu "güvenli HTML" olarak şablona gidiyor mu?
- **Gözlem:** `Markup(x).unescape()` HTML varlıklarını çözüp **düz `str`** döndürür; güvenli işaretlemez. Değer hemen `clean_html.clean_string()` ile beyaz listeye dayalı `nh3` temizleyicisinden geçirilip veritabanına yazılıyor. 1344. satırda da (`edit_cc_data_value`, `comments` türü özel sütun) aynı desen var.
- **Sonuç:** **Yanlış pozitif.** XSS koruması `nh3` temizleyicisiyle sağlanıyor. Yorumlarda izin verilen etiket ve özniteliklerin (`style`, `img src` vb.) yeterliliği 4. kişinin yükleme incelemesine bırakıldı.

### FIND-004 — B704 `Markup` · `cps/editbooks.py:884` (`prepare_authors_on_upload`) · MEDIUM/HIGH

- **Gözlem:** `Markup(render_title_template('book_exists_flash.html', entry=entry))`. Şablonda kullanıcıdan gelebilecek tek değer `{{entry.title|shortentitle}}`. Jinja otomatik kaçış açık ve `shortentitle` düz `str` döndürdüğü için başlık kaçışlanır. Soldaki çeviri metni `str + Markup` birleşiminde `Markup.__radd__` tarafından kaçışlanır.
- **Sonuç:** **Yanlış pozitif.**

### FIND-006, 007 — B103 `chmod 0o660` · `cps/server.py:129, 271` · MEDIUM/HIGH

- **Gözlem:** Bu izin yalnızca `CALIBRE_UNIX_SOCKET` ortam değişkeniyle açılan Unix soketine uygulanıyor. Sahip ve grup okuyup yazabilir, diğer kullanıcıların izni yok. Kod yorumu, ön yüz web sunucusuyla grup üzerinden paylaşım için bilinçli seçildiğini söylüyor.
- **Sonuç:** **Yanlış pozitif** (tasarım kararı). Bandit grup yazma iznini işaretliyor, ancak "others" izni verilmiyor.

### FIND-008 — B310 `urlopen` · `cps/tasks/thumbnail.py:386` · MEDIUM/HIGH

- **Gözlem:** Argüman `gdriveutils.get_cover_via_gdrive()` dönüşü. Kaynak Google Drive API'si, kullanıcının verdiği bir URL değil; `file:` şeması enjekte edilemez.
- **Sonuç:** **Yanlış pozitif.**
- **Yan gözlem (güvenlik dışı):** `get_cover_via_gdrive()` URL değil dosya içeriği (`bytes`) döndürüyor. Bu durumda `urlopen(bytes)` çalışma zamanında hata verebilir. İşlev hatası adayıdır; uygulama çalıştırılmadığı için doğrulanmadı. 4. kişiye bilgi olarak iletildi.

### FIND-009 — B104 `0.0.0.0` · `cps/server.py:138` · MEDIUM/MEDIUM

- **Gözlem:** Windows'ta, yönetici dinleme adresi belirtmemişse `0.0.0.0` kullanılıyor. Diğer sistemlerde de varsayılan `::`, yani tüm arayüzler. Adres `config_ipaddress` ile değiştirilebiliyor.
- **Sonuç:** **Düşük öncelikli uyarı.** Sunucu yazılımı için olağan bir varsayılan. Ancak varsayılan `admin/admin123` hesabıyla (FIND-044) birlikte düşünüldüğünde, ilk kurulumda ağa açık bir yönetici hesabı anlamına gelebilir. Kod değişikliği önerilmiyor; raporda risk olarak anılmalı.

### FIND-010…014 — B113 zaman aşımı olmayan `requests` · MEDIUM/LOW → **Gerçek sorun**

| FIND | Dosya:satır | Fonksiyon | Hedef |
| --- | --- | --- | --- |
| 010 | `cps/metadata_provider/comicvine.py:53` | `search` | comicvine.gamespot.com |
| 011 | `cps/metadata_provider/google.py:54` | `search` | googleapis.com |
| 012 | `cps/metadata_provider/lubimyczytac.py:121` | `search` | lubimyczytac.pl |
| 013 | `cps/metadata_provider/lubimyczytac.py:215` | `parse_single_book` | arama sonucundaki kitap sayfası |
| 014 | `cps/services/goodreads_support.py:89` | `my_GoodreadsRequest.request` | goodreads.com |

- **Gözlem:** Hedefler sabit dış servisler olduğundan SSRF yok. Ancak `timeout` verilmediği için `requests` süresiz bekler. Metadata arama, oturum açmış kullanıcının tetikleyebildiği bir uç nokta. Yanıt vermeyen bir servis, istekleri işleyen greenlet/iş parçacıklarını kilitleyerek hizmet kesintisine (DoS) yol açabilir.
- **Sonuç:** **Gerçek sorun**, etkisi orta-düşük.
- **Önerilen düzeltme:** Her çağrıya `timeout=(5, 30)` gibi açık bir değer eklemek. Çağrıların hepsi zaten `except Exception` içinde olduğundan zaman aşımı yakalanır ve davranış korunur. Aynı türden küçük bir grup olduğu için tek bir `fix/find-010` dalında yapılabilir. **K5 için en uygun aday.**

## 4. LOW önemli bulgular (kısa)

| FIND | Kural | Konum | Sonuç | Gerekçe (özet) |
| --- | --- | --- | --- | --- |
| 015 | B110 | `cps.py:61` | Düşük öncelikli | Ctrl+C sonrası kapanışta hata yutuluyor; süreç zaten çıkıyor. |
| 016 | B112 | `cps/admin.py:1081` (`pathchooser`) | Düşük öncelikli | `pathchooser()` dekoratörsüz bir yardımcıdır; yetki kontrolü onu çağıran `ajax_pathchooser` üzerindeki `@user_login_required` + `@admin_required` ile yapılır (`admin.py:952-956`). İşlenemeyen girdi atlanıyor, yetki atlatma yok. |
| 027 | B110 | `cps/error_handler.py:72` | Düşük öncelikli | Hata durumunda yığın izi gösterilmez (güvenli varsayılan). |
| 032, 033 | B110 | `cps/ub.py:766, 771` (`dispose`) | Düşük öncelikli | Veritabanı oturumu kapatılırken yapılan temizlikte hata yutuluyor. |
| 028 | B404 | `cps/subproc_wrapper.py:21` | Yanlış pozitif | Yalnızca import. Tek `Popen` çağrısı `shell=False`. Windows dışında argümanlar liste; Windows'ta (`os.name == 'nt'`) tırnaklanıp tek string'e birleştiriliyor (`subproc_wrapper.py:28-32`). Shell yok; argüman bölme/tırnaklama riski 4. kişiye not edildi. |
| 029–031 | B101 | `cps/tornado_wsgi.py:86, 111, 112` | Yanlış pozitif | Tornado'dan uyarlanmış tip daraltma assert'leri, güvenlik kontrolü değil. |
| 037 | B606 | `cps/server.py:317` | Yanlış pozitif | `os.execv` argümanları `sys.executable` ve `sys.argv`'den geliyor, kullanıcı girdisi yok. |
| 034 | B105 | `cps/admin.py:1643` | Yanlış pozitif | LDAP kullanıcısının yerel parolası `''`. Werkzeug `check_password_hash('', x)` her zaman `False` döner (`$` ayrıştırılamaz). |
| 041 | B105 | `cps/ub.py:668` | Yanlış pozitif | Guest parola özeti `''`, aynı nedenle yerel girişte eşleşmez. `web.py` Guest girişini ayrıca reddediyor. |
| 042 | B105 | `cps/usermanagement.py:71` | Yanlış pozitif | Yalnızca `config_anonbrowse == 1` iken Guest için kurulan boş yetkilendirme. |
| 035, 036 | B105 | `cps/kobo.py:1266, 1281` | Yanlış pozitif | Anahtar adında "password"/"token" geçen herkese açık kobo.com URL'leri: 1266 → `password_retrieval_page`, 1281 → `rakuten_token_exchange`. |
| 038–040 | B105 | `cps/services/simpleldap.py:101, 104, 108` | Yanlış pozitif | `''` "parola yok" (anonim bağlanma) anlamında. Gerçek değer yapılandırmadan geliyor. |
| 043 | B107 | `cps/web.py:1366` (`render_login`) | Yanlış pozitif | Giriş formunu dolduran boş varsayılan argümanlar. |

## 5. Gömülü üçüncü taraf kod (K7): kapsamda, incelendi, düzeltme yapılmaz

| FIND | Kural | Konum | Not |
| --- | --- | --- | --- |
| 017, 019–026 | B101 | `cps/cw_advocate/addrvalidator.py`, `connection.py`, `connectionpool.py`, `poolmanager.py` | İç tutarlılık assert'leri. SSRF adres kontrolü ayrıca `if`/`raise` ile yapılıyor. |
| 018 | B403 | `cps/cw_advocate/api.py:31` | `pickle` yalnızca `pickle.dumps(self)` ile önbellek anahtarı özeti üretmek için kullanılıyor. `loads` yok. |

`cps/cw_login/` altında Bandit bulgusu yok. Bu klasörlerde düzeltme yapılmaz; bulgular yalnızca kayda alınmıştır.

## 6. `# nosec` ile susturulmuş satırlar (upstream kodu)

Başlangıç raporunda `nosec: 10` görünüyor. Bunlar upstream'den gelen işaretler; ekip `# nosec` eklemedi (K4/K6). Bandit bunları raporlamaz, ancak manuel olarak gözden geçirildi:

| Konum | İçerik | Not |
| --- | --- | --- |
| `cps/constants.py:140` | `DEFAULT_PASSWORD = "admin123"` | **FIND-044 olarak kayda alındı (İnceleniyor, 3. kişi).** Varsayılan admin parolası. İlk girişte değiştirmeye zorlama var mı kontrol edilmeli. |
| `cps/cache_buster.py:52`, `cps/file_helper.py:51`, `cps/uploader.py:282`, `cps/gdrive.py:143` | `hashlib.md5` | Güvenlik amaçlı değil, önbellek anahtarı, geçici ad ve sağlama toplamı için kullanılıyor. Makul. |
| `cps/gdrive.py:48`, `cps/services/SyncToken.py:60, 94, 106` | Sabit "token" adlı dizgiler | Başlık adı ve sabit hedef metni; gizli değer değil. |
| `cps/subproc_wrapper.py:36` | `subprocess.Popen(..., shell=False)` | Çağrı yerleri 4. kişinin incelemesinde (`architecture.md` 5.2). |

## 7. Düzeltme için öneriler (K5: en az 3 güvenlik bulgusu)

1. **FIND-010…014 (B113):** `timeout` eklenmesi. Küçük ve davranışı koruyan bir değişiklik. Uygulayıcı 1 Kasım toplantısında belirlenecek (bkz. B113 düzeltme planı).
2. **FIND-001 (B307):** `eval` yerine demet karşılaştırması. Sahibi 1. kişi veya 2. kişi.
3. **FIND-002…005 (B704):** Kanıtla yanlış pozitif gösterildi (bu doküman). K5'teki "kanıtla yanlış pozitif gösterilir" maddesini karşılar. `# nosec` eklenecekse K6 gereği PR'da ayrıca belirtilmeli. Alternatif: `Markup(x).unescape()` yerine eşdeğer `html.unescape(x)` kullanmak; bu durumda uyarı gerçekten kapanır.

Son tarama sonrasında 2. kişi, düzeltmeyi yapmayan üye olarak her düzeltmeyi dosya bazlı Bandit çalıştırmasıyla (`python -m bandit cps\<dosya>.py`) doğrular ve `findings-register.csv` içindeki `son_tarama_sonucu` sütununu doldurur.


## B113 düzeltme planı

### Amaç ve kapsam

Bandit B113 kapsamında FIND-010–FIND-014 bulgularında dış HTTP isteklerine açık zaman aşımı tanımlanmamıştır. Yanıt vermeyen dış servisler uygulama kaynaklarını uzun süre meşgul edebilir. Bu bölüm, 1 Kasım ekip toplantısında değerlendirilmek üzere hazırlanmış bir düzeltme önerisidir; kaynak kodunda henüz değişiklik yapılmamıştır.

### Bulgu bazlı düzeltme önerileri

| Bulgu | Dosya ve satır | Önerilen değişiklik | Mevcut hata yönetimi |
| --- | --- | --- | --- |
| FIND-010 | `cps/metadata_provider/comicvine.py:53` | `timeout=(5, 30)` | `except Exception` ile loglanır; `[]` döner |
| FIND-011 | `cps/metadata_provider/google.py:54` | `timeout=(5, 30)` | `except Exception` ile loglanır; `[]` döner |
| FIND-012 | `cps/metadata_provider/lubimyczytac.py:121` | `timeout=(5, 30)` | `except Exception` ile loglanır; `None` döner |
| FIND-013 | `cps/metadata_provider/lubimyczytac.py:215` | `timeout=(5, 30)` | `except Exception` ile loglanır; `None` döner |
| FIND-014 | `cps/services/goodreads_support.py:89` | `timeout=(5, 30)` | İncelenen `get_author_info()` çağrı yolunda üst seviyede yakalanır |

### Teknik gerekçe ve dikkat noktaları

- Önerilen `(5, 30)` değerleri bağlantı ve okuma zaman aşımıdır; toplam istek süresine kesin bir üst sınır koymaz.
- Projede `cps/updater.py` ve `cps/helper.py` içinde açık timeout kullanımı bulunmaktadır. Önerilen değerler testlerle doğrulanmalıdır.
- FIND-010–FIND-013 için `requests.exceptions.Timeout`, mevcut `except Exception` blokları tarafından yakalanabilir.
- FIND-013'te `ThreadPool(processes=10)` kullanıldığından paralel isteklerde zaman aşımı ve `None` sonuçlarının işlenmesi ayrıca test edilmelidir.
- FIND-014'te `request()` içinde doğrudan `try/except` yoktur. İncelenen `get_author_info()` akışında istisna yakalanır; başka çağrı yolları varsa ayrıca kontrol edilmelidir.
- Dış servise erişim koşulları ve isteklerin kullanıcı tarafından tetiklenebilirliği doğrulama sırasında değerlendirilmelidir.

### Uygulama ve doğrulama planı

1. Ekip onayından sonra beş `requests.get()` çağrısına timeout parametresi eklenecek.
2. Normal servis yanıtlarında metadata araması ve yazar bilgisi işlemleri test edilecek.
3. Bağlantı ve okuma zaman aşımı kontrollü olarak simüle edilecek.
4. FIND-010–FIND-012 için mevcut hata dönüşleri kontrol edilecek.
5. FIND-013 için paralel istekler ve `None` sonuçlarının üst seviyede işlenmesi test edilecek.
6. FIND-014 için yazar sayfasının timeout durumundaki davranışı doğrulanacak.
7. Düzeltme sonrası Bandit 1.9.4 ile ilgili dosyalar yeniden taranacak; B113 sonuçları başlangıç bulgularıyla karşılaştırılacak.

### Sorumluluk ve takvim

- **Planı hazırlayan:** Dilara — Rol 2, Bandit
- **Düzeltmeyi uygulayacak kişi:** 1 Kasım toplantısında belirlenecek
- **Gözden geçiren:** Uygulayıcıdan farklı bir ekip üyesi olacak
- **Düzeltme kararı:** 1 Kasım
- **Planlanan uygulama:** 2–5 Kasım
- **Son Bandit taraması:** 7 Kasım

**Durum:** Plan hazır; kaynak kodu değişikliği ve doğrulama testleri henüz yapılmadı.
