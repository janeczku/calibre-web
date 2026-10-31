# 3. kişi rehberi — Emre Bulut: Kimlik doğrulama, oturum ve yetkilendirme

Önce `docs/guides/ortak.md`'yi oku.

## Sorumlulukların

- Giriş/çıkış, parola, oturum, kullanıcı ve yönetici yetkilerinin manuel kod incelemesi (ders gereksinimi 4 ve 6)
- `docs/review-auth.md` ve kayda eklenen manuel bulgular
- Seçilirse bu alandaki düzeltmeler
- Final raporda 5. bölümün yetki kısmı

Bu iş bir **kod okuma** işidir; uygulamayı çalıştırmazsın (K2). Amaç "açık var" demek değil, her kontrol noktasında ne gördüğünü kanıtla yazmaktır. "Sorun yok" da değerli bir sonuçtur, yeter ki neden olduğu yazılsın.

## Başlangıç noktası

`docs/architecture.md` 5. bölüm (yetki tablosu). İlgili dosyalar arasında: `cps/usermanagement.py`, `cps/web.py` (login/logout), `cps/admin.py`, `cps/ub.py`, `cps/oauth_bb.py`, `cps/kobo_auth.py`, `cps/remotelogin.py`, `cps/render_template.py` ve `__init__.py`'deki uygulama ayarları. `cps/cw_login/` gömülü Flask-Login kopyasıdır (K7): incele, düzeltme.

Bandit kayıtlarından seni ilgilendirenler:

- B105 satırları (sabit "parola" uyarıları): FIND-034/035/036/041/042 ve FIND-038…040 (`cps/services/simpleldap.py`, LDAP bağlanma parolası)
- FIND-043 (B107, `cps/web.py` `render_login` boş varsayılan argümanlar)
- FIND-014 (anonim gezinme açıkken giriş yapmamış ziyaretçinin dış isteği tetikleyebilmesi)
- **FIND-044** (Manuel, `cps/constants.py` `DEFAULT_PASSWORD = "admin123"  # nosec`): durumu **İnceleniyor**, kayıtta sana atanmış. Bunu sen sonuçlandıracaksın (bkz. B kontrol listesi).

FIND-044 dışındakileri yeniden değerlendirmen gerekmez ama yetki bağlamında not düşebilirsin.

## Kontrol listesi

Her madde için: ilgili dosya:satır, ne gördün, sonuç (sorun yok / düşük öncelikli / gerçek sorun), varsa FIND-ID.

**A. Yetki dekoratörleri**
- [ ] Yönetici işlemleri yapan her route'ta `@admin_required` (veya eşdeğeri) var mı? `admin.py`'deki route'ları tek tek listele.
- [ ] Rol gerektiren işlemler (yükleme, düzenleme, silme, indirme) ilgili rol kontrolünü yapıyor mu? (ör. `upload_required`, `edit_required`, `download_required` gibi dekoratörler — kodda gerçek adlarını doğrula)
- [ ] Dekoratörsüz yardımcı fonksiyonlar yalnızca korumalı route'lardan mı çağrılıyor? (FIND-016'daki `pathchooser` örneği gibi)
- [ ] Anonim gezinme (`config_anonbrowse`) açıkken hangi sayfalar ve işlemler giriş gerektirmiyor? `login_required_if_no_ano` kullanılan yerleri listele.

**B. Kimlik doğrulama ve parola**
- [ ] Parolalar nasıl saklanıyor? Hangi özet fonksiyonu kullanılıyor (`ub.py`, Werkzeug `generate_password_hash`)?
- [ ] Giriş başarısız olduğunda kullanıcı adı / parola hatası ayrı ayrı mı belirtiliyor (kullanıcı adı tahmini)?
- [ ] Kaba kuvvet denemelerine karşı sınırlama var mı (ör. limiter)? Nerede yapılandırılıyor?
- [ ] Varsayılan yönetici hesabı / varsayılan parola davranışı nasıl? İlk girişte parola değişikliği zorunlu mu? (**FIND-044 — sonuçlandırılmalı**)
- [ ] Guest (misafir) kullanıcısı ile giriş yapılabiliyor mu? (FIND-034/041/042 bağlantılı)
- [ ] Parola sıfırlama / değiştirme akışı mevcut parolayı ya da yetkiyi doğruluyor mu?

