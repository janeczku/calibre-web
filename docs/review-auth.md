# Yetki ve oturum incelemesi (3. kişi — Emre Bulut)

- **İncelenen commit:** `6e840acbda8d62fdd159bf3855c01872d629a914` (`docs/baseline-commit.txt`)
- **Tarih:** 29–30 Ekim 2026
- **Yöntem:** Kod okuma; uygulama çalıştırılmadı (K2). Route listesi `cps/*.py` üzerinde AST ile çıkarıldı (her fonksiyonun `@*.route` ve diğer dekoratörleri), ardından her kontrol noktası kodda izlendi.
- **Kapsam:** `docs/guides/rol-3-yetki.md` kontrol listesi A–E. `cps/cw_login/` (K7) yalnızca davranışı anlamak için okundu.

## Özet

- İncelenen kontrol noktası: **20**
- Gerçek sorun: **2** · Düşük öncelikli: **7** · Sorun yok: **11**
- Kayda eklenen / güncellenen bulgular: FIND-044 (sonuçlandırıldı), FIND-125 … FIND-133

| # | Kontrol noktası | Sonuç | FIND |
| --- | --- | --- | --- |
| A1 | Yönetici route'ları | Düşük öncelikli (1 istisna) | FIND-125 |
| A2 | Rol gerektiren işlemler | Sorun yok | – |
| A3 | Dekoratörsüz yardımcılar / iç kontroller | Düşük öncelikli | FIND-132 |
| A4 | Anonim gezinme | Sorun yok | – |
| B1 | Parola saklama | Sorun yok | – |
| B2 | Başarısız giriş yanıtı | Düşük öncelikli | FIND-133 |
| B3 | Kaba kuvvet sınırlaması | Düşük öncelikli | FIND-127 |
| B4 | Varsayılan yönetici hesabı | **Gerçek sorun** | FIND-044 |
| B5 | Guest ile giriş | Sorun yok | – |
| B6 | Parola sıfırlama / değiştirme | **Gerçek sorun** (+ düşük öncelikli) | FIND-126, FIND-129 |
| C1 | `SECRET_KEY` | Sorun yok | – |
| C2 | Çerez ayarları | Düşük öncelikli | FIND-130 |
| C3 | Çıkış ve "beni hatırla" | Sorun yok | – |
| C4 | Oturum koruması | Sorun yok | – |
| D1 | CSRF koruması ve muafiyetler | Düşük öncelikli | FIND-128 |
| D2 | `next` ile yönlendirme | Sorun yok | – |
| E1 | OAuth hesap eşleme | Sorun yok | – |
| E2 | Kobo token'ı | Düşük öncelikli | FIND-131 |
| E3 | Uzaktan giriş (Magic Link) | Sorun yok | – |
| E4 | OPDS / basic auth | Sorun yok (sınırlama notu B3'te) | – |

## A. Yetki dekoratörleri

Kodda tanımlı yetki dekoratörleri:

| Dekoratör | Konum | Kontrol |
| --- | --- | --- |
| `user_login_required` | `cps/usermanagement.py:103` | Ters proxy başlığı geçerliyse o kullanıcı, değilse Flask-Login `login_required` |
| `login_required_if_no_ano` | `cps/usermanagement.py:87` | Aynısı; `config_anonbrowse == 1` ise girişsiz geçer |
| `admin_required` | `cps/admin.py:95` | `current_user.role_admin()` yoksa `abort(403)` |
| `upload_required` / `edit_required` | `cps/editbooks.py:57` / `:67` | `role_upload()` / `role_edit() or role_admin()` |
| `download_required` / `viewer_required` | `cps/web.py:126` / `:136` | `role_download()` / `role_viewer()` |

Ters proxy ile gelen kullanıcı `g.flask_httpauth_user` içine konur ve `cps/cw_login/utils.py:375` bunu `current_user` olarak döndürür. Bu yüzden rol dekoratörleri o kullanıcıya da uygulanır, atlanmaz.

### A1. Yönetici route'ları

- **Konum:** `cps/admin.py` (blueprint `admin`, 49 route)
- **Kontrol:** Her route'un dekoratörleri tek tek listelendi.
- **Gözlem:** 46 route `@user_login_required` + `@admin_required` ile korunuyor; sıra doğru (önce giriş, sonra rol). Yapılandırma, kullanıcı ekleme/silme/düzenleme, parola sıfırlama, kısıtlamalar, log indirme, güncelleme, kapatma, LDAP içe aktarma bu gruptadır. `cps/gdrive.py` içindeki yönetim route'ları (`/authenticate`, `/watch/subscribe`, `/watch/revoke`) da aynı şekilde korunuyor. Farklı korunan 3 route:

| Route | Konum | Koruma | Değerlendirme |
| --- | --- | --- | --- |
| `GET /reconnect` | `admin.py:186` | **Yok** | `-r` bayrağı veya `CALIBRE_RECONNECT` ortam değişkeniyle açılır (`cps/cli.py:77, 123`), varsayılan kapalıdır (404). Açıksa girişsiz herkes Calibre veritabanı bağlantısını yeniden kurdurabilir; veri döndürmez. |
| `POST /ajax/loaddialogtexts/<id>` | `admin.py:620` | Yalnızca giriş | Sabit, çevrilmiş onay metinleri döndürür; işlem veya hassas veri yok. |
| `POST /ajax/fullsync` | `admin.py:939` | Yalnızca giriş | Kobo senkron kayıtlarını yalnızca `current_user.id` için siler. Başka kullanıcı için olan `/ajax/fullsync/<userid>` route'unda admin şartı var. |

- **Sonuç:** Yönetici route'ları korunuyor. `/reconnect` → **Düşük öncelikli — FIND-125.** Diğer ikisi sorun değil.

### A2. Rol gerektiren işlemler

- **Konum:** `cps/editbooks.py`, `cps/web.py`, `cps/shelf.py`, `cps/kobo_auth.py`
- **Kontrol:** Yükleme, düzenleme, silme, indirme, okuma ve raf işlemlerinin rol kontrolü.
- **Gözlem:**
  - Yükleme: `upload` → `@upload_required` (`editbooks.py:108`).
  - Düzenleme: `show_edit_book`, `edit_book`, `convert_bookformat`, `edit_list_book`, `edit_selected_books`, `merge_list_book`, `archive_selected_books` vb. → `@edit_required`.
  - İndirme/gönderme: `download_link`, `send_to_ereader` → `@download_required` (`web.py:1251, 1264`). Okuma: `serve_book`, `read_book` → `@viewer_required`.
  - Silme: `delete_book` / `delete_books_ajax` yalnızca `@user_login_required` ile işaretli, ancak tek giriş noktası olan `check_delete_book` ilk satırda `current_user.role_delete_books()` kontrol ediyor (`editbooks.py:1077`).
  - Raflar: tüm değiştiren route'lar `check_shelf_edit_permissions` (`shelf.py:342`) çağırıyor: özel raf yalnızca sahibine, herkese açık raf yalnızca `role_edit_shelfs` rolüne açık.
  - Kobo token: `generate_auth_token/<user_id>` ve `deleteauthtoken/<user_id>` → `current_user.id != user_id and not role_admin()` ise 403 (`kobo_auth.py:84, 130`). Başka kullanıcının token'ına erişim (IDOR) yok.
  - Yalnızca girişle korunan okuma uçları (`/ajax/sort_value`, `/ajax/getcustomenum`, `/ajax/listbooks`) `get_filtered_book` ve benzeri, kullanıcının görünürlük kısıtlamalarını uygulayan sorgular kullanıyor.
- **Sonuç:** Sorun yok.

### A3. Dekoratörsüz yardımcılar ve iç yetki kontrolleri

- **Konum:** `cps/shelf.py:352-361`
- **Kontrol:** Yetki kararını dekoratör yerine fonksiyon içinde veren yardımcılar.
- **Gözlem:**
  ```python
  def check_shelf_view_permissions(cur_shelf):
      try:
          if cur_shelf.is_public:
              return True
          if current_user.is_anonymous or cur_shelf.user_id != current_user.id:
              return False
      except Exception as e:
          log.error(e)
      return True          # istisna olursa izin verilir
  ```
  İstisna durumunda fonksiyon `True` döndürüyor ("fail-open"). Çağıranlar `shelf and check_shelf_view_permissions(shelf)` biçiminde `None` rafı zaten eliyor. Normal akışta istisna üretecek bir yol bulunamadı.
  `pathchooser` (FIND-016) ve `do_full_kobo_sync` gibi yardımcılar yalnızca admin korumalı veya `current_user.id` ile sınırlı route'lardan çağrılıyor.
- **Sonuç:** **Düşük öncelikli — FIND-132.** Güvenli varsayılan `return False` olmalı.

### A4. Anonim gezinme (`config_anonbrowse`)

- **Konum:** `cps/usermanagement.py:87-98` ve `@login_required_if_no_ano` kullanan route'lar
- **Gözlem:** Anonim gezinme açıkken girişsiz erişilen route'lar: ana sayfa ve listeler (`web.py:809, 937-1125`), kitap ayrıntısı, kapaklar, arama (`search.py`), `basic.py`, `simpleshelf`. Kitap düzenleme, yükleme ve indirme gibi işlemler bu dekoratörün **ardından** ayrıca rol dekoratörü taşıyor. Anonim kullanıcının rolleri `Anonymous` sınıfında veritabanındaki Guest kullanıcısından yüklenir (`ub.py:297`); yani yönetici Guest'e hangi rolü verdiyse o geçerlidir. `POST /ajax/view` (`web.py:197`) anonim kullanıcı için ayarı yalnızca kendi oturum çerezine yazar (`ub.py:336-341`), veritabanını değiştirmez.
- **Not:** Goodreads açıksa, girişsiz ziyaretçi yazar sayfasını açarak dış isteği tetikleyebilir (`web.py:545-548`). Bu, zaman aşımı eksikliğiyle (FIND-014) birleşince etkisini artırır.
- **Sonuç:** Sorun yok (davranış yöneticinin bilinçli ayarına bağlı).

## B. Kimlik doğrulama ve parola

### B1. Parola saklama

- **Konum:** `cps/ub.py:685`, `cps/admin.py:2033, 2151`, `cps/web.py:1480`
- **Gözlem:** Tüm parolalar `werkzeug.security.generate_password_hash` ile saklanıyor. Kurulu Werkzeug 3.1.9'da varsayılan yöntem `scrypt`, tuz uzunluğu 16. Doğrulama `check_password_hash` ile sabit zamanlı karşılaştırma (`hmac.compare_digest`) yapıyor.
- **Sonuç:** Sorun yok.

### B2. Başarısız giriş yanıtı

- **Konum:** `cps/web.py:1449-1451`, `cps/themes/standard/templates/login.html:15`
- **Gözlem:** Kullanıcı adı yanlışken de parola yanlışken de aynı mesaj gösteriliyor ("Wrong Username or Password"); giriş formunda kullanıcı adı tahmini yok. Ancak başarısız denemeden sonra girilen parola sayfaya geri basılıyor:
  ```python
  return render_login(username, form.get("password", "")), 401
  ```
  ```html
  <input type="password" ... name="password" value="{{ password }}">
  ```
  Jinja kaçışı olduğu için XSS yok, ancak düz metin parola HTTP yanıtında ve sayfa kaynağında yer alıyor (tarayıcı önbelleği, ara vekil sunucular).
- **Sonuç:** **Düşük öncelikli — FIND-133.**

### B3. Kaba kuvvet sınırlaması

- **Konum:** `cps/web.py:1391-1392`, `cps/main.py:69`, `cps/__init__.py:115-116, 212`
- **Gözlem:** `Flask-Limiter` varsayılan olarak açık (`config_ratelimiter` varsayılanı `True`).
  - Web girişi: kullanıcı adı başına 3/dakika ve 40/gün.
  - OPDS (basic auth): kullanıcı adı başına yalnızca 3/dakika, günlük sınır yok (≈4.300 deneme/gün).
  - Sınırların anahtarı yalnızca kullanıcı adı. IP başına sınır olmadığı için tek bir IP'den çok sayıda kullanıcı adına yaygın parola denemesi (password spraying) sınırlanmıyor.
  - Başarılı girişte sınırlar sıfırlanıyor.
- **Sonuç:** **Düşük öncelikli — FIND-127.** Koruma var ama OPDS yolunda günlük sınır eksik ve IP bazlı sınır yok.

### B4. Varsayılan yönetici hesabı (FIND-044 sonuçlandırma)

- **Konum:** `cps/constants.py:140`, `cps/ub.py:677-689, 719-721`, `cps/web.py:1442`
- **Gözlem:**
  ```python
  DEFAULT_PASSWORD    = "admin123"  # nosec                 # constants.py:140
  user.name = "admin"; user.role = constants.ADMIN_USER_ROLES   # ub.py:679-681
  user.password = generate_password_hash(constants.DEFAULT_PASSWORD)
  ```
  `app.db` ilk oluşturulduğunda tam yetkili `admin` / `admin123` hesabı açılıyor. İlk girişte parola değişikliği **zorlanmıyor**: `config_is_initial` ilk başarılı girişte yalnızca `False` yapılıyor (`web.py:1442`) ve şablonda sadece giriş türü seçeneğini gizlemek için okunuyor (`config_edit.html:202`). Yöneticiyi parolayı değiştirmeye yönlendiren bir kod yolu bulunamadı. Sunucu varsayılan olarak tüm ağ arayüzlerini dinliyor (FIND-009).
- **Sonuç:** **Gerçek sorun (Orta) — FIND-044.** Yönetici parolayı değiştirmezse, ağdan erişebilen herkes herkesçe bilinen kimlik bilgileriyle tam yönetici olur. Bandit bunu upstream'deki `# nosec` yüzünden raporlamıyor.

### B5. Guest kullanıcısıyla giriş

- **Konum:** `cps/web.py:1408-1414, 1429, 1441`, `cps/usermanagement.py:37-44`
- **Gözlem:** Web girişinde ve LDAP yedek girişinde `user.name != "Guest"` şartı var. Parola sıfırlamada da Guest dışlanıyor. OPDS'de Guest yalnızca `config_anonbrowse == 1` ise kabul ediliyor. Guest'in parola özeti `''`; `check_password_hash('', x)` her zaman `False` döner.
- **Sonuç:** Sorun yok (FIND-034/041/042 yanlış pozitif kararlarıyla tutarlı).

### B6. Parola sıfırlama ve değiştirme

- **Konum:** `cps/web.py:1428-1439`, `cps/helper.py:591-605`, `cps/web.py:1478-1486`
- **Gözlem (sıfırlama):** Giriş sayfasındaki "şifremi unuttum" seçeneği yalnızca **kullanıcı adıyla** ve **girişsiz** çalışıyor:
  ```python
  if form.get('forgot', "") == 'forgot':
      if user is not None and user.name != "Guest":
          ret, __ = reset_password(user.id)            # web.py:1430
  ...
  password = generate_random_password(config.config_password_min_length)
  existing_user.password = generate_password_hash(password)   # helper.py:598-600
  send_registration_mail(existing_user.email, existing_user.name, password, True, ...)
  ```
  E-posta sunucusu ayarlıysa, kullanıcı adını bilen herhangi biri **onay bağlantısı olmadan** o kullanıcının (yönetici dahil) parolasını anında değiştirtebiliyor. Kullanıcı yeni parolayı e-postasından öğrenene kadar hesabına giremiyor. Saldırgan bunu sınır içinde tekrarlayabilir (kullanıcı adı başına 3/dakika). Yeni parola e-postayla düz metin gönderiliyor. Ayrıca mevcut ve mevcut olmayan kullanıcı adı için farklı mesajlar dönüyor ("New Password was sent…" ve "Please enter valid username…", `web.py:1432, 1438`); bu da kullanıcı adı tahminine izin veriyor.
- **Gözlem (değiştirme):** Profil sayfasında parola ve e-posta değişikliği **mevcut parola sorulmadan** yapılıyor (`web.py:1478-1486`). Ele geçirilmiş bir oturum, kalıcı hesap ele geçirmeye dönüşebilir: e-postayı değiştir, sonra "şifremi unuttum" ile yeni parolayı kendine gönder.
- **Sonuç:** Sıfırlama akışı **Gerçek sorun (Orta) — FIND-126.** Değiştirme akışı **Düşük öncelikli — FIND-129.**

## C. Oturum

### C1. `SECRET_KEY`

- **Konum:** `cps/__init__.py:192`, `cps/config_sql.py:574-580`
- **Gözlem:** `SECRET_KEY` ortam değişkeni verilmemişse, ilk çalıştırmada `os.urandom(32)` ile üretilip `app.db` içindeki ayarlar tablosunda saklanıyor; kodda sabit bir anahtar yok. `app.db` dosyasını okuyabilen biri oturum çerezi üretebilir. Bu, dosya sistemi erişimi gerektirdiği için kabul edilebilir bir tasarım.
- **Sonuç:** Sorun yok.

### C2. Çerez ayarları

- **Konum:** `cps/__init__.py:88-95`, `cps/cw_login/config.py:7, 10`
- **Gözlem:** `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE='Lax'`, `REMEMBER_COOKIE_SAMESITE='Strict'`. `SESSION_COOKIE_SECURE` ve `REMEMBER_COOKIE_SECURE` ayarlanmıyor (Flask ve gömülü Flask-Login varsayılanı `False`). Uygulama HTTPS arkasında çalışsa bile çerezler `Secure` bayrağı olmadan gönderiliyor. "Beni hatırla" çerezinin süresi 365 gün. Ayrıca `WTF_CSRF_SSL_STRICT=False` ile HTTPS'te Referer kontrolü kapatılmış; CSRF token'ı yine zorunlu olduğu için etkisi küçük.
- **Sonuç:** **Düşük öncelikli — FIND-130.** Etki, kurulumun HTTPS ve ters proxy yapılandırmasına bağlı.

### C3. Çıkış ve "beni hatırla"

- **Konum:** `cps/web.py:1456-1465`, `cps/ub.py:94`, `cps/usermanagement.py:155-161`
- **Gözlem:** Çıkışta sunucu tarafındaki oturum kaydı siliniyor (`ub.delete_user_session`) ve `logout_user()` "beni hatırla" çerezini temizliyor. `load_user`, `User_Sessions` tablosunda kaydı olmayan oturum anahtarını reddediyor. Bu sayede çıkış yapılan oturum çerezi tekrar kullanılamaz.
- **Sonuç:** Sorun yok.

### C4. Oturum koruması

- **Konum:** `cps/__init__.py:158`, `cps/config_sql.py:177`
- **Gözlem:** `lm.session_protection = 'strong' if config.config_session == 1 else "basic"`; `config_session` varsayılanı `1`, yani `strong` (IP/User-Agent özeti değişirse oturum düşürülür).
- **Sonuç:** Sorun yok.

## D. CSRF ve yönlendirme

### D1. CSRF koruması

- **Konum:** `cps/__init__.py:104, 129-130`, `cps/kobo.py` (12 `@csrf.exempt`), `cps/gdrive.py:121`, `cps/oauth_bb.py:191-193, 353, 377`, `cps/kobo_auth.py:81`, `cps/web.py:1456`
- **Gözlem:** `CSRFProtect` tüm uygulamaya uygulanıyor; POST uçları token istiyor. Muafiyetler gerekçeli: Kobo cihaz API'si (çerez değil, URL'deki token ile kimlik doğrulama) ve Google Drive bildirim geri çağrısı (sunucudan sunucuya). Ancak bazı **GET** uçları durum değiştiriyor ve CSRF token'ı gerektirmiyor:
  - `GET /unlink/github`, `GET /unlink/google`: OAuth bağlantısını siliyor. Yapılmak istenen Referer kontrolü etkisiz (`oauth_bb.py:192-193`: `if ... != request.referrer: pass`).
  - `GET /kobo_auth/generate_auth_token/<id>`: token oluşturuyor ve KEPUB dönüştürücü ayarlıysa tüm EPUB kitapları için dönüştürme görevi başlatıyor.
  - `GET /logout`: oturumu kapatıyor.

  Başka bir sitedeki `<img src=...>` ile oturum açık kullanıcıya bu işlemler yaptırılabilir. Etki, hesap bağlantısının silinmesi, istenmeyen çıkış veya yük oluşturma ile sınırlı; veri sızmıyor.
