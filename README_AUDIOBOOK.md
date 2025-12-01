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
2. Haz clic en el botón con icono de audífonos **"Generate Audiobook"**
3. Selecciona la voz/idioma y el tamaño de las partes
4. Haz clic en "Generate Audiobook"
5. Espera a que termine (se procesa en segundo plano)
6. Descarga o reproduce los archivos MP3 generados

### 🗣️ Voces Disponibles

**Linux/Docker (espeak/espeak-ng):**
- **Spanish (Female/Male)**: Voces en español
- **Spanish Latin America (Female)**: Voz en español latinoamericano
- **English US (Male/Female)**: Inglés estadounidense
- **English UK (Male)**: Inglés británico
- **English AU (Female)**: Inglés australiano

**macOS:**
- Usa las voces nativas del sistema (Alex, Monica, Jorge, etc.)

**Windows:**
- Usa las voces SAPI instaladas en el sistema

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
→ Linux: Instala `espeak-ng` o `espeak` y `ffmpeg`:
  ```bash
  sudo apt-get install espeak-ng ffmpeg
  ```

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

| Requisito | Versión | Plataforma | Obligatorio |
|-----------|---------|------------|-------------|
| Node.js | v14+ | Todas | ✅ Sí |
| npm | 6+ | Todas | ✅ Sí (viene con Node.js) |
| espeak-ng/espeak | latest | Linux/Docker | ✅ Sí |
| ffmpeg | latest | Linux/Docker | ✅ Sí (para MP3) |
| say | 0.16+ | Windows | ✅ Sí |
| Python | 3.6+ | Todas | ✅ Sí (ya lo tienes) |
| ebooklib | latest | Todas | ❌ Opcional (EPUB) |
| pdfplumber | latest | Todas | ❌ Opcional (PDF) |

---

**¿Listo? ¡Empieza a generar audiolibros!** 🚀
