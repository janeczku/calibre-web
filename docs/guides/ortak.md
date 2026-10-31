# Ortak rehber — herkes için iş akışları ve şablonlar

Bu dosya tüm rollerin ortak kullandığı akışları anlatır. Kendi rol rehberinle birlikte oku.
Kurallar ve kararlar (K1–K8) için tek kaynak `CLAUDE.md`'dir; burası "nasıl yapılır" kısmıdır.

## Projenin şu anki durumu (28 Ekim 2026)

- ✅ Fork, roller, `project-analysis` dalı, sabit ortam (`requirements-lock.txt`)
- ✅ Başlangıç taramaları `reports/baseline/`: Pylint 6.42/10, flake8 3409 ihlal, Bandit 43 bulgu (0 HIGH, 14 MEDIUM)
- ✅ `docs/project-scope.md`, `docs/architecture.md`
- ✅ Bandit bulgu kaydı FIND-001…044 (`docs/findings-register.csv`), inceleme notları `docs/review-bandit.md`
- ⏳ Manuel incelemeler (3. ve 4. kişi), Pylint/PEP 8 kayıtları (1. kişi), düzeltmeler, son taramalar, rapor

Bu bölümü güncel tutmak 1. kişinin işidir.

## Her oturumun başında

```powershell
cd $HOME\Projeler\calibre-web
.\.venv\Scripts\Activate.ps1
git switch project-analysis
git pull
```

Claude Code'a ilk mesaj olarak hangi kişi olduğunu ve bugünkü işini söyle. Örnek:
> Ben 3. kişiyim (Emre). docs/guides/rol-3-yetki.md'yi oku, bugün review-auth.md'nin 2. adımına devam edeceğiz.

## Bir işi yapma akışı (her iş için aynı)

