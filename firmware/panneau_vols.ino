// panneau_vols.ino - firmware ESP32 du panneau LED "gare" 128x32
//
// Jumeau numerique : ce croquis reproduit exactement la mise en page de
// panel.py. Les constantes de position sont identiques, ligne pour ligne,
// et la police vient du meme fichier source (font5x7.py -> font5x7.h).
//
// Bibliotheques a installer (gestionnaire de bibliotheques Arduino) :
//   - ESP32 HUB75 LED MATRIX PANEL DMA Display  (mrcodetastic)
//   - Adafruit GFX Library                      (dependance de la precedente,
//     qui tire elle-meme Adafruit BusIO ; sans elle la compilation echoue sur
//     Adafruit_GFX.h introuvable)
//   - ArduinoJson                               (Benoit Blanchon, v7)
//
// REGLAGE OBLIGATOIRE : Outils > Partition Scheme > "Huge APP (3MB No OTA)".
// Avec le schema par defaut le croquis remplit 87 % des 1,3 Mo disponibles et
// il ne reste pas la place des logos. En Huge APP : 36 % de 3,1 Mo.
//
// Cablage HUB75 et branchements : voir README.md.
// Alimentation 5 V dediee pour les panneaux, jamais via l'USB de l'ESP32.

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <ESP32-HUB75-MatrixPanel-I2S-DMA.h>

#include "font5x7.h"
#include "audio.h"

// Logos des compagnies, generes par export_logos.py depuis logos/*.png.
// Le fichier n'existe pas tant qu'on n'a pas lance le script : le croquis
// compile sans, et affiche alors la silhouette d'avion pour tout le monde.
#if __has_include("logos.h")
#include "logos.h"
#define AVEC_LOGOS 1
#endif

// ---------------------------------------------------------------- reglages
static const char *WIFI_SSID = "TON_RESEAU";
static const char *WIFI_PASS = "TON_MOT_DE_PASSE";

// Adresse de la passerelle Python (server.py) sur le reseau local.
static const char *GATEWAY_URL = "http://192.168.1.20:8080/flight";

// Cadence d'interrogation de la passerelle. C'est une requete sur le reseau
// local, pas un appel d'API : elle ne coute rien et c'est la passerelle qui
// menage les APIs publiques, a son propre rythme (poll_seconds). Trois
// secondes suffisent pour suivre une rotation d'ecran de trente secondes.
static const uint32_t POLL_MS = 3000;
static const uint32_t HOLD_MS = 90000;   // on garde le dernier vol 90 s

// Luminosite de depart, avant la premiere reponse de la passerelle. Celle-ci
// envoie ensuite un niveau selon l'heure dans le champ "br" : un panneau a
// pleine puissance dans un salon a trois heures du matin est insupportable.
static const uint8_t BRIGHTNESS = 40;    // 0-255, 40 suffit dans un salon

// ------------------------------------------------------------- GPIO HUB75
#define P_R1 25
#define P_G1 26
#define P_B1 27
#define P_R2 14
#define P_G2 12
#define P_B2 13
#define P_A 23
#define P_B 19
#define P_C 5
#define P_D 17
#define P_E 32  // inutilise en 1/16, requis pour les panneaux 64x64
#define P_CLK 16
#define P_LAT 4
#define P_OE 15

#define PANEL_W 64
#define PANEL_H 32
#define PANEL_CHAIN 2  // deux panneaux 64x32 en ligne = 128x32

// ------------------------------------------- mise en page (cf. panel.py)
static const int16_t WIDTH_PX = PANEL_W * PANEL_CHAIN;
static const int16_t LOGO_X0 = 0, LOGO_X1 = 29;
static const int16_t SEP_X = 31;
static const int16_t TEXT_X0 = 34, TEXT_X1 = WIDTH_PX - 2;
static const int16_t TEXT_W = TEXT_X1 - TEXT_X0 + 1;
static const int16_t LINE1_Y = 1, LINE2_Y = 12, LINE3_Y = 23;

static const float SCROLL_PX_PER_SEC = 14.0f;
static const int16_t SCROLL_GAP = 12;

// Couleurs en 0xRRGGBB. Chaque couleur porte un role, pas une teinte.
// Memes valeurs que panel.py : troisieme moitie de la regle du jumeau.
static const uint32_t RGB_TEXTE = 0xFFAA28;       // bandeau, iqama
static const uint32_t RGB_SECONDAIRE = 0x7A7A86;  // niveau de vol, mosquee
static const uint32_t RGB_ACCENT = 0x50FF8C;      // route, nom de la priere
static const uint32_t RGB_PRINCIPAL = 0xFFFFFF;   // indicatif, priere imminente
static const uint32_t RGB_SEP = 0x282832;         // filets de separation

MatrixPanel_I2S_DMA *dma = nullptr;

