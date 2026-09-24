// reseau.h - la tache reseau, sur le Core 0
//
// L'affichage ne doit jamais figer. Or un appel HTTP bloque : jusqu'a
// plusieurs secondes quand la passerelle est tombee, et c'est precisement
// alors que l'ecran de liaison perdue doit rester vivant. Tout le reseau vit
// donc ici, dans une tache FreeRTOS epinglee sur le Core 0 (celui de la pile
// Wi-Fi), pendant que loop() dessine sur le Core 1 sans jamais attendre.
//
//   Core 0 : tacheReseau  -> Wi-Fi, mDNS, fetchGateway() -> g_partage
//   Core 1 : loop()       -> recupereEtat() -> dessin -> flipDMABuffer()
//
// Le seul point de contact est g_partage, garde par un mutex. La tache
// reseau remplit sa propre copie hors verrou, puis ne le prend que le temps
// d'une recopie. Le Core 1 le tente sans attendre (delai nul) : s'il est
// pris, il redessine l'etat precedent et reessaie a l'image suivante.
//
// Inclus depuis panneau_vols.ino APRES passerelle.h.

#ifndef RESEAU_H
#define RESEAU_H

#include <ESPmDNS.h>

// Nom sous lequel le panneau s'annonce lui-meme : panneau-vols.local
static const char *MDNS_NOM = "panneau-vols";
// Nouvel essai de connexion Wi-Fi quand la liaison est tombee
static const uint32_t WIFI_RELANCE_MS = 10000;
// Echecs HTTP d'affilee avant de redemander l'adresse au mDNS : le PC a pu
// changer d'adresse, par exemple au renouvellement du bail DHCP.
static const uint8_t ECHECS_AVANT_RESOLUTION = 3;
static const uint32_t PILE_RESEAU = 16384;  // HTTPClient + ArduinoJson

static EtatPasserelle g_partage;      // ecrit par le Core 0, sous g_verrou
static uint32_t g_partageNumero = 0;  // incremente a chaque reponse
static SemaphoreHandle_t g_verrou = nullptr;
static char g_url[64] = "";           // n'est lu et ecrit que par le Core 0

// Adresse de la passerelle : le nom mDNS d'abord, l'adresse fixe en repli.
static void resoutPasserelle(bool mdnsPret) {
  IPAddress ip;
  if (mdnsPret && GATEWAY_HOST[0]) ip = MDNS.queryHost(GATEWAY_HOST, 2000);
  if (ip == IPAddress(0, 0, 0, 0)) ip.fromString(GATEWAY_IP);
  snprintf(g_url, sizeof(g_url), "http://%s:%u/flight",
           ip.toString().c_str(), (unsigned)GATEWAY_PORT);
  Serial.printf("passerelle : %s\n", g_url);
}

static void tacheReseau(void *) {
  // Statique : hors de la pile de la tache, qui n'en a pas besoin de deux.
  static EtatPasserelle recu;
  uint32_t dernierEssaiWifi = millis();
  bool mdnsPret = false;
  uint8_t echecs = 0;
  for (;;) {
    uint32_t debut = millis();
    if (WiFi.status() != WL_CONNECTED) {
      if (debut - dernierEssaiWifi >= WIFI_RELANCE_MS) {
        dernierEssaiWifi = debut;
        WiFi.reconnect();
      }
    } else {
      if (!mdnsPret) mdnsPret = MDNS.begin(MDNS_NOM);
      if (!g_url[0] || echecs >= ECHECS_AVANT_RESOLUTION) {
        resoutPasserelle(mdnsPret);
        echecs = 0;
      }
      recu = EtatPasserelle();
      if (fetchGateway(g_url, recu)) {
        echecs = 0;
        xSemaphoreTake(g_verrou, portMAX_DELAY);  // le temps d'une recopie
        g_partage = recu;
        g_partageNumero++;
        xSemaphoreGive(g_verrou);
      } else if (echecs < 255) {
        echecs++;
      }
    }
    uint32_t ecoule = millis() - debut;
    vTaskDelay(pdMS_TO_TICKS(ecoule < POLL_MS ? POLL_MS - ecoule : 50));
  }
}

// Lance le Wi-Fi et la tache reseau, sans rien attendre.
static void demarreReseau() {
  g_verrou = xSemaphoreCreateMutex();
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  xTaskCreatePinnedToCore(tacheReseau, "reseau", PILE_RESEAU, nullptr, 1,
                          nullptr, 0);
}

// Cote Core 1 : recopie le dernier etat s'il est nouveau. Ne bloque jamais :
// verrou pris par le Core 0, on repassera a l'image suivante.
static bool recupereEtat(EtatPasserelle &dest, uint32_t &numeroLu) {
  if (xSemaphoreTake(g_verrou, 0) != pdTRUE) return false;
  bool nouveau = g_partageNumero != numeroLu;
  if (nouveau) {
    dest = g_partage;
    numeroLu = g_partageNumero;
  }
  xSemaphoreGive(g_verrou);
  return nouveau;
}

#endif  // RESEAU_H
