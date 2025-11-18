# 🎧 Instalación Rápida - Generador de Audiolibros

## ⚡ Instalación en 3 Pasos

### 1. Instalar Node.js

**Windows/macOS:**
- Descarga desde: https://nodejs.org/ (versión LTS recomendada)
- Ejecuta el instalador

**Linux:**
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### 2. Instalar la librería `say`

```bash
npm install -g say
```

### 3. Verificar

```bash
# Verificar Node.js
node --version

# Verificar say
npm list -g say

# Prueba de audio
node -e "const say = require('say'); say.speak('Hello world');"
```

---

## 📚 Uso

1. Ve a cualquier libro en Calibre-Web
2. Haz clic en el botón verde **"Generate Audiobook"**
3. Selecciona opciones y genera
4. Espera a que termine (se procesa en segundo plano)
5. Descarga o reproduce los archivos WAV generados

---

## 📖 Documentación Completa

- **Instalación detallada:** `INSTALACION_AUDIOLIBROS.md`
- **Funcionalidades:** `NUEVAS_FUNCIONALIDADES.md`

---

## 🐛 Problemas Comunes

**"Node.js is not installed"**
→ Instala Node.js desde nodejs.org

**"Cannot find module 'say'"**
→ Ejecuta: `npm install -g say`

**No se escucha audio**
→ Windows: Verifica que SAPI funciona
→ macOS: Ya debería funcionar
→ Linux: Instala `festival` o `espeak`

---

## 📦 Archivos Necesarios

```
calibre-web/
├── package.json                    ← Configuración de Node.js
├── cps/
│   ├── static/
│   │   └── js/
│   │       └── tts-generator.js    ← Script de generación
│   ├── tasks/
│   │   └── audiobook.py            ← Tarea asíncrona Python
│   └── web.py                       ← Rutas HTTP
```

Todos estos archivos ya están incluidos.

---

## ✅ Requisitos del Sistema

| Requisito | Versión | Obligatorio |
|-----------|---------|-------------|
| Node.js | v14+ | ✅ Sí |
| npm | 6+ | ✅ Sí (viene con Node.js) |
| say | 0.16+ | ✅ Sí |
| Python | 3.6+ | ✅ Sí (ya lo tienes) |
| ebooklib | latest | ❌ Opcional (EPUB) |
| pdfplumber | latest | ❌ Opcional (PDF) |

---

**¿Listo? ¡Empieza a generar audiolibros!** 🚀