- **Sonuç:** **Düşük öncelikli — FIND-128.**
- **4. kişiye not:** `gdrive.py:123-125` geri çağrısı yalnızca sabit `X-Goog-Channel-Token: target=calibreweb-watch_files` değerini kontrol ediyor (`gdrive.py:48`, `# nosec`). Kaynak kod açık olduğu için bu değer gizli değil. Etkisi Drive değişiklik sorgusu tetiklemekle sınırlı; dosya işleme alanında değerlendirilmesi önerilir.

### D2. `next` ile yönlendirme

- **Konum:** `cps/redirect.py:47-52`, `cps/web.py:1363, 1464`, `cps/editbooks.py:1073, 1086`
- **Gözlem:**
  ```python
  target = next or url_for(endpoint, **values)
  adapter = current_app.url_map.bind(urlparse(request.host_url).netloc)
  if not len(adapter.allowed_methods(remove_prefix(target, ...))):
      target = url_for(endpoint, **values)
  ```
  Hedef, yalnızca uygulamanın kendi route haritasında eşleşen bir yol ise kabul ediliyor. Tam URL (`https://evil.com/...`), protokolsüz URL (`//evil.com/...`) ve ters eğik çizgili biçimler eşleşmediği için varsayılan sayfaya düşülüyor. Bu, Werkzeug `Map.allowed_methods` ile ayrıca denendi; uygulama çalıştırılmadı. Kodda tanımlı `is_safe_url` kullanılmıyor (ölü kod).
