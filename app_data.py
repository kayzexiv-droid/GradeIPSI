import os

import math

import re


CURRICULUM_DATA = {
    "Année 1 (IPSI 1)": {
        "blocks": [
            {
                "name": "Fondamentaux pour l'ingénieur",
                "ects": 8,
                "modules": [
                    {"name": "Algorithmique", "weight": 25},
                    {"name": "Signaux", "weight": 25},
                    {"name": "Probabilités et Statistiques", "weight": 25},
                    {"name": "Traitement numérique des données", "weight": 25}
                ]
            },
            {
                "name": "Image",
                "ects": 8,
                "modules": [
                    {"name": "Analyse d'images", "weight": 37},
                    {"name": "DLC", "weight": 38},
                    {"name": "Projet images", "weight": 25}   
                ]
            },
            {
                "name": "Optique",
                "ects": 6,
                "modules": [
                    {"name": "Ondes électromagnétiques", "weight": 12},
                    {"name": "Optique géométrique", "weight": 33},
                    {"name": "Optique ondulatoire", "weight": 22},
                    {"name": "Optique expérimentale", "weight": 33}
                ]
            },
            {
                "name": "Smart Industries",
                "ects": 15,
                "modules": [
                    {"name": "Electronique", "weight": 30},
                    {"name": "Base de données", "weight": 20},
                    {"name": "Métrologie", "weight": 30},
                    {"name": "Ordinateurs", "weight": 20}
                ]
            },
            {
                "name": "Vision",
                "ects": 15,
                "modules": [
                    {"name": "Systèmes de vision", "weight": 35},
                    {"name": "Base des systèmes asservis", "weight": 23},
                    {"name": "Automatismes", "weight": 23},
                    {"name": "Photométrie", "weight": 19}
                ]
            },
            {
                "name": "Projet IPSI",
                "ects": 3,
                "modules": [
                    {"name": "Veille technologique", "weight": 16},
                    {"name": "Gestion de projet", "weight": 16},
                    {"name": "Projet P1", "weight": 52},
                    {"name": "Gestion DV", "weight": 16}
                ]
            },
            {
                "name": "Environnement Professionnel",
                "ects": 3,
                "modules": [
                    {"name": "Organisation des entreprises", "weight": 32},
                    {"name": "Communication", "weight": 68}
                ]
            }

        ],
        "alternance_ects": 23
    },
    "Année 2 (IPSI 2)": {
        "blocks": [
            {
                "name": "Bloc Optique",
                "ects": 8,
                "modules": [
                    {"name": "Intéraction Lumière/Matière", "weight": 33},
                    {"name": "Optique instrumentale", "weight": 11},
                    {"name": "Laser et applications", "weight": 23},
                    {"name": "Optique Expérimentale", "weight": 33}
                ]
            },
            {
                "name": "Bloc Image",
                "ects": 6,
                "modules": [
                    {"name": "Interface C#", "weight": 28},
                    {"name": "Traitement et analyse", "weight": 51},
                    {"name": "Machine Learning", "weight": 21}
                ]
            },
            {
                "name": "Bloc Vision",
                "ects": 7,
                "modules": [
                    {"name": "Chaîne de transmission élec", "weight": 19},
                    {"name": "Sources de Lumière", "weight": 19},
                    {"name": "Acquisition images", "weight": 26},
                    {"name": "Processus acquisition / traitement", "weight": 12},
                    {"name": "Vision humaine et vision artificielle", "weight": 12},
                    {"name": "Protocole caméra", "weight": 12}
                ]
            },
            {
                "name": "Bloc Fondamentaux",
                "ects": 6,
                "modules": [
                    {"name": "Programmation Orientée Objet", "weight": 28},
                    {"name": "Traitement du signal", "weight": 20},
                    {"name": "Projet C++", "weight": 28},
                    {"name": "Stats Industrielles", "weight": 24}
                ]
            },
            {
                "name": "Bloc Smart Industries",
                "ects": 7,
                "modules": [
                    {"name": "Réseaux industriels", "weight": 19},
                    {"name": "Capteurs", "weight": 16},
                    {"name": "Programmation évènement", "weight": 16},
                    {"name": "Transport de l'information", "weight": 21},
                    {"name": "Méthodes de développement", "weight": 9},
                    {"name": "Robotique", "weight": 19}
                ]
            },
            {
                "name": "Bloc Projet IPSI",
                "ects": 3,
                "modules": [
                    {"name": "Gestion de projets", "weight": 20},
                    {"name": "Conduite de réunions", "weight": 20},
                    {"name": "Projet P2", "weight": 60}
                ]
            }
        ],
        "alternance_ects": 23
    },
    "Année 3 (IPSI 3)": {
        "blocks": [
            {
                "name": "Systèmes Photoniques",
                "ects": 4,
                "modules": [
                    {"name": "Optique de Fourier", "weight": 31},
                    {"name": "Projet Optique", "weight": 69}
                ]
            },
            {
                "name": "Smart Système d'imagerie",
                "ects": 7,
                "modules": [
                    {"name": "Imagerie non conventionnelle", "weight": 13},
                    {"name": "Deep Learning", "weight": 27},
                    {"name": "Imagerie 3D", "weight": 27},
                    {"name": "Applications Robotique", "weight": 20},
                    {"name": "Mouvements et suivi", "weight": 13}
                ]
            },
            {
                "name": "Projets Innovation",
                "ects": 4,
                "modules": [
                    {"name": "Recherche et innovation", "weight": 27},
                    {"name": "Gestion financière", "weight": 21},
                    {"name": "Projet Innovation : recette", "weight": 52}
                ]
            }
        ],
        "alternance_ects": 15
    }
}

