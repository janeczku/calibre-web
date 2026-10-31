# CLAUDE.md — Calibre-Web Statik Kod Analizi Projesi

Bu dosya, ekipteki herkesin Claude Code oturumları için ortak çalışma kurallarını tanımlar.
Proje dili **Türkçe**dir: dokümanları, bulgu kayıtlarını ve kullanıcıya verilen açıklamaları Türkçe yaz.
Kod, değişken adları, commit önekleri ve dal adları İngilizce kalır.

## Oturum başında (her seferinde)

1. Kullanıcıya hangi kişi olduğunu sor (1–4), belli değilse.
2. `docs/guides/ortak.md` ile o kişinin rehberini oku:
   - 1. kişi → `docs/guides/rol-1-pylint-pep8.md`
   - 2. kişi → `docs/guides/rol-2-bandit-kayit.md`
   - 3. kişi → `docs/guides/rol-3-yetki.md`
   - 4. kişi → `docs/guides/rol-4-dosya-surec.md`
3. `git status` ve hangi dalda olunduğunu kontrol et; `project-analysis` güncel değilse `git pull` öner.
4. Kullanıcının bugünkü işini rehberdeki adımlarla eşleştir ve oradan devam et.

Bu dosya **kurallar ve kararlar** için tek kaynaktır. Rehberler "nasıl yapılır" kısmını anlatır. Rehber ile bu dosya çelişirse bu dosya geçerlidir; çelişkiyi kullanıcıya bildir.

## Proje özeti

- **Amaç:** Calibre-Web'i sıfırdan geliştirmek değil. Seçilen Python kodunu Bandit (güvenlik), Pylint (kod kalitesi) ve flake8 (PEP 8) ile analiz etmek, önemli bulguları elle doğrulamak, seçilmiş sorunları güvenli biçimde düzeltmek ve başlangıç/son taramalarını karşılaştırıp raporlamak.
- **Dönem:** 24 Ekim – 10 Kasım 2026. **8 Kasım sonunda kod dondurulur**; 9–10 Kasım yalnızca rapor, sunum ve prova içindir.
- **Ekip deposu (fork):** https://github.com/sseydaltin/calibre-web
- **Resmî kaynak (upstream):** https://github.com/janeczku/calibre-web
- **Lisans:** GPL v3. `LICENSE` dosyasını ve kaynak koddaki lisans/telif bildirimlerini asla silme veya değiştirme.
- **Analiz edilen commit:** `docs/baseline-commit.txt` içinde kayıtlı (upstream `master`, `6e840ac…`).
- **Ortam:** Windows, PowerShell, Python 3.12.10, sanal ortam `.venv`.
- **Araç sürümleri (sabit):** `requirements-analysis.txt` → bandit 1.9.4, pylint 4.1.3, astroid 4.3.4, flake8 7.4.1. Tüm ortamın tam kopyası `requirements-lock.txt` içindedir; ekip kurulumunda kullanılan dosya budur (bkz. "Ortam kurulumu").
- **Güncel durum:** `docs/guides/ortak.md` → "Projenin şu anki durumu".

## Ders gereksinimleri ve ekip kararları

Ders: **"Güvenlik İçin Statik Kod Analizi"**. Kodlar **çalıştırılmadan**, statik analiz araçlarıyla incelenir. Her karar aşağıdaki 9 maddeye hizmet etmelidir:

