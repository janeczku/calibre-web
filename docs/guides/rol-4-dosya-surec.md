# 4. kişi rehberi — Hasan Kurt: Dosya işleme ve harici süreçler

Önce `docs/guides/ortak.md`'yi oku.

## Sorumlulukların

- Kitap yükleme/indirme, dosya yolları, dönüştürme, arşivler, harici süreç ve ağ çağrılarının manuel kod incelemesi (ders gereksinimi 4 ve 6)
- `docs/review-file-handling.md` ve kayda eklenen manuel bulgular
- Seçilirse bu alandaki düzeltmeler
- Final raporda 5. bölümün dosya/süreç kısmı

Bu bir **kod okuma** işidir; uygulamayı çalıştırmazsın (K2). Her kontrol noktasında ne gördüğünü dosya:satır kanıtıyla yaz; "sorun yok" da gerekçeli bir sonuçtur.

## Başlangıç noktası

`docs/architecture.md` 4. bölüm (indirme ve yükleme akışları) ve 5. bölüm (dosya/süreç tablosu). İlgili dosyalar arasında: `cps/editbooks.py` (`upload`, `file_handling_on_upload`), `cps/uploader.py`, `cps/helper.py` (`get_download_link`, `do_download_file`, `update_dir_structure`), `cps/file_helper.py` (`validate_mime_type`), `cps/web.py` (`download_link`), `cps/tasks/convert.py`, `cps/subproc_wrapper.py`, `cps/gdriveutils.py`, `cps/updater.py`, `cps/comic.py`. `cps/cw_advocate/` gömülü SSRF kütüphanesidir (K7): incele, düzeltme.

Bandit kayıtlarından seni ilgilendirenler:

- B404/B606 (süreç) ve FIND-028 notu (Windows'ta komutun tek string'e birleştirilmesi — argüman tırnaklama)
- B310 (FIND-008) ve yan gözlem: `gdriveutils.get_cover_via_gdrive()` URL değil dosya içeriği (`bytes`) döndürüyor (`gdriveutils.py:607-608`), `thumbnail.py:386`'daki `urlopen()` buna çalışma zamanında hata verebilir. Güvenlik değil işlev hatası adayı; uygulama çalıştırılmadığı için doğrulanmadı.
- B704 (FIND-002…005, `cps/editbooks.py`): `Markup().unescape()` sonrası yorumlar `clean_html.clean_string()` (nh3/bleach) ile temizleniyor. nh3'ün izin verdiği etiket ve özniteliklerin (`style`, `img src` vb., `clean_html.py:40-46`) yeterliliği `review-bandit.md`'de sana bırakıldı (A maddesiyle birlikte değerlendir).
- B113 (dış istekler; düzeltme planı Dilara'da) ve B103 (dosya izni, FIND-006/007)

## Kontrol listesi

Her madde için: dosya:satır, ne gördün, sonuç (sorun yok / düşük öncelikli / gerçek sorun), varsa FIND-ID.

**A. Yükleme**
- [ ] Dosya adı nasıl temizleniyor (`secure_filename` veya benzeri)? Kullanıcının verdiği ad diske yazılan yola doğrudan giriyor mu?
- [ ] Uzantı ve MIME kontrolü nerede ve nasıl (`validate_mime_type`)? Uzantı listesi kimin ayarına bağlı?
- [ ] Dosya boyutu sınırı (ör. `MAX_CONTENT_LENGTH`) var mı?
- [ ] Geçici dosyalar nerede oluşturuluyor, adları tahmin edilebilir mi, sonra siliniyor mu?
- [ ] Kapak resmi yükleme / URL'den kapak indirme: URL'den indirme varsa SSRF koruması (`cw_advocate`) kullanılıyor mu?

**B. Yol işlemleri ve indirme**
- [ ] Kitap dosya yolları nasıl kuruluyor? Yazar/başlık gibi kullanıcı verisi yola girerken temizleniyor mu (`update_dir_structure`)?
- [ ] İndirmede yol, veritabanındaki kayıttan mı yoksa istek parametresinden mi geliyor? `send_from_directory` / `send_file` kullanımı yol dışına çıkmayı (path traversal) engelliyor mu?
- [ ] İndirme route'ları yetki kontrolü yapıyor mu (Emre'nin A maddesiyle çapraz kontrol)?
- [ ] Yönetici yol seçici (`pathchooser`): hangi dizinleri listeleyebiliyor? (FIND-016)

