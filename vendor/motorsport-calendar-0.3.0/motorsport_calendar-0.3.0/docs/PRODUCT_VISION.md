# PRODUCT_VISION.md

## Pourquoi Motorsport Calendar existe

Le calendrier d'un seul championnat automobile représente facilement 200 à 300 sessions par an —
essais libres, qualifications, sprints, courses — réparties sur des dizaines de fuseaux horaires.

Aucun service grand public ne les agrège en un seul endroit, avec les horaires justes,
dans le fuseau de l'utilisateur.

Le résultat : les passionnés jonglent entre une demi-douzaine d'applications fragmentées,
manquent des sessions faute de rappels, ou s'appuient sur des calendriers maintenus manuellement
et souvent en retard.

Motorsport Calendar résout ce problème en générant un fichier `.ics` standard que l'utilisateur
importe une seule fois dans l'application de son choix — Google Calendar, Apple Calendar,
Outlook, ou n'importe quel client iCalendar — et qui se met à jour à sa demande.

---

## Pour qui

**L'utilisateur cible** est un passionné de sport automobile. Pas un développeur.

Il suit plusieurs championnats, vit peut-être dans un fuseau horaire différent de celui des
courses, et veut des rappels fiables sans effort de maintenance hebdomadaire.

Il ne doit pas connaître le format ICS, les APIs OpenF1 ou F1Calendar, ni les commandes terminal.
L'application desktop est sa porte d'entrée principale. La CLI existe pour les utilisateurs
avancés qui veulent automatiser la génération.

---

## Philosophie

**Un seul fichier. Tous les championnats.**
Une génération → un fichier `.ics` → un abonnement calendrier.
Pas d'application séparée par championnat.

**Fidèle à la réalité.**
Les horaires viennent de sources officielles ou de datasets vérifiés.
Un événement incorrect est pire qu'un événement absent.

**Aucune dépendance cloud.**
L'outil fonctionne entièrement en local. Pas de compte, pas de serveur,
pas d'abonnement. Les données restent sur la machine de l'utilisateur.

**L'utilisateur garde le contrôle.**
Il choisit ses championnats, son fichier de sortie et sa fréquence de mise à jour.
Aucun comportement automatique en arrière-plan.

---

## Ce que Motorsport Calendar ne fera pas

- **Pas de serveur web ni d'API REST.** L'outil est un générateur local, pas un service hébergé.
- **Pas de notification cloud/push distante.** Les rappels VALARM du fichier ICS restent le
  mécanisme principal. L'application desktop dispose depuis les Sprints 46/56 d'un moteur de
  notification interne (`NotificationService`, indépendant de Flet) capable d'alerter
  l'utilisateur pendant qu'il a l'app ouverte ; aucun service tiers, aucun serveur, aucune
  donnée envoyée hors de la machine. Le relais vers une vraie notification système OS reste un
  no-op volontaire (`NullSystemNotifier`) tant qu'aucune solution native propre n'existe dans
  Flet — voir `docs/DECISIONS.md` (Sprint 56).
- **Pas de données de résultats, classements ou statistiques.** La portée est : *quand et où
  est la prochaine session*, pas *qui a gagné*.
- **Pas de gestion de compte ou de profil en ligne.** Aucune donnée personnelle n'est collectée
  ni transmise.
- **Motorsport au sens large, pas uniquement l'automobile.** Le périmètre couvre les
  monoplaces FIA (F1, F2, F3, F1 Academy, Formula E), l'endurance ACO (WEC, ELMS, Michelin
  Le Mans Cup), le GT (GT World Challenge Europe/America/Asia, IGTC) et la moto (MotoGP,
  Moto2, Moto3 — WorldSBK enregistré mais sans source de données fonctionnelle, voir
  `docs/DATA_SOURCES.md`). Toujours pas de sports hors motorsport (football, etc.).
- **Pas d'interface mobile native.** La GUI est desktop (Windows, macOS, Linux via Flet).
  Le fichier ICS généré est lui-même compatible mobile via l'application calendrier du téléphone.
- **Pas de mise à jour automatique des calendriers.** L'utilisateur régénère quand il le souhaite,
  avec `--refresh` si nécessaire. L'abonnement calendrier distant (webcal://) est une
  fonctionnalité future, pas un engagement.
