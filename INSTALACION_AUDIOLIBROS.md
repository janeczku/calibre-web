# 🎧 Instalación del Generador de Audiolibros

## 📋 Requisitos

La funcionalidad de generación de audiolibros requiere:

1. **Node.js** (v14 o superior)
2. **Librería `say` de Node.js** (multiplataforma)
3. **Librerías Python opcionales** (para mejorar extracción de texto)

---

## 🚀 Instalación Paso a Paso

### 1. Instalar Node.js

#### Windows
1. Descarga Node.js desde: https://nodejs.org/
2. Ejecuta el instalador (recomendado: versión LTS)
3. Verifica la instalación:
   ```cmd
   node --version
   npm --version
   ```

#### macOS
```bash
# Usando Homebrew
brew install node

# O descarga desde nodejs.org
```

#### Linux (Ubuntu/Debian)
```bash
# Instalar Node.js 18.x (LTS)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Verificar
node --version
npm --version
```

#### Linux (Fedora/RHEL/CentOS)
```bash
# Instalar Node.js 18.x
curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
sudo yum install -y nodejs

# Verificar
node --version
npm --version
```

---

### 2. Instalar la Librería `say`

Una vez que Node.js esté instalado, instala la librería `say` **globalmente**:

```bash
npm install -g say
```

**Nota:** Es importante instalarlo globalmente con `-g` para que esté disponible para todos los proyectos.

#### Verificar la instalación

Prueba que `say` funciona correctamente:

```bash
# Crear un archivo de prueba
node -e "const say = require('say'); say.speak('Hello world');"
```

Deberías escuchar "Hello world" en tu sistema.

---

### 3. Dependencias del Sistema (según tu OS)

La librería `say` usa diferentes motores TTS según el sistema operativo:

#### Windows
- Usa **SAPI (Speech API)** que viene con Windows
- No requiere instalación adicional
- Voces disponibles en: Panel de Control → Opciones de accesibilidad → Narrador

**Instalar más voces en Windows 10/11:**
1. Ve a **Configuración → Hora e idioma → Idioma**
2. Añade un idioma (ej: Español - España)
3. Haz clic en el idioma → Opciones → Voz

#### macOS
- Usa el comando **`say`** nativo de macOS
- Ya viene instalado por defecto
- Voces disponibles en: Preferencias del Sistema → Accesibilidad → Voz

**Instalar más voces en macOS:**
1. Preferencias del Sistema → Accesibilidad → Contenido Oral
2. Haz clic en "Voz del sistema" y descarga voces adicionales

#### Linux
- Usa **Festival** o **eSpeak**
- Requiere instalación manual

**Ubuntu/Debian:**
```bash
# Opción 1: Festival (mejor calidad)
sudo apt-get install festival festvox-kallpc16k

# Opción 2: eSpeak (más ligero)
sudo apt-get install espeak
```

**Fedora/RHEL:**
```bash
# Festival
sudo dnf install festival festival-freebsoft-utils

# eSpeak
sudo dnf install espeak
```

**Verificar en Linux:**
```bash
# Festival
echo "Hello world" | festival --tts

# eSpeak
espeak "Hello world"
```

---

### 4. Instalar Librerías Python Opcionales

Estas librerías mejoran la extracción de texto de EPUB y PDF:

```bash
# Para EPUB (recomendado)
pip install ebooklib beautifulsoup4 lxml

# Para PDF - Opción 1 (recomendada)
pip install pdfplumber

# Para PDF - Opción 2 (alternativa)
pip install PyPDF2
```

**Nota:** Calibre-Web funcionará sin estas librerías, pero:
- EPUB usará `ebook-convert` de Calibre (más lento)
- PDF no funcionará sin `pdfplumber` o `PyPDF2`

---

## ✅ Verificar que Todo Funciona

### Prueba Rápida

1. Verifica Node.js:
   ```bash
   node --version
   # Debe mostrar v14.x.x o superior
   ```

2. Verifica que `say` está instalado:
   ```bash
   npm list -g say
   # Debe mostrar la versión instalada
   ```

3. Prueba de audio:
   ```bash
   node -e "const say = require('say'); say.speak('Prueba de audio en español');"
   ```

4. Verifica el script TTS:
   ```bash
   cd /ruta/a/calibre-web/cps/static/js
   node tts-generator.js "Hello world" test.wav "Alex" 1.0
   ```

   Esto debería crear un archivo `test.wav` con audio.

5. Reproduce el archivo:
   - Windows: doble clic en `test.wav`
   - macOS: `afplay test.wav`
   - Linux: `aplay test.wav` o `vlc test.wav`

---

## 🎙️ Voces Disponibles por Sistema

### Windows (SAPI)

**Voces por defecto:**
- Microsoft David Desktop (Inglés US - Male)
- Microsoft Zira Desktop (Inglés US - Female)
- Microsoft Mark (Inglés UK - Male)
- Microsoft Hazel (Inglés UK - Female)

**Voces en Español (requieren instalación):**
- Microsoft Helena Desktop (Español España - Female)
- Microsoft Sabina Desktop (Español México - Female)

**Listar todas las voces disponibles:**
```javascript
const say = require('say');
console.log(say.getInstalledVoices());
```

### macOS

**Voces por defecto:**
- Alex (Inglés US - Male) ✅ Por defecto
- Samantha (Inglés US - Female)
- Victoria (Inglés US - Female)
- Daniel (Inglés UK - Male)
- Karen (Inglés AU - Female)