SAVE_FILE = "notes_data.json"

MODULE_STATUSES = ("Pas commencé", "En cours", "Terminé")

APP_ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PyPrint.ico")

DEFAULT_SETTINGS = {
    "theme": "Sombre",
    "accent": "#3b82f6",
    "font_family": "Segoe UI",
    "font_size": 10,
    "ui_scale": 100,
    "view_mode": "Confortable",
    "dashboard_year": "Année 1 (IPSI 1)",
    # Seuils indicatifs, modifiables dans les paramètres. La décision du jury
    # et les règles propres à la promotion prévalent toujours.
    "validation_threshold": 10.0,
    "enforce_module_minimum": False,
    "module_minimum": 6.0,
    "toeic_target": 785,
}

def calculate_weighted_metrics(weighted_values, target=10.0, module_minimum=None):
    """Calcule des statistiques pondérées sans dépendance à l'interface Qt.

    weighted_values contient des paires (poids, note), une note absente étant None.
    Une moyenne complète n'est exposée que lorsque toutes les notes sont présentes.
    Le seuil par module est facultatif car il dépend du règlement de la promotion.
    """
    pairs = []
    for weight, value in weighted_values:
        weight = max(0.0, float(weight))
        grade = None
        if value is not None:
            try:
                candidate = float(value)
            except (TypeError, ValueError):
                candidate = None
            if candidate is not None and math.isfinite(candidate) and 0.0 <= candidate <= 20.0:
                grade = candidate
        pairs.append((weight, grade))

    total_weight = sum(weight for weight, _ in pairs)
    entered_weight = 0.0
    weighted_sum = 0.0
    entered_count = 0
    for weight, grade in pairs:
        if grade is None:
            continue
        weighted_sum += grade * weight
        entered_weight += weight
        entered_count += 1
    count = len(pairs)
    missing_count = max(0, count - entered_count)
    missing_weight = max(0.0, total_weight - entered_weight)
    provisional = weighted_sum / entered_weight if entered_weight > 0 else None
    all_complete = count > 0 and missing_count == 0
    complete = provisional if all_complete else None
    needed = None
    if missing_count > 0 and missing_weight > 0:
        needed = (float(target) * total_weight - weighted_sum) / missing_weight

    module_minimum_met = None
    if module_minimum is not None:
        module_minimum_met = all_complete and all(grade >= float(module_minimum) for _, grade in pairs)
    validation_pass = bool(complete is not None and complete >= float(target)
                           and module_minimum_met is not False)
    return {
        "total_weight": total_weight,
        "entered_weight": entered_weight,
        "weighted_sum": weighted_sum,
        "missing_weight": missing_weight,
        "entered_count": entered_count,
        "module_count": count,
        "missing_count": missing_count,
        "provisional_average": provisional,
        "complete_average": complete,
        "completion_pct": (entered_weight / total_weight * 100.0) if total_weight > 0 else 0.0,
        "target_needed": needed,
        "module_minimum_met": module_minimum_met,
        "validation_pass": validation_pass,
    }