| # | Ders gereksinimi | Nasıl karşılanıyor | Sorumlu | Çıktı |
| --- | --- | --- | --- | --- |
| 1 | Yeterli büyüklükte Python projesi seçimi ve yapısının tanıtımı | Calibre-Web; kapsam `cps/` + `cps.py`. Büyüklük, dosya ve satır sayısıyla (LOC) gerekçelendirilir | 1. kişi | `project-scope.md`, `architecture.md` |
| 2 | Pylint ile kalite analizi, başlangıç sonuçlarının kaydı | Kod değişikliğinden önce Pylint taraması, puan ve kategori dağılımı | 1. kişi | `reports/baseline/pylint.txt`, `pylint-baseline-summary.md` |
| 3 | Bandit ile güvenlik analizi, risk düzeyine göre sınıflandırma | Önem (LOW/MEDIUM/HIGH) × güven (LOW/MEDIUM/HIGH) matrisi ve kural kodu dağılımı | 2. kişi | `reports/baseline/bandit-*.json`, `bandit-summary.md` |
| 4 | Yüksek/önemli güvenlik bulgularının kod satırlarıyla incelenmesi | Tüm HIGH ve MEDIUM önemli bulgular ile 3. ve 4. kişinin alanındaki bulgular kod parçasıyla incelenir | 2., 3. ve 4. kişi | `review-bandit.md`, `review-auth.md`, `review-file-handling.md` |
| 5 | PEP 8 ve temel kodlama standardı problemleri | Pylint `convention` kategorisi + flake8 ile saf PEP 8 (E/W) taraması | 1. kişi | `reports/baseline/pep8.txt`, `pep8-baseline-summary.md` |
| 6 | Gerçek problem / düşük öncelikli / yanlış pozitif ayrımı | Her bulgu için `dogrulama_sonucu` + `gerekce` alanları zorunlu | Herkes | `findings-register.csv` |
| 7 | Seçilen sorunların düzeltilmesi; önceki ve yeni kod karşılaştırması | `fix/find-XXX` dalları; PR açıklamasında önceki kod / yeni kod / gerekçe | Herkes | PR'lar, `final-report.md` |
| 8 | Araçların yeniden çalıştırılması ve karşılaştırma | Aynı sürüm, aynı kapsam ve aynı parametrelerle son tarama | 1. ve 2. kişi | `reports/final/`, `*-comparison.md` |
| 9 | Rapor: araçlar, önemli bulgular, düzeltmeler, yeniden analiz | Final raporu bu 9 maddeye göre bölümlenir (iskelet: `docs/guides/ortak.md`) | Ortak | `final-report.md` |

**Alınan kararlar** (değiştirmek için ekip onayı gerekir; değişiklikler buraya yazılır):

