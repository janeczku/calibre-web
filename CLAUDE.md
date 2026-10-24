# CLAUDE.md — Calibre-Web Statik Kod Analizi Projesi

Bu dosya, ekipteki herkesin Claude Code oturumları için ortak çalışma kurallarını tanımlar.
Proje dili **Türkçe**dir: dokümanları, bulgu kayıtlarını ve kullanıcıya verilen açıklamaları Türkçe yaz.
Kod, değişken adları, commit önekleri ve dal adları İngilizce kalır.

## Proje özeti

- **Amaç:** Calibre-Web'i sıfırdan geliştirmek değil. Seçilen Python kodunu Bandit (güvenlik) ve Pylint (kod kalitesi) ile analiz etmek, önemli bulguları elle doğrulamak, seçilmiş sorunları güvenli biçimde düzeltmek ve başlangıç/son taramalarını karşılaştırıp raporlamak.
- **Dönem:** 24 Ekim – 10 Kasım 2026. **8 Kasım sonunda kod dondurulur**; 9–10 Kasım yalnızca rapor, sunum ve prova içindir.
- **Ekip deposu (fork):** https://github.com/sseydaltin/calibre-web
- **Resmî kaynak (upstream):** https://github.com/janeczku/calibre-web
- **Lisans:** GPL v3. `LICENSE` dosyasını ve kaynak koddaki lisans/telif bildirimlerini asla silme veya değiştirme.
- **Analiz edilen commit:** `docs/baseline-commit.txt` içinde kayıtlı (upstream `master`, `6e840ac…`).
- **Ortam:** Windows, PowerShell, Python 3.12.10, sanal ortam `.venv`.
- **Araç sürümleri (sabit):** `requirements-analysis.txt` → bandit 1.9.4, pylint 4.1.3, astroid 4.3.4, flake8 7.4.1 (PEP 8 kontrolü için). Tüm ortamın tam kopyası `requirements-lock.txt` içindedir; ekip kurulumunda kullanılan dosya budur (bkz. "Ortam kurulumu").

## Ders gereksinimleri ve ekip kararları

Ders: **"Güvenlik İçin Statik Kod Analizi"**. Kodlar **çalıştırılmadan**, statik analiz araçlarıyla incelenir. Her karar aşağıdaki 9 maddeye hizmet etmelidir:

| # | Ders gereksinimi | Nasıl karşılanıyor | Sorumlu | Çıktı |
| --- | --- | --- | --- | --- |
| 1 | Yeterli büyüklükte Python projesi seçimi ve yapısının tanıtımı | Calibre-Web; kapsam `cps/` + `cps.py`. Büyüklük, dosya ve satır sayısıyla (LOC) gerekçelendirilir | 1. kişi | `project-scope.md`, `architecture.md` |
| 2 | Pylint ile kalite analizi, başlangıç sonuçlarının kaydı | Kod değişikliğinden önce Pylint taraması, puan ve kategori dağılımı | 1. kişi | `reports/baseline/pylint.txt` |
| 3 | Bandit ile güvenlik analizi, risk düzeyine göre sınıflandırma | Önem (LOW/MEDIUM/HIGH) × güven (LOW/MEDIUM/HIGH) matrisi ve kural kodu dağılımı | 2. kişi | `reports/baseline/bandit-*.json`, `bandit-summary.md` |
| 4 | Yüksek/önemli güvenlik bulgularının kod satırlarıyla incelenmesi | Tüm HIGH ve MEDIUM önemli bulgular ile 3. ve 4. kişinin alanındaki bulgular kod parçasıyla incelenir | 2., 3. ve 4. kişi | `review-*.md` |
| 5 | PEP 8 ve temel kodlama standardı problemleri | Pylint `convention` kategorisi + flake8 ile saf PEP 8 (E/W) taraması | 1. kişi | `reports/baseline/pep8.txt`, `pep8-summary.md` |
| 6 | Gerçek problem / düşük öncelikli / yanlış pozitif ayrımı | Her bulgu için `dogrulama_sonucu` + `gerekce` alanları zorunlu | Herkes | `findings-register.csv` |
| 7 | Seçilen sorunların düzeltilmesi; önceki ve yeni kod karşılaştırması | `fix/find-XXX` dalları; PR açıklamasında önceki kod / yeni kod / gerekçe | Herkes | PR'lar, `final-report.md` |
| 8 | Araçların yeniden çalıştırılması ve karşılaştırma | Aynı sürüm, aynı kapsam ve aynı parametrelerle son tarama | 1. ve 2. kişi | `reports/final/`, `*-comparison.md` |
| 9 | Rapor: araçlar, önemli bulgular, düzeltmeler, yeniden analiz | Final raporu bu 9 maddeye göre bölümlenir | Ortak | `final-report.md` |

