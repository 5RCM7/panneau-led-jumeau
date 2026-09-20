"""Tampon de pixels du panneau, et primitives de dessin.

Separe de panel.py, qui n'y garde que la mise en page de l'ecran des vols :
tous les ecrans passent par cette classe, et elle n'a rien a voir avec l'un
d'eux en particulier.

Dimensions et palette vivent ici parce que tout le monde s'en sert. Elles
restent soumises a la regle du jumeau : memes valeurs que dans le firmware.
"""

import struct
import zlib

WIDTH = 128
HEIGHT = 32

# Palette : chaque couleur porte un role, pas une teinte. Memes valeurs dans
# firmware/panneau_vols.ino, c'est la troisieme moitie de la regle du jumeau.
TEXTE = (255, 170, 40)        # texte courant : bandeau, iqama
SECONDAIRE = (122, 122, 134)  # second plan : niveau de vol, mosquee, horloge
ACCENT = (80, 255, 140)       # mise en valeur : route, nom de la priere
PRINCIPAL = (255, 255, 255)   # premier plan : indicatif, priere imminente
SEP = (40, 40, 50)            # filets de separation

import font5x7  # noqa: E402  (apres les constantes, pour rester lisible)
from font5x7 import ADVANCE


class Frame:
    """Tampon de pixels RGB de 128x32, identique au framebuffer du panneau."""

    def __init__(self, width=WIDTH, height=HEIGHT):
        self.width = width
        self.height = height
        self.buf = bytearray(width * height * 3)
        # decalage vertical applique a tout ce qui est dessine, et ce qui
        # sort du cadre est simplement perdu. C'est le seul mecanisme dont
        # transitions.py a besoin pour faire glisser deux ecrans.
        self.dy = 0

    def clear(self):
        for i in range(len(self.buf)):
            self.buf[i] = 0

    def set(self, x, y, color):
        y += self.dy
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return
        i = (y * self.width + x) * 3
        self.buf[i] = color[0]
        self.buf[i + 1] = color[1]
        self.buf[i + 2] = color[2]

    def vline(self, x, y0, y1, color):
        for y in range(y0, y1 + 1):
            self.set(x, y, color)

    def draw_char(self, x, y, char, color, clip=None):
        pattern = font5x7.glyph(char)
        for row, bits in enumerate(pattern):
            for col, bit in enumerate(bits):
                if bit != "#":
                    continue
                px = x + col
                if clip is not None and (px < clip[0] or px > clip[1]):
                    continue
                self.set(px, y + row, color)

    def draw_text(self, x, y, text, color, clip=None):
        cursor = x
        for char in text:
            if clip is None or (cursor + font5x7.GLYPH_WIDTH >= clip[0]
                                and cursor <= clip[1]):
                self.draw_char(cursor, y, char, color, clip)
            cursor += ADVANCE
        return cursor

    def draw_text_echelle(self, x, y, text, color, echelle, clip=None):
        """Texte agrandi : chaque pixel de la police devient un carre.

        Pas d'interpolation, a dessein : sur un panneau LED, un gros chiffre
        net vaut mieux qu'un gros chiffre flou. A l'echelle 3, un glyphe fait
        15x21 pixels et avance de ADVANCE * 3.
        """
        curseur = x
        for char in text:
            motif = font5x7.glyph(char)
            for ligne, bits in enumerate(motif):
                for colonne, bit in enumerate(bits):
                    if bit != "#":
                        continue
                    for dx in range(echelle):
                        px = curseur + colonne * echelle + dx
                        if clip is not None and (px < clip[0] or px > clip[1]):
                            continue
                        for dy in range(echelle):
                            self.set(px, y + ligne * echelle + dy, color)
            curseur += ADVANCE * echelle
        return curseur

    def draw_bitmap(self, x, y, bitmap):
        """bitmap = (largeur, hauteur, liste de tuples RGB)."""
        bw, bh, pixels = bitmap
        for row in range(bh):
            for col in range(bw):
                pixel = pixels[row * bw + col]
                if pixel[0] or pixel[1] or pixel[2]:
                    self.set(x + col, y + row, pixel)

    def draw_sprite(self, x, y, motif, color, clip=None):
        """motif = suite de chaines de '.' et '#', comme les silhouettes."""
        for row, rangee in enumerate(motif):
            for col, point in enumerate(rangee):
                if point != "#":
                    continue
                px = x + col
                if clip is not None and (px < clip[0] or px > clip[1]):
                    continue
                self.set(px, y + row, color)

    def attenue(self, niveau):
        """Baisse la luminosite de toute l'image, 255 laissant intact.

        Jumelle de dma->setBrightness8() : sans elle, le simulateur montrerait
        le panneau a pleine puissance alors que le vrai serait tamise, et on
        ne pourrait pas juger de nuit ce que donnera l'affichage.
        """
        if niveau >= 255:
            return self
        for i in range(len(self.buf)):
            self.buf[i] = self.buf[i] * niveau // 255
        return self

    def to_rgb_bytes(self):
        return bytes(self.buf)

    def to_png_bytes(self, scale=1):
        """Encode le tampon en PNG (zlib seulement, pas de dependance)."""
        w, h = self.width * scale, self.height * scale
        raw = bytearray()
        for y in range(h):
            raw.append(0)
            src = (y // scale) * self.width * 3
            for x in range(w):
                i = src + (x // scale) * 3
                raw += self.buf[i:i + 3]

        def chunk(tag, data):
            out = struct.pack(">I", len(data)) + tag + data
            return out + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

        header = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
        return (b"\x89PNG\r\n\x1a\n"
                + chunk(b"IHDR", header)
                + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
                + chunk(b"IEND", b""))


def droite(frame, x_fin, y, texte, couleur, clip=None):
    """Ecrit un texte cale sur x_fin, son dernier pixel a cette abscisse."""
    if not texte:
        return
    frame.draw_text(x_fin - font5x7.text_width(texte) + 1, y, texte, couleur,
                    clip)


def centre(frame, y, texte, couleur, largeur=WIDTH):
    """Ecrit un texte centre sur la largeur donnee."""
    if not texte:
        return
    frame.draw_text((largeur - font5x7.text_width(texte)) // 2, y, texte,
                    couleur)


def largeur_echelle(texte, echelle):
    """Largeur en pixels d'un texte agrandi."""
    if not texte:
        return 0
    return len(texte) * ADVANCE * echelle - echelle


def centre_echelle(frame, y, texte, couleur, echelle, largeur=WIDTH):
    """Ecrit un texte agrandi, centre sur la largeur donnee."""
    if not texte:
        return
    x = (largeur - largeur_echelle(texte, echelle)) // 2
    frame.draw_text_echelle(x, y, texte, couleur, echelle)
