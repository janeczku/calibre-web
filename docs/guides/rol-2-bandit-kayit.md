# 2. kişi rehberi — Dilara Yıldırım: Bandit ve bulgu kaydı

Önce `docs/guides/ortak.md`'yi oku.

## Sorumlulukların

- Bandit analizi ve risk sınıflandırması (ders gereksinimi 3)
- `docs/findings-register.csv` dosyasının sahibi: ID dağıtımı, biçim kontrolü, tutarlılık
- B113 (timeout) güvenlik düzeltmelerinin planı ve koordinasyonu (K5'in güvenlik ayağı)
- Bandit son taraması ve karşılaştırması (gereksinim 8)
- Final raporda 4. bölüm (Bandit) ve 9. bölümün Bandit kısmı

## Tamamlananlar

- ✅ Bandit başlangıç raporları 1.9.4 (K8): 43 bulgu — cps/ 42, cps.py 1; 0 HIGH, 14 MEDIUM
- ✅ FIND-001…044, `docs/review-bandit.md`, `docs/bandit-summary.md` (Bandit envanteri ve notlar Emre tarafından hazırlandı)
- 1.8.6 olayı K8'de belgelendi; orijinaller `evidence/bandit-1.8.6-original/`

## Sıradaki adımlar

### 0) ✅ Ortam kuruldu (28 Ekim, lock dosyasıyla)

✅ K8 kök nedeni için ortam bilgisi bildirildi (`docs/28-ekim-kontrol-dilara.md`: macOS, Python 3.12.16); K8 güncellendi: Windows dışı (macOS) ortamda sürüm belirtilmeden kurulum; o anki Python sürümü kayıtlı değil.

### 1) Bulgu kaydını yönet — sürekli

- ID dağıtımı: Şeyda (Pylint/PEP 8), Emre (yetki), Hasan (dosya) kendi ID bloklarını kullanır (28 Ekim ekip kararı, CLAUDE.md → "Bulgu kaydı"): Şeyda FIND-045–124, Emre FIND-125–149, Hasan FIND-150–174, sen FIND-175–199 (yedek). Blok biten kişiye yedekten ek aralık verip gruba yaz.
- Her kayıt PR'ında gözden geçiren sensin. Kontrol: 18 sütun ve sıra, BOM, izinli değerler, gerekçe dolu, `inceleyen ≠ gozden_geciren`, K7 ifadesi.
- 31 Ekim akşamı: tüm satırlar birleştikten sonra kaydın son kontrolünü yap; `İnceleniyor` kalan satırları ilgili kişiye bildir.

### 2) B113 düzeltme planı — 31 Ekim

Kayıtta B113 olarak işaretlenmiş 5 gerçek bulgu (zaman aşımı olmayan `requests` çağrıları) var. Her biri için:

- Dosya:satır ve çağrının amacı (hangi dış servise, kimin tetiklediği — ör. FIND-014 anonim ziyaretçi tarafından tetiklenebiliyor)
- K7 dışında mı?
- Kodda zaten timeout kullanılan başka `requests` çağrıları var mı? Varsa aynı değeri/örüntüyü kullan (tutarlılık). Yoksa makul bir değer öner (ör. bağlantı ve okuma için ayrı, saniye cinsinden) ve gerekçelendir.
- Zaman aşımında ne olur? Çağıran kod `requests.exceptions.Timeout`'u yakalıyor mu, yoksa düzeltme yeni bir hata yolu açar mı?
- Kim düzeltecek, kim gözden geçirecek?

Planı `docs/review-bandit.md` sonuna "B113 düzeltme planı" başlığıyla ekle ve 1 Kasım toplantısına getir.

### 3) Düzeltmeler — 2–5 Kasım

Her bulgu için `fix/find-XXX` dalı; ya da aynı türden bulgular tek dosyadaysa tek PR (CLAUDE.md: "aynı türden küçük grup"). PR açıklamasında önceki/yeni kod ve dosya bazlı `bandit` çıktısı.

### 4) Bandit son tarama ve karşılaştırma — 7–8 Kasım

- CLAUDE.md'deki "Son" Bandit komutları, aynı ortam. `python -m bandit --version` ile başla.
- `docs/bandit-comparison.md`:
  - Önem × güven matrisi önce/sonra
  - test_id adetleri önce/sonra
  - Kapanan / devam eden / yeni çıkan bulgular (normalize yol + test_id + kod parçası ile eşleştir)
  - Kapanan her bulgunun FIND-ID'si ve PR'ı
  - Yanlış pozitif olarak kalan bulguların sayısı ve neden düzeltilmedikleri

## Bitti tanımı

- [ ] Ortamın 1.9.4 / 4.1.3 / 7.4.1; K8 kök nedeni kesinleşti
- [ ] Kayıt tutarlı; tüm satırlarda gerekçe; `İnceleniyor` yok
- [ ] En az 3 güvenlik bulgusu düzeltildi (B113 adayları) ve PR'ları birleşti
- [ ] `reports/final/bandit-*.json` ve `bandit-comparison.md` hazır

## Claude Code'a örnek mesajlar

> Ben 2. kişiyim. docs/guides/rol-2-bandit-kayit.md'yi oku. findings-register.csv'deki B113 satırlarını listele; her biri için çağrının amacı, tetikleyen kullanıcı tipi, timeout'un çağıran kodda nasıl ele alınacağı ve kodda mevcut timeout örüntüleri hakkında bir tablo çıkar. Dosya değiştirme.

> docs/<dal> dalındaki findings-register.csv değişikliklerini doğrula: sütun sayısı/sırası, BOM, izinli değerler, ID çakışması, boş gerekçe. Sorunları listele.