1. `project-analysis` güncel mi? `git pull`
2. Yeni dal aç: `git switch -c <tür>/<kısa-ad>` (örn. `docs/review-auth`, `fix/find-047`)
3. İşi yap. Sık sık `git status` ile ne değiştiğine bak.
4. Dosyaları **adıyla** ekle (`git add docs/review-auth.md`), `git add .` kullanma.
5. Commit: `<tür>: <kısa açıklama>` (CLAUDE.md'deki biçim)
6. Push: `git push -u origin <dal-adı>`
7. PR'ı **yalnızca** şu linkle aç:
   `https://github.com/sseydaltin/calibre-web/compare/project-analysis...<dal-adı>`
   Sayfada `janeczku` yazıyorsa DUR, PR'ı açma.
8. PR açıklamasını şablona göre doldur (aşağıda; GitHub otomatik getirir).
9. Gözden geçiren kişiyi PR'da **Reviewers** kısmından ata ve gruba haber ver.
10. Onay gelince **Merge → Confirm merge → Delete branch**. Yerelde: `git switch project-analysis; git pull; git branch -d <dal-adı>`

## Bulgu kaydına satır ekleme

- `docs/findings-register.csv` dosyasının sorumlusu **2. kişi (Dilara)**. Herkes kendi ID bloğunu kullanır (CLAUDE.md → "Bulgu kaydı": Şeyda 045–124, Emre 125–149, Hasan 150–174, Dilara 175–199 yedek); blok biterse Dilara'dan ek aralık iste. İki kişi aynı ID'yi kullanmasın.
- Dosyayı Excel'de açıp kaydetme: Excel virgülü, BOM'u ve tırnakları bozabilir. Claude Code'a "şu satırları ekle" de ya da metin düzenleyiciyle ekle.
- Her satırda zorunlu: `dogrulama_sonucu`, `gerekce`, `inceleyen`. Gerekçe kodla desteklenmeli: dosya:satır ve ne gördüğün.
- Manuel bulgularda `kaynak = Manuel`, `kural_kodu = -`, `arac_onem = -`, `arac_guven = -`.
- `inceleyen`, `duzelten`, `gozden_geciren` alanlarına rol numarası değil ad soyad yaz (örn. `Hasan Kurt`).
- Satır eklediğin PR'da 2. kişiyi (Dilara Yıldırım) gözden geçiren olarak ata.

## Doğrulama sonucu nasıl verilir

| Sonuç | Ne zaman |
| --- | --- |
| **Gerçek sorun** | Kod yolunu izledin ve saldırganın/hatalı girdinin bu noktaya ulaşıp zarar verebileceğini gösterebiliyorsun; ya da kalite sorunu gerçekten hataya/bakım sorununa yol açıyor. |
| **Düşük öncelikli uyarı** | Sorun teorik olarak var ama etkisi küçük, yalnızca yöneticinin erişebildiği bir yerde ya da başka bir korumayla sınırlanmış. |
| **Yanlış pozitif** | Aracın uyardığı durum bu kodda oluşamıyor; nedenini kodla gösterebiliyorsun (örn. değer sabit, girdi önceden temizleniyor, araç dinamik yapıyı anlayamıyor). |
| **İnceleniyor** | Henüz karar verilmedi. 1 Kasım'dan önce kalmamalı. |

"Araç uyardı, demek ki açık var" ya da "kimse istismar etmez" gerekçe değildir.

## Düzeltme yapma akışı (2–5 Kasım)

1. Bulgu kayıtta `Gerçek sorun` ve 1 Kasım toplantısında seçilmiş olmalı. Dal: `fix/find-XXX`.
2. **En küçük** değişikliği yap; davranışı koru. İlgisiz satırları, boşlukları, importları ellemeyin.
3. K7: `cps/cw_login/` ve `cps/cw_advocate/` içinde düzeltme yok.
4. Doğrula:
   ```powershell
   python -m py_compile cps\<dosya>.py
   python -m bandit cps\<dosya>.py          # güvenlik düzeltmesiyse
   python -m pylint cps\<dosya>.py          # kalite düzeltmesiyse
   python -m flake8 --isolated --select=E,W cps\<dosya>.py   # PEP 8 düzeltmesiyse
   ```
   Uyarının kapandığını, yeni uyarı çıkmadığını kontrol et.
5. Kayıtta `durum = Düzeltildi`, `commit_pr`, `duzelten` alanlarını güncelle (aynı PR'da).
6. PR açıklamasına önceki kod / yeni kod / gerekçe / doğrulama çıktısını yaz.
7. Susturma yorumu (`# nosec`, `# noqa`, `# pylint: disable`) yalnızca K6'ya uygun durumda.

## Gözden geçiren olarak (PR review) kontrol listesi

- [ ] PR `sseydaltin/calibre-web` → `project-analysis` hedefli mi?
- [ ] Değişen dosyalar PR'ın amacıyla sınırlı mı? `.venv`, log, db, kişisel veri yok mu?
- [ ] Düzeltme PR'ıysa: `cps/cw_login/`, `cps/cw_advocate/` değişmemiş mi (K7)?
- [ ] Değişiklik davranışı koruyor mu? Hata durumlarında ne oluyor?
- [ ] Açıklamadaki doğrulama komutlarını kendin çalıştırdın mı, aynı sonucu aldın mı?
- [ ] Bulgu kaydı güncellenmiş mi; gerekçe kodla destekleniyor mu?
- [ ] `reports/baseline/` dosyalarına dokunulmamış mı?

Sorun varsa **Request changes**, yoksa **Approve**. Yorumları somut yaz: dosya:satır + ne yapılmalı.

## Son taramalar ve karşılaştırma (7–8 Kasım)

- Son taramaları **kod dondurmadan önceki son commit** üzerinde, CLAUDE.md'deki "Son" komutlarıyla, sabit ortamda yap. Çalıştıran ile düzeltmeyi yapan farklı kişi olmalı.
- Karşılaştırma eşleştirmesi: normalize yol + kural kodu + kod parçası (satır numaraları kayar). Yol ayracı farkını (`/` ve `\`) normalize et.
- Her araç için üç liste: **kapanan**, **devam eden**, **yeni çıkan**. Yeni çıkan her uyarı açıklanmalı.
- Susturulan uyarılar ile düzeltilen uyarılar ayrı sayılır (K6).

## Final rapor iskeleti (`docs/final-report.md`)

Bölümler ders gereksinimlerinin sırasını izler:

1. Proje seçimi ve yapısı (1. kişi) — gereksinim 1
2. Kullanılan araçlar, sürümler ve yöntem (1. kişi) — K1–K8 kısaca
3. Pylint başlangıç sonuçları (1. kişi) — gereksinim 2
4. Bandit sonuçları ve risk sınıflandırması (2. kişi) — gereksinim 3
5. Önemli güvenlik bulgularının kod incelemesi (2., 3., 4. kişi) — gereksinim 4
6. PEP 8 uygunluk analizi (1. kişi) — gereksinim 5
7. Bulguların değerlendirilmesi: gerçek / düşük öncelikli / yanlış pozitif (herkes) — gereksinim 6
8. Düzeltmeler: önceki ve yeni kod (düzeltmeyi yapan) — gereksinim 7
9. Yeniden analiz ve karşılaştırma (1. ve 2. kişi) — gereksinim 8
10. Sınırlılıklar ve süreç notları (K7, K8, LDAP, statik analizin sınırları)
11. Sonuç

Her bölümde sayılar `reports/` dosyalarından, kod parçaları gerçek koddan alınır; elle uydurulmaz.
