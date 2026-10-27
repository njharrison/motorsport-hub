# DATA_SOURCES.md

> Étude des sources de données disponibles pour chaque championnat motorsport.
> Dernière mise à jour : 2026-07-14 — table "Vue d'ensemble" resynchronisée avec le
> détail par championnat (WEC passée "stub" → "Implémentée" à tort non répercuté
> depuis le Sprint 48). Le détail par championnat plus bas était déjà à jour.

---

## Méthodologie

Pour chaque championnat, on évalue :

| Critère | Description |
|---|---|
| **API** | Endpoint HTTP documenté retournant des données structurées |
| **ICS** | Flux iCalendar prêt à l'emploi (abonnement ou téléchargement) |
| **JSON** | Données brutes disponibles en JSON (API ou réponse réseau) |
| **HTML** | Seule option : scraping de page web |
| **Auth** | Clé API, compte, ou autre authentification requise |
| **Stabilité** | Risque de rupture de la source (changement de structure, arrêt) |
| **Fréquence** | Rythme de mise à jour des données calendrier |
| **Licence** | Conditions d'utilisation des données |

---

## Vue d'ensemble rapide

> Mise à jour Sprint 35 pour refléter les sources réellement implémentées (certaines
> diffèrent des recommandations initiales ci-dessous, remplacées par de meilleures
> options découvertes en cours de projet — conservées telles quelles par honnêteté
> historique dans le détail par championnat plus bas).