// ------------------------------------------------------------- etat du vol
struct Flight {
  bool ok = false;
  char callsign[12] = "";
  char airline[28] = "";
  char icao[5] = "";
  char from[5] = "";
  char to[5] = "";
  char city[28] = "";
  char avion[32] = "";  // BOEING 777 328ER, ou le code type a defaut
  char level[8] = "";
  float km = -1.0f;
  char ticker[144] = "";
};

static Flight g_flight;
static uint32_t g_lastPoll = 0;
static uint32_t g_lastOk = 0;
// Derniere reponse de la passerelle. Sans elle, l'heure affichee se fige :
// l'ESP32 n'a pas d'horloge, cf. ecran_liaison.h.
static uint32_t g_lastGateway = 0;

// ------------------------------------------------------------ rendu texte
static int16_t textWidth(const char *text) {
  size_t n = strlen(text);
  return n ? (int16_t)(n * FONT_ADVANCE - 1) : 0;
}

#include "transitions.h"

static inline void px(int16_t x, int16_t y, uint32_t rgb) {
  y += g_dy;  // decalage de transition, cf. transitions.h
  // Memes bornes que Frame.set() en Python : ce qui sort du cadre est perdu,
  // aussi bien pour les transitions que pour l'avion de l'ecran d'alerte.
  if (x < 0 || x >= WIDTH_PX || y < 0 || y >= PANEL_H) return;
  dma->drawPixelRGB888(x, y, (rgb >> 16) & 0xFF, (rgb >> 8) & 0xFF, rgb & 0xFF);
}

static void drawChar(int16_t x, int16_t y, char c, uint32_t rgb, int16_t clipL,
                     int16_t clipR) {
  const uint8_t *glyph = fontGlyph(c);
  for (uint8_t row = 0; row < FONT_HEIGHT; row++) {
    uint8_t bits = glyph[row];
    if (!bits) continue;
    for (uint8_t col = 0; col < FONT_WIDTH; col++) {
      if (!(bits & (0x10 >> col))) continue;
      int16_t p = x + col;
      if (p < clipL || p > clipR) continue;
      px(p, y + row, rgb);
    }
  }
}

static void drawText(int16_t x, int16_t y, const char *text, uint32_t rgb,
                     int16_t clipL, int16_t clipR) {
  int16_t cursor = x;
  for (const char *p = text; *p; ++p) {
    if (cursor + FONT_WIDTH >= clipL && cursor <= clipR)
      drawChar(cursor, y, *p, rgb, clipL, clipR);
    cursor += FONT_ADVANCE;
  }
}

// Inclus ici, et non en tete de fichier, parce que l'ecran des prieres se
// sert des primitives et des constantes ci-dessus sans les redeclarer.
// L'ordre compte : chaque en-tete se sert de ce que les precedents
// declarent. ecran_horaires.h et ecran_adkar.h viennent en dernier : ils ont
// besoin de drawSprite (ecran_alerte.h), de drawTextEchelle (ecran_heure.h)
// et de leurs silhouettes respectives.
#include "ecran_prieres.h"
#include "ecran_alerte.h"
#include "ecran_liaison.h"
#include "ecran_claude.h"
#include "icones_meteo.h"
#include "ecran_meteo.h"
#include "ecran_heure.h"
#include "arabe.h"
#include "ecran_horaires.h"
#include "ecran_annonces.h"
#include "adkar.h"
#include "ecran_adkar.h"

static Heure g_heure;
static Meteo g_meteo;
static Usage g_usage;
static Prieres g_prieres;
// Assez large pour "horaires" et son zero final : a 8 octets le nom etait
// tronque en "horaire", que ecranDepuisNom() ne reconnait pas, et le panneau
// retombait en veille a chaque tour du tableau.
static char g_screen[12] = "";
static uint32_t g_alerte = 0;        // millis du debut de l'annonce d'avion
static uint32_t g_alertePriere = 0;  // idem pour l'annonce de priere
static uint32_t g_alerteMeteo = 0;   // idem pour l'annonce meteo
static char g_priereAnnoncee[12] = "";
static int16_t g_adkar = -1;         // rang de l'entree adkar, choisi par la
                                     // passerelle

#include "ecran_vol.h"

// --------------------------------------------------------- choix d'ecran
enum { ECRAN_VEILLE = 0, ECRAN_VOL, ECRAN_PRIERE, ECRAN_HORAIRES, ECRAN_METEO,
       ECRAN_HEURE, ECRAN_ADKAR, ECRAN_CLAUDE, ECRAN_ANNONCES,
       ECRAN_LIAISON, ECRAN_ALERTE, ECRAN_ALERTE_PRIERE, ECRAN_ALERTE_METEO };

