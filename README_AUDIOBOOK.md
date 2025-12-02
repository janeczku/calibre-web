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

### 🗣️ Voces Disponibles (Neural TTS - Alta Calidad)

**Linux/Docker (Piper TTS - RECOMENDADO):**
- **🇪🇸 Spanish Female (Monica)**: Voz natural femenina española - ¡Excelente calidad!
- **🇪🇸 Spanish Male (Jorge)**: Voz masculina española
- **🇲🇽 Spanish Latin America (Paulina)**: Voz femenina mexicana
- **🇺🇸 English US (Alex)**: Voz masculina estadounidense
- **🇬🇧 English UK (Daniel)**: Voz masculina británica

**Fallback (espeak-ng):**
Si Piper no está disponible, el sistema usa automáticamente espeak-ng como respaldo.

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

**No se escucha audio o voces robóticas**
→ Windows: Verifica que SAPI funciona
→ macOS: Ya debería funcionar
→ Linux/Docker:
  - **Voces naturales (Piper TTS)**: Ya incluido en Docker, reconstruye la imagen
  - **Voces robóticas (espeak)**: Actualiza a Piper TTS para mejor calidad
  ```bash
  # En Docker, reconstruir la imagen incluye Piper automáticamente
  docker-compose build
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

| Requisito | Versión | Plataforma | Obligatorio | Notas |
|-----------|---------|------------|-------------|-------|
| Node.js | v14+ | Todas | ✅ Sí | |
| npm | 6+ | Todas | ✅ Sí (viene con Node.js) | |
| **Piper TTS** | latest | Linux/Docker | ⭐ Recomendado | Voces neuronales de alta calidad |
| ffmpeg | latest | Linux/Docker | ✅ Sí (para MP3) | |
| espeak-ng | latest | Linux/Docker | ❌ Fallback | Solo si Piper no funciona |
| say | 0.16+ | Windows | ✅ Sí | |
| Python | 3.6+ | Todas | ✅ Sí (ya lo tienes) | |
| ebooklib | latest | Todas | ❌ Opcional (EPUB) | |
| pdfplumber | latest | Todas | ❌ Opcional (PDF) | |

---

**¿Listo? ¡Empieza a generar audiolibros!** 🚀