| Championnat | Meilleure source | Format | Auth | Complexité |
|---|---|---|---|---|
| Formula 1 (2023+) | OpenF1 | JSON REST | Non | ✅ Implémentée |
| Formula 1 (historique) | Jolpica | JSON REST | Non | 🟢 Facile |
| Formula 2 | Dataset `sportstimes/f1` (GitHub, MIT) | JSON | Non | ✅ Implémentée |
| Formula 3 | Dataset `sportstimes/f1` (GitHub, MIT) | JSON | Non | ✅ Implémentée |
| F1 Academy | Dataset `sportstimes/f1` (GitHub, MIT) | JSON | Non | ✅ Implémentée |
| Formula E | Dataset `sportstimes/f1` (GitHub, MIT) | JSON | Non | ✅ Implémentée |
| WEC | fiawec.com (JSON-LD, même CMS ACO que ELMS/MLMC) | JSON-LD | Non | ✅ Implémentée |
| ELMS | europeanlemansseries.com (JSON-LD schema.org) | JSON-LD | Non | ✅ Implémentée |
| Michelin Le Mans Cup | lemanscup.com (JSON-LD schema.org) | JSON-LD | Non | ✅ Implémentée |
| Road to Le Mans | lemanscup.com (round MLMC, pas de championship_id séparé) | JSON-LD | Non | ✅ Implémentée |
| Porsche Supercup | Probablement dataset `sportstimes/f1` — non vérifié | JSON (à confirmer) | Non | 🟢 Facile si confirmé |
| IMSA WeatherTech SportsCar Championship | Aucune trouvée (imsa.com bloqué Cloudflare, Al Kamel = résultats post-course, Wikipedia = pas d'horaires) | — | — | 🔴 Aucune — stub |
| GT World Challenge Europe | gt-world-challenge-europe.com (tableau HTML par jour) | HTML | Non | ✅ Implémentée |
| GT World Challenge America | gt-world-challenge-america.com (tableau HTML par jour) | HTML | Non | ✅ Implémentée |
| GT World Challenge Asia | gt-world-challenge-asia.com (tableau HTML par jour) | HTML | Non | ✅ Implémentée |
| Intercontinental GT Challenge (IGTC) | intercontinentalgtchallenge.com (tableau HTML par jour) | HTML | Non | ✅ Implémentée |
| MotoGP | api.pulselive.motogp.com (API REST officielle Dorna) | JSON REST | Non | ✅ Implémentée |
| Moto2 | api.pulselive.motogp.com (même API, filtrée par classe) | JSON REST | Non | ✅ Implémentée |
| Moto3 | api.pulselive.motogp.com (même API, filtrée par classe) | JSON REST | Non | ✅ Implémentée |
| World Superbike (WorldSBK) | Aucune trouvée (calendrier JS-only, hôte API candidat injoignable) | — | — | 🔴 Aucune — stub |

---

## Observation architecturale clé

**F2, F3, F1 Academy et Porsche Supercup sont des « support series » de la F1.**

Ils courent sur un sous-ensemble des circuits F1, durant le même week-end.
Cela permet une optimisation importante :

> Les données de **circuit** (ville, pays, fuseau IANA) sont déjà disponibles via
> le provider Formula 1. Seuls les **horaires de sessions** propres à chaque série
> doivent être récupérés depuis une source tierce.

| Série | Rounds F1 couverts (2026) | Sessions propres à scraper |
|---|---|---|
| F2 | 14 des 24 | Essais, Qualif, Course sprint, Course |
| F3 | 10 des 24 | Essais, Qualif, Course sprint, Course |
| F1 Academy | 7 des 24 | Essais, Qualif, Course 1, Course 2 |
| Porsche Supercup | 8 (Europe uniquement) | Essais, Qualif, Course |

---

## Détails par championnat

---

### 🏎 Formula 1

**Site officiel :** https://formula1.com | https://calendar.formula1.com

#### OpenF1 — Recommandé pour 2023+

| Critère | Détail |
|---|---|
| URL API | `https://api.openf1.org/v1/` |
| Endpoints clés | `/meetings`, `/sessions`, `/laps`, `/position`, `/pit`, `/car_data`, `/weather` |
| Format | JSON (défaut), CSV |
| Authentification | **Aucune** |
| Couverture | **2023 → présent** |
| Temps réel | Oui — 3 s de délai pendant les sessions actives |
| Rate limit | 3 req/s (gratuit), 6 req/s (sponsor) |
| Stabilité | **Élevée** — projet open source actif, GitHub public |
| Fréquence | Temps réel pendant les sessions ; données permanentes après |
| Licence | **CC BY-NC-SA 4.0** — usage non commercial uniquement |
| GitHub | https://github.com/br-g/openf1 |

**Remarque licence :** CC BY-NC-SA 4.0 interdit l'usage commercial. Pour un projet open source ou personnel, c'est acceptable. Pour une offre commerciale, contacter les mainteneurs.

#### Jolpica — Recommandé pour données historiques (1950+)

| Critère | Détail |
|---|---|
| URL API | `http://api.jolpi.ca/ergast/f1/` |
| Compatibilité | **100 % compatible Ergast** (migration sans réécriture) |
| Format | JSON, XML |
| Authentification | **Aucune** |
| Couverture | **1950 → présent** |
| Stabilité | **Élevée** — successeur communautaire officiel d'Ergast (arrêté fin 2024) |
| Fréquence | Mise à jour le **lundi après chaque week-end de course** |
| Licence | **Apache-2.0** — usage commercial autorisé |
| GitHub | https://github.com/jolpica/jolpica-f1 |

> **Note :** L'API Ergast originale (ergast.com) a été définitivement arrêtée fin 2024.
> Jolpica est le successeur officiel, maintenu par la communauté.

#### ICS officiel Formula 1

| Critère | Détail |
|---|---|
| Source | https://www.formula1.com/en/latest/article/download-or-sync-the-f1-race-calendar-to-your-device.7mpETY062kafAl55qVnemu |
| Format | Fichier `.ics` statique ou abonnement |
| Contenu | Dates des Grand Prix uniquement (pas les sessions séparées) |
| Fréquence | Mis à jour en début de saison, pas en temps réel |
| Utilité | Faible pour ce projet (sessions individuelles non couvertes) |

#### f1calendar.com — Source ICS communautaire

| Critère | Détail |
|---|---|
| Site | https://f1calendar.com |
| GitHub | https://github.com/sportstimes/f1 (MIT) |
| Séries couvertes | F1, **F2, F3, F1 Academy**, Formula E, IndyCar, MotoGP |
| Format | ICS par abonnement (URLs générées dynamiquement) |
| Granularité | Par session (FP1/FP2/FP3, Qualif, Sprint, Course) |
| Stabilité | **Élevée** — projet actif, open source, 420+ stars |
| Utilité | Référence utile pour les horaires F2/F3/F1A ; à consommer en ICS ou via le code source |

**Recommandation F1 :** OpenF1 pour 2023+ (déjà implémenté). Jolpica pour les saisons historiques (1950-2022).

---

### 🔵 Formula 2

**Site officiel :** https://www.fiaformula2.com

| Critère | Détail |
|---|---|
| API publique | ❌ Aucune documentée. `api.fia.com` existe mais nécessite authentification |
| Flux ICS | ❌ Non trouvé sur le site officiel |
| JSON | ❌ Pas d'endpoint public |
| HTML | ✅ `https://www.fiaformula2.com/Calendar` — calendrier HTML |
| Authentification | N/A |
| Stabilité (scraping) | 🟡 Moyenne — site FIA, peu de restructurations fréquentes |
| Fréquence | Mise à jour en début de saison + annonces ponctuelles |
| Licence | Scraping : zone grise (ToS FIA) — données non commerciales |

**Caractéristiques séries :**
- 14 rounds en 2026, tous en support F1
- 4 sessions par round : Essais libres, Qualifications, Course Sprint, Course principale
- Mêmes circuits que F1 → venues dérivables du provider F1

**Sources alternatives :**
- `f1calendar.com` couvre F2 avec horaires complets (open source, MIT)
- Wikipedia pour le calendrier de saison (données statiques)

**Recommandation F2 :** Scraping de `fiaformula2.com/Calendar` + fallback `f1calendar.com` (ICS open source). Réutiliser les métadonnées circuit du provider F1.

---

### 🟢 Formula 3

**Site officiel :** https://www.fiaformula3.com

| Critère | Détail |
|---|---|
| API publique | ❌ Aucune documentée |
| Flux ICS | ❌ Non trouvé |
| JSON | ❌ Pas d'endpoint public |
| HTML | ✅ `https://www.fiaformula3.com/Calendar` |
| Stabilité (scraping) | 🟡 Moyenne |
| Fréquence | Début de saison + ajustements |

**Caractéristiques :**
- 10 rounds en 2026, tous en support F1
- Structure identique à F2 (architecture de site identique — même CMS FIA)
- 3 sessions : Qualifications, Course 1, Course 2

**Recommandation F3 :** Même approche que F2. Le code de scraping sera quasi-identique (même CMS FIA entre F2 et F3).

---

### 🩷 F1 Academy

**Site officiel :** https://www.f1academy.com

| Critère | Détail |
|---|---|
| API publique | ❌ Aucune documentée |
| Flux ICS | ❌ Non trouvé |
| JSON | ❌ Pas d'endpoint public |
| HTML | ✅ `https://www.f1academy.com/Racing-Series/Calendar` |
| Stabilité (scraping) | 🟡 Moyenne |
| Fréquence | Début de saison |

**Caractéristiques :**
- 7 rounds en 2026, support F1 (sous-ensemble des rounds européens + quelques autres)
- 4 sessions par round : Essais, Qualifications, Course 1, Course 2
- Série créée en 2023, site relativement récent

**Recommandation F1A :** Scraping de `f1academy.com/Racing-Series/Calendar`. Même logique de réutilisation des venues F1.

---

### 🟣 FIA World Endurance Championship (WEC) ✅ Implémentée Sprint 48

**Site officiel :** https://www.fiawec.com

> ✅ Piste identifiée au Sprint 35 (jamais vérifiée sur une vraie manche jusqu'ici),
> confirmée en direct au Sprint 48 : fiawec.com tourne bien sur le même CMS ACO
> qu'ELMS/MLMC. Vérifié sur les 8 manches réelles de la saison 2026 (pas seulement un
> Prologue) — schéma JSON-LD identique confirmé.

| Critère | Détail |
|---|---|
| API publique | ❌ Aucune documentée publiquement |
| Flux ICS | ❌ Non trouvé (fiawec.com ne publie pas d'ICS accessible) |
| JSON | ✅ **Confirmé** — chaque page course (`/en/race/{slug}-{year}`) embarque un bloc `<script type="application/ld+json">` schema.org `SportsEvent`/`subEvent`, un objet par session, horodatage ISO 8601 exact (offset UTC inclus) — même schéma qu'ELMS/MLMC |
| HTML | ✅ Saison : `https://www.fiawec.com/en/season/{year}` — rendu côté serveur, mais **liste à la fois l'année demandée et la suivante** dans le même DOM (contrairement à ELMS/MLMC), filtré par le suffixe `-{year}` de chaque URL de course |
| Rendu JS | ❌ Non nécessaire — confirmé par fetch direct, calendrier et JSON-LD tous deux présents dans le HTML brut |
| Timing live | `https://fiawec.alkamelsystems.com/` (propriétaire, accès restreint, non utilisé) |
| Stabilité (scraping) | 🟢 Élevée — données structurées JSON-LD, même garanties qu'ELMS/MLMC |
| Fréquence | Mis à jour en septembre pour la saison suivante + ajustements |
| Licence | Scraping : zone grise (ToS fiawec.com) — cohérent avec ELMS/MLMC déjà en production |

**Caractéristiques (2026) :**
- 8 rounds : Imola, Spa-Francorchamps, Le Mans (24h), São Paulo, Austin (Lone Star Le
  Mans), Fuji, Qatar (1812km), Bahreïn — plus un Prologue pré-saison (Imola, exclu du
  calendrier des rounds)
- Sessions : FP1/FP2/FP3, Qualifying, Hyperpole (`SessionType.HYPERPOLE`, présent dans
  le modèle depuis les tout premiers sprints WEC), Course — Le Mans ajoute en plus
  Free Practice 4 (nuit) et Warm-up (matin course), absents de tout autre round
- **Durée de course non déductible de l'`endDate` JSON-LD** (contrairement à
  ELMS/MLMC) : toujours minuit du dernier jour annoncé, sans rapport avec la fin réelle
  — silencieusement plausible-mais-fausse pour Le Mans (~8h au lieu de 24h). Déduite à
  la place du nom de l'épreuve (motif "X Hours", + 2 exceptions nommées confirmées via
  fiawec.com/Wikipedia : "Lone Star Le Mans" = 6h, "Qatar 1812km" = 10h)
