import math

from PySide6.QtCore import Qt, QLocale

from PySide6.QtGui import QDoubleValidator, QIntValidator, QKeySequence, QShortcut

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QFrame, QScrollArea, QComboBox, QToolButton, QProgressBar, QSizePolicy

from app_data import DEFAULT_SETTINGS, MODULE_STATUSES, calculate_weighted_metrics


class KpiTile(QFrame):
    """Petite tuile KPI réutilisable pour les synthèses."""
    def __init__(self, title, value="—", subtitle=""):
        super().__init__()
        self.setObjectName("KpiTile")
        self.setMinimumHeight(94)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 11, 14, 11)
        layout.setSpacing(3)
        self.title_label = QLabel(title)
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("font-size: 10px; font-weight: 700; color: #94a3b8; letter-spacing: 1px;")
        self.value_label = QLabel(value)
        self.value_label.setWordWrap(True)
        self.value_label.setStyleSheet("font-size: 23px; font-weight: 800;")
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setStyleSheet("font-size: 11px; color: #94a3b8;")
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.subtitle_label)

    def set_values(self, value, subtitle=""):
        self.value_label.setText(value)
        self.subtitle_label.setText(subtitle)

class BlockCardWidget(QFrame):
    """Carte d'un bloc avec KPI, barre de progression et détail des modules."""
    def __init__(self, block_data, on_grade_changed_callback, settings_provider=None):
        super().__init__()
        self.setObjectName("Card")
        self.block_data = block_data
        self.on_grade_changed_callback = on_grade_changed_callback
        self.settings_provider = settings_provider or (lambda: DEFAULT_SETTINGS)
        self.inputs = {}
        self.grade_input_order = []
        self.compact_columns = False
        self.view_mode = "Confortable"
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 13, 15, 14)
        layout.setSpacing(9)

        header = QHBoxLayout()
        self.lbl_title = QLabel(f"{self.block_data['name']}  ·  {self.block_data['ects']} ECTS")
        self.lbl_title.setProperty("class", "BlockHeader")
        self.lbl_title.setWordWrap(True)
        self.lbl_average = QLabel("— / 20")
        self.lbl_average.setAlignment(Qt.AlignCenter)
        self.lbl_average.setMinimumWidth(100)
        self.lbl_average.setProperty("class", "HeaderBadge")
        self.update_badge_style(None)
        self.lbl_completion = QLabel("Notes : 0 %")
        self.lbl_completion.setProperty("class", "Muted")
        self.lbl_completion.setMinimumWidth(92)
        self.btn_toggle = QToolButton()
        self.btn_toggle.setObjectName("BlockToggle")
        self.btn_toggle.setText("Détails ▾")
        self.btn_toggle.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.btn_toggle.setCheckable(True)
        self.btn_toggle.setChecked(True)
        self.btn_toggle.toggled.connect(self.toggle_details)
        header.addWidget(self.lbl_title, 1)
        header.addWidget(self.lbl_completion)
        header.addWidget(self.lbl_average)
        header.addWidget(self.btn_toggle)
        layout.addLayout(header)

        self.progress = QProgressBar()
        self.progress.setRange(0, 200)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)
        self.progress.setToolTip("Progression de la moyenne du bloc sur 20")
        layout.addWidget(self.progress)

        self.details_widget = QWidget()
        details_layout = QVBoxLayout(self.details_widget)
        details_layout.setContentsMargins(0, 1, 0, 0)
        details_layout.setSpacing(9)
        self.lbl_target_info = QLabel("Saisissez vos notes pour calculer la moyenne du bloc.")
        self.lbl_target_info.setWordWrap(True)
        self.lbl_target_info.setStyleSheet("color: #94a3b8; font-style: italic;")
        details_layout.addWidget(self.lbl_target_info)
        separator = QFrame()
        separator.setObjectName("Separator")
        details_layout.addWidget(separator)

        grid = QGridLayout()
        self.module_grid = grid
        grid.setHorizontalSpacing(9)
        grid.setVerticalSpacing(6)
        grid.setColumnStretch(0, 1)
        grid.setColumnMinimumWidth(1, 48)
        grid.setColumnMinimumWidth(2, 72)
        grid.setColumnMinimumWidth(3, 110)
        grid.setColumnMinimumWidth(4, 58)
        self.weight_header = QLabel("<b>Poids</b>")
        self.target_header = QLabel("<b>Objectif</b>")
        self.weight_header.setAlignment(Qt.AlignCenter)
        self.target_header.setAlignment(Qt.AlignCenter)
        grid.addWidget(QLabel("<b>Module / matière</b>"), 0, 0)
        grid.addWidget(self.weight_header, 0, 1)
        grid.addWidget(QLabel("<b>Note /20</b>"), 0, 2, Qt.AlignCenter)
        grid.addWidget(QLabel("<b>État</b>"), 0, 3, Qt.AlignCenter)
        grid.addWidget(self.target_header, 0, 4)

        validator = QDoubleValidator(0.0, 20.0, 2, self)
        validator.setNotation(QDoubleValidator.StandardNotation)
        validator.setLocale(QLocale())
        for row, module in enumerate(self.block_data["modules"], start=1):
            name_label = QLabel(module["name"])
            name_label.setWordWrap(True)
            weight_label = QLabel(f"{module['weight']} %")
            weight_label.setAlignment(Qt.AlignCenter)
            grade_input = QLineEdit()
            grade_input.setFixedWidth(72)
            grade_input.setAlignment(Qt.AlignCenter)
            grade_input.setPlaceholderText("Note")
            grade_input.setValidator(validator)
            grade_input.textChanged.connect(self.on_input_changed)
            grade_input.setAccessibleName(f"Note sur 20 · {module['name']}")
            grade_input.setToolTip("Saisissez une note de 0 à 20. Entrée passe au module suivant.")
            status_selector = QComboBox()
            status_selector.setObjectName("ModuleStatus")
            status_selector.setFixedWidth(110)
            status_selector.addItems(MODULE_STATUSES)
            status_selector.currentTextChanged.connect(
                lambda status, selector=status_selector:
                self.on_module_status_changed(selector, status)
            )
            status_selector.activated.connect(
                lambda _, name=module["name"], selector=status_selector:
                self.focus_grade_for_status(name, selector.currentText())
            )
            status_selector.setAccessibleName(f"État · {module['name']}")
            target_label = QLabel("—")
            target_label.setAlignment(Qt.AlignCenter)
            target_label.setMinimumWidth(58)
            target_label.setToolTip(
                "Note moyenne à viser dans les modules non notés pour atteindre 10/20."
            )
            grid.addWidget(name_label, row, 0)
            grid.addWidget(weight_label, row, 1)
            grid.addWidget(grade_input, row, 2, Qt.AlignCenter)
            grid.addWidget(status_selector, row, 3)
            grid.addWidget(target_label, row, 4)
            self.inputs[module["name"]] = {
                "weight": float(module["weight"]),
                "name_label": name_label,
                "input": grade_input,
                "weight_label": weight_label,
                "status": status_selector,
                "target_lbl": target_label,
                "matches_filter": True,
            }
            input_index = len(self.grade_input_order)
            self.grade_input_order.append(grade_input)
            grade_input.returnPressed.connect(
                lambda index=input_index: self.focus_next_grade(index)
            )
            self.update_module_status_style(status_selector, MODULE_STATUSES[0])

        details_layout.addLayout(grid)
        layout.addWidget(self.details_widget)
        self.recalculate()

    def on_module_status_changed(self, selector, status):
        self.update_module_status_style(selector, status)
        self.on_input_changed()

    def focus_grade_for_status(self, module_name, status):
        grade_input = self.inputs[module_name]["input"]
        if status == "En cours" and not grade_input.text().strip():
            grade_input.setFocus()

    def update_module_status_style(self, selector, status):
        dark = (self.settings_provider() or DEFAULT_SETTINGS).get("theme", "Sombre") == "Sombre"
        colors = {
            "Pas commencé": ("#334155", "#e2e8f0", "#64748b") if dark else ("#e2e8f0", "#334155", "#94a3b8"),
            "En cours": ("#1e3a8a", "#dbeafe", "#3b82f6") if dark else ("#dbeafe", "#1e3a8a", "#3b82f6"),
            "Terminé": ("#064e3b", "#d1fae5", "#10b981") if dark else ("#dcfce7", "#065f46", "#10b981"),
        }
        background, foreground, border = colors.get(status, colors["Pas commencé"])
        selector.setStyleSheet(
            f"QComboBox#ModuleStatus {{ min-width: 0; padding: 4px 6px; "
            f"background-color: {background}; color: {foreground}; "
            f"border: 1px solid {border}; border-radius: 6px; font-weight: 600; }}"
        )

    def focus_next_grade(self, current_index):
        if not self.grade_input_order:
            return
        next_index = (current_index + 1) % len(self.grade_input_order)
        self.grade_input_order[next_index].setFocus()
        self.grade_input_order[next_index].selectAll()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.compact_columns = self.width() < 650
        self.module_grid.setColumnMinimumWidth(
            1, 0 if self.compact_columns else 48
        )
        self.module_grid.setColumnMinimumWidth(
            4, 0 if self.compact_columns else 58
        )
        self.weight_header.setVisible(not self.compact_columns)
        self.target_header.setVisible(not self.compact_columns)
        for item in self.inputs.values():
            item["weight_label"].setVisible(
                item["matches_filter"] and not self.compact_columns
            )
            item["target_lbl"].setVisible(
                item["matches_filter"] and not self.compact_columns
            )

    def toggle_details(self, expanded):
        self.details_widget.setVisible(expanded)
        self.btn_toggle.setText("Détails ▾" if not expanded else "Réduire ▴")

    def set_view_mode(self, mode):
        self.view_mode = mode
        if mode == "Résumé compact":
            self.btn_toggle.setChecked(False)
        else:
            self.btn_toggle.setChecked(True)

    def on_input_changed(self):
        self.recalculate()
        self.on_grade_changed_callback()

    @staticmethod
    def parse_grade(text):
        text = str(text).replace(",", ".").strip()
        if not text:
            return None
        try:
            value = float(text)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(value) or value < 0.0 or value > 20.0:
            return None
        return value

    def recalculate(self):
        entered_weight = 0.0
        weighted_sum = 0.0
        missing_weight = 0.0
        missing_count = 0
        for item in self.inputs.values():
            value = self.parse_grade(item["input"].text())
            if value is None:
                missing_weight += item["weight"]
                missing_count += 1
                item["input"].setStyleSheet("")
                item["input"].setToolTip(
                    "Aucune note saisie. Entrez une note de 0 à 20."
                )
                item["target_lbl"].setText("—")
                item["target_lbl"].setStyleSheet("color: #94a3b8;")
            else:
                weighted_sum += value * item["weight"]
                entered_weight += item["weight"]
                grade_color = "#ef4444" if value < 8 else "#f59e0b" if value < 10 else "#10b981"
                item["input"].setStyleSheet(
                    f"QLineEdit {{ border: 1px solid {grade_color}; }}"
                )
                item["input"].setToolTip(
                    f"Note saisie : {value:g}/20 · "
                    + ("sous 8/20" if value < 8 else "sous le seuil indicatif de 10/20" if value < 10 else "seuil indicatif atteint")
                )
                item["target_lbl"].setText("Saisi")
                item["target_lbl"].setStyleSheet("color: #64748b; font-weight: 600;")

        current_avg = weighted_sum / entered_weight if entered_weight else None
        total_weight_for_progress = sum(item["weight"] for item in self.inputs.values())
        completion = (entered_weight / total_weight_for_progress * 100.0) if total_weight_for_progress else 0.0
        self.lbl_completion.setText(f"Notes : {completion:.0f} %")
        self.lbl_completion.setToolTip(f"{sum(1 for item in self.inputs.values() if self.parse_grade(item['input'].text()) is not None)}/{len(self.inputs)} modules renseignés")
        if current_avg is None:
            self.lbl_average.setText("— / 20")
            self.progress.setValue(0)
        else:
            self.lbl_average.setText(f"{current_avg:.2f} / 20")
            self.progress.setValue(round(current_avg * 10))
        self.update_badge_style(current_avg)

        if missing_count > 0 and missing_weight > 0:
            total_weight = sum(item["weight"] for item in self.inputs.values())
            needed = (10.0 * total_weight - weighted_sum) / missing_weight
            if needed <= 0:
                target_text, color = "Objectif déjà atteint", "#10b981"
            elif needed > 20:
                target_text, color = f"Impossible : {needed:.2f}/20 requis", "#ef4444"
            else:
                target_text, color = f"Viser {needed:.2f}/20 sur les modules restants", "#38bdf8"
            self.lbl_target_info.setText(f"{missing_count} module(s) sans note · {target_text}")
            self.lbl_target_info.setStyleSheet(f"color: {color}; font-weight: 600;")
            for item in self.inputs.values():
                if self.parse_grade(item["input"].text()) is None:
                    item["target_lbl"].setText("—" if needed > 20 else ("0" if needed <= 0 else f"{needed:.2f}"))
                    item["target_lbl"].setStyleSheet(f"color: {color}; font-weight: 700;")
        else:
            self.lbl_target_info.setText("Bloc complet : toutes les notes sont renseignées." if missing_count == 0 else "Aucune note renseignée pour le moment.")
            self.lbl_target_info.setStyleSheet("color: #10b981; font-weight: 600;" if missing_count == 0 else "color: #94a3b8; font-style: italic;")

    def update_badge_style(self, average):
        if average is None:
            style = "background-color: #334155; color: #cbd5e1; border-radius: 7px; padding: 6px 8px; font-weight: 800;"
        elif average < 8:
            style = "background-color: #7f1d1d; color: #fecaca; border: 1px solid #ef4444; border-radius: 7px; padding: 6px 8px; font-weight: 800;"
        elif average < 10:
            style = "background-color: #78350f; color: #fde68a; border: 1px solid #f59e0b; border-radius: 7px; padding: 6px 8px; font-weight: 800;"
        else:
            style = "background-color: #064e3b; color: #a7f3d0; border: 1px solid #10b981; border-radius: 7px; padding: 6px 8px; font-weight: 800;"
        self.lbl_average.setStyleSheet(style)

    def get_block_metrics(self, target=10.0, module_minimum=None):
        weighted_values = [
            (item["weight"], self.parse_grade(item["input"].text()))
            for item in self.inputs.values()
        ]
        return calculate_weighted_metrics(weighted_values, target=target, module_minimum=module_minimum)

    def get_block_average(self):
        """Moyenne provisoire, calculée uniquement sur les notes renseignées."""
        return self.get_block_metrics()["provisional_average"]

    def get_complete_average(self):
        """Moyenne du bloc seulement si toutes les notes sont renseignées."""
        return self.get_block_metrics()["complete_average"]

    def export_data(self):
        return {
            name: {
                "grade": item["input"].text().strip(),
                "status": item["status"].currentText(),
            }
            for name, item in self.inputs.items()
        }

    def import_data(self, data):
        for name, item in self.inputs.items():
            module_data = data.get(name, "")
            if isinstance(module_data, dict):
                grade = module_data.get("grade", "")
                status = module_data.get("status", MODULE_STATUSES[0])
            else:
                grade = module_data
                status = MODULE_STATUSES[0]
            item["input"].setText(str(grade))
            item["status"].setCurrentText(
                status if status in MODULE_STATUSES else MODULE_STATUSES[0]
            )
        self.recalculate()