**Alınan kararlar** (değiştirmek için ekip onayı gerekir; değişiklikler buraya yazılır):

- **K1 — Proje ve kapsam:** Calibre-Web, upstream commit `docs/baseline-commit.txt` içinde. Otomatik tarama kapsamı `cps/` ve `cps.py`. `test/`, `library/`, JS/CSS/HTML şablonları kapsam dışı.
- **K2 — Uygulama çalıştırılmaz:** Analiz tamamen statiktir. Düzeltmeler `py_compile` ve araçların yeniden çalıştırılmasıyla doğrulanır. Uygulamayı çalıştırmak yalnızca bir düzeltmenin davranışını göstermek için gerekirse, yerelde (`127.0.0.1`) ve boş örnek kitaplıkla yapılır.
- **K3 — Bağımlılıklar kurulur:** Calibre-Web'in `requirements.txt` bağımlılıkları, başlangıç taramasından **önce** `.venv` ortamına kurulur ve `pip freeze` çıktısı `docs/environment-notes.md` dosyasına yazılır. Amaç Pylint'in importları çözebilmesidir; kod çalıştırılmaz. Son taramada aynı ortam kullanılır.
- **K4 — Araç ayarları:** Bandit varsayılan ayarlarla tüm testleri çalıştırır (skip veya `# nosec` eklenmez). Pylint repo içinde bir yapılandırma dosyası (`.pylintrc`, `pylintrc`, `pyproject.toml`, `setup.cfg`) varsa onu kullanır; ayar değiştirilmez ve hangi dosyanın kullanıldığı `environment-notes.md` dosyasına yazılır. flake8 `--isolated` ile saf PEP 8 varsayılanlarında (satır uzunluğu 79) ve yalnızca `E,W` kodlarıyla çalışır.
- **K5 — Düzeltme hedefi:** En az **3 güvenlik** bulgusu düzeltilir veya kanıtla yanlış pozitif gösterilir. En az **5 kod kalitesi / PEP 8** bulgu türü düzeltilir. Düzeltmeler küçük ve davranışı koruyan değişikliklerdir. Binlerce stil uyarısını toplu biçimlendirme (black/autopep8 ile tüm projeyi yeniden biçimlendirme) **yapılmaz**, çünkü önce-sonra karşılaştırmasını anlamsızlaştırır ve diff'i okunmaz hale getirir.
- **K6 — Uyarıları susturmak düzeltme değildir:** `# nosec`, `# pylint: disable` veya `# noqa` yalnızca yanlış pozitif kararı gerekçeyle bulgu kaydına yazıldıktan sonra ve PR'da açıkça belirtilerek eklenebilir. Raporda "susturulan" ve "düzeltilen" uyarılar ayrı sayılır.

## Ekip ve sorumluluklar

| Kişi | Alan | Ana teslim |
| --- | --- | --- |
| 1. kişi — Şeyda Altın (repo sahibi) | Repo/dallar, mimari ve kapsam dokümanı, Pylint ve PEP 8 (flake8) başlangıç/son taraması, seçilmiş PEP 8/kod kalitesi düzeltmeleri | `docs/project-scope.md`, `docs/architecture.md`, Pylint ve PEP 8 raporları ve önce-sonra karşılaştırması |
| 2. kişi | Bandit taramaları (`cps/` ve `cps.py`), bulgu envanteri, yanlış pozitif gerekçeleri | Bandit raporları, `docs/findings-register.csv`, manuel değerlendirme notları |
| 3. kişi | Kimlik doğrulama, oturum, parola, kullanıcı/yönetici yetkilendirmesi | `docs/review-auth.md`, düzeltme kanıtları |
| 4. kişi | Kitap yükleme/indirme, dosya yolları, dönüştürme, harici süreç çağrıları | `docs/review-file-handling.md`, doğrulama kanıtları |

