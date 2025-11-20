#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para añadir estilos de audiolibro al final de caliBlur.css
"""

import os

def add_audiobook_styles():
    css_file = os.path.join(os.path.dirname(__file__), 'cps', 'static', 'css', 'caliBlur.css')

    print("=" * 60)
    print("Añadiendo estilos de audiolibro a caliBlur.css")
    print("=" * 60)
    print()

    if not os.path.exists(css_file):
        print(f"ERROR: No se encuentra {css_file}")
        return 1

    # Leer el archivo
    with open(css_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Verificar si ya existen los estilos
    if 'AUDIOBOOK BUTTONS' in content:
        print("ℹ Los estilos de audiolibro ya existen en caliBlur.css")
        print("  No se realizarán cambios.")
        return 0

    # Estilos mínimos de audiolibro
    audiobook_styles = """

/* ===================================================================
   AUDIOBOOK BUTTONS - Minimal styling (added automatically)
   =================================================================== */

/* Audiobook dropdown menu positioning fix */
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
    .audiobook-dropdown .dropdown-menu {
        position: fixed;
        left: 10px !important;
        right: 10px !important;
        max-width: calc(100% - 20px);
    }
}

/* End of Audiobook Buttons Styles */
"""

    # Añadir al final
    content += audiobook_styles

    # Guardar
    with open(css_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print("✓ Estilos de audiolibro añadidos exitosamente")
    print(f"  Archivo: {css_file}")
    print("=" * 60)

    return 0

if __name__ == '__main__':
    import sys
    sys.exit(add_audiobook_styles())