class YearTabWidget(QWidget):
    """Onglet de saisie et de synthèse d'une année."""
    def __init__(self, year_name, year_config, on_data_changed, settings_provider=None):
        super().__init__()
        self.year_name = year_name
        self.year_config = year_config
        self.on_data_changed = on_data_changed
        self.settings_provider = settings_provider or (lambda: DEFAULT_SETTINGS)
        self.block_widgets = []
        self.view_mode = "Confortable"
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        summary_card = QFrame()
        summary_card.setObjectName("Card")
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(15, 12, 15, 12)
        top_line = QHBoxLayout()
        self.lbl_year_avg = QLabel("Moyenne provisoire : — / 20")
        self.lbl_year_avg.setWordWrap(True)
        self.lbl_year_avg.setStyleSheet("font-size: 17px; font-weight: 800;")
        self.lbl_complete_avg = QLabel("Moyenne éléments complets : — / 20")
        self.lbl_complete_avg.setWordWrap(True)
        self.lbl_complete_avg.setStyleSheet("font-size: 14px; font-weight: 700;")
        self.lbl_status = QLabel("En attente de notes")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet("font-weight: 700; color: #94a3b8;")
        top_line.addWidget(self.lbl_year_avg, 2)
        top_line.addWidget(self.lbl_complete_avg, 2)
        top_line.addWidget(self.lbl_status)
        summary_layout.addLayout(top_line)
        self.lbl_ects_info = QLabel("ECTS évalués : 0 · ECTS acquis estimés : 0 · Complétude : 0 %")
        self.lbl_ects_info.setWordWrap(True)
        self.lbl_ects_info.setProperty("class", "Muted")
        summary_layout.addWidget(self.lbl_ects_info)
        self.year_progress = QProgressBar()
        self.year_progress.setRange(0, 200)
        self.year_progress.setTextVisible(False)
        self.year_progress.setFixedHeight(8)
        summary_layout.addWidget(self.year_progress)
        main_layout.addWidget(summary_card)
        self.lbl_year_avg.setToolTip(
            "Moyenne provisoire calculée avec les notes saisies et pondérée selon la complétude."
        )
        self.lbl_complete_avg.setToolTip(
            "Moyenne calculée uniquement à partir des blocs entièrement notés et de l'alternance notée."
        )
        self.lbl_ects_info.setToolTip(
            "Les ECTS évalués et acquis sont estimatifs et ne remplacent pas la validation officielle."
        )

        general_card = QFrame()
        general_card.setObjectName("Card")
        general_layout = QHBoxLayout(general_card)
        general_layout.setContentsMargins(15, 10, 15, 10)
        general_layout.setSpacing(12)
        general_layout.addWidget(QLabel("<b>Alternance (/20)</b>"))
        self.inp_alternance = QLineEdit()
        self.inp_alternance.setFixedWidth(90)
        self.inp_alternance.setAlignment(Qt.AlignCenter)
        self.inp_alternance.setPlaceholderText("—")
        alt_validator = QDoubleValidator(0.0, 20.0, 2, self)
        alt_validator.setLocale(QLocale())
        self.inp_alternance.setValidator(alt_validator)
        self.inp_alternance.textChanged.connect(self.on_internal_changed)
        general_layout.addWidget(self.inp_alternance)
        separator = QLabel("  ·  ")
        separator.setStyleSheet("color: #94a3b8;")
        general_layout.addWidget(separator)
        general_layout.addWidget(QLabel("<b>Score TOEIC</b>"))
        self.inp_toeic = QLineEdit()
        self.inp_toeic.setFixedWidth(100)
        self.inp_toeic.setAlignment(Qt.AlignCenter)
        self.inp_toeic.setPlaceholderText("Points")
        self.inp_toeic.setValidator(QIntValidator(0, 990, self))
        self.inp_toeic.textChanged.connect(self.on_internal_changed)
        general_layout.addWidget(self.inp_toeic)
        self.lbl_toeic_status = QLabel("Objectif : 785 points")
        self.lbl_toeic_status.setWordWrap(True)
        self.lbl_toeic_status.setStyleSheet("color: #94a3b8;")
        general_layout.addWidget(self.lbl_toeic_status, 1)
        main_layout.addWidget(general_card)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.blocks_container = QWidget()
        self.blocks_container_layout = QVBoxLayout(self.blocks_container)
        self.blocks_container_layout.setContentsMargins(1, 1, 7, 1)
        self.blocks_container_layout.setSpacing(12)
        for block_data in self.year_config["blocks"]:
            block = BlockCardWidget(
                block_data, self.on_internal_changed, self.settings_provider
            )
            self.block_widgets.append(block)
            self.blocks_container_layout.addWidget(block)
        self.blocks_container_layout.addStretch(1)

        filter_row = QHBoxLayout()
        self.module_search = QLineEdit()
        self.module_search.setPlaceholderText("Rechercher un module…  (Ctrl+F)")
        self.module_search.setClearButtonEnabled(True)
        self.module_search.setAccessibleName("Rechercher un module")
        self.module_search.textChanged.connect(self.apply_module_filters)
        self.module_status_filter = QComboBox()
        self.module_status_filter.addItem("Tous les états", "all")
        for status in MODULE_STATUSES:
            self.module_status_filter.addItem(status, status)
        self.module_status_filter.addItem("Sans note", "no_grade")
        self.module_status_filter.currentIndexChanged.connect(self.apply_module_filters)
        self.module_status_filter.setAccessibleName("Filtrer les modules par état")
        self.lbl_module_count = QLabel()
        self.lbl_module_count.setProperty("class", "Muted")
        filter_row.addWidget(self.module_search, 1)
        filter_row.addWidget(self.module_status_filter)
        filter_row.addWidget(self.lbl_module_count)
        main_layout.addLayout(filter_row)

        self.search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self.search_shortcut.setContext(Qt.WidgetWithChildrenShortcut)
        self.search_shortcut.activated.connect(self.module_search.setFocus)
        self.scroll.setWidget(self.blocks_container)
        main_layout.addWidget(self.scroll, 1)
        self.apply_module_filters()
        self.update_year_summary()

    def set_view_mode(self, mode):
        self.view_mode = mode
        if mode == "Grille (2 colonnes)":
            for block in self.block_widgets:
                block.set_view_mode("Confortable")
            new_container = QWidget()
            new_layout = QGridLayout(new_container)
            new_layout.setContentsMargins(1, 1, 7, 1)
            new_layout.setHorizontalSpacing(12)
            new_layout.setVerticalSpacing(12)
            for index, block in enumerate(self.block_widgets):
                block.setParent(new_container)
                new_layout.addWidget(block, index // 2, index % 2)
            new_layout.setRowStretch((len(self.block_widgets) + 1) // 2, 1)
        else:
            new_container = QWidget()
            new_layout = QVBoxLayout(new_container)
            new_layout.setContentsMargins(1, 1, 7, 1)
            new_layout.setSpacing(12)
            for block in self.block_widgets:
                block.setParent(new_container)
                block.set_view_mode("Résumé compact" if mode == "Résumé compact" else "Confortable")
                new_layout.addWidget(block)
            new_layout.addStretch(1)
        self.blocks_container = new_container
        self.scroll.setWidget(new_container)

    def on_internal_changed(self):
        self.apply_module_filters()
        self.update_year_summary()
        self.on_data_changed()

    def apply_module_filters(self, *_):
        query = self.module_search.text().strip().casefold() if hasattr(self, "module_search") else ""
        selected_status = (
            self.module_status_filter.currentData()
            if hasattr(self, "module_status_filter")
            else "all"
        )
        visible_modules = 0
        total_modules = 0
        for block in self.block_widgets:
            block_matches = 0
            for module_name, item in block.inputs.items():
                total_modules += 1
                grade_entered = bool(item["input"].text().strip())
                matches = (
                    query in module_name.casefold()
                    and (
                        selected_status == "all"
                        or item["status"].currentText() == selected_status
                        or (selected_status == "no_grade" and not grade_entered)
                    )
                )
                item["matches_filter"] = matches
                for widget in (
                    item["name_label"], item["input"], item["status"],
                ):
                    widget.setVisible(matches)
                item["weight_label"].setVisible(matches and not block.compact_columns)
                item["target_lbl"].setVisible(matches and not block.compact_columns)
                if matches:
                    visible_modules += 1
                    block_matches += 1
            block.setVisible(block_matches > 0)
        if hasattr(self, "lbl_module_count"):
            self.lbl_module_count.setText(
                f"{visible_modules}/{total_modules} modules"
            )

    def update_year_summary(self):
        settings = self.settings_provider() or DEFAULT_SETTINGS
        toeic_target = int(settings.get("toeic_target", 785))
        toeic_text = self.inp_toeic.text().strip() if hasattr(self, "inp_toeic") else ""
        if toeic_text:
            try:
                score = int(toeic_text)
                if score >= toeic_target:
                    self.lbl_toeic_status.setText("TOEIC : objectif atteint ✓")
                    self.lbl_toeic_status.setStyleSheet("color: #10b981; font-weight: 700;")
                else:
                    self.lbl_toeic_status.setText(f"TOEIC : {toeic_target - score} points manquants")
                    self.lbl_toeic_status.setStyleSheet("color: #f59e0b; font-weight: 700;")
            except ValueError:
                self.lbl_toeic_status.setText("Score TOEIC invalide")
        else:
            self.lbl_toeic_status.setText(f"Objectif TOEIC : {toeic_target} points")
            self.lbl_toeic_status.setStyleSheet("color: #94a3b8;")

        metrics = self.get_year_metrics()
        provisional = metrics["provisional_average"]
        complete = metrics["complete_average"]
        if provisional is None:
            self.lbl_year_avg.setText("Moyenne provisoire : — / 20")
        else:
            self.lbl_year_avg.setText(f"Moyenne provisoire : {provisional:.2f} / 20")
        if complete is None:
            self.lbl_complete_avg.setText("Moyenne éléments complets : — / 20")
        else:
            self.lbl_complete_avg.setText(f"Moyenne éléments complets : {complete:.2f} / 20")

        total_blocks = len(self.block_widgets)
        complete_blocks = metrics["complete_blocks"]
        failing_complete = metrics["complete_blocks_below_threshold"] + (1 if metrics["alternance_grade"] is not None and metrics["alternance_grade"] < float(settings.get("validation_threshold", 10.0)) else 0)
        self.lbl_ects_info.setText(
            f"ECTS évalués : {metrics['ects_evaluated']:.0f} · "
            f"ECTS acquis estimés : {metrics['ects_acquired_estimated']:.0f} · "
            f"Blocs complets : {complete_blocks}/{total_blocks} · "
            f"Complétude : {metrics['completion_pct']:.0f} %"
        )
        self.year_progress.setValue(round((provisional or 0.0) * 10))
        self.year_progress.setToolTip("La barre représente la moyenne provisoire sur 20, pas la complétude des notes.")
        if metrics["ects_evaluated"] <= 0:
            self.lbl_status.setText("Aucun bloc complet")
            self.lbl_status.setStyleSheet("color: #94a3b8; font-weight: 700;")
        elif failing_complete:
            self.lbl_status.setText(f"{failing_complete} élément(s) complet(s) ne satisfaisant pas les critères indicatifs")
            self.lbl_status.setStyleSheet("color: #ef4444; font-weight: 700;")
        elif complete_blocks < total_blocks or metrics["alternance_grade"] is None:
            self.lbl_status.setText("Évaluation provisoire · notes ou éléments manquants")
            self.lbl_status.setStyleSheet("color: #f59e0b; font-weight: 700;")
        else:
            self.lbl_status.setText("Notes complètes · validation à confirmer selon le règlement")
            self.lbl_status.setStyleSheet("color: #10b981; font-weight: 700;")

    def get_year_metrics(self, threshold=None):
        """Retourne des métriques prudentes : les ECTS évalués/acquis comptent les blocs complets uniquement."""
        settings = self.settings_provider() or DEFAULT_SETTINGS
        if threshold is None:
            threshold = float(settings.get("validation_threshold", 10.0))
        threshold = float(threshold)
        module_minimum = None
        if bool(settings.get("enforce_module_minimum", False)):
            module_minimum = float(settings.get("module_minimum", 6.0))
        total_possible_ects = 0.0
        completion_ects_equivalent = 0.0
        provisional_weighted_sum = 0.0
        provisional_ects_equivalent = 0.0
        complete_weighted_sum = 0.0
        complete_ects = 0.0
        ects_evaluated = 0.0
        ects_acquired = 0.0
        complete_blocks = 0
        blocks_with_any_grade = 0
        complete_blocks_below_threshold = 0
        blocks_metrics = []

        for block in self.block_widgets:
            block_metrics = block.get_block_metrics(target=threshold, module_minimum=module_minimum)
            ects = float(block.block_data["ects"])
            total_possible_ects += ects
            completion_ratio = block_metrics["completion_pct"] / 100.0
            completion_ects_equivalent += ects * completion_ratio
            avg = block_metrics["provisional_average"]
            if avg is not None:
                blocks_with_any_grade += 1
                effective_ects = ects * completion_ratio
                provisional_weighted_sum += avg * effective_ects
                provisional_ects_equivalent += effective_ects
            complete_avg = block_metrics["complete_average"]
            if complete_avg is not None:
                complete_blocks += 1
                complete_weighted_sum += complete_avg * ects
                complete_ects += ects
                ects_evaluated += ects
                if block_metrics["validation_pass"]:
                    ects_acquired += ects
                else:
                    complete_blocks_below_threshold += 1
            blocks_metrics.append({
                "name": block.block_data["name"],
                "ects": ects,
                **block_metrics,
            })

        alt_ects = float(self.year_config.get("alternance_ects", 23))
        total_possible_ects += alt_ects
        alt = BlockCardWidget.parse_grade(self.inp_alternance.text())
        if alt is not None:
            completion_ects_equivalent += alt_ects
            provisional_weighted_sum += alt * alt_ects
            provisional_ects_equivalent += alt_ects
            complete_weighted_sum += alt * alt_ects
            complete_ects += alt_ects
            ects_evaluated += alt_ects
            if alt >= threshold:
                ects_acquired += alt_ects

        return {
            "provisional_average": provisional_weighted_sum / provisional_ects_equivalent if provisional_ects_equivalent else None,
            "complete_average": complete_weighted_sum / complete_ects if complete_ects else None,
            "provisional_weighted_sum": provisional_weighted_sum,
            "provisional_ects_equivalent": provisional_ects_equivalent,
            "complete_weighted_sum": complete_weighted_sum,
            "complete_ects": complete_ects,
            "ects_evaluated": ects_evaluated,
            "ects_acquired_estimated": ects_acquired,
            "total_possible_ects": total_possible_ects,
            "completion_pct": (completion_ects_equivalent / total_possible_ects * 100.0) if total_possible_ects else 0.0,
            "complete_blocks": complete_blocks,
            "blocks_with_any_grade": blocks_with_any_grade,
            "complete_blocks_below_threshold": complete_blocks_below_threshold,
            "blocks": blocks_metrics,
            "alternance_grade": alt,
            "alternance_ects": alt_ects,
            "alternance_below_threshold": alt is not None and alt < threshold,
        }

    def get_provisional_year_average(self):
        metrics = self.get_year_metrics()
        return metrics["provisional_average"], metrics["provisional_ects_equivalent"]

    def get_year_average(self):
        """Moyenne fiable des blocs complets, avec l'alternance si elle est notée."""
        metrics = self.get_year_metrics()
        return metrics["complete_average"], metrics["ects_evaluated"]

    def export_data(self):
        return {
            "alternance": self.inp_alternance.text().strip(),
            "toeic": self.inp_toeic.text().strip(),
            "blocks": {block.block_data["name"]: block.export_data() for block in self.block_widgets},
        }

    def import_data(self, data):
        self.inp_alternance.setText(str(data.get("alternance", "")))
        self.inp_toeic.setText(str(data.get("toeic", "")))
        block_data = data.get("blocks", {})
        for block in self.block_widgets:
            block.import_data(block_data.get(block.block_data["name"], {}))
        self.update_year_summary()
