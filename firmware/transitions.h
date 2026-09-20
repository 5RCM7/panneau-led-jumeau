// transitions.h - roulement vertical entre deux ecrans
//
// Jumeau de transitions.py. La duree et la courbe doivent garder les memes
// valeurs que du cote Python, sinon les deux panneaux n'animent pas pareil.
//
// L'ecran sortant monte, l'entrant le suit par le bas. Aucun tampon
// supplementaire : on dessine les deux ecrans dans la meme trame, decales par
// g_dy, et ce qui deborde est perdu.
//
// Inclus AVANT px(), qui lit g_dy a chaque pixel.

#ifndef TRANSITIONS_H
#define TRANSITIONS_H

// Mise en page - memes valeurs que transitions.py
static const uint32_t TRANSITION_MS = 450;

// Decalage vertical applique a tout ce qui est dessine.
static int16_t g_dy = 0;

// Courbe en S : demarrage et arrivee freines, milieu rapide. Meme formule
// que du cote Python. En lineaire, l'a-coup de debut et de fin se voit
// nettement sur 32 pixels de haut.
static float adoucis(float avancement) {
  float t = avancement < 0.0f ? 0.0f : (avancement > 1.0f ? 1.0f : avancement);
  return t * t * (3.0f - 2.0f * t);
}

#endif  // TRANSITIONS_H