**C. Oturum**
- [ ] `SECRET_KEY` nereden geliyor, nasıl üretiliyor, nerede saklanıyor?
- [ ] Oturum çerezi ayarları: `SESSION_COOKIE_HTTPONLY`, `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_SAMESITE`.
- [ ] Çıkışta oturum gerçekten temizleniyor mu? "Beni hatırla" çerezi nasıl?
- [ ] Oturum koruması (Flask-Login `session_protection`) ayarı ne?

**D. CSRF ve yönlendirme**
- [ ] CSRF koruması (ör. Flask-WTF `CSRFProtect`) genel olarak etkin mi? Muaf tutulan route'lar hangileri (Kobo, OPDS gibi API uçları)? Muafiyet gerekçeli mi?
- [ ] Giriş sonrası `next` parametresiyle yönlendirme yapılıyor mu? Hedef URL'nin aynı siteye ait olduğu kontrol ediliyor mu (açık yönlendirme)?

**E. Diğer giriş yolları**
- [ ] OAuth (GitHub/Google) eşleme: dış hesap mevcut kullanıcıya nasıl bağlanıyor?
- [ ] Kobo senkronizasyon token'ı: nasıl üretiliyor, URL'de mi taşınıyor, hangi yetkiyi veriyor?
- [ ] Uzaktan giriş (remote login) akışı: token süresi ve tek kullanımlık mı?
- [ ] OPDS / basic auth uçlarında kimlik doğrulama nasıl yapılıyor?

Her şeyi bitiremezsen öncelik sırası: A → B → C → D → E.

## Çıktı: `docs/review-auth.md` şablonu

```markdown
# Yetki ve oturum incelemesi (3. kişi — Emre Bulut)

İncelenen commit: <baseline-commit.txt>
Tarih: ...
Yöntem: kod okuma, uygulama çalıştırılmadı (K2)

## Özet
- İncelenen kontrol noktası: N
- Gerçek sorun: x · Düşük öncelikli: y · Sorun yok: z
- Kayda eklenen bulgular: FIND-...

## A. Yetki dekoratörleri
### A1. Yönetici route'ları
- **Konum:** cps/admin.py:...
- **Kontrol:** ...
- **Gözlem:** (kısa kod parçası)
- **Sonuç:** Sorun yok / Düşük öncelikli / Gerçek sorun — FIND-...
...

## Bandit bulgularıyla ilişki
FIND-014, B105 satırları hakkında notlar.

## Düzeltme önerileri
Kayda eklenen gerçek sorunlar için önerilen küçük düzeltmeler.
```

Kod parçalarını kısa tut (birkaç satır). Rapora girecek.

## Bulgu kaydı

Gerçek sorun veya düşük öncelikli uyarı bulduğunda kendi ID bloğundan (FIND-125–FIND-149) sıradaki ID'yi kullan, `kaynak = Manuel` ile ekle; `inceleyen = Emre Bulut`. "Sorun yok" sonuçları kayda girmez, `review-auth.md`'de kalır.

## Takvim

- 29 Ekim: A ve B
- 30 Ekim: C, D, E; `review-auth.md` PR'ı (gözden geçiren: Hasan veya Şeyda)
- 31 Ekim: kayıt satırları (gözden geçiren: Dilara)
- 1 Kasım: düzeltme seçimi toplantısı
- 2–5 Kasım: seçilen düzeltmeler / başkalarının PR'larını gözden geçirme

## Bitti tanımı

- [ ] A–E maddelerinin hepsi (en azından A–C) dosya:satır kanıtıyla yazıldı
- [ ] Bulunan sorunlar kayıtta, gerekçeli
- [ ] PR birleşti

## Claude Code'a örnek mesajlar

> Ben 3. kişiyim (Emre). docs/guides/rol-3-yetki.md'yi oku. docs/review-auth dalını aç. Kontrol listesinin A bölümü için cps/admin.py'deki tüm route'ları, dekoratörlerini ve yaptıkları işi tablo olarak çıkar. Dekoratörsüz ya da beklenenden zayıf korunan route'ları ayrıca işaretle. Henüz dosyaya yazma, bana göster.

> Kontrol listesi C maddesi: SECRET_KEY'in kaynağını ve oturum çerezi ayarlarını kodda bul, dosya:satır ile göster. Ayar yapılmıyorsa Flask varsayılanının ne olduğunu belirt.

Claude Code'un söylediklerini körü körüne yazma: önemli bulguları kendin de dosyada açıp gör.
