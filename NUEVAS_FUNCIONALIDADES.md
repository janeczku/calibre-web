# Nuevas Funcionalidades de Calibre-Web

## 📚 Resumen

Se han implementado dos nuevas funcionalidades importantes para Calibre-Web:

1. **Detector de Libros Duplicados** - Encuentra y elimina copias duplicadas en tu biblioteca
2. **Generador de Audiolibros** - Convierte libros a audiolibros usando macOS Text-to-Speech (Say)

---

## 🔍 1. Detector de Libros Duplicados

### Descripción
Esta funcionalidad permite identificar libros duplicados en tu biblioteca comparando títulos y autores, facilitando la limpieza y organización de tu colección.

### Ubicación
**Admin → Library Management → Find Duplicate Books**

### Características
- ✅ Detección inteligente por título y autor (normalizado)
- ✅ Muestra todos los duplicados agrupados
- ✅ Información detallada de cada copia:
  - Portada del libro
  - Formatos disponibles (EPUB, PDF, MOBI, etc.)
  - Tamaño total de archivos
  - Fecha de añadido
  - Ruta en el sistema de archivos
- ✅ Eliminación selectiva con confirmación
- ✅ Vista previa antes de eliminar
- ✅ Ordenamiento automático (más antiguos primero)

### Archivos Modificados/Creados

#### Backend
- **`cps/admin.py`** (líneas 2109-2218)
  - `@admi.route("/admin/duplicates")` - Detecta duplicados
  - `@admi.route("/admin/duplicates/delete/<int:book_id>")` - Elimina libro específico

#### Frontend
- **`cps/templates/admin_duplicates.html`** (NUEVO)
  - Vista completa de duplicados
  - Tabla responsive con detalles
  - Modal de confirmación de eliminación
  - Estilos personalizados

- **`cps/templates/admin.html`** (líneas 165-176)
  - Botón "Find Duplicate Books" en sección Library Management

### Algoritmo de Detección

```python
# Normalización
normalized_title = ' '.join(book.title.lower().split())
normalized_author = ' '.join(book.authors[0].name.lower().split())

# Agrupación por (título, autor)
key = (normalized_title, normalized_author)

# Solo se consideran duplicados si hay 2+ libros con la misma key
```

### Uso

1. Ve a **Admin → Find Duplicate Books**
2. El sistema escaneará toda la biblioteca (puede tardar en bibliotecas grandes)
3. Se mostrarán grupos de libros duplicados
4. Revisa cada grupo y decide qué copias mantener
5. Haz clic en el botón de eliminar (🗑️) de la copia que no necesitas
6. Confirma la eliminación en el modal
7. El libro y todos sus archivos se eliminarán permanentemente

### Recomendaciones

- **Mantén la copia con más formatos** (ej: si una tiene EPUB+PDF+MOBI, y otra solo EPUB)
- **Mantén la de mejor calidad** (compara tamaños - archivos más grandes suelen ser mejor calidad)
- **Considera la fecha** - La más antigua suele ser la original, pero no siempre la mejor

---

## 🎧 2. Generador de Audiolibros

### Descripción
Convierte libros de texto (EPUB, PDF, TXT) en audiolibros usando el comando `say` de macOS. Soporta generación asíncrona en segundo plano y preview rápido para escuchar inmediatamente.

### Requisitos
- ⚠️ **Node.js v14+** (multiplataforma: Windows, macOS, Linux)
- ⚠️ **Librería `say` de Node.js** - Instalar con: `npm install -g say`
- Librerías Python opcionales (mejoran la extracción de texto):
  - `ebooklib` - Para EPUB
  - `beautifulsoup4` - Para HTML dentro de EPUB
  - `pdfplumber` o `PyPDF2` - Para PDF

**Ver `INSTALACION_AUDIOLIBROS.md` para instrucciones detalladas de instalación**

### Ubicación
En la página de detalle de cualquier libro con formatos EPUB, PDF o TXT:
- Botón verde **"Generate Audiobook"** con dropdown

### Características

#### Generación Completa (Asíncrona)
- ✅ Procesa el libro completo
- ✅ Divide en múltiples archivos M4A (fáciles de manejar)
- ✅ Configuración de voz (8 voces disponibles)
- ✅ Ajuste de palabras por archivo (3K-15K palabras)
- ✅ Ejecución en segundo plano (no bloquea la UI)
- ✅ Notificación cuando está listo
- ✅ Progreso visible en página de Tasks
- ✅ Archivos registrados automáticamente en la biblioteca

#### Preview Rápido (Síncrono)
- ✅ Genera audio de las primeras 1000 palabras
- ✅ Descarga inmediata para escuchar
- ✅ Ideal para probar voces antes de generar el audiolibro completo