Ekip üyeleri GitHub'da: `dilarayldrmm`, `emjebulut`, `kurtmhasan` (kişi–rol eşleşmesi ekip tarafından `docs/project-scope.md` içine yazılır).

**Ortak kural:** Her bulgunun bir inceleme sahibi ve bir gözden geçireni olur. Düzeltmeyi yapan kişi neden güvenli olduğunu açıklar. Son taramayı düzeltmeyi yapmayan farklı bir üye kontrol eder.

Bir oturuma başlarken kullanıcıya hangi kişi olduğunu sor (belli değilse) ve o kişinin alanına odaklan.

## Değişmez kurallar

1. **Başlangıç raporları üretilip commit edilmeden `cps/` veya `cps.py` içinde hiçbir kaynak kod değişikliği yapma.** Kontrol: `reports/baseline/` içinde `bandit-cps.json`, `bandit-entrypoint.json` ve `pylint.txt` var mı?
2. `master` dalına asla commit veya push yapma. Ana çalışma dalı `project-analysis`.
3. Upstream'e (`janeczku/calibre-web`) asla push yapma veya PR açma. PR'ların **base repository** değeri her zaman `sseydaltin/calibre-web` olmalı.
4. `LICENSE`, `README.md`, `SECURITY.md` ve lisans başlıklarını silme.
5. Şunları asla commit etme: `.venv/`, `venv/`, `__pycache__/`, `*.py[cod]`, loglar, `app.db`, `gdrive.db`, `client_secrets.json`, kişisel e-kitaplar, gerçek bir Calibre kitaplığı, gizli anahtarlar/tokenlar. `git add .` yerine dosyaları adıyla ekle ve commit öncesi `git status` çıktısını kullanıcıya göster.
6. Rapor ve ekran görüntülerinde kişisel veri, kullanıcı adı/şifre, yerel tam yol gibi bilgileri kontrol et; varsa maskele.
7. Uygulamayı internete açık şekilde çalıştırma. Çalıştırmak gerekirse yalnızca `127.0.0.1` üzerinde, örnek/boş kitaplıkla.
8. Bandit uyarısı tek başına doğrulanmış açık değildir; Pylint uyarısı otomatik olarak güvenlik açığı değildir. Uygulamada açık olduğunu önceden varsayma; her önemli bulguyu kod üzerinden gerekçelendir.
9. Pylint'in import/bağımlılık hatalarını (`E0401 import-error` vb.) güvenlik bulgusu sayma; ortam sorunu olarak `docs/environment-notes.md` dosyasına ayrı kaydet.
10. Commit, push, PR açma ve dal silme gibi geri alınması zor işlemlerden önce kullanıcıdan onay al.

## Dosya yapısı

```
docs/
  baseline-commit.txt       # analiz edilen upstream commit SHA
  project-scope.md          # 1. kişi: amaç, kapsam, ekip/rol eşleşmesi, kapsam dışı
  architecture.md           # 1. kişi: dizin yapısı, ana modüller, istek akışı
  environment-notes.md      # araç sürümleri, kurulum sorunları, import hataları
  findings-register.csv     # 2. kişi yönetir, herkes katkı verir
  review-auth.md            # 3. kişi
  review-file-handling.md   # 4. kişi
  pylint-comparison.md      # 1. kişi: önce-sonra
  bandit-comparison.md      # 2. kişi: önce-sonra
  final-report.md           # ortak
reports/
  baseline/                 # başlangıç çıktıları — kod değişikliğinden önce, sonra DOKUNMA
  final/                    # son tarama çıktıları
evidence/
  screenshots/
requirements-analysis.txt
requirements-lock.txt        # .venv'in tam dondurulmuş hali; ekip kurulumunda kullanılır (python-ldap/Flask-SimpleLDAP hariç)
```

`reports/baseline/` içindeki dosyalar oluşturulup commit edildikten sonra asla yeniden üretilmez veya düzenlenmez.

## Gerekli `.gitignore` kuralları

