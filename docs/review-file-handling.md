# Dosya işleme ve harici süreç incelemesi (4. kişi — Hasan Kurt)

İncelenen commit: `6e840acbda8d62fdd159bf3855c01872d629a914` (`docs/baseline-commit.txt`)
Tarih: 28 Ekim 2026
Yöntem: kod okuma; uygulama çalıştırılmadı (K2). İki noktada uygulama dışı, yalıtılmış kütüphane davranışı doğrulandı: `nh3.clean()` (A7) ve standart kütüphane `urllib.request.urlopen()` (E4). Bu çağrılar Calibre-Web kodunu çalıştırmaz, yalnızca kodun dayandığı kütüphanenin davranışını gösterir.
Rehber: `docs/guides/rol-4-dosya-surec.md`. Satır numaraları baseline commit'e aittir.

## Özet

- İncelenen kontrol noktası: 22 (A 7, B 5, C 3, D 4, E 3) ve 1 bağlam notu (E5, B113)
- Gerçek sorun: 3 · Düşük öncelikli: 7 · Sorun yok: 12
- Kayda eklenen bulgular: FIND-150 … FIND-158 (`kaynak = Manuel`)

| ID | Konum | Konu | Sonuç | Ekip önemi |
| --- | --- | --- | --- | --- |
| FIND-150 | `cps/web.py:1265` | `/send/` route'u içerik kısıtlamalarını uygulamıyor | Gerçek sorun | Orta |
| FIND-151 | `cps/editbooks.py:57-64, 105-108` | Global "yüklemeye izin ver" ayarı sunucu tarafında uygulanmıyor | Gerçek sorun | Düşük |
| FIND-152 | `cps/tasks/thumbnail.py:380-386` | Google Drive'da seri küçük resmi `urlopen(bytes)` ile her zaman hata veriyor | Gerçek sorun (işlev) | Düşük |
| FIND-153 | `cps/uploader.py:282-285` | Geçici yükleme dosyası adı yalnızca dosya adının MD5'i | Düşük öncelikli | Düşük |
| FIND-154 | `cps/comic.py:80`, `cps/epub.py:46`, `cps/helper.py:832-834` | Arşiv üyesi ve URL'den kapak okumada boyut sınırı yok | Düşük öncelikli | Düşük |
| FIND-155 | `cps/helper.py:1119-1128` | `Content-Disposition` içinde `"` kaçışlanmıyor | Düşük öncelikli | Düşük |
| FIND-156 | `cps/clean_html.py:44-46` | Yorum HTML'inde `style` ve dış `img src` serbest | Düşük öncelikli | Düşük |
| FIND-157 | `cps/updater.py:82-91` | Güncelleme paketi için imza/özet doğrulaması yok | Düşük öncelikli | Düşük |
| FIND-158 | `cps/subproc_wrapper.py:28-32` | Windows'ta çalıştırılabilir dosya yolu (0. eleman) tırnaklanmıyor | Düşük öncelikli | Düşük |

## A. Yükleme

Akış: `POST /upload` (`cps/editbooks.py:105`) → `file_handling_on_upload()` (`:971`) → `uploader.upload()` (`cps/uploader.py:277`) → `process()` → `helper.update_dir_structure()` (`cps/helper.py:695`).

### A1. Dosya adı temizleme
- **Konum:** `cps/uploader.py:280-285`
- **Kontrol:** Kullanıcının verdiği dosya adı diske yazılan yola giriyor mu?
- **Gözlem:**
  ```python
  filename = uploadfile.filename
  filename_root, file_extension = os.path.splitext(filename)
  md5 = hashlib.md5(filename.encode('utf-8')).hexdigest()  # nosec
  tmp_file_path = os.path.join(tmp_dir, md5)
  ```
  Geçici dosyanın adı, dosya adının 32 karakterlik onaltılık MD5 özetidir. Kullanıcı adı yola girmez. `filename_root` yalnızca başlık için meta veri olarak kullanılır. Kalıcı yol `update_dir_structure_file()` içinde başlık ve yazardan `get_valid_filename()` ile kurulur (bkz. B1).
- **Sonuç:** Sorun yok. `../` içeren bir dosya adı geçici yola giremez.