### Archivos Creados/Modificados

#### Backend

**`cps/tasks/audiobook.py`** (NUEVO - 379 líneas)
- Clase `TaskGenerateAudiobook` (hereda de `CalibreTask`)
- Extracción de texto desde EPUB, PDF, TXT
- División inteligente de texto en partes
- Generación de audio con `say`
- Registro automático en base de datos

**`cps/web.py`** (líneas 1677-1907)
- `@web.route("/book/<int:book_id>/generate-audiobook/<book_format>")` - Inicia generación async
- `@web.route("/book/<int:book_id>/quick-audiobook/<book_format>")` - Preview rápido
- Función `extract_text_preview()` - Extrae primeras N palabras

#### Frontend

**`cps/templates/detail.html`** (líneas 133-162, 406-555)
- Botón dropdown "Generate Audiobook"
- Opciones para cada formato disponible
- Modal de configuración con:
  - Selector de voz (8 voces)
  - Selector de palabras por archivo
  - Alertas informativas
- JavaScript para manejar modal y AJAX

### Voces Disponibles

| Voz | Idioma | Género | Descripción |
|-----|--------|--------|-------------|
| Alex | English (US) | Male | Voz por defecto, clara y natural |
| Samantha | English (US) | Female | Voz femenina agradable |
| Victoria | English (US) | Female | Voz femenina profesional |
| Daniel | English (UK) | Male | Acento británico |
| Karen | English (AU) | Female | Acento australiano |
| Monica | Español | Female | Voz en español clara |
| Jorge | Español | Male | Voz masculina en español |
| Paulina | Español (MX) | Female | Español de México |

### Configuración de Palabras por Archivo

| Palabras | Duración Estimada | Uso Recomendado |
|----------|-------------------|-----------------|
| 3,000 | 20-30 minutos | Capítulos cortos |
| **5,000** (default) | 30-45 minutos | Balance ideal |
| 10,000 | 60-90 minutos | Libros cortos completos |
| 15,000 | 90-120 minutos | Sesiones largas |

### Uso

#### Generación Completa

1. Ve a la página de detalle del libro
2. Haz clic en el botón verde **"Generate Audiobook"**
3. Selecciona **"Full Audiobook (EPUB)"** (o el formato disponible)
4. En el modal:
   - Elige una voz
   - Ajusta palabras por archivo
5. Haz clic en **"Generate Audiobook"**
6. El proceso iniciará en segundo plano
7. Ve a **Tasks** para ver el progreso
8. Cuando termine, los archivos M4A estarán disponibles para:
   - Descargar
   - Reproducir online (Listen in Browser)

#### Preview Rápido

1. Ve a la página de detalle del libro
2. Haz clic en **"Quick Preview (EPUB)"**
3. El audio se descargará automáticamente
4. Abre el archivo M4A descargado para escuchar

### Formatos Soportados

#### ✅ EPUB
- Extracción completa de texto
- Requiere: `ebooklib` y `beautifulsoup4`
- Fallback a `ebook-convert` de Calibre

#### ✅ PDF
- Extracción página por página
- Requiere: `pdfplumber` o `PyPDF2`
- Puede tener problemas con PDFs escaneados (OCR no incluido)

#### ✅ TXT
- Lectura directa del archivo
- Sin dependencias adicionales
- Siempre funciona

### Flujo de Generación

```
1. Usuario hace clic en "Generate Audiobook"
   ↓
2. Se crea TaskGenerateAudiobook
   ↓
3. Se añade a WorkerThread (cola de tareas)
   ↓
4. En segundo plano:
   a. Extraer texto del libro
   b. Dividir en partes de N palabras
   c. Para cada parte:
      - Generar audio con 'say'
      - Guardar como part001.m4a, part002.m4a, etc.
      - Registrar en base de datos
   ↓
5. Tarea completa
   ↓
6. Usuario ve archivos M4A en detalle del libro
   ↓
7. Puede descargarlos o reproducirlos online
```

### Estructura de Archivos Generados

```
/calibre-library/
└── Author Name/
    └── Book Title (123)/
        ├── Book Title.epub          (original)
        ├── Book Title_part001.m4a   (audio 1)
        ├── Book Title_part002.m4a   (audio 2)
        ├── Book Title_part003.m4a   (audio 3)
        └── ...
```

### Monitoreo de Tareas

Ve a **Tasks** (icono de engranajes en la navbar) para:
- Ver progreso en tiempo real
- Ver qué parte se está generando (ej: "Generating audio part 3 of 10...")
- Cancelar tareas (si está habilitado)
- Ver historial de tareas completadas

---

## 📊 Tabla Comparativa de Funcionalidades

