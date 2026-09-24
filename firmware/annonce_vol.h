// annonce_vol.h - quand l'annonce d'un avion doit partir
//
// Meme regle que passerelle.Gateway._alerte_en_cours : un avion s'annonce
// la premiere fois que la passerelle met l'ecran "vol" a l'antenne avec son
// indicatif, et non des qu'il apparait. Un avion arrive pendant un ecran de
// priere attend donc que la rotation en sorte, des deux cotes du jumeau.
// Declencher sur le seul changement d'indicatif lancait le chrono pendant la
// priere : l'annonce etait expiree quand "sc" passait a "vol", et le panneau
// sautait l'annonce que le simulateur montrait.
//
// Aucune dependance Arduino : verif_annonce.py compile ce fichier sur le PC
// et rejoue les memes scenarios que la passerelle Python.

#ifndef ANNONCE_VOL_H
#define ANNONCE_VOL_H

#include <stddef.h>
#include <stdio.h>
#include <string.h>

// Vrai si l'annonce doit partir maintenant. dejaAnnonce retient le dernier
// indicatif annonce, et n'est mis a jour que lorsque l'ecran est "vol".
static bool annonceVolDue(const char *ecran, bool volOk, const char *indicatif,
                          char *dejaAnnonce, size_t taille) {
  if (!volOk || strcmp(ecran, "vol") != 0) return false;
  if (strcmp(indicatif, dejaAnnonce) == 0) return false;
  snprintf(dejaAnnonce, taille, "%s", indicatif);
  return true;
}

#endif  // ANNONCE_VOL_H