**C. Arşivler ve dönüştürme**
- [ ] Zip/rar/cbz/cbr açılırken üye adları kontrol ediliyor mu (zip slip: `../` içeren üye adları)?
- [ ] Çok büyük ya da iç içe arşivlere karşı sınır var mı (arşiv bombası)?
- [ ] Dönüştürme (`tasks/convert.py`) harici programa hangi argümanları veriyor; bunlardan biri kullanıcı verisinden mi geliyor?

**D. Harici süreçler**
- [ ] `subprocess` çağrıları liste argümanlı mı, `shell=True` var mı?
- [ ] Windows dalında komutun tek string'e birleştirilmesi (FIND-028, `subproc_wrapper.py:28-32`): tırnaklama, boşluk ve özel karakter içeren dosya adlarında doğru mu? Kullanıcı kontrollü bir değer bu string'e giriyor mu?
- [ ] Harici program yolları (Calibre `ebook-convert`, `kepubify`, `unrar`) nereden geliyor? Yalnızca yönetici mi ayarlayabiliyor?

**E. Ağ ve güncelleme**
- [ ] `updater.py`: güncelleme paketi nereden indiriliyor, bütünlüğü (imza/hash) doğrulanıyor mu, arşiv açılırken yol kontrolü var mı?
- [ ] `gdriveutils.py`: dosya yolları ve kimlik bilgileri nasıl ele alınıyor? `client_secrets.json`, `gdrive.db` repoya girmiyor mu (.gitignore)?
- [ ] Dış isteklerde zaman aşımı (B113 — Dilara'nın planıyla çakışmadan, sadece bağlam notu).

Öncelik sırası: A → B → D → C → E.

## Çıktı: `docs/review-file-handling.md` şablonu

```markdown
# Dosya işleme ve harici süreç incelemesi (4. kişi — Hasan Kurt)

İncelenen commit: <baseline-commit.txt>
Tarih: ...
Yöntem: kod okuma, uygulama çalıştırılmadı (K2)

## Özet
- İncelenen kontrol noktası: N
- Gerçek sorun: x · Düşük öncelikli: y · Sorun yok: z
- Kayda eklenen bulgular: FIND-...

## A. Yükleme
### A1. Dosya adı temizleme
- **Konum:** cps/uploader.py:...
- **Kontrol:** ...
- **Gözlem:** (kısa kod parçası)
- **Sonuç:** ... — FIND-...
...

## Bandit bulgularıyla ilişki
FIND-006/007/008/028 ve B404/B606 hakkında notlar.

## Düzeltme önerileri
```

## Bulgu kaydı

Gerçek sorun veya düşük öncelikli uyarı bulduğunda kendi ID bloğundan (FIND-150–FIND-174) sıradaki ID'yi kullan, `kaynak = Manuel` ile ekle; `inceleyen = Hasan Kurt`. "Sorun yok" sonuçları yalnızca `review-file-handling.md`'de kalır.

## Takvim

- 29 Ekim: A ve B
- 30 Ekim: C, D, E; `review-file-handling.md` PR'ı (gözden geçiren: Emre veya Şeyda)
- 31 Ekim: kayıt satırları (gözden geçiren: Dilara)
- 1 Kasım: düzeltme seçimi
- 2–5 Kasım: seçilen düzeltmeler / PR gözden geçirme

## Bitti tanımı

- [ ] A–E (en azından A, B, D) dosya:satır kanıtıyla yazıldı
- [ ] FIND-028 notu sonuçlandırıldı
- [ ] Bulunan sorunlar kayıtta, gerekçeli
- [ ] PR birleşti

## Claude Code'a örnek mesajlar

> Ben 4. kişiyim (Hasan). docs/guides/rol-4-dosya-surec.md'yi oku. docs/review-file-handling dalını aç. Kontrol listesi B için: kitap indirme isteğinin route'tan diske kadar izlediği yolu dosya:satır ile göster; dosya yolunun hangi kısmı kullanıcıdan, hangisi veritabanından geliyor ve path traversal'ı ne engelliyor? Dosyaya yazma.

> Kontrol listesi D: subproc_wrapper.py'nin Windows dalında komut string'ini oluşturan kodu göster. İçinde boşluk, tırnak veya & içeren bir dosya adı geldiğinde sonuç ne olur, kod okumasıyla değerlendir. Bu dosya adları kullanıcı kontrolünde mi?

Claude Code'un söylediklerini körü körüne yazma: önemli bulguları kendin de dosyada açıp gör.