- **K1 — Proje ve kapsam:** Calibre-Web, upstream commit `docs/baseline-commit.txt` içinde. Otomatik tarama kapsamı `cps/` ve `cps.py`. `test/`, `library/`, JS/CSS/HTML şablonları kapsam dışı.
- **K2 — Uygulama çalıştırılmaz:** Analiz tamamen statiktir. Düzeltmeler `py_compile` ve araçların yeniden çalıştırılmasıyla doğrulanır. Uygulamayı çalıştırmak yalnızca bir düzeltmenin davranışını göstermek için gerekirse, yerelde (`127.0.0.1`) ve boş örnek kitaplıkla yapılır.
- **K3 — Bağımlılıklar kurulur:** Calibre-Web'in `requirements.txt` ve `optional-requirements.txt` bağımlılıkları (Windows'ta kurulamayan LDAP paketleri hariç) başlangıç taramasından **önce** `.venv` ortamına kuruldu; `pip freeze` çıktısı `docs/environment-notes.md` ve `requirements-lock.txt` içinde. Amaç Pylint'in importları çözebilmesidir; kod çalıştırılmaz. Son taramada aynı ortam kullanılır.
- **K4 — Araç ayarları:** Bandit varsayılan ayarlarla tüm testleri çalıştırır (skip veya `# nosec` eklenmez). Repoda Pylint veya flake8 yapılandırma dosyası yoktur; Pylint varsayılanlarıyla çalışır. flake8 `--isolated` ile saf PEP 8 varsayılanlarında (satır uzunluğu 79) ve yalnızca `E,W` kodlarıyla çalışır.
- **K5 — Düzeltme hedefi:** En az **3 güvenlik** bulgusu düzeltilir veya kanıtla yanlış pozitif gösterilir. En az **5 kod kalitesi / PEP 8** bulgu türü düzeltilir. Düzeltmeler küçük ve davranışı koruyan değişikliklerdir. Binlerce stil uyarısını toplu biçimlendirme (black/autopep8 ile tüm projeyi yeniden biçimlendirme) **yapılmaz**, çünkü önce-sonra karşılaştırmasını anlamsızlaştırır ve diff'i okunmaz hale getirir.
- **K6 — Uyarıları susturmak düzeltme değildir:** `# nosec`, `# pylint: disable` veya `# noqa` yalnızca yanlış pozitif kararı gerekçeyle bulgu kaydına yazıldıktan sonra ve PR'da açıkça belirtilerek eklenebilir. Raporda "susturulan" ve "düzeltilen" uyarılar ayrı sayılır.
- **K7 — Gömülü üçüncü taraf kod:** `cps/cw_login/` ve `cps/cw_advocate/` gömülü üçüncü taraf koddur. Kapsamda kalır (başlangıç taraması bunları içeriyor), bulgu kaydında "Gömülü üçüncü taraf (K7): kapsamda, incelendi, düzeltme yapılmaz." olarak işaretlenir, bu klasörlerde düzeltme yapılmaz; yalnızca incelenir.
- **K8 — Bandit baseline sürüm düzeltmesi:** Başlangıç Bandit raporları yanlışlıkla 1.8.6 ile üretildi (kök neden: Windows dışı (macOS) ortamda sürüm belirtilmeden kurulum; o anki Python sürümü kayıtlı değil). Kod değişikliği yapılmadan önce aynı commit ve aynı parametrelerle 1.9.4 ile yeniden üretildi. Orijinaller `evidence/bandit-1.8.6-original/` altında. Bu, "baseline yeniden üretilmez" kuralına tek seferlik istisnadır (ekip onayı 28 Ekim).
- **K9 — Yalıtılmış davranış denemeleri:** Bir bulgunun doğrulanması için uygulamayı başlatmadan, tek bir kütüphane ya da fonksiyon davranışını küçük bir Python parçasıyla denemek serbesttir (ör. zipfile'ın bozuk arşivde hangi istisnayı fırlattığı, SQLAlchemy istisna öznitelikleri). Bu durumda gerekçeye "yalıtılmış deneme ile doğrulandı" yazılır ve yöntem raporda belirtilir. Uygulama, veritabanı veya ağ servisleri çalıştırılmaz (K2).

## Ekip ve sorumluluklar

| Kişi | GitHub | Alan | Ana teslim | Rehber |
| --- | --- | --- | --- | --- |
| 1. kişi — Şeyda Altın (repo sahibi) | `sseydaltin` | Repo/dallar/PR birleştirme, mimari ve kapsam dokümanı, Pylint ve PEP 8 (flake8) başlangıç/son taraması, seçilmiş kod kalitesi/PEP 8 düzeltmeleri | `project-scope.md`, `architecture.md`, Pylint/PEP 8 raporları, özetleri ve karşılaştırmaları | `docs/guides/rol-1-pylint-pep8.md` |
| 2. kişi — Dilara Yıldırım | `dilarayldrmm` | Bandit taramaları, risk sınıflandırması, **bulgu kaydının sahibi** (ID dağıtımı, biçim kontrolü), B113 güvenlik düzeltme planı | Bandit raporları, `findings-register.csv`, `bandit-summary.md`, `bandit-comparison.md` | `docs/guides/rol-2-bandit-kayit.md` |
| 3. kişi — Emre Bulut | `emjebulut` | Kimlik doğrulama, oturum, parola, kullanıcı/yönetici yetkilendirmesi, CSRF | `review-auth.md`, ilgili bulgu satırları ve düzeltmeler | `docs/guides/rol-3-yetki.md` |
| 4. kişi — Hasan Kurt | `kurtmhasan` | Kitap yükleme/indirme, dosya yolları, arşivler, dönüştürme, harici süreç ve ağ çağrıları | `review-file-handling.md`, ilgili bulgu satırları ve düzeltmeler | `docs/guides/rol-4-dosya-surec.md` |

Not: Bandit başlangıç envanteri ve `review-bandit.md` 3. kişi (Emre Bulut) tarafından hazırlandı; 2. kişi bulgu kaydı sorumluluğunu sürdürür.

**Ortak kural:** Her bulgunun bir inceleme sahibi ve bir gözden geçireni olur (`inceleyen ≠ gozden_geciren`). Düzeltmeyi yapan kişi neden güvenli olduğunu açıklar. Son taramayı düzeltmeyi yapmayan farklı bir üye kontrol eder.

## Değişmez kurallar

1. **Başlangıç raporları commit edilmeden `cps/` veya `cps.py` içinde hiçbir kaynak kod değişikliği yapma.** Kontrol: `reports/baseline/` içinde `bandit-cps.json`, `bandit-entrypoint.json`, `pylint.txt` ve `pep8.txt` var mı? (28 Ekim itibarıyla dördü de var.)
2. `master` dalına asla commit veya push yapma. Ana çalışma dalı `project-analysis`. `project-analysis`'e de doğrudan commit atma; her değişiklik dal + PR ile gelir (istisna: yalnızca 1. kişinin onayıyla tek satırlık kural/doküman düzeltmeleri).
3. Upstream'e (`janeczku/calibre-web`) asla push yapma veya PR açma. PR'ların **base repository** değeri her zaman `sseydaltin/calibre-web` olmalı.
   - PR'lar her zaman şu link biçimiyle açılır: `https://github.com/sseydaltin/calibre-web/compare/project-analysis...DAL_ADI` — GitHub'ın varsayılan "Compare & pull request" butonu ve `git push` çıktısındaki `/pull/new/...` linki fork'larda upstream'i hedefler, kullanma ve kullanıcıya önerme.
4. `LICENSE`, `README.md`, `SECURITY.md` ve lisans başlıklarını silme.
5. Şunları asla commit etme: `.venv/`, `venv/`, `__pycache__/`, `*.py[cod]`, loglar, `app.db`, `gdrive.db`, `client_secrets.json`, kişisel e-kitaplar, gerçek bir Calibre kitaplığı, gizli anahtarlar/tokenlar. `git add .` yerine dosyaları adıyla ekle ve commit öncesi `git status` çıktısını kullanıcıya göster.
6. Rapor ve ekran görüntülerinde kişisel veri, kullanıcı adı/şifre, yerel tam yol gibi bilgileri kontrol et; varsa maskele.
7. Uygulamayı internete açık şekilde çalıştırma. Çalıştırmak gerekirse yalnızca `127.0.0.1` üzerinde, örnek/boş kitaplıkla.
8. Bandit uyarısı tek başına doğrulanmış açık değildir; Pylint uyarısı otomatik olarak güvenlik açığı değildir. Uygulamada açık olduğunu önceden varsayma; her önemli bulguyu kod üzerinden gerekçelendir.
9. Pylint'in import/bağımlılık hatalarını (`E0401 import-error` vb.) güvenlik bulgusu sayma; ortam sorunu olarak `docs/environment-notes.md` dosyasına ayrı kaydet.
10. Commit, push, PR açma ve dal silme gibi geri alınması zor işlemlerden önce kullanıcıdan onay al.
11. `reports/baseline/` içindeki dosyaları asla değiştirme veya yeniden üretme (tek istisna K8, kapandı).
12. 8 Kasım kod dondurmasından sonra `cps/` veya `cps.py` değiştiren PR birleştirilmez.

## Dosya yapısı

```
.github/
  pull_request_template.md  # PR açıklama şablonu (GitHub otomatik getirir)
docs/
  guides/                   # rol rehberleri: ortak.md, rol-1…rol-4
  baseline-commit.txt       # analiz edilen upstream commit SHA
  project-scope.md          # 1. kişi: amaç, kapsam, büyüklük, roller, sınırlılıklar
  architecture.md           # 1. kişi: dizin yapısı, ana modüller, istek akışı, güvenlik haritası
  environment-notes.md      # araç sürümleri, kurulum sorunları, tarama kayıtları
  pylint-baseline-summary.md, pep8-baseline-summary.md   # 1. kişi
  bandit-summary.md         # 2. kişi (betikle üretilir)
  findings-register.csv     # 2. kişi yönetir, herkes katkı verir
  review-bandit.md          # Bandit bulgularının manuel değerlendirmesi
  review-auth.md            # 3. kişi
  review-file-handling.md   # 4. kişi
  pylint-comparison.md, pep8-comparison.md   # 1. kişi: önce-sonra
  bandit-comparison.md      # 2. kişi: önce-sonra
  final-report.md           # ortak
reports/
  baseline/                 # başlangıç çıktıları — DOKUNMA
  final/                    # son tarama çıktıları
evidence/
  bandit-1.8.6-original/    # K8: yanlış sürümle üretilmiş ilk Bandit raporları
  screenshots/
scripts/                    # özet/karşılaştırma betikleri (ham raporları değiştirmez)
requirements-analysis.txt
requirements-lock.txt       # .venv'in tam dondurulmuş hali; ekip kurulumunda kullanılır (python-ldap/Flask-SimpleLDAP hariç)
```

## Gerekli `.gitignore` kuralları

Upstream `.gitignore` dosyası `.venv/` klasörünü yok saymıyor. Aşağıdaki blok `.gitignore` dosyasının **sonuna** eklenmiştir (tekrar eklenmez):

```
# Local analysis environment and private data
.venv/
venv/
__pycache__/
*.py[cod]
*.log
app.db
gdrive.db
client_secrets.json
```

Kontrol: `git status` çıktısında `.venv/` görünmemeli. `git check-ignore -v .venv app.db` her ikisi için de bir kural satırı göstermeli.

## Ortam kurulumu (her ekip üyesi için)

Önce Python sürümünü kontrol et: `py --version` **3.12.x** olmalı (en az 3.10; Bandit 1.9 serisi 3.10 altında kurulmaz, pip sessizce eski sürüme düşer; K8'deki yanlış sürüm de sürüm belirtilmeden yapılan kurulumdan kaynaklandı). Varsayılan `py` farklı bir sürümse sanal ortamı `py -3.12 -m venv .venv` ile oluştur. **Araç sürümleri (aşağıdaki `--version` komutları) doğrulanmadan tarama yapılmaz.**

```powershell
py --version                 # 3.12.x olmalı (en az 3.10)
cd $HOME\Projeler
git clone https://github.com/sseydaltin/calibre-web.git
cd calibre-web
git switch project-analysis
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-lock.txt
python -m bandit --version   # 1.9.4 olmalı
python -m pylint --version   # 4.1.3 olmalı
python -m flake8 --version   # 7.4.1 olmalı
```

`requirements-lock.txt`, analiz ortamının (`requirements-analysis.txt` + Calibre-Web `requirements.txt` + `optional-requirements.txt`, LDAP paketleri hariç) tam dondurulmuş (lock) halidir ve K3 kararı gereği tek komutla kurulur. Ayrı ayrı `requirements-analysis.txt`/`requirements.txt`/`optional-requirements.txt` kurmaya gerek yoktur; bu üç dosya yalnızca kaynak/kapsam referansı olarak kalır.

`python-ldap` ve `Flask-SimpleLDAP`, Windows'ta eksik OpenLDAP C başlık dosyaları (`lber.h`) yüzünden derlenemediği için `requirements-lock.txt` içinde **yoktur** (bkz. dosyanın başındaki yorum ve `docs/environment-notes.md`). LDAP girişi özelliğine ait kod (`cps/` içinde) yine de taranır; bu iki modüle ait Pylint `import-error` uyarıları ortam sorunu sayılır, güvenlik/kod kalitesi bulgusu sayılmaz.

`Activate.ps1` engellenirse: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

Komutları her zaman depo kök dizininde ve `.venv` etkin iken çalıştır.

## Tarama komutları (parametreleri DEĞİŞTİRME)

Başlangıç ve son taramada aynı araç sürümü, aynı kapsam ve aynı parametreler kullanılır.

**Başlangıç** (tamamlandı; yeniden çalıştırılmaz — kural 11):
```powershell
python -m bandit -r cps -f json -o reports\baseline\bandit-cps.json
python -m bandit cps.py -f json -o reports\baseline\bandit-entrypoint.json
python -m pylint cps.py cps --output=reports\baseline\pylint.txt
python -m flake8 --isolated --select=E,W --statistics --count --output-file=reports\baseline\pep8.txt cps.py cps
```

**Son** (7 Kasım):
```powershell
python -m bandit -r cps -f json -o reports\final\bandit-cps.json
python -m bandit cps.py -f json -o reports\final\bandit-entrypoint.json
python -m pylint cps.py cps --output=reports\final\pylint.txt
python -m flake8 --isolated --select=E,W --statistics --count --output-file=reports\final\pep8.txt cps.py cps
```

PowerShell 5'te `>` yönlendirmesi dosyayı UTF-16 olarak yazar. Bu yüzden rapor üretirken her zaman aracın kendi çıktı seçeneğini (`-o`, `--output`, `--output-file`) kullan.

Notlar:
- Bandit/Pylint/flake8 uyarı bulunca sıfırdan farklı çıkış kodu verir; bu hata değildir. Her komuttan sonra rapor dosyasının oluştuğunu ve boş olmadığını kontrol et.
- Her taramanın tarihini, araç sürümünü ve çıkış kodunu `docs/environment-notes.md` → "Tarama kayıtları" bölümüne yaz.
- Okunabilir özetler JSON/TXT çıktılarından `scripts/` altındaki betiklerle türetilir; ham raporlar değiştirilmez.
- Yol ayracı: Windows'ta üretilen raporlarda `cps\...`, bulgu kaydında `cps/...` kullanılır. Karşılaştırma betikleri yolları normalize etmeli.

## Dal ve commit düzeni

- Ana entegrasyon dalı: `project-analysis`.
- Her iş için ondan yeni dal aç:
  - Doküman/kayıt: `docs/pylint-findings`, `docs/review-auth`, `docs/review-file-handling`
  - Tarama: `scan/final`
  - Düzeltme: `fix/find-014` (bulgu ID'si ile birebir; aynı türden küçük grup tek dalda olabilir, dal adında ilk ID kullanılır)
- Birleştirme: `project-analysis` hedefli Pull Request + en az bir ekip üyesinin incelemesi. Ayrıntılı akış: `docs/guides/ortak.md`.
- Commit mesajı biçimi: `<tür>: <kısa açıklama>` — türler: `docs`, `scan`, `fix`, `chore`.
  - Örn. `docs: add pylint findings to register`, `fix(FIND-014): add timeout to goodreads request`
- Bir düzeltme commit'i yalnızca tek bir bulguyu (veya aynı türden küçük bir grubu) kapsar; ilgisiz biçim değişiklikleri karıştırılmaz.

## Bulgu kaydı: `docs/findings-register.csv`

UTF-8 (BOM'lu, Excel uyumu için), CRLF satır sonları, virgülle ayrılmış. Excel'de açıp kaydetme. Satır sonu `.gitattributes` ile CRLF'ye sabitlendi; satır sonu farkı tek başına değişiklik olarak commit edilmez. Sütunlar sırasıyla:

```
id,kaynak,kural_kodu,dosya,satir,fonksiyon,arac_onem,arac_guven,ekip_onem,dogrulama_sonucu,gerekce,onerilen_duzeltme,durum,commit_pr,son_tarama_sonucu,inceleyen,duzelten,gozden_geciren
```

- `id`: `FIND-001`, `FIND-002`… sırayla, asla yeniden kullanılmaz. **Yeni ID'leri 2. kişi (Dilara) dağıtır**; mevcut kayıt FIND-001…044. ID blokları (28 Ekim ekip kararı); herkes kendi bloğunu sırayla kullanır, blok biterse Dilara'dan ek aralık ister:

  | Kişi | Blok |
  | --- | --- |
  | Şeyda Altın (1. kişi, Pylint/PEP 8) | FIND-045–FIND-124 |
  | Emre Bulut (3. kişi, yetki) | FIND-125–FIND-149 |
  | Hasan Kurt (4. kişi, dosya/süreç) | FIND-150–FIND-174 |
  | Dilara Yıldırım (2. kişi, yedek) | FIND-175–FIND-199 |
- `inceleyen`, `duzelten`, `gozden_geciren`: rol numarası değil **ad soyad** yazılır (örn. `Emre Bulut`); henüz belli değilse `-`.
- `kaynak`: `Bandit` / `Pylint` / `PEP8` (flake8) / `Manuel`.
- `kural_kodu`: örn. `B602`, `W0703`, `E501`; manuel ise `-`.
- `dosya`: depo köküne göre yol, `/` ile (örn. `cps/helper.py`).
- `arac_onem` / `arac_guven`: Bandit için `LOW/MEDIUM/HIGH`; Pylint için mesaj türü (`convention/refactor/warning/error/fatal/information`), güven `-`; flake8 ve manuel için `-`.
- `ekip_onem`: `Yüksek` / `Orta` / `Düşük`.
- `dogrulama_sonucu`: `Gerçek sorun` / `Yanlış pozitif` / `Düşük öncelikli uyarı` / `İnceleniyor`.
- `durum`: `Açık` / `Düzeltildi` / `Kabul edildi (düzeltilmeyecek)` / `Yanlış pozitif`.
- Pylint/flake8'in yüzlerce benzer stil uyarısını tek tek satır yapma: aynı kural kodunu tek satırda grupla ve `satir` alanına `çoklu (N adet)` yaz; yalnızca düzeltilmek üzere seçilenleri ayrı satır olarak aç.
- K7 klasörlerinden gelen satırlarda gerekçe "Gömülü üçüncü taraf (K7): kapsamda, incelendi, düzeltme yapılmaz." ile başlar.

## Manuel inceleme odakları

Ayrıntılı kontrol listeleri ve şablonlar rehberlerdedir (`rol-3-yetki.md`, `rol-4-dosya-surec.md`). Kısaca:

- **3. kişi (yetki):** `cps/usermanagement.py`, `cps/web.py` (login/logout), `cps/admin.py`, `cps/ub.py`, `cps/oauth*.py`, `cps/kobo_auth.py`, `cps/remotelogin.py`; yetki dekoratörleri, parola saklama, oturum/çerez ayarları, CSRF, açık yönlendirme.
- **4. kişi (dosya/süreç):** `cps/uploader.py`, `cps/editbooks.py`, `cps/helper.py`, `cps/file_helper.py`, `cps/tasks/convert.py`, `cps/subproc_wrapper.py`, `cps/gdriveutils.py`, `cps/updater.py`, `cps/comic.py`; yol birleştirme, `secure_filename`, `subprocess`, arşiv açma, indirme yanıtları.
- Dosya ve fonksiyon adlarını önce kodda doğrula (`docs/architecture.md` 5. bölüm doğrulanmış listedir).

Her inceleme notunda: dosya:satır, ne kontrol edildi, gözlem, sonuç (sorun yok / düşük öncelikli / gerçek sorun), ilgili FIND-ID.

## Düzeltme yaparken

1. Bulgu `findings-register.csv` içinde `Gerçek sorun` olarak işaretlenmiş ve 1 Kasım toplantısında seçilmiş olmalı.
2. K7 klasörlerinde düzeltme yapılmaz.
3. Değişikliği en küçük, davranışı koruyan biçimde yap. Önceki kod / yeni kod / gerekçe / doğrulama dörtlüsünü PR açıklamasına yaz (`.github/pull_request_template.md`).
4. Doğrulama: `python -m py_compile cps\<dosya>.py` ve ilgili araçla dosya bazlı tarama (`bandit`, `pylint` veya `flake8 --isolated --select=E,W`). Uyarı kapanmalı, yeni uyarı çıkmamalı.
5. Bulgu kaydında `durum`, `commit_pr`, `duzelten` alanlarını aynı PR'da güncelle.

## Önce-sonra karşılaştırması

Karşılaştırma raporlarında ayrı ayrı belirt: **kapanan**, **devam eden** ve **yeni oluşan** uyarılar. Bandit için kural kodu + önem düzeyine, Pylint için mesaj kodu + toplam puana (score), flake8 için kod + toplam ihlale göre tablo yap. Satır numaraları kayar; eşleştirmeyi normalize yol + kural kodu + kod parçası üzerinden yap. Susturulan ve düzeltilen uyarıları ayrı say (K6).

## Takvim (kontrol noktaları)

| Tarih | Çıktı | Durum |
| --- | --- | --- |
| 24 Eki | Fork, collaborator'lar, `project-analysis` dalı, ortam | ✅ |
| 25 Eki | `project-scope.md`, `architecture.md` | ✅ |
| 26 Eki | Herkeste çalışan analiz ortamı | ✅ |
| 27 Eki | Bandit başlangıç raporları | ✅ (K8 ile 28 Ekim'de 1.9.4) |
| 28 Eki | Pylint ve PEP 8 başlangıç raporları | ✅ |
| 29–30 Eki | Yetki ve dosya işleme manuel inceleme notları | |
| 31 Eki | Bulgu envanteri tamam (Pylint/PEP 8 + manuel satırlar), B113 planı | |
| 1 Kas | Önceliklendirilmiş düzeltme listesi (toplantı) | |
| 2–5 Kas | Düzeltme PR'ları ve incelemeler | |
| 6 Kas | Düzeltilen dosyalarda `py_compile` + dosya bazlı tekrar tarama (K2) | |
| 7 Kas | Son taramalar (`reports/final/`) | |
| 8 Kas | Önce-sonra karşılaştırması, **kod dondurma** | |
| 9–10 Kas | Rapor, sunum, prova, teslim | |

Gecikmede öncelik: bulgu değerlendirmesi → en anlamlı düzeltmeler → tekrar tarama → rapor/sunum.