def make_stylesheet(settings):
    """Construit le thème complet à partir des préférences utilisateur."""
    dark = settings.get("theme", "Sombre") == "Sombre"
    accent = settings.get("accent", "#3b82f6")
    font_family = settings.get("font_family", "Segoe UI").replace("'", "")
    font_size = int(settings.get("font_size", 10))
    ui_scale = max(0.7, min(1.5, float(settings.get("ui_scale", 100)) / 100.0))
    if dark:
        bg, surface, surface2 = "#0b1120", "#172338", "#202f46"
        border, text, muted, field = "#314158", "#f1f5f9", "#a8b6ca", "#0d1728"
        hover = "#293b56"
    else:
        bg, surface, surface2 = "#f1f5f9", "#ffffff", "#e7edf5"
        border, text, muted, field = "#cbd5e1", "#0f172a", "#475569", "#ffffff"
        hover = "#e2e8f0"
    stylesheet = f"""
        QMainWindow, QDialog {{ background-color: {bg}; }}
        QWidget {{ color: {text}; font-family: '{font_family}'; font-size: {font_size}px; }}
        QToolBar {{ background: {surface}; border: none; border-bottom: 1px solid {border}; spacing: 5px; padding: 4px; }}
        QToolBar QToolButton {{ background: {surface2}; border: 1px solid {border}; border-radius: 6px; padding: 4px 7px; font-weight: 600; }}
        QToolBar QToolButton:hover {{ background: {hover}; border-color: {accent}; }}
        QToolBar::separator {{ background: {border}; width: 1px; margin: 4px 5px; }}
        QMenuBar {{ background: {surface}; color: {text}; border-bottom: 1px solid {border}; }}
        QMenuBar::item {{ padding: 5px 9px; border-radius: 5px; }}
        QMenuBar::item:selected, QMenu::item:selected {{ background: {accent}; color: white; }}
        QMenu {{ background: {surface}; color: {text}; border: 1px solid {border}; padding: 5px; }}
        QMenu::item {{ padding: 7px 24px; border-radius: 4px; }}
        QStatusBar {{ background: {surface}; color: {muted}; border-top: 1px solid {border}; }}
        QTabWidget::pane {{ border: 1px solid {border}; background: {bg}; border-radius: 9px; top: -1px; }}
        QTabBar::tab {{ background: {surface2}; color: {muted}; padding: 8px 13px; margin-right: 3px; border-top-left-radius: 7px; border-top-right-radius: 7px; font-weight: 600; }}
        QTabBar::tab:selected {{ background: {accent}; color: white; }}
        QTabBar::tab:hover:!selected {{ background: {hover}; color: {text}; }}
        QFrame#Card, QFrame.Card {{ background: {surface}; border: 1px solid {border}; border-radius: 12px; }}
        QFrame#KpiTile {{ background: {surface}; border: 1px solid {border}; border-radius: 12px; }}
        QLabel.BlockHeader {{ font-size: {font_size + 2}px; font-weight: 700; }}
        QLabel.Muted {{ color: {muted}; }}
        QLineEdit {{ background: {field}; border: 1px solid {border}; border-radius: 7px; color: {text}; padding: 7px 9px; selection-background-color: {accent}; }}
        QLineEdit:focus {{ border: 2px solid {accent}; }}
        QComboBox {{ background: {surface2}; border: 1px solid {border}; border-radius: 7px; padding: 7px 9px; min-width: 120px; }}
        QComboBox QAbstractItemView {{ background: {surface}; selection-background-color: {accent}; }}
        QPushButton {{ background: {surface2}; border: 1px solid {border}; border-radius: 7px; padding: 8px 13px; }}
        QPushButton:hover {{ border-color: {accent}; background: {hover}; }}
        QToolButton#BlockToggle {{ background: transparent; border: 1px solid {border}; border-radius: 6px; padding: 5px 8px; }}
        QFrame#Separator {{ background: {border}; max-height: 1px; }}
        QScrollArea {{ border: none; background: transparent; }}
        QProgressBar {{ border: none; background: {surface2}; border-radius: 5px; height: 9px; text-align: center; }}
        QProgressBar::chunk {{ background: {accent}; border-radius: 5px; }}
        QSpinBox {{ background: {field}; border: 1px solid {border}; border-radius: 6px; padding: 5px; }}
    """
    return re.sub(
        r"(\d+(?:\.\d+)?)px",
        lambda match: f"{max(1, round(float(match.group(1)) * ui_scale))}px",
        stylesheet,
    )