// Nom d'ecran envoye par la passerelle dans "sc" -> constante locale.
static uint8_t ecranDepuisNom(const char *nom) {
  if (strcmp(nom, "priere") == 0) return ECRAN_PRIERE;
  if (strcmp(nom, "horaires") == 0) return ECRAN_HORAIRES;
  if (strcmp(nom, "annonces") == 0) return ECRAN_ANNONCES;
  if (strcmp(nom, "meteo") == 0) return ECRAN_METEO;
  if (strcmp(nom, "heure") == 0) return ECRAN_HEURE;
  if (strcmp(nom, "adkar") == 0) return ECRAN_ADKAR;
  if (strcmp(nom, "claude") == 0) return ECRAN_CLAUDE;
  if (strcmp(nom, "vol") == 0) return ECRAN_VOL;
  return ECRAN_VEILLE;
}

static uint8_t g_ecran = ECRAN_VEILLE;
static uint8_t g_ecranPrecedent = ECRAN_VEILLE;
static uint32_t g_bascule = 0;  // millis du dernier changement d'ecran

static void dessineEcran(uint8_t ecran, uint32_t nowMs) {
  if (ecran == ECRAN_ALERTE) {
    float avancement = g_alerte ? (nowMs - g_alerte) / (float)ALERTE_MS : 1.0f;
    renderAlerte(g_flight, avancement);
  } else if (ecran == ECRAN_ALERTE_PRIERE) {
    float avancement =
        g_alertePriere ? (nowMs - g_alertePriere) / (float)ALERTE_MS : 1.0f;
    renderAlertePriere(g_prieres, avancement);
  } else if (ecran == ECRAN_VOL) {
    renderFlight(g_flight, nowMs, g_heure.heure);
  } else if (ecran == ECRAN_PRIERE) {
    renderPrieres(g_prieres);
  } else if (ecran == ECRAN_HORAIRES) {
    renderHoraires(g_prieres, nowMs);
  } else if (ecran == ECRAN_ANNONCES) {
    renderAnnonces(g_prieres, nowMs);
  } else if (ecran == ECRAN_LIAISON) {
    renderLiaison(g_lastGateway ? nowMs - g_lastGateway : nowMs);
  } else if (ecran == ECRAN_METEO) {
    renderMeteo(g_meteo);
  } else if (ecran == ECRAN_HEURE) {
    renderHeure(g_heure);
  } else if (ecran == ECRAN_ADKAR) {
    renderAdkar(g_adkar, g_heure.heure, nowMs);
  } else if (ecran == ECRAN_CLAUDE) {
    renderClaude(g_usage, g_heure.heure, nowMs);
  } else if (ecran == ECRAN_ALERTE_METEO) {
    float avancement =
        g_alerteMeteo ? (nowMs - g_alerteMeteo) / (float)ALERTE_MS : 1.0f;
    renderAlerteMeteo(g_meteo, avancement);
  } else {
    renderIdle(g_heure.heure);
  }
}

#include "passerelle.h"

// ------------------------------------------------------------------ setup
void setup() {
  Serial.begin(115200);

  // Affectation champ par champ : plus lisible et insensible a l'ordre
  // des membres de la structure selon la version de la bibliotheque.
  HUB75_I2S_CFG cfg(PANEL_W, PANEL_H, PANEL_CHAIN);
  cfg.gpio.r1 = P_R1;
  cfg.gpio.g1 = P_G1;
  cfg.gpio.b1 = P_B1;
  cfg.gpio.r2 = P_R2;
  cfg.gpio.g2 = P_G2;
  cfg.gpio.b2 = P_B2;
  cfg.gpio.a = P_A;
  cfg.gpio.b = P_B;
  cfg.gpio.c = P_C;
  cfg.gpio.d = P_D;
  cfg.gpio.e = P_E;
  cfg.gpio.lat = P_LAT;
  cfg.gpio.oe = P_OE;
  cfg.gpio.clk = P_CLK;
  cfg.clkphase = false;  // a basculer si l'image est decalee d'une colonne

  dma = new MatrixPanel_I2S_DMA(cfg);
  dma->begin();
  dma->setBrightness8(BRIGHTNESS);
  dma->clearScreen();

  audioSetup();

  drawText(6, 12, "CONNEXION", RGB_SECONDAIRE, 0, WIDTH_PX - 1);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 20000) delay(250);

  Serial.println(WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString()
                                               : String("wifi absent"));
  g_lastPoll = millis() - POLL_MS;
}

