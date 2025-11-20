#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para aplicar todas las mejoras a caliBlur_override.css
"""

import re
import os

def apply_improvements():
    css_file = os.path.join(os.path.dirname(__file__), 'cps', 'static', 'css', 'caliBlur_override.css')

    print("=" * 60)
    print("Aplicando mejoras a caliBlur_override.css")
    print("=" * 60)
    print()

    if not os.path.exists(css_file):
        print(f"ERROR: No se encuentra {css_file}")
        return 1

    # Leer el archivo
    with open(css_file, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    changes_made = []

    # 1. Cambiar imágenes de 150px a 180px
    print("1. Actualizando tamaños de imagen de 150px a 180px...")

    # height: 150px -> height: 180px
    pattern1 = r'height:\s*150px'
    replacement1 = 'height: 180px'
    content = re.sub(pattern1, replacement1, content)
    count1 = len(re.findall(pattern1, original_content))
    if count1 > 0:
        changes_made.append(f"   ✓ Cambiadas {count1} instancias de 'height: 150px' a 'height: 180px'")

    # max-width: 150px -> max-width: 180px
    pattern2 = r'max-width:\s*150px'
    replacement2 = 'max-width: 180px'
    content = re.sub(pattern2, replacement2, content)
    count2 = len(re.findall(pattern2, original_content))
    if count2 > 0:
        changes_made.append(f"   ✓ Cambiadas {count2} instancias de 'max-width: 150px' a 'max-width: 180px'")

    # width: 150px -> width: 180px (si existe)
    pattern3 = r'width:\s*150px'
    replacement3 = 'width: 180px'
    content = re.sub(pattern3, replacement3, content)
    count3 = len(re.findall(pattern3, original_content))
    if count3 > 0:
        changes_made.append(f"   ✓ Cambiadas {count3} instancias de 'width: 150px' a 'width: 180px'")

    # 2. Añadir estilos de botones de audiolibro al final
    print("\n2. Añadiendo estilos de botones de audiolibro...")

    audiobook_styles = """

/* ===================================================================
   AUDIOBOOK BUTTONS - Icon-only styling with perfect alignment
   =================================================================== */

/* Play Online Button - Quick Preview (1000 words) */
#audiobook-play-btn,
a[href*="audiobook/play/"] {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 6px 12px;
    margin-right: 5px;
    background-color: #2196F3;
    border: 1px solid #1976D2;
    border-radius: 4px;
    color: #fff !important;
    text-decoration: none;
    transition: all 0.3s ease;
    vertical-align: middle;
}

#audiobook-play-btn:hover,
a[href*="audiobook/play/"]:hover {
    background-color: #1976D2;
    border-color: #0D47A1;
    transform: translateY(-1px);
    box-shadow: 0 2px 5px rgba(33, 150, 243, 0.3);
}

/* Get Audiobook Button - Full generation via tasks */
#audiobook-download-btn,
.generate-audiobook-link,
a[href="#"].btn.generate-audiobook-link {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 6px 12px;
    margin-right: 5px;
    background-color: #4CAF50;
    border: 1px solid #388E3C;
    border-radius: 4px;
    color: #fff !important;
    text-decoration: none;
    transition: all 0.3s ease;
    vertical-align: middle;
}

#audiobook-download-btn:hover,
.generate-audiobook-link:hover,
a[href="#"].btn.generate-audiobook-link:hover {
    background-color: #388E3C;
    border-color: #1B5E20;
    transform: translateY(-1px);
    box-shadow: 0 2px 5px rgba(76, 175, 80, 0.3);
}

/* Icon-only styling - NO TEXT, perfect alignment */
#audiobook-play-btn .glyphicon-play,
#audiobook-download-btn .glyphicon-headphones,
.generate-audiobook-link .glyphicon-headphones,
a.btn .glyphicon-play,
a.btn .glyphicon-headphones {
    vertical-align: middle;
    margin: 0 !important;  /* No margin for icon-only buttons */
    top: 0;
    font-size: 14px;
}

/* Ensure buttons align with Download, Send to eReader, Read */
.btn-toolbar .btn {
    vertical-align: middle;
    display: inline-flex;
    align-items: center;
    justify-content: center;
}

/* Audiobook dropdown menu positioning fix */
.audiobook-dropdown {
    position: relative;
}

.audiobook-dropdown .dropdown-menu {
    position: absolute;
    top: 100%;
    left: 0;
    right: auto;
    margin-top: 2px;
    min-width: 200px;
    max-width: 300px;
    z-index: 1000;
}

/* Prevent dropdown from going off-screen */
.audiobook-dropdown .dropdown-menu.pull-right {
    left: auto;
    right: 0;
}

/* Loading spinner for audiobook generation */
.audiobook-generating {
    opacity: 0.6;
    pointer-events: none;
    position: relative;
}

.audiobook-generating::after {
    content: "";
    position: absolute;
    top: 50%;
    left: 50%;
    width: 16px;
    height: 16px;
    margin: -8px 0 0 -8px;
    border: 2px solid #fff;
    border-top-color: transparent;
    border-radius: 50%;
    animation: audiobook-spin 0.8s linear infinite;
}

@keyframes audiobook-spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

/* Responsive adjustments for mobile */
@media (max-width: 767px) {
    #audiobook-play-btn,
    #audiobook-download-btn,
    .generate-audiobook-link {
        padding: 8px 12px;
        margin: 2px;
        width: auto;
    }

    .audiobook-dropdown .dropdown-menu {
        position: fixed;
        left: 10px !important;
        right: 10px !important;
        max-width: calc(100% - 20px);
    }
}

/* End of Audiobook Buttons Styles */
"""

    # Verificar si los estilos ya existen
    if 'AUDIOBOOK BUTTONS' not in content:
        content += audiobook_styles
        changes_made.append("   ✓ Añadidos estilos completos de botones de audiolibro")
    else:
        print("   ℹ Estilos de audiolibro ya existen, actualizándolos...")
        # Reemplazar sección existente
        pattern = r'/\* ===+\s*AUDIOBOOK BUTTONS.*?End of Audiobook Buttons Styles \*/'
        content = re.sub(pattern, audiobook_styles.strip(), content, flags=re.DOTALL)
        changes_made.append("   ✓ Actualizados estilos de botones de audiolibro")

    # Guardar el archivo modificado
    with open(css_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print("\n" + "=" * 60)
    print("RESUMEN DE CAMBIOS:")
    print("=" * 60)
    for change in changes_made:
        print(change)

    print("\n✓ Archivo actualizado exitosamente:")
    print(f"  {css_file}")
    print("\n" + "=" * 60)

    return 0

if __name__ == '__main__':
    import sys
    sys.exit(apply_improvements())
