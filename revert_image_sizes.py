#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para revertir tamaños de imagen de 180px a 150px
"""

import re
import os

def revert_image_sizes():
    css_file = os.path.join(os.path.dirname(__file__), 'cps', 'static', 'css', 'caliBlur_override.css')

    print("=" * 60)
    print("Revirtiendo tamaños de imagen a 150px")
    print("=" * 60)
    print()

    if not os.path.exists(css_file):
        print(f"ERROR: No se encuentra {css_file}")
        return 1

    # Leer el archivo
    with open(css_file, 'r', encoding='utf-8') as f:
        content = f.read()

    changes_made = []

    # 1. Revertir height: 180px -> height: 150px
    pattern1 = r'height:\s*180px'
    replacement1 = 'height: 150px'
    count1 = len(re.findall(pattern1, content))
    content = re.sub(pattern1, replacement1, content)
    if count1 > 0:
        changes_made.append(f"✓ Revertidas {count1} instancias de 'height: 180px' a 'height: 150px'")

    # 2. Revertir max-width: 180px -> max-width: 150px
    pattern2 = r'max-width:\s*180px'
    replacement2 = 'max-width: 150px'
    count2 = len(re.findall(pattern2, content))
    content = re.sub(pattern2, replacement2, content)
    if count2 > 0:
        changes_made.append(f"✓ Revertidas {count2} instancias de 'max-width: 180px' a 'max-width: 150px'")

    # 3. Revertir width: 120px -> width: 100px (solo los relacionados con covers)
    pattern3 = r'width:\s*120px'
    replacement3 = 'width: 100px'
    count3 = len(re.findall(pattern3, content))
    content = re.sub(pattern3, replacement3, content)
    if count3 > 0:
        changes_made.append(f"✓ Revertidas {count3} instancias de 'width: 120px' a 'width: 100px'")

    # Guardar el archivo modificado
    with open(css_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print("Cambios aplicados:")
    for change in changes_made:
        print(f"  {change}")
    print()
    print(f"✓ Archivo actualizado: {css_file}")
    print("=" * 60)

    return 0

if __name__ == '__main__':
    import sys
    sys.exit(revert_image_sizes())