Upstream `.gitignore` dosyası `.venv/` klasörünü yok saymıyor. Aşağıdaki blok `.gitignore` dosyasının **sonuna** eklenmeli. Var olan satırlar silinmez; blok zaten eklenmişse tekrar eklenmez:

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

```powershell
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

**Başlangıç:**
```powershell
python -m bandit -r cps -f json -o reports\baseline\bandit-cps.json
python -m bandit cps.py -f json -o reports\baseline\bandit-entrypoint.json
python -m pylint cps.py cps --output=reports\baseline\pylint.txt
python -m flake8 --isolated --select=E,W --statistics --count --output-file=reports\baseline\pep8.txt cps.py cps
```

**Son:**
```powershell
python -m bandit -r cps -f json -o reports\final\bandit-cps.json
python -m bandit cps.py -f json -o reports\final\bandit-entrypoint.json
python -m pylint cps.py cps --output=reports\final\pylint.txt
python -m flake8 --isolated --select=E,W --statistics --count --output-file=reports\final\pep8.txt cps.py cps
```

PowerShell 5'te `>` yönlendirmesi dosyayı UTF-16 olarak yazar. Bu yüzden rapor üretirken her zaman aracın kendi çıktı seçeneğini (`-o`, `--output`, `--output-file`) kullan.

Notlar:
- Bandit/Pylint uyarı bulunca sıfırdan farklı çıkış kodu verir; bu hata değildir. Her komuttan sonra rapor dosyasının oluştuğunu ve boş olmadığını kontrol et.
- Her taramanın tarihini, araç sürümünü ve çıkış kodunu `docs/environment-notes.md` dosyasına yaz.
- Okunabilir özetler (kural kodu/önem dağılımı tabloları) JSON/TXT çıktılarından Python ile türetilir; ham raporlar değiştirilmez. Özet betikleri gerekiyorsa `scripts/` klasörüne koy.
- Pylint'in import hatalarını azaltmak için Calibre-Web bağımlılıklarını (`requirements.txt`) kurmak ekip kararıdır. Kurulursa **başlangıç taramasından önce** kurulmalı ve son taramada da aynı ortam kullanılmalıdır; karar `environment-notes.md` içine yazılır.

## Dal ve commit düzeni

- Ana entegrasyon dalı: `project-analysis`.
- Her iş için ondan yeni dal aç:
  - Doküman: `docs/project-scope`, `docs/architecture`, `docs/review-auth`
  - Tarama: `scan/baseline`, `scan/final`
  - Düzeltme: `fix/find-001` (bulgu ID'si ile birebir)
- Birleştirme: `project-analysis` hedefli Pull Request + en az bir ekip üyesinin incelemesi.
- Commit mesajı biçimi: `<tür>: <kısa açıklama>` — türler: `docs`, `scan`, `fix`, `chore`.
  - Örn. `scan: add baseline bandit and pylint reports`, `fix(FIND-007): use subprocess without shell=True`
- Bir düzeltme commit'i yalnızca tek bir bulguyu (veya aynı türden küçük bir grubu) kapsar; ilgisiz biçim değişiklikleri karıştırılmaz.

## Bulgu kaydı: `docs/findings-register.csv`

UTF-8 (BOM'lu, Excel uyumu için) ve virgülle ayrılmış. Sütunlar sırasıyla:

```
id,kaynak,kural_kodu,dosya,satir,fonksiyon,arac_onem,arac_guven,ekip_onem,dogrulama_sonucu,gerekce,onerilen_duzeltme,durum,commit_pr,son_tarama_sonucu,inceleyen,duzelten,gozden_geciren
```

- `id`: `FIND-001`, `FIND-002`… sırayla, asla yeniden kullanılmaz.
- `kaynak`: `Bandit` / `Pylint` / `PEP8` (flake8) / `Manuel`.
- `kural_kodu`: örn. `B602`, `W0703`; manuel ise `-`.
- `dosya`: depo köküne göre yol, `/` ile (örn. `cps/helper.py`).
- `arac_onem` / `arac_guven`: Bandit için `LOW/MEDIUM/HIGH`; Pylint için mesaj türü (`convention/refactor/warning/error/fatal`), güven `-`.
- `ekip_onem`: `Yüksek` / `Orta` / `Düşük`.
- `dogrulama_sonucu`: `Gerçek sorun` / `Yanlış pozitif` / `Düşük öncelikli uyarı` / `İnceleniyor`.
- `durum`: `Açık` / `Düzeltildi` / `Kabul edildi (düzeltilmeyecek)` / `Yanlış pozitif`.
- Pylint'in yüzlerce benzer stil uyarısını tek tek satır yapma: aynı kural kodunu tek satırda grupla ve `satir` alanına `çoklu (N adet)` yaz; yalnızca düzeltilmek üzere seçilenleri ayrı satır olarak aç.

## Manuel inceleme odakları

- **3. kişi (yetki):** `cps/usermanagement.py`, `cps/web.py` (login/logout), `cps/admin.py`, `cps/ub.py` (kullanıcı modeli, parola özetleri), `cps/oauth*.py`, `cps/kobo_auth.py`, `cps/remotelogin.py`, `@login_required` / `@admin_required` / rol dekoratörlerinin kullanımı, oturum ve CSRF ayarları.
- **4. kişi (dosya/süreç):** `cps/uploader.py`, `cps/editbooks.py`, `cps/helper.py`, `cps/file_helper.py`, `cps/tasks/convert.py`, `cps/subproc_wrapper.py`, `cps/gdriveutils.py`, `cps/updater.py`; yol birleştirme, `secure_filename`, `subprocess` çağrıları, arşiv açma, indirme yanıtları.
- (Dosya adları upstream sürümüne göre değişebilir; önce `cps/` altını listeleyip doğrula.)

Her inceleme notunda: dosya/satır, ne kontrol edildi, gözlem, sonuç (sorun var/yok), ilgili FIND-ID.

## Düzeltme yaparken

1. Bulgu `findings-register.csv` içinde `Gerçek sorun` olarak işaretlenmiş ve seçilmiş olmalı.
2. Değişikliği en küçük, davranışı koruyan biçimde yap. Önceki kod / yeni kod / gerekçe üçlüsünü PR açıklamasına yaz.
3. Mümkünse ilgili dosyaya tek başına Bandit/Pylint çalıştırıp uyarının kapandığını göster:
   `python -m bandit cps\<dosya>.py` veya `python -m pylint cps\<dosya>.py`
4. Söz dizimi kontrolü: `python -m py_compile cps\<dosya>.py`.
5. Bulgu kaydında `durum`, `commit_pr`, `duzelten` alanlarını güncelle.

## Önce-sonra karşılaştırması

Karşılaştırma raporlarında ayrı ayrı belirt: **kapanan**, **devam eden** ve **yeni oluşan** uyarılar. Bandit için kural kodu + önem düzeyine, Pylint için mesaj kodu + toplam puana (score) göre tablo yap. Satır numaraları kod değiştiği için kayabilir; eşleştirmeyi dosya + kural kodu + kod parçası üzerinden yap.

## Takvim (kontrol noktaları)

| Tarih | Çıktı |
| --- | --- |
| 24 Eki | Fork, collaborator'lar, `project-analysis` dalı, ortam |
| 25 Eki | `project-scope.md`, `architecture.md` taslağı |
| 26 Eki | Herkeste çalışan analiz ortamı |
| 27 Eki | Bandit başlangıç raporları |
| 28 Eki | Pylint ve PEP 8 (flake8) başlangıç raporları |
| 29–30 Eki | Yetki ve dosya işleme manuel inceleme notları |
| 31 Eki | İlk bulgu envanteri |
| 1 Kas | Önceliklendirilmiş düzeltme listesi |
| 2–5 Kas | Düzeltme PR'ları ve incelemeler |
| 6 Kas | Düzeltilen dosyalarda `py_compile` + dosya bazlı tekrar tarama kontrolleri (K2) |
| 7 Kas | Son taramalar (`reports/final/`) |
| 8 Kas | Önce-sonra karşılaştırması, **kod dondurma** |
| 9–10 Kas | Rapor, sunum, prova, teslim |

Gecikmede öncelik: başlangıç taraması → bulgu değerlendirmesi → en anlamlı düzeltmeler → tekrar tarama → rapor/sunum.