**Voces en Español:**
- Monica (Español - Female)
- Jorge (Español - Male)
- Paulina (Español México - Female)

**Listar voces:**
```bash
say -v ?
```

### Linux (Festival/eSpeak)

**Festival:**
- kal_diphone (Inglés - Male)
- Don't have many Spanish voices by default

**eSpeak:**
- Soporta múltiples idiomas incluyendo español
- Voces sintéticas (calidad menor que Windows/macOS)

**Listar voces eSpeak:**
```bash
espeak --voices
```

---

## 🛠️ Configuración en detail.html

Las voces en el dropdown de Calibre-Web (`detail.html`) están configuradas para macOS. Si usas Windows o Linux, actualiza las opciones:

### Para Windows

Edita `cps/templates/detail.html` línea 429-437:

```html
<select id="voice-select" name="voice" class="form-control">
    <option value="Microsoft David Desktop">David (US English - Male)</option>
    <option value="Microsoft Zira Desktop">Zira (US English - Female)</option>
    <option value="Microsoft Mark">Mark (UK English - Male)</option>
    <option value="Microsoft Helena Desktop">Helena (Spanish - Female)</option>
    <option value="Microsoft Sabina Desktop">Sabina (Spanish Mexico - Female)</option>
</select>
```

### Para Linux (eSpeak)

```html
<select id="voice-select" name="voice" class="form-control">
    <option value="english">English</option>
    <option value="spanish">Spanish</option>
    <option value="french">French</option>
    <option value="german">German</option>
</select>
```

---

## 📁 Estructura de Archivos

```
calibre-web/
├── cps/
│   ├── static/
│   │   └── js/
│   │       └── tts-generator.js  ← Script de Node.js (debe existir)
│   ├── tasks/
│   │   └── audiobook.py          ← Tarea asíncrona
│   └── web.py                     ← Rutas HTTP
└── node_modules/
    └── say/                       ← Instalado con npm install -g say
```

---

## 🐛 Solución de Problemas

### "Node.js is not installed"

**Causa:** Node.js no está en el PATH o no está instalado.

**Solución:**
1. Verifica: `node --version`
2. Si falla, reinstala Node.js
3. Asegúrate de que esté en el PATH del sistema
4. Reinicia Calibre-Web después de instalar

### "Cannot find module 'say'"

**Causa:** La librería `say` no está instalada o no está accesible.

**Solución:**
```bash
# Instalar globalmente
npm install -g say

# O localmente en el proyecto
cd /ruta/a/calibre-web
npm install say
```

### "TTS script not found"

**Causa:** El archivo `tts-generator.js` no existe en `cps/static/js/`

**Solución:**
1. Verifica que el archivo existe
2. Si no existe, créalo con el contenido del script
3. Asegúrate de que tenga permisos de lectura

### No se escucha audio en Linux

**Causa:** Festival o eSpeak no están instalados o configurados correctamente.

**Solución:**
```bash
# Instalar Festival
sudo apt-get install festival festvox-kallpc16k

# Probar
echo "test" | festival --tts

# Si falla, instalar eSpeak
sudo apt-get install espeak
espeak "test"
```

### "Could not extract text from book"

**Causa:** Falta librería Python para el formato del libro.

**Solución:**
```bash
# Para EPUB
pip install ebooklib beautifulsoup4

# Para PDF
pip install pdfplumber
```

### Los archivos generados son muy grandes

**Causa:** WAV es un formato sin comprimir.

**Solución futura:** Convertir a MP3 o M4A después de generar:

```bash
# Instalar ffmpeg
sudo apt-get install ffmpeg  # Linux
brew install ffmpeg          # macOS
choco install ffmpeg         # Windows

# Convertir WAV a MP3
ffmpeg -i input.wav -acodec libmp3lame -ab 128k output.mp3
```

---

## 🔄 Actualizar la Librería `say`

```bash
npm update -g say
```

---

## 📊 Comparación de Motores TTS

| Sistema | Motor | Calidad | Voces | Instalación |
|---------|-------|---------|-------|-------------|
| Windows | SAPI | ⭐⭐⭐⭐ | Muchas | Fácil |
| macOS | say | ⭐⭐⭐⭐⭐ | Muchas | Ya instalado |
| Linux | Festival | ⭐⭐⭐ | Pocas | Manual |
| Linux | eSpeak | ⭐⭐ | Muchas | Manual |

---

## 🎯 Próximos Pasos

Una vez instalado todo:

1. Ve a la página de detalle de un libro en Calibre-Web
2. Haz clic en "Generate Audiobook"
3. Selecciona una voz y configuración
4. Espera a que se genere (proceso en segundo plano)
5. Los archivos WAV aparecerán en el libro para descargar o reproducir

---

## 📞 Soporte

Si tienes problemas:

1. Verifica los logs en **Admin → Logfile**
2. Ejecuta las pruebas de verificación de este documento
3. Asegúrate de que Node.js y `say` funcionan fuera de Calibre-Web primero
4. Reporta el problema con información del sistema y logs

---

## 📝 Notas Finales

- **Formato de salida:** WAV (sin comprimir, ~10MB por minuto)
- **Velocidad:** Varía según el sistema (1-5 minutos por cada 5000 palabras)
- **Limitaciones:** No soporta pausas, énfasis o entonación personalizada
- **Calidad:** Depende del motor TTS del sistema

---

**¡Disfruta generando audiolibros!** 📚🎧
