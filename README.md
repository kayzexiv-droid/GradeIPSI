# GradeIPSI

GradeIPSI est une application de bureau destinée au suivi de la scolarité du
cursus **Image Photonique & Smart Industries (IPSI)**. Elle permet de saisir
les notes et l'avancement des modules, de suivre des moyennes et des ECTS
estimés, puis de tester des objectifs sans modifier les résultats enregistrés.

L'interface est en français et s'appuie sur Python et PySide6 (Qt).

## Sommaire

- [Fonctionnalités](#fonctionnalités)
- [Cursus intégré](#cursus-intégré)
- [Calculs et interprétation](#calculs-et-interprétation)
- [Installation et lancement](#installation-et-lancement)
- [Utilisation](#utilisation)
- [Préférences](#préférences)
- [Sauvegarde et export](#sauvegarde-et-export)
- [Raccourcis clavier](#raccourcis-clavier)
- [Développement et création de l'exécutable](#développement-et-création-de-lexécutable)
- [Structure du projet](#structure-du-projet)
- [Limites et précautions](#limites-et-précautions)

## Fonctionnalités

- Saisie des notes sur 20, du statut et de la note d'alternance pour chacune
  des trois années IPSI.
- Saisie du score TOEIC, avec un objectif configurable (785 points par défaut).
- Calcul des moyennes par bloc et des synthèses annuelles pondérées par les
  poids des modules et les ECTS configurés.
- Indication de la couverture des notes, des blocs complets, des ECTS évalués
  et d'une estimation des ECTS acquis.
- Estimation de la note moyenne à obtenir sur les modules restants pour viser
  un objectif de bloc.
- Tableau de bord annuel avec indicateurs, graphiques de progression et liste
  des modules triable par statut ou par note.
- Recherche de modules et filtres par statut ou par absence de note.
- Simulateur de notes hypothétiques pour étudier l'effet d'un scénario sur un
  bloc et sur la projection annuelle. Le scénario ne remplace jamais les notes
  réelles.
- Enregistrement automatique local, sauvegarde JSON manuelle, export CSV et
  historique Annuler/Rétablir.
- Thème sombre ou clair, couleur d'accentuation, police, échelle de l'interface
  et résolution de la fenêtre, ainsi que plusieurs modes d'affichage.
- Vérification de la disponibilité d'une nouvelle version publiée sur GitHub
  au démarrage. Cette vérification ne met pas l'application à jour
  automatiquement.
- Accès au dépôt GitHub de l'application depuis la toolbar avec « À propos ».

## Cursus intégré

La maquette fournie dans l'application est répartie ainsi :

| Année | Blocs |
| --- | --- |
| Année 1 (IPSI 1) | Fondamentaux pour l'ingénieur, Image, Optique, Smart Industries, Vision, Projet IPSI et Environnement Professionnel |
| Année 2 (IPSI 2) | Bloc Optique, Bloc Image, Bloc Vision, Bloc Fondamentaux, Bloc Smart Industries et Bloc Projet IPSI |
| Année 3 (IPSI 3) | Systèmes Photoniques, Smart Système d'imagerie et Projets Innovation |

Chaque bloc contient les modules, leurs poids respectifs et une valeur d'ECTS.
L'alternance dispose également d'une valeur d'ECTS par année. Ces données sont
définies dans `app_data.py` et servent aux calculs de l'application.

## Calculs et interprétation

- Une note de module est comprise entre **0 et 20**. Les poids des modules
  déterminent la moyenne pondérée de leur bloc.
- La **moyenne provisoire d'un bloc** utilise les notes déjà saisies. La
  **moyenne complète** n'est affichée que lorsque toutes les notes du bloc sont
  renseignées.
- La **moyenne provisoire annuelle** estime la contribution des blocs au
  prorata de leur couverture de notes et de leurs ECTS. La moyenne des
  **éléments complets** ne prend en compte que les blocs entièrement notés et
  l'alternance si sa note est saisie.
- Les ECTS évalués correspondent aux blocs complets et à l'alternance notée.
  Les ECTS acquis affichés sont une estimation fondée sur le seuil configuré.
- Par défaut, le seuil indicatif est de **10/20**. Une règle facultative permet
  aussi d'exiger une note minimale dans chaque module d'un bloc. Elle est
  désactivée par défaut et ne doit être activée que si le règlement de la
  formation applicable le prévoit.
- Les notes à viser sont des projections mathématiques : elles supposent une
  même moyenne sur les modules non notés. Le simulateur annuel exclut les
  autres blocs incomplets de sa projection.

Ces indicateurs sont des aides au suivi personnel. Ils ne constituent ni une
validation académique, ni un relevé officiel, ni une décision de jury.

> **À vérifier :** la maquette actuellement incluse totalise 81 ECTS en année 1,
> 60 ECTS en année 2 et 30 ECTS en année 3, alternance comprise. L'application
> signale les années dont le total configuré diffère de 60 ECTS, mais ne corrige
> pas les valeurs. Vérifiez les blocs et les ECTS avec la maquette officielle
> correspondant à votre promotion avant d'interpréter les résultats.

## Installation et lancement

### Prérequis

- Windows est la plateforme visée par les scripts de packaging fournis.
- Python 3 et `pip`, avec une version prise en charge par PySide6.

Le dépôt ne fournit pas actuellement de fichier `requirements.txt`. PySide6
est la dépendance nécessaire pour lancer l'application depuis les sources.

### Depuis PowerShell

À la racine du projet :

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install PySide6
python main.py
```

Si l'activation de l'environnement virtuel est bloquée, appelez directement
son interpréteur :

```powershell
.\.venv\Scripts\python.exe -m pip install PySide6
.\.venv\Scripts\python.exe main.py
```

## Utilisation

### Suivre une année

1. Choisissez l'année à l'aide du sélecteur en haut de la fenêtre. Elle est
   partagée entre le tableau de bord, l'onglet des modules et le simulateur.
2. Dans l'onglet **Modules**, développez un bloc et saisissez les notes
   disponibles. Les notes acceptées vont de 0 à 20.
3. Mettez à jour le statut de chaque module : **Pas commencé**, **En cours** ou
   **Terminé**. Le statut est indépendant de la saisie de la note.
4. Renseignez, si nécessaire, la note d'alternance sur 20 et le score TOEIC
   (de 0 à 990).
5. Consultez le **Dashboard** pour retrouver les moyennes, la complétude, les
   ECTS estimés, le graphique par bloc et le détail triable des modules.

La barre de recherche de l'onglet Modules filtre les noms de modules. Le menu
de filtre permet d'afficher tous les états, un état particulier ou les modules
sans note.

### Simuler un objectif

Dans l'onglet **Simulateur**, choisissez un bloc et modifiez les notes du
scénario. Les indicateurs présentent notamment la moyenne réelle provisoire,
la moyenne simulée, la moyenne nécessaire pour atteindre l'objectif du bloc
et une projection annuelle. Le bouton de réinitialisation recharge les notes
réelles dans le scénario. Les saisies de simulation restent séparées des notes
enregistrées.

### Réglages et édition

Le menu **Préférences** permet de configurer l'apparence, les seuils indicatifs,
la règle facultative de note minimale par module et l'objectif TOEIC.

La résolution de fenêtre se règle dans **Préférences > Paramètres**. Le mode
**Automatique** conserve le dimensionnement adapté à l'écran; les résolutions
prédéfinies sont limitées à l'espace disponible. Le réglage d'échelle de
l'interface reste indépendant.

Le menu **Affichage** propose les modes Confortable, Grille (2 colonnes) et
Résumé compact, ainsi que le plein écran. Les menus **Fichier** et **Édition**
permettent respectivement de sauvegarder, exporter, effacer les notes et
d'annuler ou rétablir les modifications.

## Préférences

Valeurs initiales de l'application :

| Préférence | Valeur par défaut |
| --- | --- |
| Thème | Sombre |
| Police | Segoe UI |
| Taille du texte | 10 px |
| Échelle de l'interface | 100 % |
| Résolution de la fenêtre | Automatique |
| Mode d'affichage | Confortable |
| Seuil indicatif | 10/20 |
| Note minimale par module | Désactivée (valeur réglable : 6/20 par défaut) |
| Objectif TOEIC | 785 points |

Les seuils et objectifs peuvent être adaptés dans **Préférences > Paramètres**.
Ils ne modifient pas les notes saisies.

## Sauvegarde et export

- Les notes et les préférences sont enregistrées automatiquement dans
  `%APPDATA%\GradeIPSI\notes_data.json` (par exemple
  `C:\Users\<utilisateur>\AppData\Roaming\GradeIPSI\notes_data.json`). Le
  dossier est créé automatiquement. Le menu **Fichier > Enregistrer JSON**
  (ou `Ctrl+S`) force aussi une sauvegarde.
- `notes_data.json` est un fichier local lisible au format JSON. Pensez à en
  conserver une copie si vous souhaitez transférer ou archiver vos données.
- Si aucune sauvegarde AppData n'existe mais qu'un ancien `notes_data.json`
  est présent dans le dossier de lancement, l'application le charge puis en
  copie le contenu vers AppData. Le fichier d'origine n'est pas supprimé.
- **Fichier > Exporter CSV** (ou `Ctrl+E`) crée un fichier CSV en UTF-8 avec
  séparateur point-virgule. Il comprend les notes, états, poids, ECTS,
  complétudes, moyennes et diagnostics indicatifs.
- L'application propose un historique Annuler/Rétablir limité aux 100 derniers
  instantanés. Effacer toutes les notes peut être annulé avec `Ctrl+Z`.
- L'export CSV est une sortie de rapport ; il n'existe pas de fonction
  d'importation de CSV dans l'application.

## Raccourcis clavier

| Raccourci | Action |
| --- | --- |
| `Ctrl+S` | Enregistrer le fichier JSON |
| `Ctrl+E` | Exporter les données en CSV |
| `Ctrl+Z` | Annuler |
| `Ctrl+Y` | Rétablir |
| `Ctrl+F` | Placer le curseur dans la recherche de modules |
| `F11` | Activer ou quitter le plein écran |
| `Ctrl+Q` | Quitter l'application |
| `Entrée` dans une note | Passer au module suivant du bloc |

## Développement et création de l'exécutable

Pour lancer l'application pendant le développement, installez PySide6 dans
l'environnement Python puis exécutez `python main.py` depuis la racine du
projet.

La configuration PyInstaller est fournie dans `GradeIPSI.spec`. Pour créer la
version Windows depuis un environnement où PySide6 et PyInstaller sont
installés :

```powershell
python -m pip install PySide6 PyInstaller
python -m PyInstaller --noconfirm --clean GradeIPSI.spec
```

Le dossier produit est `dist\GradeIPSI`. Pour distribuer la version construite,
conservez le dossier complet et lancez `GradeIPSI.exe` à l'intérieur : ce n'est
pas un exécutable autonome à déplacer seul.

## Structure du projet

| Fichier | Rôle |
| --- | --- |
| `main.py` | Point d'entrée de l'application Qt |
| `app_window.py` | Fenêtre principale, menus, sauvegarde, export et historique |
| `app_data.py` | Maquette IPSI, paramètres par défaut, calculs et styles |
| `grade_widgets.py` | Saisie des notes, cartes de blocs et synthèses annuelles |
| `dashboard_widgets.py` | Tableau de bord annuel, graphiques et simulateur |
| `settings_dialog.py` | Dialogue des préférences |
| `update_checker.py` | Vérification des releases GitHub |
| `version.txt` | Version lue par le vérificateur de mises à jour |
| `GradeIPSI.spec` | Configuration de construction PyInstaller |

## Limites et précautions

- La maquette, les pondérations et les ECTS doivent être vérifiés pour chaque
  promotion. L'application les utilise tels qu'ils sont configurés et ne les
  synchronise pas avec un établissement.
- Une moyenne provisoire ou un ECTS acquis estimé ne vaut pas validation
  officielle. Le règlement des études et la décision du jury prévalent.
- Les notes et paramètres sont stockés localement. La vérification des mises à
  jour interroge GitHub, mais les notes ne sont pas envoyées par cette
  fonctionnalité.
- La vérification des releases nécessite un accès réseau ; son échec n'empêche
  pas l'utilisation de l'application.