### A2. Uzantı ve MIME kontrolü
- **Konum:** `cps/editbooks.py:971-990`, `cps/file_helper.py:63-88`
- **Kontrol:** Uzantı ve MIME nerede kontrol ediliyor, liste kimin ayarına bağlı?
- **Gözlem:**
  - Uzantı listesi `config.config_upload_formats` ayarından gelir. Varsayılanı `constants.EXTENSIONS_UPLOAD` (`cps/constants.py:155`, `cps/config_sql.py:150`). Yalnızca yönetici değiştirebilir (`cps/admin.py:1840-1843`, `/admin/ajaxconfig`, `@admin_required`).
  - `config_check_extensions` açıksa (varsayılan `True`, `config_sql.py:181`) `validate_mime_type()` python-magic ile içerik tipini kontrol eder.
  - Ardından uzantı ayrıca kontrol edilir (`editbooks.py:981-985`). Uzantısız dosya reddedilir.
  - `validate_mime_type()`, içinde `mimetype` girdisi olan her zip dosyasını kabul eder (`file_helper.py:79-84`). Ama uzantı kontrolü ayrıca çalıştığı için bu tek başına izin verilmeyen bir uzantının yüklenmesini sağlamaz.
- **Sonuç:** Sorun yok. Kontrol, yönetici ayarına bağlı iki katmandan oluşuyor.

### A3. Global yükleme ayarı ile yükleme rolü
- **Konum:** `cps/editbooks.py:57-64` (`upload_required`), `cps/editbooks.py:105-108`, `cps/admin.py:122`, `cps/themes/standard/templates/layout.html:55`
- **Kontrol:** "Yüklemeye izin ver" yönetici ayarı (`config_uploading`) sunucu tarafında uygulanıyor mu?
- **Gözlem:**
  ```python
  def upload_required(f):
      @wraps(f)
      def inner(*args, **kwargs):
          if current_user.role_upload():
              return f(*args, **kwargs)
          abort(403)
  ```
  - `config_uploading` kodda yalnızca `g.allow_upload = config.config_uploading` (`admin.py:122`) olarak kullanılıyor. Bu değeri sadece şablonlar okuyor (`{% if current_user.role_upload() and g.allow_upload %}`).
  - `/upload` route'u ve aynı route'tan çağrılan `upload_book_formats()` (`editbooks.py:1459`) yalnızca kullanıcı rolüne bakar.
  - Kodda `config_uploading` geçen başka bir yer yok (`grep -rn config_uploading cps/`).
  - Sonuç: Yönetici yüklemeyi global olarak kapatsa bile, yükleme rolü olan bir kullanıcı `POST /upload` isteğini doğrudan göndererek dosya yükleyebilir. Bunun için kullanıcının yükleme rolüne sahip olması (yönetici tarafından verilmiş olması) ve CSRF belirtecini taşıyan oturumlu bir istek göndermesi gerekir.
- **Sonuç:** Gerçek sorun (düşük etki). Yönetici ayarı yalnızca arayüzde uygulanıyor. — **FIND-151**

### A4. Dosya boyutu sınırı
- **Konum:** `cps/server.py:250-253`. Flask tarafında `MAX_CONTENT_LENGTH` yok (`grep -rn MAX_CONTENT_LENGTH cps/`).
- **Kontrol:** Yüklenen dosya için boyut sınırı var mı?
- **Gözlem:**
  - Tornado sunucusu `max_buffer_size=209700000` (yaklaşık 200 MB) ile başlatılıyor.
  - Gevent yolunda (`server.py:226`) ve Flask'ta (`MAX_CONTENT_LENGTH`) bir sınır bulunamadı.
  - Yükleme yalnızca yükleme rolü olan oturumlu kullanıcılara açık.
- **Sonuç:** Düşük öncelikli. Sınır sunucu türüne bağlı, uygulama düzeyinde yok. Asıl risk arşiv içeriğinin belleğe okunması (C2). — **FIND-154** ile birlikte

### A5. Geçici dosyalar
- **Konum:** `cps/file_helper.py:47-55`, `cps/uploader.py:282-285`
- **Kontrol:** Geçici dosyalar nerede oluşuyor, adları tahmin edilebilir mi, siliniyor mu?
- **Gözlem:**
  - Geçici dizin `gettempdir()/calibre_web/instance_<md5(kitaplık|port)[:12]>` olarak oluşturuluyor (`os.makedirs`, izin belirtilmemiş).
  - Dosya adı yalnızca dosya adının MD5'i, kullanıcıya veya isteğe özgü bir bileşen yok. Aynı anda aynı dosya adıyla yükleme yapan iki kullanıcının geçici dosyaları aynı yola yazılır.
  - Ad tahmin edilebilir. Ancak dizin sistem geçici dizininde ve uygulama kullanıcısına ait. Çok kullanıcılı bir sunucuda yerel bir saldırganın dizini önceden oluşturması teorik bir senaryo.
  - Dosya, kalıcı yere `move_files_on_change()` ile taşınıyor. Hata durumunda geçici dosyanın silindiğine dair bir yol görmedim.