- **Sonuç:** Sorun yok (açık yönlendirme yok).

## E. Diğer giriş yolları

### E1. OAuth (GitHub/Google) eşleme

- **Konum:** `cps/oauth_bb.py:101-166`
- **Gözlem:** Dış hesap, sağlayıcının değişmez kullanıcı kimliği (`provider_user_id`) ile eşleniyor; e-posta ile otomatik eşleme yok. Başka kullanıcıya bağlı bir dış hesabı oturum açık bir kullanıcı kendine bağlayamıyor (`oauth_bb.py:139-144`). Bağlanmamış dış hesapla giriş reddediliyor; otomatik kayıt yok.
- **Sonuç:** Sorun yok.

### E2. Kobo senkronizasyon token'ı

- **Konum:** `cps/kobo_auth.py:97-110, 155-172`, `cps/kobo.py:61`
- **Gözlem:** Token `hexlify(os.urandom(16))` ile (128 bit) üretiliyor. Bu iyi, ancak:
  - Süresi yok (`expiration = datetime.max`).
  - URL yolunda taşınıyor (`/kobo/<auth_token>/...`); bu yüzden sunucu, vekil sunucu ve erişim loglarına düşüyor.
  - Veritabanında düz metin saklanıyor.
  - Token ile gelen istekte `login_user(user)` çağrılıyor ve kullanıcının tam oturumu açılıyor.

  Kobo protokolü cihazın token'ı URL'de taşımasını gerektirdiği için tasarımdan kaynaklanan bir durum. Kobo blueprint'i IP başına 3/dakika ile sınırlı (`main.py:80`).
