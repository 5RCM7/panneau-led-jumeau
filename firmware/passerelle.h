// passerelle.h - dialogue avec server.py
//
// Un seul appel ramene le vol, la priere et l'ecran a afficher. C'est la
// passerelle qui mene la rotation : le firmware obeit au champ "sc" sans
// rejouer la regle de son cote.
//
// Ce fichier tourne sur le Core 0, dans la tache reseau (cf. reseau.h) :
// il ne touche JAMAIS a l'affichage. Tout ce qu'il lit part dans une
// EtatPasserelle, que le Core 1 recopie et applique entre deux images. Meme
// la luminosite voyage ainsi, au lieu d'appeler setBrightness8() d'ici.
//
// Inclus depuis panneau_vols.ino APRES les structures Flight et Prieres.

#ifndef PASSERELLE_H
#define PASSERELLE_H

// Tout ce qu'une reponse de la passerelle apporte, en un bloc copiable.
struct EtatPasserelle {
  Flight flight;
  Prieres prieres;
  Meteo meteo;
  Heure heure;
  Usage usage;
  Audio son;
  char screen[12] = "";  // cf. g_screen : "horaires" et son zero final
  int16_t adkar = -1;    // rang de l'entree adkar, -1 sans
  int16_t br = -1;       // luminosite 0-255, -1 si absente
};

// ------------------------------------------------------------- passerelle
static void upperCopy(char *dst, size_t size, const char *src) {
  size_t i = 0;
  for (; src[i] && i + 1 < size; i++) dst[i] = toupper((unsigned char)src[i]);
  dst[i] = '\0';
}

static void appendPart(char *buf, size_t size, const char *part, bool &first) {
  if (!part || !part[0]) return;
  if (!first) strncat(buf, "   \x01   ", size - strlen(buf) - 1);
  strncat(buf, part, size - strlen(buf) - 1);
  first = false;
}

static void buildTicker(Flight &f) {
  char buf[144];
  buf[0] = '\0';
  bool first = true;
  // Meme ordre que build_ticker() en Python : compagnie, ville, appareil,
  // distance. L'appareil passe avant la distance, qui ferme la phrase.
  appendPart(buf, sizeof(buf), f.airline, first);
  appendPart(buf, sizeof(buf), f.city, first);
  appendPart(buf, sizeof(buf), f.avion, first);
  if (f.km >= 0) {
    char km[12];
    snprintf(km, sizeof(km), "%d KM", (int)lroundf(f.km));
    appendPart(buf, sizeof(buf), km, first);
  }
  if (first) snprintf(buf, sizeof(buf), "ROUTE INCONNUE");
  upperCopy(f.ticker, sizeof(f.ticker), buf);
}