// ------------------------------------------------------------------- loop
void loop() {
  uint32_t now = millis();

  if (now - g_lastPoll >= POLL_MS) {
    g_lastPoll = now;
    Flight fresh;
    Prieres prieres;
    Meteo meteo;
    Heure heure;
    Usage usage;
    Audio son;
    char screen[12] = "";
    int16_t adkarRang = -1;
    if (fetchGateway(fresh, prieres, meteo, heure, usage, son, screen,
                     sizeof(screen), adkarRang)) {
      g_lastGateway = now;
      // L'adhan part ici, sur la cle envoyee par la passerelle : c'est elle
      // qui decide quoi jouer et quand, cf. audio.py.
      audioAppliquer(son);
      g_meteo = meteo;
      g_heure = heure;
      g_usage = usage;
      g_adkar = adkarRang;
      // Priere qui prend la main pour la premiere fois : on l'annonce
      if (prieres.ok && prieres.priseMain
          && strcmp(prieres.nom, g_priereAnnoncee) != 0) {
        g_alertePriere = now;
        snprintf(g_priereAnnoncee, sizeof(g_priereAnnoncee), "%s", prieres.nom);
      }
      // La meteo s'annonce quand la rotation arrive sur elle, et non sur un
      // changement de donnee : le temps qu'il fait n'arrive pas, il est la.
      if (strcmp(screen, "meteo") == 0 && strcmp(g_screen, "meteo") != 0)
        g_alerteMeteo = now;
      g_prieres = prieres;
      snprintf(g_screen, sizeof(g_screen), "%s", screen);
      if (fresh.ok) {
        // Nouvel indicatif : on annonce l'avion avant d'afficher ses details
        if (strcmp(fresh.callsign, g_flight.callsign) != 0) g_alerte = now;
        g_flight = fresh;
        g_lastOk = now;
      }
    }
  }

  bool volFrais = g_flight.ok && now - g_lastOk < HOLD_MS;

  // Quel ecran devrait etre a l'antenne, independamment de l'animation
  bool alerteEnCours = g_alerte && now - g_alerte < ALERTE_MS;
  bool alertePriereEnCours =
      g_alertePriere && now - g_alertePriere < ALERTE_MS;
  bool alerteMeteoEnCours = g_alerteMeteo && now - g_alerteMeteo < ALERTE_MS;

  // La passerelle mene la rotation ; on ne fait que l'habiller d'une annonce
  uint8_t voulu = ecranDepuisNom(g_screen);
  if (voulu == ECRAN_PRIERE && alertePriereEnCours) voulu = ECRAN_ALERTE_PRIERE;
  else if (voulu == ECRAN_METEO && alerteMeteoEnCours) voulu = ECRAN_ALERTE_METEO;
  else if (voulu == ECRAN_VOL && alerteEnCours) voulu = ECRAN_ALERTE;

  // Passerelle muette depuis trop longtemps : plus rien n'est sur, pas meme
  // l'heure, et on le dit plutot que de laisser croire le panneau. C'est le
  // seul ecran que le firmware impose contre le champ "sc" : la passerelle
  // ne peut pas signaler son propre silence.
  if (liaisonPerdue(g_lastGateway ? now - g_lastGateway : now))
    voulu = ECRAN_LIAISON;

  // Garde-fous : si la passerelle devient injoignable, g_screen se fige sur
  // un ecran dont les donnees ont expire. Mieux vaut retomber que mentir.
  if ((voulu == ECRAN_VOL || voulu == ECRAN_ALERTE) && !volFrais)
    voulu = g_prieres.ok ? ECRAN_PRIERE : ECRAN_VEILLE;
  if ((voulu == ECRAN_PRIERE || voulu == ECRAN_HORAIRES
       || voulu == ECRAN_ALERTE_PRIERE) && !g_prieres.ok)
    voulu = volFrais ? ECRAN_VOL : ECRAN_VEILLE;
  if ((voulu == ECRAN_METEO || voulu == ECRAN_ALERTE_METEO) && !g_meteo.ok)
    voulu = volFrais ? ECRAN_VOL : ECRAN_VEILLE;
  if (voulu == ECRAN_ADKAR && g_adkar < 0) voulu = ECRAN_VEILLE;
  if (voulu == ECRAN_CLAUDE && !g_usage.ok) voulu = ECRAN_VEILLE;
  if (voulu == ECRAN_ANNONCES && !g_prieres.annonces[0])
    voulu = g_prieres.ok ? ECRAN_PRIERE : ECRAN_VEILLE;

  if (voulu != g_ecran) {
    g_ecranPrecedent = g_ecran;
    g_ecran = voulu;
    g_bascule = now;
  }

  dma->clearScreen();

  uint32_t depuis = now - g_bascule;
  if (g_bascule && depuis < TRANSITION_MS) {
    int16_t d = (int16_t)lroundf(adoucis(depuis / (float)TRANSITION_MS) * PANEL_H);
    g_dy = -d;
    dessineEcran(g_ecranPrecedent, now);
    g_dy = PANEL_H - d;
    dessineEcran(g_ecran, now);
    g_dy = 0;
  } else {
    dessineEcran(g_ecran, now);
  }

  delay(40);  // ~25 images par seconde, defilement fluide
}