- Pays résolu depuis `location.address` du JSON-LD (`"{ville}, {code ISO alpha-3}"`),
  pas une table statique — voir `providers/wec/circuit_data.py`

**Fournisseur de timing :** Al Kamel Systems (`fiawec.alkamelsystems.com`). Données de
timing propriétaires, non accessibles publiquement sans accord commercial — non
utilisées, le calendrier public JSON-LD suffit entièrement.

**Implémentation réelle (Sprint 48) :** `providers/wec/sources/official.py::OfficialWecSource`,
sous-classe de `providers/aco_series/sports_event_base.py::AcoSportsEventSource` — voir
ADR-039. Conservée sous le nom historique `OfficialWecSource`/clé `"official"` (le défaut
`ProvidersConfig.wec.source`) plutôt que renommée en `"aco_scraper"` comme ELMS/MLMC.
Base partagée étendue de façon additive (nouveaux labels de session, exclusion du
prologue, deux points d'extension `_race_session_end`/`_race_url_belongs_to_season`) —
ELMS/MLMC strictement inchangés, vérifié par leur suite de tests existante.

---

### 🟠 European Le Mans Series (ELMS) ✅ Implémentée Sprint 35

**Site officiel :** https://www.europeanlemansseries.com

| Critère | Détail |
|---|---|
| API publique | ❌ Aucune documentée |
| Flux ICS | ❌ Non trouvé (site mentionne un bouton "Subscribe" mais redirige vers compte) |
| JSON | ✅ **Confirmé** — chaque page course (`/en/race/{slug}-{year}`) embarque un bloc `<script type="application/ld+json">` schema.org `SportsEvent`/`subEvent`, un objet par session, horodatage ISO 8601 exact (offset UTC inclus) |
| HTML | ✅ Saison : `https://www.europeanlemansseries.com/en/season/{year}` — **rendu côté serveur, pas de JS requis** (contrairement à l'hypothèse initiale) |
| Rendu JS | ❌ Non nécessaire — confirmé par fetch direct (`httpx`/`curl`), calendrier et JSON-LD tous deux présents dans le HTML brut |
| Timing live | `https://elms.alkamelsystems.com/` (propriétaire, non utilisé) |
| Stabilité (scraping) | 🟢 Élevée — données structurées JSON-LD, pas de parsing de mise en page fragile |
| Fréquence | Annonce calendrier en octobre pour l'année suivante ; `/en/season/{year}` ne fonctionne que pour l'année courante (404 sinon, pas d'archive) |

**Caractéristiques (2026) :**
- 6 rounds : Barcelone, Le Castellet, Imola, Spa, Silverstone, Portimão
- Sessions par round : FP1, FP2, Bronze Driver Collective Test, Qualifying (souvent
  découpée en plusieurs créneaux par classe LMGT3/LMP3/LMP2 PRO-AM/LMP2 — fusionnés en
  une seule Session par `AcoSportsEventSource`, voir ADR-026), Race (durée dérivée de
  l'`endDate` de l'événement top-level, généralement 4h)
- Organisé par l'ACO (Automobile Club de l'Ouest)

**Implémentation réelle :** `providers/elms/` — voir ADR-026. `AcoScraperSource` réutilise
entièrement `AcoSportsEventSource` (`providers/aco_series/`), partagée avec MLMC.

---

### 🔵 Michelin Le Mans Cup (MLMC) ✅ Implémentée Sprint 35

**Site officiel :** https://www.lemanscup.com

| Critère | Détail |
|---|---|
| API publique | ❌ Aucune documentée |
| Flux ICS | ❌ Non trouvé |
| JSON | ✅ **Confirmé** — même schéma JSON-LD `SportsEvent`/`subEvent` qu'ELMS (même CMS ACO) |
| HTML | ✅ Saison : `https://www.lemanscup.com/en/season/{year}` |
| Rendu JS | ⚠️ Partiellement confirmé — le **calendrier** est rendu côté serveur (pas de JS requis), seuls les tableaux de classement ("Standings") affichent "Loading..." et nécessitent du JS ; non bloquant pour ce projet (classements hors scope) |
| Timing live | `https://lemanscup.alkamelsystems.com/` (propriétaire, non utilisé) |
| Stabilité (scraping) | 🟢 Élevée — mêmes garanties qu'ELMS |
| Fréquence | Mise à jour annuelle ; même limitation qu'ELMS (pas d'archive par année) |

**Caractéristiques (2026) :**
- 6 rounds, co-localisés avec ELMS : Barcelone, Le Castellet, Imola, Spa, Silverstone,
  Portimão — table de circuits **partagée** avec ELMS (`aco_series/circuit_data.py`)
- Inclut **Road to Le Mans** (voir ci-dessous) — apparaît comme un round de plus sur la
  même page saison, pas une série séparée sur le site
- Organisé par l'ACO

**Implémentation réelle :** `providers/mlmc/` — voir ADR-026. Même base partagée qu'ELMS.

---

### 🟡 Road to Le Mans (RTLM) ✅ Implémentée Sprint 35 (comme round MLMC)

**Site officiel :** https://www.lemanscup.com (intégré au MLMC)

Confirmé exactement comme anticipé dans cette section avant investigation : RTLM apparaît
comme une entrée de plus sur la page saison MLMC (`/en/race/road-to-le-mans-{year}`),
avec le même schéma JSON-LD que les autres rounds. **Aucun `championship_id` séparé** —
elle est retournée par `MlmcSource.get_season()` comme un `Event` de plus, round 3/6 en
2026, fidèle à la présentation du site officiel.

**Caractéristique notable (2026) :** format changé — une seule course d'endurance
("Race 1") au lieu des 2 sprints traditionnels. Piège rencontré : la durée calculée
depuis l'`endDate` de l'événement JSON-LD donnait +61h (couvre toute la semaine des 24h
du Mans, pas seulement la course RTLM) — corrigé par un plafond de plausibilité, voir
ADR-026.

---

### 🟡 Porsche Mobil 1 Supercup (PMSC)

**Site officiel :** https://racing.porsche.com/mobil-1-supercup

| Critère | Détail |
|---|---|
| API publique | ❌ Aucune documentée |
| Flux ICS | ❌ Non trouvé |
| JSON | ❌ Pas d'endpoint public |
| HTML | ✅ `https://racing.porsche.com/mobil-1-supercup/race-calendar-{year}` |
| Rendu JS | ⚠️ Probable (site Porsche moderne) |
| Stabilité (scraping) | 🟡 Moyenne |
| Fréquence | Annonce calendrier en fin d'année précédente |

**Caractéristiques :**
- 8 rounds en 2026, tous en support **F1 Europe** (Monaco, Barcelone, Autriche, Belgique, Hongrie, Pays-Bas ×2, Monza)
- 3 sessions par round : Essais Libres, Qualifications, Course
- Nouveau modèle 2026 : Porsche 911 Cup (992.2)

**Approche recommandée :** Les venues (circuit, ville, pays, fuseau IANA) sont identiques aux rounds F1 correspondants. Seuls les horaires de sessions sont spécifiques.

**Plan d'implémentation :**
1. Scraper `racing.porsche.com/mobil-1-supercup/race-calendar-{year}` pour la liste des rounds F1 concernés
2. Réutiliser les métadonnées circuit du provider F1
3. Compléter avec les horaires propres au Supercup

---

### 🔴 IMSA WeatherTech SportsCar Championship — 🛑 Aucune source viable trouvée (Sprint 36, ré-investigué Sprint 48)

**Site officiel :** https://www.imsa.com

> Investigation exhaustive au Sprint 36 (objectif : premier championnat entièrement hors
> écosystème ACO, pour valider que l'architecture Provider/Source généralise). Chaque
> piste ci-dessous a été vérifiée en direct (requêtes réelles, pas de supposition) — voir
> ADR-027 dans `docs/DECISIONS.md` pour le détail complet du raisonnement. **Ré-investigué
> en direct au Sprint 48** (brief : "rechercher la meilleure source disponible" plutôt que
> de recopier une conclusion vieille de plusieurs sprints) — même conclusion, blocage
> encore plus strict qu'au Sprint 36.

| Critère | Détail |
|---|---|
| API publique | ❌ Aucune documentée |
| Flux ICS | ❌ Non trouvé |
| JSON | ❌ Pas d'endpoint public accessible |
| HTML (imsa.com) | 🛑 **Bloqué au niveau infrastructure** — Cloudflare renvoie HTTP 403 sur toutes les routes testées, **y compris `/robots.txt` et `/sitemap.xml` eux-mêmes** (reconfirmé Sprint 48 — un blocage encore plus strict qu'au Sprint 36, où au moins ces deux fichiers auraient pu être exemptés d'une protection anti-bot standard) |
| Timing live (Al Kamel) | 🟡 `imsa.results.alkamelcloud.com` accessible (reconfirmé Sprint 48), mais **archive de résultats post-course uniquement** — les dossiers de session n'existent qu'après la session (vérifié en direct : seuls les dossiers de la manche en cours au moment du test étaient présents), aucune donnée prévisionnelle |
| Wikipedia (API MediaWiki) | 🟡 Tableau "Schedule" de la page "2026 IMSA SportsCar Championship" (reconfirmé Sprint 48 via l'API MediaWiki) : round, course, circuit, ville, **date seulement** ("January 24–25") — toujours sans heure de session, insuffisant pour construire un `Session` valide |
| Sportscar365 / 51gt3.com | 🟡 Horaires de session publiés, mais en **prose libre** dans des articles individuels, pas de données structurées ; 51gt3.com renvoie lui-même HTTP 403 |
| Stabilité | N/A — aucune source exploitable identifiée |
| Fréquence | N/A |

**Pourquoi aucune de ces pistes n'a été retenue :**
- **imsa.com** : contourner le blocage Cloudflare nécessiterait une automatisation de
  navigateur complète (Playwright), une dépendance bien plus lourde que tout ce qui existe
  dans le projet, et plus proche d'un contournement actif d'anti-bot que d'un scraping —
  non tenté.
- **Al Kamel (résultats)** : structurellement inadapté — c'est une archive, pas un
  calendrier. Aucune donnée n'existe avant que la session ait eu lieu.
- **Wikipedia** : la source la plus propre et la plus stable des quatre, mais son
  incomplétude (pas d'horaires de session) empêcherait de respecter la contrainte du
  modèle `Session` (début ET fin obligatoires) sans inventer des horaires — jugé
  inacceptable pour un calendrier destiné à être réellement utilisé.
- **Sportscar365/51gt3.com** : parser du texte en langage naturel sur ~11 rounds x
  plusieurs sessions par round serait fragile et non maintenable ; ne correspond pas à une
  "source stable et documentée".

**Décision :** `OfficialImsaSource.get_season()` reste un stub (`NotImplementedError`),
exactement le même traitement que `OfficialWecSource` avant son implémentation réelle
(Sprint 48). L'architecture Provider/Source complète est enregistrée et intégrée partout
(registry, wizard, "Ce week-end", agrégateur, catégories, noms lisibles) — voir ADR-027
et ADR-039.

**Prochaines pistes (non explorées) :** automatisation navigateur (Playwright), contact
direct IMSA/SRO pour un accès API partenaire, ou surveiller une éventuelle publication
future d'un flux structuré par IMSA.

---

### 🟢 GT World Challenge Europe / America / Asia + Intercontinental GT Challenge (IGTC) ✅ Implémentées Sprint 37

**Sites officiels :** https://www.gt-world-challenge-europe.com,
https://www.gt-world-challenge-america.com, https://www.gt-world-challenge-asia.com,
https://www.intercontinentalgtchallenge.com — les quatre championnats sont organisés par
**SRO Motorsports Group**.

> Investigation menée sur les quatre sites en parallèle (Sprint 37) : fetch direct du HTML
> réel (pas de résumé IA à cette étape), confirmant qu'ils tournent tous sur le même CMS —
> même schéma d'URL `/event/{id}/{slug}`, mêmes classes CSS. Voir ADR-028 dans
> `docs/DECISIONS.md` pour le détail complet.

| Critère | Détail |
|---|---|
| API publique | ❌ Aucune documentée pour aucune des quatre séries |
| Flux ICS | ❌ Non trouvé |
| JSON / JSON-LD | ❌ **Aucun** — contrairement à WEC/ELMS/MLMC (Sprint 35), aucune donnée structurée intermédiaire n'existe sur ces sites |
| HTML | ✅ `https://www.{site}/calendar` (liste des rounds) puis `https://www.{site}/event/{id}/{slug}` (horaires détaillés, un `<table class="timetable__table">` HTML par jour — colonnes Session / Local Time / GMT) |
| Authentification | N/A |
| Stabilité (scraping) | 🟢 Élevée — structure identique confirmée sur 4 domaines différents, HTML server-rendu (pas de JS requis) |
| Fréquence | Calendrier publié en fin d'année précédente ; tableaux d'horaires détaillés publiés progressivement, quelques semaines avant chaque round (certains rounds éloignés n'ont pas encore de tableau — voir Limites) |
| Licence | Scraping : zone grise (ToS SRO) |

**Caractéristiques :**
- GT World Challenge Europe : 10 rounds en 2026 (6 "Sprint Cup" à deux courses + rounds
  "Endurance Cup" dont CrowdStrike 24 Hours of Spa)
- GT World Challenge America : 7 rounds, format à course unique uniquement
- GT World Challenge Asia : 6 venues, chacune hébergeant un week-end "Sprint Cup" à deux
  courses (le site les étiquette "Round N & M" — non reproduit tel quel, voir ADR-028)
- IGTC : 5 rounds "crown jewel" d'endurance (Bathurst 12 Hour, Nürburgring 24h, 24 Hours of
  Spa, Suzuka 1000km, Indianapolis 8 Hour) — deux d'entre eux (Spa, Indianapolis) sont
  également calendarisés indépendamment par GT World Challenge Europe/America sous leurs
  propres identifiants d'événement ; aucune déduplication n'est effectuée (cohérent avec le
  reste du projet, voir ADR-028)
- Aucune heure de fin de session fournie par la source — durée inférée (voir ADR-028 pour
  le détail des règles de mapping/durée/fusion)

**Recommandation :** aucune évolution nécessaire — les quatre providers sont pleinement
implémentés sur `providers/sro_series/timetable_base.py::SroTimetableSource`. Piste future :
SRO organise aussi d'autres championnats GT régionaux (British GT, Italian GT…) probablement
sur le même CMS — à vérifier avant d'écrire quoi que ce soit (voir `docs/TODO.md`).

---

### 🟢 MotoGP / Moto2 / Moto3 ✅ Implémentées Sprint 38

**Site officiel :** https://www.motogp.com — organisées par **Dorna Sports**.

> Meilleure source trouvée depuis le début du projet : une véritable API REST officielle,
> non authentifiée, avec des données de session complètes (début ET fin réelles pour la
> quasi-totalité des sessions). Voir ADR-029 dans `docs/DECISIONS.md` pour le détail
> complet de l'investigation.

| Critère | Détail |
|---|---|
| API publique | ✅ `https://api.pulselive.motogp.com/motogp/v1/events?seasonYear={year}` — non documentée officiellement, mais réellement une API REST classique (endpoints découverts via les messages d'erreur explicites du serveur, ex. paramètre requis manquant) |
| Flux ICS | ❌ Non trouvé |
| JSON | ✅ Une seule requête par saison retourne tous les événements (tests, présentations média, rounds réels) ; chaque round de Grand Prix (`kind: "GP"`) embarque déjà le tableau `broadcasts` complet des trois classes, filtrable par `category.acronym` (`MGP`/`MT2`/`MT3`) |
| Authentification | **Aucune** |
| Couverture | 2021 → présent (années disponibles observées sur le dataset `sportstimes/f1/motogp`, non vérifié directement sur l'API pulselive elle-même) |
| Stabilité | 🟢 Élevée — API REST classique avec des messages d'erreur explicites, pas de rendu JS à contourner |
| Fréquence | Calendrier publié en fin d'année précédente ; horaires de sessions détaillés disponibles dès la publication, y compris pour le dernier round de la saison (vérifié en direct, Sprint 38) |
| Licence | Zone grise (pas de documentation publique de l'API, donc pas de conditions d'usage explicites) |

**Caractéristiques :**
- 22 rounds en 2026, chacun avec MotoGP + Moto2 + Moto3 au même circuit le même week-end
- MotoGP uniquement : format Sprint (depuis 2023) — Qualifying → Sprint samedi, puis Race
  dimanche ; `SessionType.SPRINT`/`SPRINT_QUALIFYING` réutilisés (mêmes valeurs que les
  week-ends Sprint F1)
- Moto2/Moto3 : format classique (Qualifying → Race), pas de Sprint
- Chaque classe court 3 séances Free Practice par week-end (`FP1`, une séance non
  numérotée "Practice", puis `FP2`) — assignées `FP1`/`FP2`/`FP3` par ordre chronologique,
  pas par libellé source (voir ADR-029)
- Fuseau horaire IANA directement exposé par la source (`time_zone`, ex.
  `"ASIA/BANGKOK"` → normalisé `"Asia/Bangkok"`) — aucune table de circuits à maintenir,
  contrairement à ACO (Sprint 35) et SRO (Sprint 37)

**Recommandation :** aucune évolution nécessaire — implémentation complète sur
`providers/motogp_series/pulselive_base.py::PulseliveGpSource`.

---

### 🔴 World Superbike (WorldSBK) — 🛑 Aucune source viable trouvée (Sprint 38, ré-investigué Sprint 48)

**Site officiel :** https://www.worldsbk.com — organisé par **Dorna Sports** (depuis 2022,
même groupe que MotoGP).

> Investigation menée au Sprint 38 (fetch direct des pages calendrier/résultats, recherche
> de l'hôte API équivalent à celui de MotoGP). Voir ADR-029 dans `docs/DECISIONS.md` pour
> le détail complet du raisonnement. **Ré-investigué en direct au Sprint 48** avec deux
> nouveaux hôtes de la famille Pulselive découverts — même conclusion.

| Critère | Détail |
|---|---|
| API publique | ❌ Aucune trouvée (voir ci-dessous) |
| Flux ICS | ❌ Non trouvé |
| JSON | ❌ Pas d'endpoint public accessible |
| HTML | 🛑 **Calendrier/planning entièrement rendu côté client** — aucune donnée exploitable dans le HTML brut (contrairement aux sites SRO GT, Sprint 37, qui étaient server-rendus) |
| Hôte API candidat | 🟡 `wsbk-api-origin.gplat-test.pulselive.com` (référencé dans le code source de la page, `window.SD_DOMAIN`) — **injoignable depuis l'extérieur** (timeout de connexion, reconfirmé Sprint 48), probablement un service interne non exposé publiquement |
| Hôte candidat (Sprint 48) | 🟡 `api.wsbk.pulselive.com` — **réel et joignable** (contrairement à l'hôte `-test` ci-dessus), mais renvoie le même 404 applicatif générique Spring-Boot-style sur toutes les routes devinées (`/wsbk/v1/events`, `/motogp/v1/events`, `/v1/events`) |
| Hôte candidat (Sprint 48) | 🟡 `wsbk.pulselive.com` — réel et joignable, mais s'avère être le CMS média du site (`/photo-resources/...`, `/wsbk/document/...`) doublé d'un simple miroir SPA (chaque route testée renvoie le même shell HTML de 4184 octets) — pas une API |
| Stabilité | N/A — aucune source exploitable identifiée |
| Fréquence | N/A |

**Pourquoi aucune de ces pistes n'a été retenue :**
- **Même plateforme que MotoGP ("Pulse Live"), mais tenant séparé** : confirmé via un
  fichier de traductions multi-tenant partagé
  (`translations.gplat-prod.pulselive.com/wsbk/en.js`, `accountId: 8`), mais l'API MotoGP
  elle-même ne couvre pas WorldSBK (ses `circuit.timing_ids` n'exposent jamais de business
  unit SBK) — une plateforme réellement distincte, pas un simple filtre à ajouter à
  l'API existante.
- **`wsbk-api-origin.gplat-test.pulselive.com`** : hôte le plus prometteur trouvé (nommé
  explicitement `SD_DOMAIN`, "Static/Sports Data Domain"), mais injoignable en pratique —
  et son nom `-test` suggère qu'il ne s'agit peut-être même pas de l'hôte de production.
  Une variante `-prod` a été devinée et testée au Sprint 48 (`wsbk-api-origin.gplat-prod.
  pulselive.com`) — également injoignable.
- **Endpoints devinés sur `api.pulselive.worldsbk.com`** (suivant la convention de
  nommage MotoGP : `/wsbk/v1/events`, `/sbk/v1/events`, `/superbike/v1/events`, etc.) :
  tous renvoient un vrai 404 applicatif du propre backend du serveur (pas une erreur de
  passerelle générique), confirmant l'hôte actif mais aucune route devinée correcte.
- **`api.wsbk.pulselive.com`/`wsbk.pulselive.com`** (Sprint 48) : découverts en cherchant
  toute référence `*.pulselive.com` dans le HTML de la page calendrier et le fichier de
  traductions — le premier est une API réelle mais aucune route devinée n'existe ; le
  second s'est avéré être l'hébergement CMS/média du site public lui-même, pas un backend
  d'événements. Sans accès à un navigateur exécutant le JavaScript de la page (les vrais
  appels XHR ne sont jamais visibles via un simple fetch HTTP), impossible de découvrir la
  route réelle sans deviner indéfiniment.

**Décision :** `OfficialWorldSbkSource.get_season()` reste un stub (`NotImplementedError`),
exactement le même traitement que `OfficialImsaSource` (WEC a été implémentée pour de bon
au Sprint 48 — voir sa propre section ci-dessus). L'architecture Provider/Source complète
est enregistrée et intégrée partout (registry, wizard, "Ce week-end", agrégateur,
catégories, noms lisibles) — voir ADR-029 et ADR-039.

**Prochaines pistes (non explorées) :** automatisation navigateur (Playwright) pour
intercepter les vrais appels XHR de la page calendrier, contact direct Dorna/WorldSBK pour
un accès API partenaire, ou surveiller une éventuelle publication future d'un hôte API
public équivalent à `api.pulselive.motogp.com`.

---

## Sources tierces polyvalentes

### Rushsync (rushsync.com)

Service tiers qui agrège les calendriers motorsport et expose des abonnements ICS pour WEC, ELMS, Porsche Supercup et autres. Pratique pour valider les données scrapées. Non recommandé comme source primaire (service commercial, pas de garantie de pérennité).

### Motorsport.com / Autosport.com

Proposent des calendriers pour la plupart des championnats. HTML-only pour la plupart des séries. Utiles comme référence de vérification, pas comme source primaire.

### f1calendar.com (sportstimes/f1)

- **GitHub :** https://github.com/sportstimes/f1
- **Licence :** MIT
- **Couverture :** F1, F2, F3, F1 Academy, Formula E, IndyCar, MotoGP
- **Utilisation recommandée :** Source de référence pour valider les horaires F2/F3/F1A. Le code source expose les données en JSON dans le dossier `_db/` du dépôt — extractibles sans scraping.
- **Mise à jour :** Manuelle par les mainteneurs après chaque annonce officielle

---

## Recommandations d'implémentation

> ⚠️ Section conservée telle quelle depuis l'étude initiale (planning pré-implémentation)
> — plusieurs des sources listées ci-dessous ont été **remplacées** en cours de projet
> par de meilleures options découvertes par investigation (voir le détail par
> championnat plus haut, et ADR-026 pour ELMS/MLMC). Conservée par honnêteté historique
> plutôt que réécrite ; le tableau ci-dessous reflète l'état **réel** au Sprint 38.

### Tableau de décision

| Championnat | Source | Endpoint | Complexité | Statut |
|---|---|---|---|---|
| **Formula 1** (2023+) | OpenF1 | `https://api.openf1.org/v1/` | ✅ Fait | — |
| **Formula 1** (1950-2022) | Jolpica | `http://api.jolpi.ca/ergast/f1/` | 🟢 Facile | À faire |
| **Formula 2** | Dataset `sportstimes/f1` (pas fiaformula2.com — remplacé) | `_db/f2/{year}.json` | ✅ Fait | — |
| **Formula 3** | Dataset `sportstimes/f1` (pas fiaformula3.com — remplacé) | `_db/f3/{year}.json` | ✅ Fait | — |
| **F1 Academy** | Dataset `sportstimes/f1` (pas f1academy.com — remplacé) | `_db/f1-academy/{year}.json` | ✅ Fait | — |
| **Formula E** | Dataset `sportstimes/f1` | `_db/fe/{year}.json` | ✅ Fait — Sprint 34 | — |
| **ELMS** | JSON-LD europeanlemansseries.com (pas de scraping HTML classique — remplacé) | `/en/race/{slug}-{year}` | ✅ Fait — Sprint 35 | — |
| **MLMC + RTLM** | JSON-LD lemanscup.com (pas Playwright — remplacé, pas de JS requis pour le calendrier) | `/en/race/{slug}-{year}` | ✅ Fait — Sprint 35 | — |
| **WEC** | fiawec.com — JSON-LD probable (même CMS ACO), non confirmé sur une vraie manche | `/en/race/{slug}-{year}` | 🟡 Moyen | À faire — piste Sprint 35 |
| **Porsche Supercup** | Probablement dataset `sportstimes/f1` — non vérifié | À confirmer | 🟢 Facile si confirmé | À faire |
| **IMSA** | Aucune trouvée — imsa.com bloqué (Cloudflare), Al Kamel = résultats post-course, Wikipedia = pas d'horaires, Sportscar365 = prose | — | 🔴 Aucune | Stub — investigation exhaustive Sprint 36 |
| **GT World Challenge Europe/America/Asia** | HTML — tableau `timetable__table` par jour (même CMS SRO) | `/event/{id}/{slug}` | 🟢 Facile une fois le CMS identifié | ✅ Fait — Sprint 37 |
| **IGTC** | HTML — tableau `timetable__table` par jour (même CMS SRO) | `/event/{id}/{slug}` | 🟢 Facile une fois le CMS identifié | ✅ Fait — Sprint 37 |
| **MotoGP/Moto2/Moto3** | API REST officielle Dorna (non documentée mais réelle) | `api.pulselive.motogp.com/motogp/v1/events` | ✅ Fait — Sprint 38 | — |
| **WorldSBK** | Aucune trouvée — calendrier JS-only, hôte API candidat injoignable | — | 🔴 Aucune | Stub — investigation Sprint 38 |

### Ordre d'implémentation recommandé

**P1 — Court terme (v0.2.0)**
1. `ErgastSource` (Jolpica) pour les saisons F1 historiques — API REST propre, Apache-2.0
2. `OfficialWecSource` — scraping HTML de fiawec.com + investigation XHR

**P2 — Moyen terme (v0.3.0)**
3. `ELMSSource` — investigation XHR europeanlemansseries.com en priorité
4. `Formula2Source` — scraping fiaformula2.com + venues réutilisées du provider F1
5. `Formula3Source` — même code que F2 (site identique)

**P3 — Long terme (v0.4.0 ou ultérieur)**
6. `PorscheSupercupSource` — scraping racing.porsche.com + dérivation venues F1
7. `F1AcademySource` — scraping f1academy.com
8. `MichelinLeMansSource` — fusionné MLMC + RTLM, approche Playwright si XHR indisponible

### Principe directeur

> Avant d'implémenter un scraper HTML, **ouvrir les DevTools du navigateur** et inspecter les requêtes réseau (onglet Network → XHR/Fetch) sur la page du calendrier.
> De nombreux sites modernes chargent leurs données via un endpoint JSON interne non documenté mais accessible.
> Un endpoint XHR est **10× plus stable** qu'un scraper HTML.

---

## Licences et usage des données

| Source | Licence | Usage commercial | Attribution |
|---|---|---|---|
| OpenF1 | CC BY-NC-SA 4.0 | ❌ Interdit | Requise |
| Jolpica | Apache-2.0 | ✅ Autorisé | Requise |
| f1calendar.com code | MIT | ✅ Autorisé | Requise |
| Sites HTML scrapés | ToS non commerciale | ⚠️ Zone grise | Bonne pratique |

**Recommandation :** Pour un usage open source / non commercial, toutes ces sources sont acceptables. Pour une offre commerciale, utiliser Jolpica (Apache-2.0) et s'assurer d'un accord ou d'une politique claire pour les données scrapées.
