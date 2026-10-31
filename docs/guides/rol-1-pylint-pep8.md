# 1. kişi rehberi — Şeyda Altın: Repo, mimari, Pylint ve PEP 8

Önce `docs/guides/ortak.md`'yi oku.

## Sorumlulukların

- Repo yönetimi: dallar, PR birleştirme, `CLAUDE.md` ve rehberlerin güncelliği
- Ders gereksinimi 1 (proje tanıtımı), 2 (Pylint), 5 (PEP 8) ve 8'in Pylint/PEP 8 kısmı
- Final raporda 1, 2, 3, 6 ve 9. bölümlerin Pylint/PEP 8 kısmı

## Tamamlananlar

- ✅ Fork, collaborator'lar, ortam, lock dosyası
- ✅ `project-scope.md`, `architecture.md`
- ✅ Pylint (6.42/10) ve flake8 (3409) başlangıç raporları + özetleri

## Sıradaki adımlar

### 1) Pylint ve PEP 8 bulgularını kayda ekle — 31 Ekim

Dal: `docs/pylint-findings`. ID bloğun: FIND-045–FIND-124 (CLAUDE.md → "Bulgu kaydı"); sırayla kullan.

Gruplama kuralı (CLAUDE.md): aynı kural kodu tek satır, `satir = çoklu (N adet)`.

- Pylint: `warning` ve `error` kategorisindeki her kod ayrı satır; en sık convention/refactor kodları ayrı satır; kalanlar "diğer convention" / "diğer refactor" gibi toplu satırlar.
- flake8: en sık 5 E/W kodu ayrı satır, kalanlar tek satır.
- **E0611 (252 adet, üç grup — `pylint-baseline-summary.md`, `architecture.md` 6. bölüm):**
  - **250 adet, `in module 'cps'`** (`simpleldap.py`'deki 2 dahil): `Yanlış pozitif`, tek satır. Gerekçe: `cps/__init__.py`'deki paket düzeyi dinamik atama ve döngüsel importlar (R0401) nedeniyle astroid adları çözemiyor. `architecture.md` 6. bölümdeki kod örneğine atıf yap; birkaç örnek dosya:satır ver.
  - **1 adet, `cps/clean_html.py:20` (`lxml.etree`):** `Yanlış pozitif`. Gerekçe: `lxml.etree` derlenmiş C uzantısı, astroid içini göremiyor; `ParserError` kurulu ortamda mevcut (`python -c "import lxml.etree as e; print(hasattr(e, 'ParserError'))"` → `True`).
  - **1 adet, `cps/cw_advocate/api.py:175` (`from . import cw_advocate`):** K7 kodu, düzeltilmez; ama gerçek hata mı yanlış pozitif mi olduğunu **sen doğrulayıp kayıtta gerekçelendir**. Pakette `cw_advocate` adlı bir alt modül yok; satırın hangi durumda çalıştığına (`__getattr__` içindeki `AttributeError` dalı) ve oraya ulaşılıp ulaşılamadığına bak. K7 ifadesiyle işaretle.
- **E0401 (LDAP, 2 adet):** E0401 kayda girmez (kural 9), `environment-notes.md`'de kayıtlı.
- `cps/cw_login/`, `cps/cw_advocate/` kaynaklı satırlar K7 ifadesiyle işaretlenir.

### 2) Düzeltme adaylarını hazırla — 31 Ekim

K5 hedefi: en az 5 kod kalitesi / PEP 8 **türü**. Seçim ölçütleri:

- **Anlamlı olsun:** Davranış ya da bakım üzerinde etkisi olan uyarılar öncelikli. İyi adaylar: `unspecified-encoding` (W1514), `broad-exception-caught` (W0718), `unused-import` (W0611), `unused-variable` (W0612), `dangerous-default-value` (W0102), `raise-missing-from` (W0707), `no-else-return` (R1705), `consider-using-with` (R1732).
- **Küçük ve güvenli olsun:** Her tür için 1–3 dosyada, gözle doğrulanabilir değişiklik. Yüzlerce yerde geçen türde hepsini değil, seçilmiş bir dosyadaki örnekleri düzelt.
- **PEP 8 için:** E501'i tüm projede değil, düzelttiğin dosyalarda sınırlı tut. E/W'den 1–2 farklı tür (ör. boşluk/girinti kuralları) seç.
- **K7 dışında olsun.**
- Toplu biçimlendirme (black/autopep8 ile tüm proje) yasak (K5).

1 Kasım toplantısına tablo getir: kural kodu, adet, önerilen dosya(lar), değişikliğin özeti, risk.

### 3) Düzeltmeler — 2–5 Kasım

Her tür için ayrı `fix/find-XXX` dalı ve PR (ortak.md akışı). Gözden geçiren olarak başka birini ata.
Diğerlerinin PR'larını da gözden geçir; repo sahibi olarak birleştirme sende.

### 4) Son tarama ve karşılaştırma — 7–8 Kasım

- Pylint ve flake8 son taramalarını sen değil, düzeltme yapmamış biri çalıştırsın ya da sen çalıştırıp o kişi kontrol etsin.
- `docs/pylint-comparison.md`: puan 6.42 → yeni puan; kategori dağılımı önce/sonra; kapanan / devam eden / yeni çıkan kodlar.
- `docs/pep8-comparison.md`: toplam ihlal önce/sonra; düzeltilen türler; düzeltilen dosyalardaki değişim.
- 8 Kasım akşamı: kod dondurma. Sonrasında `cps/` PR'ı birleştirme.

## Bitti tanımı

- [ ] Pylint/PEP 8 satırları kayıtta, hepsinde gerekçe var, `İnceleniyor` kalmadı
- [ ] En az 5 tür düzeltildi, her birinin PR'ı birleşti
- [ ] Son raporlar `reports/final/` içinde, karşılaştırma dokümanları yazıldı
- [ ] `ortak.md`'deki "Projenin şu anki durumu" güncel

## Claude Code'a örnek mesajlar

> Ben 1. kişiyim. docs/guides/rol-1-pylint-pep8.md'yi oku. 1. adım için önce plan çıkar, dosyaya yazma: hangi kodlar ayrı satır olacak, E0611 gerekçesi, 5–7 düzeltme adayı.

> fix/find-0XX dalında W1514 (unspecified-encoding) düzeltmesini cps/<dosya>.py için yap. Yalnızca open() çağrılarına encoding="utf-8" ekle; dosyanın gerçekten metin olduğunu ve önceki davranışın UTF-8 varsaydığını kontrol et. py_compile ve dosya bazlı pylint çıktısını göster, commit etme.