- **Sonuç:** **Düşük öncelikli — FIND-131.**

### E3. Uzaktan giriş (Magic Link)

- **Konum:** `cps/remotelogin.py:62-150`, `cps/ub.py:540-543`
- **Gözlem:**
  - Özellik `config_remote_login` ile açılıyor, varsayılan kapalı.
  - Token 128 bit rastgele ve 10 dakika geçerli; süresi dolan token siliniyor.
  - Onay (`/verify/<token>`) oturum açık kullanıcı ve POST + CSRF ile yapılıyor.
  - Cihaz tarafı oturumu açtıktan sonra token siliniyor, yani tek kullanımlık.
  - Küçük not: token sorgularında `token_type` filtresi yok, Kobo token'ları (tür 1) da bu tabloda. Ancak Kobo token'ı bilinmeden bundan yararlanılamaz.
- **Sonuç:** Sorun yok.

### E4. OPDS / basic auth

- **Konum:** `cps/usermanagement.py:37-58, 61-84`, `cps/opds.py` (36 route `@requires_basic_auth_if_no_ano`)
- **Gözlem:** OPDS, HTTP Basic ile `verify_password` üzerinden doğrulanıyor (parola özeti veya LDAP). Anonim gezinme kapalıysa kimlik bilgisi zorunlu. Basic auth parolayı her istekte gönderdiği için HTTPS gerekir; bu bir kurulum konusu. Sınırlama farkı B3'te (FIND-127).
- **Sonuç:** Sorun yok.