| Característica | Duplicados | Audiolibros |
|----------------|------------|-------------|
| **Ubicación** | Admin page | Detail page |
| **Procesamiento** | Síncrono | Asíncrono |
| **Tiempo estimado** | < 1 minuto | 5-60 minutos |
| **Dependencias** | Ninguna | macOS, Say |
| **Formatos** | Todos | EPUB, PDF, TXT |
| **Reversible** | ❌ No | ✅ Sí (archivos guardados) |

---

## 🔧 Instalación de Dependencias Opcionales

Para mejorar la extracción de texto en audiolibros:

```bash
# Para EPUB
pip install ebooklib beautifulsoup4 lxml

# Para PDF (opción 1 - recomendada)
pip install pdfplumber

# Para PDF (opción 2 - alternativa)
pip install PyPDF2
```

**Nota:** Calibre-Web funcionará sin estas librerías, pero:
- EPUB usará `ebook-convert` de Calibre (más lento)
- PDF no funcionará sin pdfplumber o PyPDF2

---

## 🐛 Solución de Problemas

### Duplicados

**"No se encontraron duplicados pero sé que los hay"**
- El algoritmo compara títulos y autores normalizados
- Si los títulos tienen ligeras diferencias (ej: "Harry Potter 1" vs "Harry Potter I"), no se detectarán
- Revisa manualmente libros con títulos similares

**"Error al eliminar libro"**
- Verifica permisos de escritura en el directorio de Calibre
- El libro puede estar siendo usado por otro proceso
- Revisa los logs en Admin → Logfile

### Audiolibros

**"Node.js is not installed"**
- Esta función requiere Node.js v14 o superior
- Descarga e instala desde: https://nodejs.org/
- Verifica con: `node --version`

**"Cannot find module 'say'"**
- La librería `say` de Node.js no está instalada
- Instala con: `npm install -g say`
- Verifica con: `npm list -g say`

**"Could not extract text from book"**
- Para EPUB: Instala `ebooklib` y `beautifulsoup4`
- Para PDF: Instala `pdfplumber` o `PyPDF2`
- Si el PDF es escaneado, necesita OCR (no incluido)

**"Audiobook generation failed"**
- Revisa que el archivo de libro exista y sea legible
- Verifica espacio en disco
- Revisa logs en Admin → Logfile
- Prueba con el "Quick Preview" primero

**"Audio files not appearing after generation"**
- Recarga la página del libro (F5)
- Verifica que los archivos M4A existen en el directorio del libro
- Revisa que se registraron en la base de datos

---

## 📝 Notas Técnicas

### Detector de Duplicados

- **Complejidad temporal:** O(n) donde n = número de libros
- **Memoria:** Carga todos los libros en memoria (puede ser pesado en bibliotecas >10K libros)
- **Optimización futura:** Agregar paginación o búsqueda por letra

### Generador de Audiolibros

- **Formato de salida:** M4A (AAC en contenedor MPEG-4)
- **Calidad:** Determinada por `say` (variable según voz)
- **Velocidad:** ~5-10 minutos por cada 10K palabras (depende del hardware)
- **Tamaño de archivos:** ~1-2 MB por minuto de audio
- **Limitaciones:**
  - No procesa imágenes, tablas o fórmulas matemáticas complejas
  - La calidad de extracción varía según el formato original
  - No hay soporte para pausas, énfasis o entonación personalizada

### Extensiones Futuras Posibles

#### Para Duplicados
- [ ] Fusión automática de metadatos
- [ ] Detección por ISBN
- [ ] Comparación de contenido (hash MD5)
- [ ] Búsqueda de duplicados en toda la red de Calibre-Web

#### Para Audiolibros
- [ ] Soporte para Windows (SAPI 5) y Linux (espeak)
- [ ] Más voces y idiomas
- [ ] Control de velocidad de narración
- [ ] Inserción de pausas en capítulos
- [ ] Generación de metadata ID3 en archivos M4A
- [ ] Integración con servicios de TTS en la nube (Google, Amazon Polly)
- [ ] Generación de playlist M3U para reproducción secuencial
- [ ] Bookmarks y resumen de progreso

---

## 📜 Licencia

Estas funcionalidades siguen la misma licencia que Calibre-Web (GNU General Public License v3.0).

---

## 🙏 Créditos

**Desarrollado por:** Claude (Anthropic)
**Fecha:** 2025
**Versión de Calibre-Web:** Compatible con v0.6.x+

---

## 📞 Soporte

Para reportar bugs o sugerir mejoras:
1. Verifica los logs en **Admin → Logfile**
2. Reproduce el error con pasos claros
3. Incluye información del sistema (macOS version, Python version, etc.)
4. Reporta en el repositorio de Calibre-Web

---

**¡Disfruta de tus nuevas funcionalidades!** 📚🎧