// Recupere en un seul appel le vol, la priere, et l'ecran a afficher.
// C'est la passerelle qui arbitre entre les deux ecrans : le firmware obeit
// au champ "sc" sans rejouer la regle de priorite de son cote.
//
// Bloquant, et c'est voulu : il ne tourne que dans la tache reseau. Les
// delais bornent seulement la duree d'un essai, l'affichage ne les voit pas.
static bool fetchGateway(const char *url, EtatPasserelle &out) {
  if (WiFi.status() != WL_CONNECTED || !url[0]) return false;

  HTTPClient http;
  http.setConnectTimeout(2000);
  http.setTimeout(4000);
  if (!http.begin(url)) return false;

  int code = http.GET();
  if (code != 200) {
    http.end();
    return false;
  }

  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, http.getStream());
  http.end();
  if (err) return false;

  snprintf(out.screen, sizeof(out.screen), "%s", doc["sc"] | "");

  // Rang de l'entree adkar : la passerelle le choisit, comme elle choisit
  // l'ecran. -1 quand elle n'en envoie pas, et l'ecran est alors saute.
  out.adkar = doc["ad"] | -1;

  Prieres p;
  JsonObjectConst pr = doc["pr"];
  if (!pr.isNull()) {
    p.ok = true;
    upperCopy(p.nom, sizeof(p.nom), pr["n"] | "");
    upperCopy(p.adhan, sizeof(p.adhan), pr["a"] | "");
    upperCopy(p.iqama, sizeof(p.iqama), pr["i"] | "");
    upperCopy(p.restant, sizeof(p.restant), pr["r"] | "");
    upperCopy(p.mosquee, sizeof(p.mosquee), pr["m"] | "");
    upperCopy(p.heure, sizeof(p.heure), pr["h"] | "");
    upperCopy(p.horaires, sizeof(p.horaires), pr["pt"] | "");
    upperCopy(p.annonces, sizeof(p.annonces), pr["an"] | "");
    p.priseMain = pr["u"] | false;
    p.enCours = pr["e"] | false;
    p.demain = pr["d"] | false;
    p.rang = pr["rg"] | -1;
    p.joumoua = pr["jm"] | false;
  }
  out.prieres = p;

  Meteo m;
  JsonObjectConst mt = doc["mt"];
  if (!mt.isNull()) {
    m.ok = true;
    m.temperature = mt["t"] | 0;
    m.ressenti = mt["r"] | 0;
    m.vent = mt["v"] | -1;
    m.icone = mt["i"] | -1;
    m.pluieMin = mt["pm"] | -1;
    upperCopy(m.pluieHeure, sizeof(m.pluieHeure), mt["ph"] | "");
    upperCopy(m.texte, sizeof(m.texte), mt["x"] | "");
    upperCopy(m.lieu, sizeof(m.lieu), mt["l"] | "");
    upperCopy(m.heure, sizeof(m.heure), mt["h"] | "");
  }
  out.meteo = m;

  Heure hr;
  JsonObjectConst ho = doc["hr"];
  if (!ho.isNull()) {
    hr.ok = true;
    upperCopy(hr.heure, sizeof(hr.heure), ho["h"] | "");
    upperCopy(hr.date, sizeof(hr.date), ho["d"] | "");
  }
  out.heure = hr;

  Audio au;
  JsonObjectConst ao = doc["au"];
  if (!ao.isNull()) {
    au.ok = true;
    au.son = ao["s"] | 0;
    au.volume = ao["v"] | -1;
    snprintf(au.cue, sizeof(au.cue), "%s", ao["c"] | "");
  }
  out.son = au;

  Usage u;
  JsonObjectConst cl = doc["cl"];
  if (!cl.isNull()) {
    u.ok = true;
    upperCopy(u.cleA, sizeof(u.cleA), cl["ka"] | "");
    upperCopy(u.cleB, sizeof(u.cleB), cl["kb"] | "");
    u.restantA = cl["ra"] | -1;
    u.restantB = cl["rb"] | -1;
    upperCopy(u.resetA, sizeof(u.resetA), cl["ta"] | "");
    upperCopy(u.resetB, sizeof(u.resetB), cl["tb"] | "");
  }
  out.usage = u;

  // Luminosite selon l'heure, decidee par la passerelle comme le reste.
  // Appliquee par le Core 1 : le DMA de l'affichage n'est pas a nous ici.
  int16_t br = doc["br"] | -1;
  out.br = (br >= 0 && br <= 255) ? br : -1;

  Flight f;
  f.ok = doc["ok"] | false;
  if (f.ok) {
    upperCopy(f.callsign, sizeof(f.callsign), doc["cs"] | "");
    upperCopy(f.airline, sizeof(f.airline), doc["al"] | "");
    upperCopy(f.icao, sizeof(f.icao), doc["ic"] | "");
    upperCopy(f.from, sizeof(f.from), doc["fr"] | "");
    upperCopy(f.to, sizeof(f.to), doc["to"] | "");
    upperCopy(f.city, sizeof(f.city), doc["ct"] | "");
    upperCopy(f.avion, sizeof(f.avion), doc["av"] | "");
    upperCopy(f.level, sizeof(f.level), doc["lv"] | "");
    f.km = doc["km"] | -1.0f;
    buildTicker(f);
  }
  out.flight = f;
  return true;
}


#endif  // PASSERELLE_H
