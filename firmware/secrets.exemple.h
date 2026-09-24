// secrets.exemple.h - modele de firmware/secrets.h
//
// Copier ce fichier en firmware/secrets.h et y mettre les vraies valeurs.
// secrets.h est dans .gitignore : le mot de passe Wi-Fi et l'adresse du
// domicile ne doivent jamais etre versionnes, pas plus que config.json.
//
// Sans secrets.h, le croquis compile avec ce modele et le signale a la
// compilation : pratique pour la verification, inutile sur le mur.

#ifndef SECRETS_H
#define SECRETS_H

static const char *WIFI_SSID = "TON_RESEAU";
static const char *WIFI_PASS = "TON_MOT_DE_PASSE";

// Nom mDNS du PC qui fait tourner server.py, SANS ".local" : c'est en
// general son nom d'hote (Windows 10+, macOS et Linux avec Avahi le
// publient d'eux-memes). Chaine vide pour se passer du mDNS.
static const char *GATEWAY_HOST = "mon-pc";

// Adresse de repli, quand le nom ne repond pas. Reserver l'adresse du PC
// dans la box la garde stable.
static const char *GATEWAY_IP = "192.168.1.20";

// Port de server.py, http_port dans config.json.
static const uint16_t GATEWAY_PORT = 8080;

#endif  // SECRETS_H