- **Sonuç:** Düşük öncelikli. Eşzamanlı aynı adlı yüklemelerde çakışma olabilir. Önerilen düzeltme: adın sonuna `uuid4()` eklemek. — **FIND-153**

### A6. URL'den kapak indirme (SSRF)
- **Konum:** `cps/helper.py:828-853`, çağıran `cps/editbooks.py:694` (`do_edit_book`, düzenleme rolü)
- **Kontrol:** URL'den kapak indirmede SSRF koruması (`cw_advocate`) kullanılıyor mu?
- **Gözlem:**
  ```python
  if cli_param.allow_localhost:
      img = requests.get(url, timeout=(10, 200), allow_redirects=False)
  elif use_advocate:
      img = cw_advocate.get(url, timeout=(10, 200), allow_redirects=False)
  ```
  - Varsayılan yol `cw_advocate`. Bu kütüphane yerel ve özel adresleri engeller ve `UnacceptableAddressException` ile reddeder. Yönlendirme kapalı (`allow_redirects=False`), zaman aşımı tanımlı.
  - Yerel ağa erişim yalnızca sunucu başlatılırken verilen `-l` komut satırı parametresiyle (`cli_param.allow_localhost`) açılabilir. Bu bir işletmeci kararı.
  - İçerik tipi `save_cover()` (`helper.py:883-905`) içinde resim türleriyle sınırlanıyor.
  - Yanıt gövdesi `img.content` ile tamamen belleğe alınıyor, boyut sınırı yok.
  - `cps/cw_advocate/` gömülü üçüncü taraf kod (K7). Yalnızca kullanım şekli incelendi.
- **Sonuç:** Sorun yok (SSRF). Boyut sınırı eksikliği **FIND-154** içinde.

