# Ortam notları

## Python ve araç sürümleri

- Python: 3.12.10 (Windows, `.venv` sanal ortamı)
- pip: 26.2.2
- bandit: 1.9.4
- pylint: 4.1.3 (astroid 4.3.4)
- flake8: 7.4.1 (pycodestyle 2.15.0, pyflakes 4.0.3, mccabe 0.7.0)

Sürümler `requirements-analysis.txt` içinde sabitlenmiştir.

## K3 — Calibre-Web bağımlılıklarının kurulumu

`requirements.txt` içindeki tüm çalışma zamanı bağımlılıkları, başlangıç taramasından **önce** `.venv` ortamına kuruldu (amaç: Pylint'in `import` ifadelerini çözebilmesi; uygulama çalıştırılmadı). Kurulum komutu:

```
python -m pip install -r requirements.txt
```

`optional-requirements.txt` içindeki isteğe bağlı bağımlılıklar da kurulmaya çalışıldı, çünkü bu özelliklere ait kod (`gdrive`, `gmail`, `goodreads`, `ldap`, `oauth`, `metadata`, `comics`, `kobo`) `cps/` içinde yer alıyor ve taranacak. Önce toplu kurulum denendi:

```
python -m pip install -r optional-requirements.txt
```

Bu komut **tamamen başarısız oldu**: `python-ldap` derleme hatası (Windows'ta eksik OpenLDAP C başlık dosyaları, `lber.h`) yüzünden pip, atomik kurulum davranışıyla hiçbir paketi kurmadı (`pip freeze` öncesi/sonrası fark yok). Bunun üzerine `optional-requirements.txt`'deki her paket **tek tek** kuruldu (`python -m pip install "<paket>"`). 30 pakette 28'i başarıyla kuruldu; 2'si başarısız oldu (aşağıda "Kurulamayan paketler" bölümünde).

Son taramada (7 Kas) aynı `.venv` ortamı kullanılacak; ortam yeniden kurulmayacak.

### `pip freeze` çıktısı (tüm kurulumlar sonrası)

```
alabaster==1.0.0
anyio==4.15.1
APScheduler==3.11.3
arrow==1.4.0
astroid==4.3.4
attrs==26.1.0
babel==2.18.0
backports.zstd==1.8.0
bandit==1.9.4
beautifulsoup4==4.15.0
bibtexparser==2.1.0
blinker==1.9.0
brotli==1.2.1
certifi==2026.5.20
cffi==2.1.1
chardet==5.2.0
charset-normalizer==3.5.2
click==8.5.0
colorama==0.4.6
comicapi==3.2.0
cryptography==43.0.3
Deprecated==3.0.0
dill==0.4.1
docutils==0.22.4
fake-useragent==2.2.0
faust-cchardet==2.1.19
flake8==7.4.1
Flask==3.1.3
flask-babel==4.0.0
Flask-Dance==7.1.0
Flask-HTTPAuth==4.8.1
Flask-Limiter==4.1.1
Flask-Principal==0.4.0
Flask-Themes2==1.0.1
Flask-WTF==1.3.0
free_proxy==1.3.0
gevent==25.9.1
goodreads==0.3.2
google-api-core==2.43.0
google-api-python-client==2.199.0
google-auth==2.62.0
google-auth-httplib2==0.4.4
google-auth-oauthlib==1.2.4
googleapis-common-protos==1.76.0
greenlet==3.5.6
h11==0.16.0
html2text==2025.4.15
httpcore==1.0.9
httplib2==0.32.0
httpx==0.28.1
idna==3.20
imagesize==2.0.1
importlib_metadata==9.0.0
inflate64==1.0.4
isort==9.0.2
itsdangerous==2.2.0
Jinja2==3.1.6
jsonschema==4.26.0
jsonschema-specifications==2025.9.1
Levenshtein==0.27.5
limits==5.8.0
lxml==6.1.3
markdown-it-py==4.2.0
markdown2==2.5.5
MarkupSafe==3.0.4
mccabe==0.7.0
mdurl==0.1.2
multivolumefile==0.2.3
mutagen==1.48.1
mypy_extensions==1.1.0
natsort==8.4.0
netifaces-plus==0.12.5
nh3==0.3.7
nose==1.3.7
oauth2client==4.1.3
oauthlib==4.0.0
opentelemetry-api==1.45.1
ordered-set==4.1.0
outcome==1.3.0.post0
packaging==26.3
pillow==13.0.0
platformdirs==4.13.5
proto-plus==1.29.0
protobuf==7.36.2
psutil==7.2.2
py7zr==0.20.8
pyasn1==0.6.4
pyasn1_modules==0.4.2
pybcj==1.0.8
pycodestyle==2.15.0
pycountry==22.3.5
pycparser==3.12
pycryptodomex==3.24.1
PyDrive2==1.21.3
pyflakes==4.0.3
Pygments==2.21.0
pylatexenc==2.11
pylint==4.1.3
pyOpenSSL==24.2.1
pyparsing==3.3.3
pypdf==6.10.2
pyppmd==1.1.1
PySocks==1.7.1
python-dateutil==2.9.0.post0
python-dotenv==1.2.4
python-Levenshtein==0.27.5
python-magic==0.4.27
python-magic-bin==0.4.14
pytz==2026.5
PyYAML==6.0.3
pyzstd==0.20.0
RapidFuzz==3.14.6
rarfile==4.5
rauth==0.7.3
referencing==0.37.0
regex==2026.1.15
requests==2.34.2
requests-oauthlib==2.0.0
rich==15.0.0
roman-numerals==4.1.0
rpds-py==2026.9.1
rsa==4.9.1
scholarly==1.7.11
selenium==4.51.0
setuptools==84.2.1
six==1.17.0
sniffio==1.3.1
snowballstemmer==3.1.1
sortedcontainers==2.4.0
soupsieve==3.0.4
Sphinx==9.1.1
sphinx_rtd_theme==3.1.0
sphinxcontrib-applehelp==2.0.0
sphinxcontrib-devhelp==2.0.0
sphinxcontrib-htmlhelp==2.1.0
sphinxcontrib-jquery==4.1
sphinxcontrib-jsmath==2.0.0
sphinxcontrib-qthelp==2.0.0
sphinxcontrib-serializinghtml==2.0.0
SQLAlchemy==2.0.55
SQLAlchemy-Utils==0.42.1
stevedore==5.9.1
text2digits==0.1.2
texttable==1.7.2
tomlkit==0.15.2
tornado==6.5.10
trio==0.34.0
trio-websocket==0.12.2
typing_extensions==4.16.0
tzdata==2026.5
tzlocal==5.4.5
Unidecode==1.4.0
uritemplate==4.2.0
urllib3==2.8.0
URLObject==3.0.0
Wand==0.7.2
websocket-client==1.9.2
Werkzeug==3.1.9
wordninja==2.0.0
wrapt==2.5.1
wsproto==1.3.2
WTForms==3.3.1
xmltodict==1.0.4
zipp==4.1.2
zope.event==6.2
zope.interface==8.7
```

Notlar:
- `iso-639` (yalnızca `python_version<'3.12'` için gerekli) bu ortamda (Python 3.12) uygulanmadı/atlandı; beklenen bir durumdur, hata değildir.
- `cryptography`, isteğe bağlı `scholarly`/`pyOpenSSL` bağımlılık zinciri nedeniyle `47.0.0`'dan `43.0.3`'e düştü. Bu, `requirements.txt`'deki kısıt olan `cryptography>=39.0.0,<48.0.0` ile hâlâ uyumludur; bir hata değildir.

### Kurulamayan paketler — Pylint'te bu modüllere ait import-error'lar ortam sorunudur, bulgu sayılmaz

| Paket | Hata özeti |
| --- | --- |
| `python-ldap>=3.0.0,<3.5.0` | Kaynaktan derleme (`_ldap` C uzantısı) Windows'ta başarısız: `fatal error C1083: Cannot open include file: 'lber.h': No such file or directory`. Sistemde OpenLDAP geliştirme başlık dosyaları (`lber.h`, `ldap.h`) ve bağlı kütüphaneleri yok; Windows için bu paketin hazır (prebuilt) wheel'i de PyPI'de mevcut değil. |
| `Flask-SimpleLDAP>=1.4.0,<2.2.0` | `python-ldap`'e bağımlı; kurulumu yukarıdaki aynı derleme hatasıyla başarısız oluyor. |

Bu iki paket `cps/kobo_auth.py` ile ilgili değil; LDAP girişi (`ldap` özelliği) ile ilgilidir. Pylint'in bu modüllere ait `E0401 import-error` (veya benzeri) uyarıları **güvenlik bulgusu veya kod kalitesi bulgusu sayılmayacak**; ortam/platform kısıtı olarak kabul edilip bulgu kaydına (`findings-register.csv`) girilmeyecek, gerekirse yalnızca bu dosyaya not düşülecek.

## K4 — Araç yapılandırma dosyası durumu

Repo köküne bakıldı; aşağıdaki yapılandırma dosyalarından **hiçbiri mevcut değil**:

| Aranan dosya | Durum |
| --- | --- |
| `.pylintrc` / `pylintrc` | Yok |
| `pyproject.toml` içinde `[tool.pylint]` bölümü | Yok |
| `setup.cfg` | Yok (dosyanın kendisi de yok) |
| `.flake8` | Yok |
| `pyproject.toml` içinde `[tool.flake8]` bölümü | Yok |
| `tox.ini` | Yok |

**Sonuç:**
- **Pylint:** Repo içinde bir yapılandırma dosyası bulunmadığından Pylint'in **kendi varsayılan ayarları** kullanılacak; hiçbir ayar repo için özelleştirilmedi, kurallar değiştirilmedi.
- **flake8:** K4 kararı gereği zaten `--isolated` bayrağıyla çalıştırılacak (repo/kullanıcı/global yapılandırma dosyalarını tamamen yok sayar), sadece `E,W` kod aralığı seçilecek (satır uzunluğu varsayılan 79). Repo içinde bir `.flake8`/`setup.cfg`/`tox.ini` bulunmaması bu kararla tutarlı; `--isolated` olmasaydı da kullanılacak bir yapılandırma dosyası yoktu.

## Kurulum/import notları (güvenlik bulgusu DEĞİL)

Bu bölüm, Pylint'in olası `E0401 import-error` / benzeri ortam kaynaklı uyarılarını kaydetmek için ayrılmıştır (CLAUDE.md madde 9).

Başlangıç Pylint taraması çalıştırıldı (bkz. "Tarama kayıtları"). Tespit edilen tek `E0401 import-error`, `cps/services/simpleldap.py` içinde `flask_simpleldap` modülünün bulunamamasından kaynaklanıyor (2 adet) — bu paket Windows'ta `python-ldap` derleme hatası nedeniyle `.venv` ortamına kurulamadı (bkz. yukarıdaki "Kurulamayan paketler" bölümü). Ayrıca 252 adet `E0611 no-name-in-module` bulundu; bunun 2 adedi aynı LDAP modülünde, kalan 250 adedi `cps/__init__.py`'nin alt modülleri paket özniteliği olarak çalışma zamanında atamasından kaynaklanan, LDAP ile ilgisiz ayrı bir Pylint statik analiz kısıtıdır. Ayrıntılı tablo: `docs/pylint-baseline-summary.md` → "Ortamdan kaynaklanan mesajlar".

## Tarama kayıtları

| Araç | Komut | Başlangıç (UTC) | Bitiş (UTC) | Çıkış kodu | Rapor dosyası | Rapor boyutu |
| --- | --- | --- | --- | --- | --- | --- |
| Pylint 4.1.3 | `python -m pylint cps.py cps --output=reports\baseline\pylint.txt` | 2026-10-24T17:24:36Z | 2026-10-24T17:25:42Z | 30 | `reports/baseline/pylint.txt` | 403.902 bayt |
| flake8 7.4.1 | `python -m flake8 --isolated --select=E,W --statistics --count --output-file=reports\baseline\pep8.txt cps.py cps` | 2026-10-24T17:25:53Z | 2026-10-24T17:25:55Z | 1 | `reports/baseline/pep8.txt` | 225.077 bayt |

Notlar:
- Her iki çıkış kodu da beklenen davranıştır: Pylint ve flake8, uyarı/hata bulunduğunda sıfırdan farklı çıkış kodu döner (CLAUDE.md "Tarama komutları" notları). Bu bir çalıştırma hatası değildir.
- Her iki rapor dosyasının da oluştuğu ve boş olmadığı doğrulandı (satır sayıları: pylint.txt 4223 satır, pep8.txt 3451 satır).
- Her iki ham rapor da kişisel veri veya yerel tam yol (`C:\Users...` vb.) içermiyor; kontrol edildi, dosya yolları repo köküne göre relatiftir (örn. `cps\admin.py`).
- Bu tarama, Bandit'i kapsamaz; Bandit taraması 2. kişinin sorumluluğundadır.
