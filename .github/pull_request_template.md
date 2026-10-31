## Ne yapıldı
<!-- Kısa açıklama. İlgili FIND-ID'leri yaz. -->

## Tür
- [ ] Doküman / bulgu kaydı
- [ ] Tarama raporu
- [ ] Düzeltme (fix/find-XXX)

## Düzeltme ise
**Bulgu:** FIND-___ · Kural: ___ · Dosya: `cps/___.py:___`

**Önceki kod**
```python

```

**Yeni kod**
```python

```

**Gerekçe** — neden güvenli / neden davranış korunuyor:

**Doğrulama**
```text
python -m py_compile ...
python -m bandit / pylint / flake8 ... (dosya bazlı çıktı)
```

## Kontrol
- [ ] Base: `sseydaltin/calibre-web` → `project-analysis`
- [ ] `reports/baseline/` değişmedi
- [ ] `cps/cw_login/`, `cps/cw_advocate/` değişmedi (K7)
- [ ] `.venv`, log, db, kişisel veri yok
- [ ] Bulgu kaydı güncellendi (gerekiyorsa)
- [ ] Gözden geçiren atandı: @___
