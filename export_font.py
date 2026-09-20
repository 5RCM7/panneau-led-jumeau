"""Exporte font5x7.py vers firmware/font5x7.h (meme police des deux cotes).

Lancer depuis le dossier du projet :  python3 export_font.py
"""

import os

import font5x7

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "firmware", "font5x7.h")

HEADER = """// Genere par export_font.py - ne pas editer a la main.
// Police 5x7 partagee entre le simulateur Python et le firmware ESP32.
// Chaque ligne d'un glyphe tient sur 5 bits, alignes a gauche (0x10 = colonne 0).

#pragma once
#include <stdint.h>

#define FONT_WIDTH 5
#define FONT_HEIGHT 7
#define FONT_ADVANCE 6

#define FONT_ARROW '\\x01'
#define FONT_PLANE '\\x02'
#define FONT_DEGRE '\\x03'

"""


def encode(pattern):
    rows = []
    for line in pattern:
        bits = 0
        for col, char in enumerate(line):
            if char == "#":
                bits |= 0x10 >> col
        rows.append(bits)
    return rows


def main():
    entries = []
    for char, pattern in sorted(font5x7.GLYPHS.items()):
        code = ord(char)
        rows = encode(pattern)
        label = char if 32 <= code < 127 else "\\x%02x" % code
        entries.append((code, rows, label))

    lines = [HEADER]
    lines.append("static const uint8_t FONT_COUNT = %d;\n\n" % len(entries))
    lines.append("static const uint8_t FONT_CODES[] = {\n  ")
    lines.append(", ".join("0x%02X" % code for code, _, _ in entries))
    lines.append("\n};\n\n")
    lines.append("static const uint8_t FONT_ROWS[][FONT_HEIGHT] = {\n")
    for code, rows, label in entries:
        body = ", ".join("0x%02X" % row for row in rows)
        lines.append("  {%s},  // '%s'\n" % (body, label))
    lines.append("};\n\n")
    lines.append("""static const uint8_t FONT_FALLBACK[FONT_HEIGHT] = {%s};

static inline const uint8_t *fontGlyph(char c) {
  uint8_t code = (uint8_t)c;
  if (code >= 'a' && code <= 'z') code -= 32;
  for (uint8_t i = 0; i < FONT_COUNT; i++)
    if (FONT_CODES[i] == code) return FONT_ROWS[i];
  return FONT_FALLBACK;
}
""" % ", ".join("0x%02X" % row for row in encode(font5x7.GLYPHS["?"])))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as handle:
        handle.write("".join(lines))
    print("ecrit %s (%d glyphes)" % (OUT, len(entries)))


if __name__ == "__main__":
    main()
