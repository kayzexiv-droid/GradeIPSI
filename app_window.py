import os

import json

import csv

from copy import deepcopy

from PySide6.QtCore import QTimer, QEvent, QUrl

from PySide6.QtGui import QAction, QActionGroup, QFont, QKeySequence, QIcon, QDesktopServices

from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QFrame, QMessageBox, QFileDialog, QComboBox, QDialog, QStatusBar

from app_data import APP_ICON_PATH, CURRICULUM_DATA, DEFAULT_SETTINGS, DISPLAY_RESOLUTIONS, SAVE_FILE, make_stylesheet

from dashboard_widgets import GradeSimulationWidget, YearRecapWidget

from grade_widgets import YearTabWidget

from settings_dialog import SettingsDialog
from update_checker import ReleaseChecker, load_current_version


PROJECT_URL = "https://github.com/kayzexiv-droid/GradeIPSI"


class GradeTrackerApp(QMainWindow):
    """Application principale de suivi des notes, exports, préférences et historique."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Suivi de scolarité ingénieur · IPSI")
        self.setWindowIcon(QIcon(APP_ICON_PATH))
        screen = QApplication.primaryScreen()
        if screen is None:
            self.resize(1320, 900)
        else:
            available = screen.availableGeometry()
            width = min(1320, int(available.width() * 0.96))
            height = min(900, int(available.height() * 0.94))
            self.setGeometry(
                available.x() + (available.width() - width) // 2,
                available.y() + (available.height() - height) // 2,
                width,
                height,
            )
        self.settings = deepcopy(DEFAULT_SETTINGS)
        self.year_tabs = {}
        self.view_mode_actions = {}
        self._restoring = False
        self._history = []
        self._history_index = -1
        self._history_timer = QTimer(self)
        self._history_timer.setSingleShot(True)
        self._history_timer.setInterval(350)
        self._history_timer.timeout.connect(self._capture_history)
        self.init_ui()
        self.load_data()
        self._reset_history_baseline()
        self.release_checker = ReleaseChecker(self)
        self.release_checker.release_available.connect(self._show_release_available)
        self.release_checker.up_to_date.connect(self._show_up_to_date)
        self.release_checker.check_failed.connect(self._show_release_check_error)
        QTimer.singleShot(0, self.release_checker.check)

    def _show_release_available(self, tag, name, url):
        message = QMessageBox(self)
        message.setWindowTitle("Mise à jour disponible")
        message.setIcon(QMessageBox.Icon.Information)
        message.setText(f"La version {tag} est disponible.")
        message.setInformativeText(name)
        open_release = message.addButton(
            "Voir la release", QMessageBox.ButtonRole.AcceptRole
        )
        message.addButton("Plus tard", QMessageBox.ButtonRole.RejectRole)
        message.exec()
        if message.clickedButton() == open_release and not QDesktopServices.openUrl(QUrl(url)):
            self.statusBar().showMessage(
                "Impossible d'ouvrir la page de la release.", 6000
            )

    def _show_up_to_date(self, version):
        self.statusBar().showMessage(f"L'application est à jour (v{version}).", 5000)

    def _show_release_check_error(self, error):
        self.statusBar().showMessage(error, 8000)

    def init_ui(self):
        self.setStyleSheet(make_stylesheet(self.settings))
        self._create_actions()
        self._create_menus()

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(12, 9, 12, 9)
        main_layout.setSpacing(9)

        header = QFrame()
        header.setObjectName("Card")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(14, 9, 14, 9)
        title_box = QVBoxLayout()
        title = QLabel("Image Photonique & Smart Industries · Suivi de notes")
        title.setStyleSheet("font-size: 22px; font-weight: 800;")
        version_error = None
        try:
            version = load_current_version()
        except ValueError as error:
            version = "indisponible"
            version_error = str(error)
        subtitle = QLabel(
            f"IPSI · Notes, ECTS et progression sur trois années · v{version}"
        )
        if version_error is not None:
            subtitle.setToolTip(version_error)
        subtitle.setStyleSheet("color: #94a3b8;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box, 1)
        selected_year = self.settings.get("dashboard_year", next(iter(CURRICULUM_DATA), ""))
        if not isinstance(selected_year, str) or selected_year not in CURRICULUM_DATA:
            selected_year = next(iter(CURRICULUM_DATA), "")
            self.settings["dashboard_year"] = selected_year
        header_layout.addWidget(QLabel("Année :"))
        self.year_selector = QComboBox()
        self.year_selector.setObjectName("GlobalYearSelector")
        self.year_selector.addItems(list(CURRICULUM_DATA.keys()))
        self.year_selector.setCurrentText(selected_year)
        self.year_selector.setMinimumWidth(150)
        self.year_selector.setAccessibleName("Année scolaire affichée")
        self.year_selector.setToolTip(
            "Cette année s'applique au Dashboard, aux modules et au simulateur."
        )
        self.year_selector.currentTextChanged.connect(self.set_dashboard_year)
        header_layout.addWidget(self.year_selector)
        main_layout.addWidget(header)

        for year_name, config in CURRICULUM_DATA.items():
            tab = YearTabWidget(year_name, config, self.on_data_changed, lambda: self.settings)
            self.year_tabs[year_name] = tab

        self._displayed_year = selected_year
        self.tabs = QTabWidget()
        self.recap_tab = YearRecapWidget(self.year_tabs, lambda: self.settings)
        self.tabs.addTab(self.recap_tab, "Dashboard")
        self.tabs.addTab(self.year_tabs[selected_year], f"Modules · {selected_year}")
        self.simulation_tab = GradeSimulationWidget(self.year_tabs, lambda: self.settings)
        self.tabs.addTab(self.simulation_tab, "Simulateur")
        self.tabs.setCurrentIndex(0)
        main_layout.addWidget(self.tabs, 1)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Prêt · Les notes sont sauvegardées automatiquement dans le JSON.")
        self.apply_settings(self.settings, refresh_history=False)

    def _create_actions(self):
        self.action_save = QAction("💾 Enregistrer JSON", self)
        self.action_save.setShortcut(QKeySequence("Ctrl+S"))
        self.action_save.triggered.connect(self.save_data)

        self.action_export = QAction("⇩ Exporter CSV…", self)
        self.action_export.setShortcut(QKeySequence("Ctrl+E"))
        self.action_export.triggered.connect(self.export_csv)

        self.action_undo = QAction("↶ Annuler", self)
        self.action_undo.setShortcut(QKeySequence("Ctrl+Z"))
        self.action_undo.triggered.connect(self.undo)

        self.action_redo = QAction("↷ Rétablir", self)
        self.action_redo.setShortcut(QKeySequence("Ctrl+Y"))
        self.action_redo.triggered.connect(self.redo)

        self.action_settings = QAction("⚙ Paramètres…", self)
        self.action_settings.triggered.connect(self.open_settings)

        self.action_about = QAction("À propos", self)
        self.action_about.triggered.connect(self.open_project_page)

        self.action_reset = QAction("Effacer toutes les notes…", self)
        self.action_reset.triggered.connect(self.reset_data)

        self.action_quit = QAction("Quitter", self)
        self.action_quit.setShortcut(QKeySequence("Ctrl+Q"))
        self.action_quit.triggered.connect(self.close)

        self.action_fullscreen = QAction("Plein écran", self)
        self.action_fullscreen.setShortcut(QKeySequence("F11"))
        self.action_fullscreen.setCheckable(True)
        self.action_fullscreen.toggled.connect(self._set_fullscreen)

    def _create_menus(self):
        file_menu = self.menuBar().addMenu("Fichier")
        file_menu.addAction(self.action_save)
        file_menu.addAction(self.action_export)
        file_menu.addSeparator()
        file_menu.addAction(self.action_reset)
        file_menu.addAction(self.action_quit)

        edit_menu = self.menuBar().addMenu("Édition")
        edit_menu.addAction(self.action_undo)
        edit_menu.addAction(self.action_redo)

        view_menu = self.menuBar().addMenu("Affichage")
        self.view_modes_menu = view_menu.addMenu("Modes d'affichage")
        mode_group = QActionGroup(self)
        mode_group.setExclusive(True)
        for mode in ("Confortable", "Grille (2 colonnes)", "Résumé compact"):
            action = QAction(mode, self)
            action.setCheckable(True)
            action.setChecked(mode == self.settings.get("view_mode", "Confortable"))
            mode_group.addAction(action)
            self.view_mode_actions[mode] = action
            action.triggered.connect(lambda checked=False, m=mode: self.set_view_mode(m))
            self.view_modes_menu.addAction(action)
        view_menu.addSeparator()
        view_menu.addAction(self.action_fullscreen)

        settings_menu = self.menuBar().addMenu("Préférences")
        settings_menu.addAction(self.action_settings)
        self.menuBar().addAction(self.action_about)

    def open_project_page(self):
        if not QDesktopServices.openUrl(QUrl(PROJECT_URL)):
            self.statusBar().showMessage(
                "Impossible d'ouvrir la page GitHub de l'application.", 6000
            )

    def set_dashboard_year(self, year_name):
        if year_name not in self.year_tabs:
            return
        self.settings["dashboard_year"] = year_name
        self._show_year_tab(year_name)
        if not self._restoring:
            self.save_data_quietly()

    def _show_year_tab(self, year_name):
        current_widget = self.tabs.currentWidget()
        previous_tab = self.year_tabs.get(self._displayed_year)
        previous_index = self.tabs.indexOf(previous_tab) if previous_tab is not None else -1
        if previous_index >= 0:
            self.tabs.removeTab(previous_index)
        self._displayed_year = year_name
        selected_tab = self.year_tabs[year_name]
        self.tabs.insertTab(1, selected_tab, f"Modules · {year_name}")
        if current_widget is previous_tab:
            self.tabs.setCurrentWidget(selected_tab)
        elif current_widget is not None:
            self.tabs.setCurrentWidget(current_widget)
        self.recap_tab.refresh()
        self.simulation_tab.refresh_for_year()

    def set_view_mode(self, mode):
        if mode not in ("Confortable", "Grille (2 colonnes)", "Résumé compact"):
            return
        for action_mode, action in self.view_mode_actions.items():
            action.setChecked(action_mode == mode)
        for tab in self.year_tabs.values():
            tab.set_view_mode(mode)
        self.settings["view_mode"] = mode
        if hasattr(self, "recap_tab"):
            self.recap_tab.refresh()
        if not self._restoring:
            self.save_data_quietly()

    def _set_fullscreen(self, enabled):
        if enabled and not self.isFullScreen():
            self.showFullScreen()
        elif not enabled and self.isFullScreen():
            self.showNormal()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange and hasattr(self, "action_fullscreen"):
            self.action_fullscreen.setChecked(self.isFullScreen())

    def on_data_changed(self):
        if self._restoring:
            return
        self.update_global_summary()
        self.save_data_quietly()
        self._history_timer.start()
        self.statusBar().showMessage("Modifications enregistrées automatiquement · Ctrl+Z pour annuler", 3500)

    def update_global_summary(self):
        if hasattr(self, "recap_tab"):
            self.recap_tab.refresh()
        if hasattr(self, "simulation_tab"):
            self.simulation_tab.refresh_from_data()

    def _snapshot_notes(self):
        return {name: tab.export_data() for name, tab in self.year_tabs.items()}

    def _reset_history_baseline(self):
        self._history_timer.stop()
        self._history = [deepcopy(self._snapshot_notes())]
        self._history_index = 0
        self._update_history_actions()

    def _capture_history(self):
        if self._restoring:
            return
        snapshot = self._snapshot_notes()
        if self._history_index >= 0 and snapshot == self._history[self._history_index]:
            return
        del self._history[self._history_index + 1:]
        self._history.append(deepcopy(snapshot))
        self._history_index = len(self._history) - 1
        # Limite l'historique pour garder l'application légère.
        if len(self._history) > 100:
            self._history.pop(0)
            self._history_index -= 1
        self._update_history_actions()

    def _update_history_actions(self):
        if hasattr(self, "action_undo"):
            self.action_undo.setEnabled(self._history_index > 0)
            self.action_redo.setEnabled(self._history_index >= 0 and self._history_index < len(self._history) - 1)

    def _apply_snapshot(self, snapshot, label):
        self._restoring = True
        try:
            for name, tab in self.year_tabs.items():
                tab.import_data(snapshot.get(name, {}))
        finally:
            self._restoring = False
        self.update_global_summary()
        self.save_data_quietly()
        self._update_history_actions()
        self.statusBar().showMessage(label, 3000)

    def undo(self):
        self._history_timer.stop()
        self._capture_history()
        if self._history_index > 0:
            self._history_index -= 1
            self._apply_snapshot(self._history[self._history_index], "Modification annulée.")
        self._update_history_actions()

    def redo(self):
        self._history_timer.stop()
        self._capture_history()
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            self._apply_snapshot(self._history[self._history_index], "Modification rétablie.")
        self._update_history_actions()

    def save_data(self):
        if self.save_data_quietly():
            QMessageBox.information(
                self,
                "Sauvegarde",
                f"Les notes et paramètres ont été enregistrés dans {SAVE_FILE}.",
            )

    def save_data_quietly(self):
        payload = {
            "version": 3,
            "settings": deepcopy(self.settings),
            "years": self._snapshot_notes(),
        }
        temporary = SAVE_FILE + ".tmp"
        try:
            os.makedirs(os.path.dirname(SAVE_FILE), exist_ok=True)
            with open(temporary, "w", encoding="utf-8") as file:
                json.dump(payload, file, ensure_ascii=False, indent=2)
            os.replace(temporary, SAVE_FILE)
        except (OSError, TypeError, ValueError) as error:
            try:
                if os.path.exists(temporary):
                    os.remove(temporary)
            except OSError:
                pass
            if hasattr(self, "statusBar"):
                self.statusBar().showMessage(f"Erreur de sauvegarde JSON : {error}", 6000)
            return False
        return True

    def load_data(self):
        legacy_file = os.path.abspath("notes_data.json")
        load_file = SAVE_FILE
        migrating_legacy_data = (
            not os.path.exists(SAVE_FILE)
            and os.path.isfile(legacy_file)
            and os.path.normcase(legacy_file)
            != os.path.normcase(os.path.abspath(SAVE_FILE))
        )
        if migrating_legacy_data:
            load_file = legacy_file
        if not os.path.exists(load_file):
            return
        try:
            with open(load_file, "r", encoding="utf-8") as file:
                payload = json.load(file)
            # Rétrocompatibilité avec l'ancien JSON qui stockait directement les années à la racine.
            years_data = payload.get("years", payload) if isinstance(payload, dict) else {}
            if isinstance(payload, dict) and isinstance(payload.get("settings"), dict):
                self.settings.update({key: value for key, value in payload["settings"].items() if key in DEFAULT_SETTINGS})
            self._restoring = True
            try:
                for year_name, tab in self.year_tabs.items():
                    data = years_data.get(year_name, {}) if isinstance(years_data, dict) else {}
                    if isinstance(data, dict):
                        tab.import_data(data)
            finally:
                self._restoring = False
            self.apply_settings(self.settings, refresh_history=False)
            self.update_global_summary()
            if migrating_legacy_data:
                if self.save_data_quietly():
                    self.statusBar().showMessage(
                        f"Anciennes notes copiées vers {SAVE_FILE}.", 6000
                    )
            else:
                self.statusBar().showMessage(f"Notes chargées depuis {SAVE_FILE}.", 4000)
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
            self.statusBar().showMessage(f"Impossible de charger le JSON : {error}", 7000)

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exporter les notes en CSV", "notes_export.csv", "Fichiers CSV (*.csv)")
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path += ".csv"
        headers = [
            "Année", "Catégorie", "Bloc", "ECTS du bloc", "Module", "Poids (%)",
            "Note /20", "État du module", "Moyenne provisoire du bloc /20", "Bloc complet", "Diagnostic indicatif du bloc",
            "Moyenne provisoire annuelle /20", "Moyenne annuelle éléments complets /20",
            "Complétude annuelle (%)", "ECTS évalués", "ECTS acquis estimés",
            "Seuil indicatif /20", "Alternance /20", "TOEIC (points)"
        ]
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as file:
                writer = csv.DictWriter(file, fieldnames=headers, delimiter=";")
                writer.writeheader()
                threshold = float(self.settings.get("validation_threshold", 10.0))
                for year_name, tab in self.year_tabs.items():
                    year_metrics = tab.get_year_metrics(threshold=threshold)
                    provisional_text = "" if year_metrics["provisional_average"] is None else f"{year_metrics['provisional_average']:.2f}"
                    complete_year_text = "" if year_metrics["complete_average"] is None else f"{year_metrics['complete_average']:.2f}"
                    common = {
                        "Année": year_name,
                        "Moyenne provisoire annuelle /20": provisional_text,
                        "Moyenne annuelle éléments complets /20": complete_year_text,
                        "Complétude annuelle (%)": f"{year_metrics['completion_pct']:.1f}",
                        "ECTS évalués": f"{year_metrics['ects_evaluated']:.0f}",
                        "ECTS acquis estimés": f"{year_metrics['ects_acquired_estimated']:.0f}",
                        "Seuil indicatif /20": f"{threshold:g}",
                        "Alternance /20": tab.inp_alternance.text().strip(),
                        "TOEIC (points)": tab.inp_toeic.text().strip(),
                    }
                    for block in tab.block_widgets:
                        module_minimum = float(self.settings.get("module_minimum", 6.0)) if self.settings.get("enforce_module_minimum", False) else None
                        block_metrics = block.get_block_metrics(target=threshold, module_minimum=module_minimum)
                        block_avg = block_metrics["provisional_average"]
                        block_avg_text = "" if block_avg is None else f"{block_avg:.2f}"
                        if block_metrics["complete_average"] is None:
                            block_status = "Incomplet"
                        elif block_metrics["validation_pass"]:
                            block_status = "Critères indicatifs atteints"
                        elif block_metrics["module_minimum_met"] is False and block_metrics["complete_average"] >= threshold:
                            block_status = "Note minimale par module non atteinte"
                        else:
                            block_status = "Sous le seuil indicatif"
                        for module_name, item in block.inputs.items():
                            row = dict(common)
                            row.update({
                                "Catégorie": "Module",
                                "Bloc": block.block_data["name"],
                                "ECTS du bloc": block.block_data["ects"],
                                "Module": module_name,
                                "Poids (%)": item["weight"],
                                "Note /20": item["input"].text().strip(),
                                "État du module": item["status"].currentText(),
                                "Moyenne provisoire du bloc /20": block_avg_text,
                                "Bloc complet": "Oui" if block_metrics["complete_average"] is not None else "Non",
                                "Diagnostic indicatif du bloc": block_status,
                            })
                            writer.writerow(row)
                    if tab.inp_alternance.text().strip() or tab.inp_toeic.text().strip():
                        row = dict(common)
                        row.update({
                            "Catégorie": "Informations annuelles",
                            "Module": "Alternance / TOEIC",
                            "Diagnostic indicatif du bloc": "Alternance : seuil atteint (est.)" if year_metrics["alternance_grade"] is not None and year_metrics["alternance_grade"] >= threshold else ("Alternance : sous le seuil (est.)" if year_metrics["alternance_grade"] is not None else "Alternance non évaluée"),
                        })
                        writer.writerow(row)
            self.statusBar().showMessage(f"Export CSV terminé : {path}", 5000)
            QMessageBox.information(self, "Export CSV", "Les notes, états des modules, complétudes, moyennes provisoires, moyennes des éléments complets et ECTS estimés ont été exportés.")
        except OSError as error:
            QMessageBox.critical(self, "Erreur d'export", f"Le fichier CSV n'a pas pu être écrit.\n\n{error}")

    def open_settings(self):
        dialog = SettingsDialog(self.settings, self)
        dialog.setStyleSheet(make_stylesheet(self.settings))
        if dialog.exec() == QDialog.Accepted:
            self.settings.update(dialog.get_settings())
            self.apply_settings(self.settings)
            self.save_data_quietly()
            self.statusBar().showMessage("Préférences enregistrées.", 3000)

    def apply_settings(self, settings, refresh_history=True):
        self.settings.update(settings)
        self._apply_display_resolution()
        self.setStyleSheet(make_stylesheet(self.settings))
        app = QApplication.instance()
        if app is not None:
            scaled_font_size = max(
                1,
                round(
                    int(self.settings.get("font_size", 10))
                    * max(0.7, min(1.5, float(self.settings.get("ui_scale", 100)) / 100.0))
                ),
            )
            app.setFont(QFont(self.settings.get("font_family", "Segoe UI"), scaled_font_size))
        # Met à jour aussi les polices qui avaient une taille personnalisée.
        font_family = self.settings.get("font_family", "Segoe UI")
        for widget in self.findChildren(QWidget):
            font = widget.font()
            font.setFamily(font_family)
            widget.setFont(font)
        mode = self.settings.get("view_mode", "Confortable")
        if mode not in self.view_mode_actions:
            mode = "Confortable"
        self.settings["view_mode"] = mode
        for action_mode, action in self.view_mode_actions.items():
            action.setChecked(action_mode == mode)
        for tab in self.year_tabs.values():
            for block in tab.block_widgets:
                for item in block.inputs.values():
                    block.update_module_status_style(
                        item["status"], item["status"].currentText()
                    )
            tab.set_view_mode(mode)
            tab.update_year_summary()
        selected_year = self.settings.get("dashboard_year", next(iter(self.year_tabs), ""))
        if not isinstance(selected_year, str) or selected_year not in self.year_tabs:
            selected_year = next(iter(self.year_tabs), "")
            self.settings["dashboard_year"] = selected_year
        self.year_selector.blockSignals(True)
        self.year_selector.setCurrentText(selected_year)
        self.year_selector.blockSignals(False)
        if selected_year != self._displayed_year:
            self._show_year_tab(selected_year)
        elif hasattr(self, "recap_tab"):
            self.recap_tab.refresh()
        if hasattr(self, "simulation_tab"):
            self.simulation_tab.refresh_from_data()
        if refresh_history and not self._restoring:
            self.save_data_quietly()

    def _apply_display_resolution(self):
        resolution_name = self.settings.get("display_resolution", "Automatique")
        if not isinstance(resolution_name, str) or resolution_name not in DISPLAY_RESOLUTIONS:
            resolution_name = "Automatique"
            self.settings["display_resolution"] = resolution_name

        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return

        available = screen.availableGeometry()
        requested_size = DISPLAY_RESOLUTIONS[resolution_name]
        if requested_size is None:
            width = min(1320, int(available.width() * 0.96))
            height = min(900, int(available.height() * 0.94))
        else:
            width = min(requested_size[0], available.width())
            height = min(requested_size[1], available.height())
        self.setGeometry(
            available.x() + (available.width() - width) // 2,
            available.y() + (available.height() - height) // 2,
            width,
            height,
        )

    def reset_data(self):
        reply = QMessageBox.question(
            self,
            "Effacer les notes",
            "Voulez-vous vraiment effacer toutes les notes de toutes les années ? Cette opération peut être annulée avec Ctrl+Z.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._history_timer.stop()
        self._restoring = True
        try:
            for tab in self.year_tabs.values():
                tab.inp_alternance.clear()
                tab.inp_toeic.clear()
                for block in tab.block_widgets:
                    for item in block.inputs.values():
                        item["input"].clear()
                tab.update_year_summary()
        finally:
            self._restoring = False
        self.update_global_summary()
        self.save_data_quietly()
        self._history_timer.start()
        self.statusBar().showMessage("Toutes les notes ont été effacées. Ctrl+Z permet de revenir en arrière.", 5000)
