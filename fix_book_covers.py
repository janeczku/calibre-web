#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para arreglar los tamaños de las cubiertas de libros en caliBlur.css
"""

import re
import os

def fix_book_covers():
    css_file = os.path.join(os.path.dirname(__file__), 'cps', 'static', 'css', 'caliBlur.css')

    print("=" * 60)
    print("Arreglando tamaños de cubiertas en caliBlur.css")
    print("=" * 60)
    print()

    if not os.path.exists(css_file):
        print(f"ERROR: No se encuentra {css_file}")
        return 1

    # Leer el archivo
    with open(css_file, 'r', encoding='utf-8') as f:
        content = f.read()

    changes = []

    # 1. Arreglar el tamaño de las cubiertas en la vista de biblioteca
    # Buscar .container-fluid .book .cover img y asegurarse que tenga max-width y height auto

    # Patrón para encontrar las reglas de las imágenes de cover
    patterns_to_fix = [
        # Imágenes de cover en general
        (r'(\.container-fluid\s+\.book\s+\.cover\s+img\s*\{[^}]*)(width:\s*\d+px[^;]*;)',
         r'\1max-width: 100%; width: auto;'),

        (r'(\.container-fluid\s+\.book\s+\.cover\s+img\s*\{[^}]*)(height:\s*\d+px[^;]*;)',
         r'\1height: auto;'),

        # Cover en vista de grilla
        (r'(\.book\.isotope-item\s+\.cover\s+img\s*\{[^}]*)(width:\s*\d+px[^;]*;)',
         r'\1max-width: 100%; width: auto;'),

        (r'(\.book\.isotope-item\s+\.cover\s+img\s*\{[^}]*)(height:\s*\d+px[^;]*;)',
         r'\1height: auto;'),
    ]

    # Aplicar los fixes
    original_content = content
    for pattern, replacement in patterns_to_fix:
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
        if new_content != content:
            content = new_content
            changes.append(f"✓ Aplicado fix: {pattern[:50]}...")

    # Añadir reglas CSS específicas al final si no existen
    cover_fix_css = """

/* ===================================================================
   BOOK COVER FIXES - Ensure proper proportions
   =================================================================== */

/* Main library view - book covers */
.container-fluid .book .cover img,
#books .cover img,
#books_rand .cover img,
.book.isotope-item .cover img {
    max-width: 100% !important;
    width: auto !important;
    height: auto !important;
    object-fit: contain !important;
}

.container-fluid .book .cover {
    max-width: 140px !important;
    height: auto !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}

/* Book detail view */
.book-meta .cover img,
#bookDetailsModal .cover img {
    max-width: 100% !important;
    width: auto !important;
    height: auto !important;
    object-fit: contain !important;
}

/* Responsive - mobile */
@media (max-width: 767px) {
    .container-fluid .book .cover {
        max-width: 100px !important;
    }

    .container-fluid .book .cover img {
        max-width: 100% !important;
        width: auto !important;
        height: auto !important;
    }
}

/* End of Book Cover Fixes */
"""

    if 'BOOK COVER FIXES' not in content:
        content += cover_fix_css
        changes.append("✓ Añadidas reglas CSS para cubiertas")

    # Guardar el archivo solo si hubo cambios
    if content != original_content:
        with open(css_file, 'w', encoding='utf-8') as f:
            f.write(content)

        print("Cambios aplicados:")
        for change in changes:
            print(f"  {change}")
        print()
        print(f"✓ Archivo actualizado: {css_file}")
    else:
        print("ℹ No se necesitaron cambios")

    print("=" * 60)

    return 0

if __name__ == '__main__':
    import sys
    sys.exit(fix_book_covers())