### A7. Yorum alanının HTML temizliği (FIND-002…005 ile ilişkili)
- **Konum:** `cps/clean_html.py:40-46, 53-66`. Çağıran `editbooks.py:1281-1285` (`edit_book_comments`). Çıktıda şablonlar ayrıca `|clean_string|safe` uyguluyor (`themes/standard/templates/detail.html:290`).
- **Kontrol:** `review-bandit.md` tarafından bırakılan soru: nh3'ün izin verdiği etiketler ve öznitelikler yeterli mi?
- **Gözlem:** İzin listesi nh3 varsayılanlarına `p, span, div, pre, br, h1-h6, img` etiketlerini, tüm etiketler için `class, style` özniteliklerini, `a` için `href, title, rel` ve `img` için `src, alt, title, width, height` özniteliklerini ekliyor. Aynı ayarlarla `nh3 0.3.7` üzerinde yalıtılmış deneme yapıldı:

  | Girdi | Çıktı |
  | --- | --- |
  | `<script>alert(1)</script>x` | `x` |
  | `<img src=x onerror=alert(1)>` | `<img src="x">` |
  | `<a href="javascript:alert(1)">a</a>` | `<a>a</a>` |
  | `<img src="data:image/svg+xml;base64,...">` | `<img>` |
  | `<svg onload=...>`, `<iframe ...>` | boş |
  | `<img src="https://tracker.example/p.gif">` | değişmeden geçer |
  | `<div style="position:fixed;...;width:100%;height:100%">` | değişmeden geçer |

  Betik çalıştırma yolları (olay öznitelikleri, `javascript:` ve `data:` URL'leri, `script`, `svg`, `iframe`) temizleniyor. Bu, FIND-002…005'teki "yanlış pozitif" kararını destekliyor. Ancak `style` özniteliği içerik olarak denetlenmiyor ve dış `img src` adresine izin veriliyor. Yorumu düzenleyebilen bir kullanıcı (düzenleme veya yükleme rolü, yükleme sırasında e-kitap meta verisi de olabilir) sayfanın üstünü kaplayan bir katman (UI redress) veya görüntüleyenin IP adresini dış sunucuya bildiren bir takip pikseli ekleyebilir.
- **Sonuç:** Düşük öncelikli. XSS yok, ama arayüz manipülasyonu ve gizlilik riski var. FIND-002…005 kararları değişmiyor. — **FIND-156**

## B. Yol işlemleri ve indirme

### B1. Kitap dizin yollarının kurulması
- **Konum:** `cps/helper.py:243-263` (`get_valid_filename`), `cps/helper.py:451-486` (`update_dir_structure_file`)
- **Kontrol:** Yazar veya başlık gibi kullanıcı verisi yola girerken temizleniyor mu?
- **Gözlem:**
  ```python
  if value[-1:] == '.':
      value = value[:-1]+'_'
  value = value.replace("/", "_").replace(":", "_").strip('\0')
  ...
  if replace_whitespace:
      value = re.sub(r'[*+:\\\"/<>?]+', '_', value, flags=re.U)
  ```
  - Yol için yapılan çağrılar (`chars=96` ve `chars=42`) varsayılan `replace_whitespace=True` ile yapılıyor. Böylece `/`, `\`, `:`, `"`, `<`, `>`, `?`, `*` ve `+` karakterleri `_` ile değiştiriliyor.
  - Sondaki nokta `_` ile değiştirildiği için `.` ve `..` adları oluşamıyor (`..` → `._`).
  - Dizin adı `<başlık> (<book_id>)` biçiminde kuruluyor.
- **Sonuç:** Sorun yok. Kullanıcı verisi yol ayıracı veya üst dizin bileşeni üretemiyor.

### B2. İndirmede yol kaynağı ve path traversal
- **Konum:** `cps/web.py:1247-1258`, `cps/helper.py:1106-1132` (`get_download_link`), `cps/helper.py:921-989` (`do_download_file`)
- **Kontrol:** Yol veritabanından mı, istekten mi geliyor? `send_from_directory` dizin dışına çıkmayı engelliyor mu?
- **Gözlem:**
  - İstekten yalnızca `book_id` (int dönüştürücü) ve `book_format` alınıyor.
  - `book_format.split(".")[0]` ile noktadan sonrası atılıyor. Ardından `calibre_db.get_book_format(book.id, book_format.upper())` ile veritabanında o biçim aranıyor, bulunamazsa 404 dönüyor.
  - Dizin `config.get_book_path()` ve `book.path` (veritabanı), dosya adı `data.name` (veritabanı) ve uzantıdan oluşuyor.
  - Gönderim `send_from_directory()` ile yapılıyor. Werkzeug `safe_join` kullandığı için dizin dışına çıkan yollar reddediliyor.
  - Flask'ın varsayılan `<book_format>` dönüştürücüsü `/` karakterini kabul etmiyor.
- **Sonuç:** Sorun yok. Path traversal için kullanıcı kontrollü bir yol bileşeni yok.

### B3. İndirme ve gönderme route'larında yetki (Emre'nin A maddesiyle çapraz kontrol)
- **Konum:** `cps/web.py:1247-1251` (`download_link`), `cps/opds.py:438-444` (`opds_download_link`), `cps/web.py:1261-1272` (`send_to_ereader`), `cps/helper.py:218-220` (`send_mail`), `cps/db.py:728-733`
- **Kontrol:** İndirme ve gönderme route'ları rol kontrolü ve kullanıcının içerik kısıtlamalarını (`common_filters`: izinli/yasak etiketler, dil, kısıtlı özel sütun, arşiv) uyguluyor mu?
- **Gözlem:**
  - `download_link`: `@login_required_if_no_ano` + `@download_required`. Kitap `get_filtered_book(book_id, allow_show_archived=True)` ile alınıyor, kısıtlamalar uygulanıyor.
  - `opds_download_link`: Basic Auth + `role_download()` kontrolü. Aynı `get_download_link()` kullanılıyor. `current_user`, Basic Auth kullanıcısına çözülüyor (`cps/cw_login/utils.py:375-377`).
  - `send_to_ereader` ise filtresiz `get_book()` kullanıyor:
    ```python
    @web.route('/send/<int:book_id>/<book_format>/<int:convert>', methods=["POST"])
    @login_required_if_no_ano
    @download_required
    def send_to_ereader(book_id, book_format, convert):
        book = calibre_db.get_book(book_id)          # web.py:1265, filtre yok
    ```
    ```python
    def get_book(self, book_id):                     # db.py:728
        return self.session.query(Books).filter(Books.id == book_id).first()
    ```
    `send_mail()` de kitabı yine `get_book()` ile alıyor (`helper.py:220`). Kullanıcı e-okuyucu adresini kendi profilinden belirleyebiliyor (`web.py:1481-1482`).
  - Senaryo: Yönetici bir kullanıcıya etiket, dil veya özel sütun kısıtlaması koyuyor. Kullanıcı o kitabı listede ve indirmede göremiyor (`get_filtered_book` 404 dönüyor). Ama `POST /send/<id>/epub/0` ile kitap kimliğini tahmin ederek kısıtlı kitabı kendi belirlediği e-posta adresine gönderebiliyor. Kitap kimlikleri ardışık tam sayılar.
  - Yan gözlem: Kitabın hiç dosyası yoksa `check_send_to_ereader()` `None` döndürüyor (`helper.py:197-199`). `web.py:1267`'deki `any(... for option in allowed_formats)` bu durumda `TypeError` (500) verir.
- **Sonuç:** İndirme route'larında sorun yok. `/send/` route'unda **gerçek sorun**: içerik kısıtlaması atlanabiliyor. Önerilen küçük düzeltme: `web.py:1265` satırında `get_filtered_book(book_id, allow_show_archived=True)` kullanmak. — **FIND-150** (yetki alanıyla kesiştiği için Emre Bulut'a bildirilecek)

### B4. İndirme yanıtındaki `Content-Disposition` başlığı
- **Konum:** `cps/helper.py:1115-1128`
- **Kontrol:** İndirme dosya adı başlığa güvenli biçimde yazılıyor mu?
- **Gözlem:**
  ```python
  file_name = get_valid_filename(file_name, replace_whitespace=False, force_unidecode=True)
  ...
  headers["Content-Disposition"] = ('attachment; filename="{}.{}"; filename*=UTF-8\'\'{}.{}').format(
      file_name, book_format, quoted_file_name, book_format)
  ```
  - `replace_whitespace=False` olduğu için `"` karakteri temizlenmiyor. Başlık ve yazar adı (düzenleme rolüyle değiştirilebilir) içinde `"` olursa `filename="..."` parametresi erken kapanır.
  - Satır sonu karakterleri Werkzeug `Headers` tarafından reddedildiği için başlık enjeksiyonu (CRLF) mümkün görünmüyor. Etki, tarayıcıda yanlış veya kesik dosya adı ile sınırlı.
  - `filename*` kısmı `quote()` ile kodlandığı için güvenli, modern tarayıcılar bunu tercih eder.
- **Sonuç:** Düşük öncelikli. — **FIND-155**

### B5. Yönetici yol seçici (`pathchooser`, FIND-016)
- **Konum:** `cps/admin.py:952-956`, `cps/admin.py:1034-1110`
- **Kontrol:** Hangi dizinleri listeleyebiliyor, kim erişebiliyor?
- **Gözlem:**
  - Route `@user_login_required` + `@admin_required` ile korunuyor.
  - `path` parametresi `os.path.realpath()` ile çözülüyor ve tüm dosya sistemi listelenebiliyor. Bu, yöneticinin kitaplık ve ikili dosya yolunu seçmesi için tasarlanmış bir davranış.
  - Dosya adları `Markup.escape()` ile kaçışlanıyor.
  - `before_request` (`admin.py:125-136`), veritabanı yapılandırılmamışken bu route'a izin veriyor, ama route'un kendi dekoratörleri yine de giriş ve yönetici yetkisi istiyor.
- **Sonuç:** Sorun yok. Yalnızca yöneticinin erişebildiği, tasarıma uygun bir işlev. FIND-016'nın "Düşük öncelikli / Kabul edildi" kararıyla uyumlu.

## C. Arşivler ve dönüştürme

### C1. Arşiv üye adları (zip slip)
- **Konum:** `cps/comic.py:71-116`, `cps/epub.py:33-47`
- **Kontrol:** Zip/rar/tar/7z açılırken üye adları diske yazılan bir yola giriyor mu?
- **Gözlem:**
  - Kullanıcının yüklediği arşivlerde üyeler `cf.read(name)` veya `extractfile(name).read()` ile yalnızca belleğe okunuyor. `extract()` veya `extractall()` çağrılmıyor.
  - EPUB kapağında geçici ad `prefix + '.' + os.path.basename(zip_cover_path)` biçiminde kuruluyor (`epub.py:39-40`). `basename` kullanıldığı için `../` içeren üye adı dizin dışına çıkamıyor.
  - `extractall()` yalnızca güncelleyicide kullanılıyor (E1).
- **Sonuç:** Sorun yok.

### C2. Büyük ve iç içe arşivler (arşiv bombası)
- **Konum:** `cps/comic.py:80, 89, 100, 112`, `cps/epub.py:46`, `cps/file_helper.py:74, 81`
- **Kontrol:** Sıkıştırılmış verinin açılmış boyutuna sınır var mı?
- **Gözlem:**
  - Kapak adayı olan üye, açılmış boyutu kontrol edilmeden tamamen belleğe okunuyor (`cf.read(name)`).
  - `validate_mime_type()` de dosyanın tamamını `file_buffer.read()` ile belleğe alıyor.
  - Küçük boyutlu ama açıldığında çok büyük bir `cover.jpg` üyesi içeren bir CBZ, bellek tüketimine yol açabilir.
  - Yükleme rolü gerekli. Tek seferlik okuma yapılıyor, iç içe açma yok.
- **Sonuç:** Düşük öncelikli. Önerilen düzeltme: `ZipInfo.file_size` için bir üst sınır kontrolü. — **FIND-154**

### C3. Dönüştürme argümanları
- **Konum:** `cps/editbooks.py:176-215` (`convert_bookformat`), `cps/helper.py:84-118`, `cps/tasks/convert.py:224-330`
- **Kontrol:** Harici programa hangi argümanlar veriliyor, kullanıcı verisi giriyor mu?
- **Gözlem:**
  - Kaynak ve hedef biçim `constants.EXTENSIONS_CONVERT_FROM` ve `EXTENSIONS_CONVERT_TO` beyaz listeleriyle kontrol ediliyor (`editbooks.py:188-202`). Route düzenleme rolü gerektiriyor.
  - Komut şu parçalardan oluşuyor: `config.config_converterpath` (yönetici), `file_path + format` (B1'de temizlenmiş veritabanı yolu), `--from-opf <uuid4 geçici dosya>`, `--cover <kitap dizini>/cover.jpg` ve `config.config_calibre` içindeki ek parametreler (yönetici, `convert.py:311-322`).
  - Kullanıcıdan gelen serbest bir metin argüman olarak geçmiyor.
- **Sonuç:** Sorun yok.

## D. Harici süreçler

### D1. `subprocess` kullanımı ve `shell=True`
- **Konum:** `cps/subproc_wrapper.py:24-36`. Tüm çağrılar bu dosyadan geçiyor: `tasks/convert.py:238, 281, 323`, `embed_helper.py:43`, `converter.py:42`, `config_sql.py:513`, `helper.py:1020, 1046`.
- **Kontrol:** Liste argümanı kullanılıyor mu, `shell=True` var mı?
- **Gözlem:** Tek `Popen` çağrısı `shell=False`. Linux ve macOS'ta argümanlar liste olarak geçiyor (`exc_command = [x for x in command]`). Projede başka bir `subprocess` çağrısı yok (gömülü kod hariç).
- **Sonuç:** Sorun yok. B404 ve B603 uyarıları (FIND-028 dahil) bu bağlamda yanlış pozitif kararını destekliyor.

### D2. Windows dalında komutun tek string'e birleştirilmesi (FIND-028 notu)
- **Konum:** `cps/subproc_wrapper.py:28-32`
- **Kontrol:** Tırnaklama; boşluk, `"` ve `&` içeren adlarda doğru mu, kullanıcı kontrollü bir değer bu string'e giriyor mu?
- **Gözlem:**
  ```python
  if os.name == 'nt':
      for key, element in enumerate(command):
          if key in quotes:
              command[key] = '"' + element + '"'
      exc_command = " ".join(command)
  ```
  1. **Kabuk yok:** `shell=False` ile Windows'ta string doğrudan `CreateProcess`'e gidiyor, `cmd.exe` araya girmiyor. Bu yüzden `&`, `|`, `>` gibi karakterler komut ayırıcı olarak yorumlanmıyor, komut enjeksiyonu yok.
  2. **İç `"` kaçışlanmıyor:** Tırnaklanan elemanın içinde `"` olsaydı hedef programın argüman ayrıştırması kayardı. Ama tırnaklanan elemanlar dosya yolları. Calibre-Web kendi oluşturduğu yollarda `"` karakterini temizliyor (B1). Ayrıca Windows dosya adlarında `"` zaten yasak. Kalan tırnaklı değerler yönetici ayarları (`config_calibre` parametreleri, kitaplık yolu).
  3. **Boşluklar:** Tırnak listeleri (`quotes`) dosya yolu elemanlarını kapsıyor: `convert.py:235` için `[1, 3]`, `convert.py:299-308` için `[1, 2, 4, 6]`, `convert.py:269` için `[5]` ve `embed_helper.py:31` için `[5, 7]`. Boşluklu dosya yolları doğru tırnaklanıyor.
  4. **0. eleman tırnaklanmıyor:** Hiçbir `quotes` listesi 0. indeksi içermiyor. Çalıştırılabilir dosya yolu (örn. varsayılan Calibre kurulumu `C:\Program Files\Calibre2\ebook-convert.exe`) boşluk içerdiğinde `CreateProcess` önce `C:\Program.exe` dosyasını dener. Bu, bilinen "tırnaksız arama yolu" (CWE-428) durumudur. Sömürülmesi için saldırganın `C:\` köküne yazabilmesi gerekir, bu da genelde yönetici hakkı ister. Yalnızca Windows'u etkiliyor.
  5. **Kullanıcı kontrolü:** Argümanların hiçbiri normal kullanıcıdan gelen serbest metin değil (bkz. C3, D3).
- **Sonuç:** FIND-028 notu sonuçlandı. Komut veya argüman enjeksiyonu yok, FIND-028'in "yanlış pozitif" kararı geçerli. Tek zayıflık Windows'ta 0. elemanın tırnaklanmaması, düşük öncelikli. Önerilen düzeltme: Windows dalında `subprocess.list2cmdline()` kullanmak ya da listeyi doğrudan `Popen`'e vermek (iç `"` kaçışını da çözer). — **FIND-158**

### D3. Harici program yollarını kim ayarlıyor?
- **Konum:** `cps/admin.py:1845-1859` (`config_calibre`, `config_kepubifypath`, `config_binariesdir`, `config_converterpath`), `cps/admin.py:1958-1964` (`config_rarfile_location`). Yazan fonksiyon `_configuration_update_helper()`, route'u `/admin/ajaxconfig` (`admin.py:261-265`).
- **Kontrol:** Calibre, kepubify ve unrar yollarını kim değiştirebiliyor?
- **Gözlem:** Route `@user_login_required` + `@admin_required` ile korunuyor. Yollar `resolve_binary_path()` ile desteklenen ikili dosya adlarına (`SUPPORTED_*_BINARIES`) çözülüyor.
- **Sonuç:** Sorun yok. Yalnızca yönetici ayarlayabiliyor. Yöneticinin rastgele bir programı çalıştırabilmesi yetki modelinin parçası.

### D4. `process_wait()` boru (pipe) kullanımı
- **Konum:** `cps/subproc_wrapper.py:39-54`
- **Kontrol:** Süreç çıktısı okunurken kilitlenme (deadlock) riski var mı?
- **Gözlem:** `p.wait()` çağrısı `stdout` okunmadan önce yapılıyor, `stderr` hiç okunmuyor. Çıktı boru tamponunu (genelde 64 KB) aşarsa süreç bekler, bu da kilitlenmeye yol açabilir. Ancak bu fonksiyon yalnızca `--version` ve `unrar` sürüm sorgusu için kullanılıyor (`helper.py:1020, 1046`, `config_sql.py:513`, `converter.py:42`). Bu çıktılar birkaç satır.
- **Sonuç:** Sorun yok (pratikte oluşmuyor). Kod kalitesi notu olarak kalıyor.

## E. Ağ ve güncelleme

### E1. Güncelleyici (`updater.py`)
- **Konum:** `cps/updater.py:77-128`, `:596-603`. Route'lar `cps/admin.py:1560-1573` (`@admin_required`).
- **Kontrol:** Paket nereden indiriliyor, bütünlüğü doğrulanıyor mu, açılırken yol kontrolü var mı?
- **Gözlem:**
  ```python
  r = requests.get(self._get_request_path(), stream=True, headers=headers, timeout=(10, 600))
  z = zipfile.ZipFile(BytesIO(r.content))
  z.extractall(tmp_dir)
  ```
  - Kaynak `https://api.github.com/repos/janeczku/calibre-web` (zipball veya sürüm paketi), HTTPS üzerinden ve zaman aşımı tanımlı.
  - İmza veya özet (hash) doğrulaması yok, bütünlük yalnızca TLS'e ve GitHub hesabına dayanıyor.
  - `extractall()` için Python `zipfile` belgesi, mutlak yolları ve `..` bileşenlerini temizlediğini belirtiyor. Zip slip standart kütüphane tarafından engelleniyor.
  - İşlemi yalnızca yönetici başlatabiliyor.
- **Sonuç:** Düşük öncelikli. Tasarım tercihi, ama tedarik zinciri riski taşıyor. Düzeltme kapsam dışı, raporda sınırlılık olarak anılabilir. — **FIND-157**

### E2. Google Drive kimlik bilgileri
- **Konum:** `cps/gdriveutils.py:72-75`, `cps/constants.py:49-55`, `.gitignore`
- **Kontrol:** Kimlik dosyaları nerede tutuluyor, repoya girme riski var mı?
- **Gözlem:**
  - `settings.yaml`, `gdrive_credentials` ve `client_secrets.json` dosyaları `CONFIG_DIR` altında. Varsayılanı `CALIBRE_DBPATH` ortam değişkeni ya da depo kök dizini.
  - `.gitignore` bunların hepsini ve `gdrive.db`, `app.db` dosyalarını kapsıyor (`git check-ignore -v` ile doğrulandı: satır 33, 34, 46, 47, 45).
- **Sonuç:** Sorun yok.

### E3. `gdriveutils.get_cover_via_gdrive()` ve seri küçük resmi (FIND-008 yan gözlemi)
- **Konum:** `cps/gdriveutils.py:587-611`, `cps/tasks/thumbnail.py:366-410` (`generate_series_thumbnail`)
- **Kontrol:** `review-bandit.md`'de doğrulanmamış bırakılan işlev hatası adayı.
- **Gözlem:**
  ```python
  resp, content = df.auth.Get_Http_Object().request(df.metadata.get('downloadUrl'), headers=headers)
  return content                                     # gdriveutils.py:607-608, bytes döner
  ```
  ```python
  web_content_link = gdriveutils.get_cover_via_gdrive(book.path)   # thumbnail.py:380
  ...
  stream = urlopen(web_content_link)                               # thumbnail.py:386
  ```
  - Kitap küçük resmi (`thumbnail.py:187`) aynı fonksiyonun dönüşünü doğru biçimde içerik olarak kullanıyor. Seri küçük resmi ise onu URL sanıp `urlopen()`'a veriyor.
  - Standart kütüphanede yalıtılmış deneme: `urllib.request.urlopen(b'...')` → `AttributeError: 'bytes' object has no attribute 'timeout'`.
  - Hata `thumbnail.py:405-407`'de yakalanıp loglanıyor ve yeniden fırlatılıyor. Google Drive kullanılan kurulumlarda seri küçük resimleri hiç oluşmuyor.
- **Sonuç:** Gerçek sorun (işlev hatası, güvenlik değil). FIND-008'in B310 "yanlış pozitif" kararı değişmiyor, çünkü `urlopen()` URL şemasıyla ilgili bir risk taşımıyor. — **FIND-152**

### E4. Dış isteklerde zaman aşımı (bağlam notu)
B113 bulguları (FIND-010…014) ve düzeltme planı Dilara Yıldırım'da (`review-bandit.md`, B113 planı). Bu inceleme kapsamında görülen dış istekler (`helper.py:831-833` kapak indirme, `updater.py:82, 359, 385, 620`) zaman aşımı tanımlıyor. Bu satırlar B113 bulgusu değil.

## Bandit bulgularıyla ilişki

| Bandit kaydı | Mevcut karar | Bu incelemenin katkısı |
| --- | --- | --- |
| FIND-002…005 (B704) | Yanlış pozitif | nh3 ayarıyla XSS yolları temizleniyor, karar destekleniyor (A7). `style` ve dış `img` ayrı kayıt: FIND-156. |
| FIND-006/007 (B103, `server.py`) | Yanlış pozitif | Dosya ve süreç alanı dışında (sunucu soketi izni). Ek gözlem yok. |
| FIND-008 (B310) | Yanlış pozitif | Güvenlik kararı değişmiyor. Yan gözlem doğrulandı, işlev hatası olarak FIND-152'ye taşındı (E3). |
| FIND-016 (B112, `pathchooser`) | Düşük öncelikli, kabul edildi | Yalnızca yönetici erişiyor, karar uyumlu (B5). |
| FIND-028 (B404) ve B603 | Yanlış pozitif | Not sonuçlandı (D1, D2). Enjeksiyon yok. Windows'ta 0. eleman tırnaklanmıyor: FIND-158. |

Mevcut FIND-001…044 satırlarında değişiklik yapılmadı. Yeni gözlemler kendi ID bloğumdan (FIND-150–174) yeni satır olarak açıldı.

## Düzeltme önerileri (1 Kasım toplantısı için)

K5 kapsamında güvenlik düzeltmesi adayları, küçükten büyüğe:

1. **FIND-150 (önerilen, Orta):** `cps/web.py:1265` satırında `calibre_db.get_book(book_id)` yerine `calibre_db.get_filtered_book(book_id, allow_show_archived=True)`. Tek satırlık değişiklik, indirme route'uyla aynı davranışı sağlar. Kitap bulunamazsa mevcut `allowed_formats = ... if book else []` yolu "Book format not supported" yanıtı veriyor. Yetki alanıyla kesiştiği için Emre Bulut'un görüşü alınmalı.
2. **FIND-151 (önerilen, Düşük):** `upload_required` dekoratörüne `config.config_uploading` koşulu eklemek: `if current_user.role_upload() and config.config_uploading:`. Arayüzdeki koşulla aynı.
3. **FIND-152 (işlev):** `thumbnail.py:384-386` satırlarında `urlopen(web_content_link)` yerine `io.BytesIO(web_content_link)` kullanmak (`thumbnail.py:187`'deki kitap küçük resmi yoluyla aynı). Güvenlik değil, kod kalitesi ve işlev düzeltmesi.
4. **FIND-158:** Windows dalında `subprocess.list2cmdline()`. Yalnızca Windows'ta gözlemlenebilir; davranış değişikliği riski nedeniyle öncelik düşük.
5. FIND-153, 154, 155, 156 ve 157 için düzeltme önerilmiyor (düşük etki ve davranış değişikliği riski). Raporda sınırlılık olarak anılabilir.
