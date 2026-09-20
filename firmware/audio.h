// audio.h - adhan et iqama par DFPlayer Mini
//
// Jumeau d'audio.py pour les constantes ; la politique, elle, vit cote
// Python. Le firmware recoit un son, un volume et une cle, et joue quand la
// cle change. Il ne decide rien, exactement comme pour la rotation.
//
// Pourquoi un module plutot qu'un ampli I2S : la bibliotheque du panneau est
// ESP32-HUB75-MatrixPanel-I2S-DMA, qui tient le peripherique I2S et la DMA
// en permanence pour rafraichir les LED. Un decodeur MP3 sur le meme ESP32
// se disputerait la DMA avec l'affichage, et ferait scintiller le panneau
// pendant les trois minutes de l'adhan. Le DFPlayer decode et amplifie dans
// son coin ; il ne coute que deux broches et quelques octets de serie.
//
// CABLAGE
//   DFPlayer VCC  -> 5 V (la meme alimentation que le panneau)
//   DFPlayer GND  -> GND
//   DFPlayer RX   -> GPIO 18 de l'ESP32, au travers d'une resistance de 1 k
//   DFPlayer TX   -> GPIO 35 (entree seule, ce qui suffit)
//   DFPlayer SPK_1 / SPK_2 -> petit haut-parleur 3 W
//   ou DAC_R / GND -> entree ligne d'une enceinte amplifiee, bien meilleur
//
// CARTE MICROSD, formatee en FAT32
//   /mp3/0001.mp3   l'adhan
//   /mp3/0002.mp3   le signal court de l'iqama
//
// Inclus depuis panneau_vols.ino AVANT passerelle.h.

#ifndef AUDIO_H
#define AUDIO_H

// Pistes - memes valeurs qu'audio.py
static const int16_t SON_AUCUN = 0;
static const int16_t SON_ADHAN = 1;
static const int16_t SON_IQAMA = 2;
static const int16_t VOLUME_MAX = 30;
static const int16_t VOLUME_JOUR = 22;
static const int16_t VOLUME_NUIT = 12;

// Broches de la liaison serie vers le module
static const int8_t AUDIO_TX = 18;
static const int8_t AUDIO_RX = 35;
static const uint32_t AUDIO_BAUD = 9600;

// Commandes DFPlayer utilisees. Le protocole tient en une trame de dix
// octets ; l'ecrire a la main evite une bibliotheque de plus, et rend le
// dialogue entierement lisible ici.
static const uint8_t DFP_JOUER_MP3 = 0x12;  // joue /mp3/NNNN.mp3 par numero
static const uint8_t DFP_VOLUME = 0x06;
static const uint8_t DFP_STOP = 0x16;

struct Audio {
  bool ok = false;
  int16_t son = 0;
  int16_t volume = -1;
  char cue[24] = "";  // "MAGHREB:iqama" - on joue quand elle change
};

static char g_audioCue[24] = "";
static int16_t g_audioVolume = -1;
// Au premier echange on enregistre la cle sans jouer : sinon un redemarrage
// pendant la fenetre d'une priere relancerait l'adhan dans le salon.
static bool g_audioAmorce = false;

// Trame DFPlayer : 7E FF 06 CMD 00 PARAM_H PARAM_L SOMME_H SOMME_L EF.
// La somme de controle est l'oppose de la somme des octets 1 a 6.
static void audioCommande(uint8_t commande, uint16_t parametre) {
  uint8_t trame[10] = {0x7E, 0xFF, 0x06, commande, 0x00,
                       (uint8_t)(parametre >> 8), (uint8_t)(parametre & 0xFF),
                       0x00, 0x00, 0xEF};
  uint16_t somme = 0;
  for (uint8_t n = 1; n <= 6; n++) somme += trame[n];
  somme = (uint16_t)(-somme);
  trame[7] = (uint8_t)(somme >> 8);
  trame[8] = (uint8_t)(somme & 0xFF);
  Serial2.write(trame, sizeof(trame));
}

static void audioVolume(int16_t niveau) {
  if (niveau < 0 || niveau > VOLUME_MAX || niveau == g_audioVolume) return;
  g_audioVolume = niveau;
  audioCommande(DFP_VOLUME, (uint16_t)niveau);
}

static void audioSetup() {
  Serial2.begin(AUDIO_BAUD, SERIAL_8N1, AUDIO_RX, AUDIO_TX);
  delay(600);  // le module met une demi-seconde a monter sa carte
  audioVolume(VOLUME_NUIT);
}

// Joue la piste demandee quand la cle change, et rien d'autre. Appelee a
// chaque reponse de la passerelle, donc toutes les trois secondes : c'est
// la cle, et non l'appel, qui decide.
static void audioAppliquer(const Audio &a) {
  if (!a.ok) return;
  audioVolume(a.volume);
  if (strcmp(a.cue, g_audioCue) == 0) return;
  snprintf(g_audioCue, sizeof(g_audioCue), "%s", a.cue);
  if (!g_audioAmorce) {
    g_audioAmorce = true;  // premiere reponse : on note, on ne joue pas
    return;
  }
  if (a.son > SON_AUCUN) audioCommande(DFP_JOUER_MP3, (uint16_t)a.son);
}

#endif  // AUDIO_H