## Bandit bulgularıyla ilişki

- **B105 / B107 (FIND-034, 038–043):** Yetki bağlamında yeniden bakıldı. Boş `''` parola değerleri giriş yolu açmıyor (B5); `render_login` varsayılanları sabit kimlik bilgisi değil. `review-bandit.md`'deki yanlış pozitif kararları geçerli.
- **FIND-035/036 (`kobo.py`):** Herkese açık URL sabitleri; yetkiyle ilgisi yok.
- **FIND-014 (goodreads zaman aşımı):** Anonim gezinme açıkken girişsiz ziyaretçi de yazar sayfasından tetikleyebiliyor (A4). Bu, B113 düzeltmesinin önceliğini destekler.
- **FIND-009 (0.0.0.0):** FIND-044 ile birlikte risk oluşturuyor (B4).

## Düzeltme önerileri

1 Kasım toplantısında seçim için; hepsi küçük ve davranışı koruyan değişiklikler:

| FIND | Öneri | Boyut |
| --- | --- | --- |
| FIND-132 | `check_shelf_view_permissions` içinde `except` sonrası `return False` | 1 satır |
| FIND-133 | `render_login(username, "")`: başarısız girişte parolayı forma geri basmamak | 1 satır |
| FIND-128 | `unlink_oauth` içindeki etkisiz Referer kontrolünü `abort(403)` yapmak ya da unlink route'larını POST'a çevirmek (şablon değişikliği gerekir) | 1–3 satır |
| FIND-126 | Var olan/olmayan kullanıcı için aynı mesajı göstermek (kullanıcı adı tahminini kapatır). Asıl çözüm (onay bağlantılı sıfırlama) büyük bir değişiklik, kapsam dışı. | 2 satır |
| FIND-127 | OPDS sınırlamasına `40/day` eklemek (`main.py:69`) | 1 satır |
| FIND-044 | İlk girişte parola değiştirmeye zorlamak davranış değişikliği ve küçük değil; rapora risk ve kurulum önerisi olarak yazılması önerilir | – |
