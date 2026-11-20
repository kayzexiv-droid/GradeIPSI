import math

from PySide6.QtCore import Qt, QLocale

from PySide6.QtGui import QDoubleValidator, QIntValidator, QKeySequence, QShortcut

from PySide6.QtWidgets import QWidget, QBoxLayout, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QFrame, QScrollArea, QComboBox, QToolButton, QProgressBar, QSizePolicy, QTabWidget

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
        self.view_mode = "Confortable"
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 13, 15, 14)
        layout.setSpacing(9)

        header = QHBoxLayout()
        ects = self.block_data["ects"]
        detail = f"{ects} ECTS" if ects else "Validation séparée"
        self.lbl_title = QLabel(f"{self.block_data['name']}  ·  {detail}")
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
        self.btn_toggle.setText("Réduire")
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
        self.lbl_average.setVisible(bool(ects))
        self.progress.setVisible(bool(ects))
        layout.addWidget(self.progress)

        self.details_widget = QWidget()
        details_layout = QVBoxLayout(self.details_widget)
        details_layout.setContentsMargins(0, 1, 0, 0)
        details_layout.setSpacing(8)
        self.lbl_target_info = QLabel("Saisissez vos notes pour calculer la moyenne du bloc.")
        self.lbl_target_info.setWordWrap(True)
        self.lbl_target_info.setProperty("class", "Muted")
        details_layout.addWidget(self.lbl_target_info)

        validator = QDoubleValidator(0.0, 20.0, 2, self)
        validator.setNotation(QDoubleValidator.StandardNotation)
        validator.setLocale(QLocale())
        for module in self.block_data["modules"]:
            row = QFrame()
            row.setObjectName("ModuleRow")
            row_layout = QBoxLayout(QBoxLayout.TopToBottom, row)
            row_layout.setContentsMargins(13, 9, 13, 9)
            row_layout.setSpacing(10)

            identity = QHBoxLayout()
            name_label = QLabel(module["name"])
            name_label.setObjectName("ModuleName")
            name_label.setWordWrap(True)
            identity.addWidget(name_label, 1)
            weight = module["weight"]
            weight_label = QLabel("Sans coefficient" if weight is None else f"Poids {weight:g} %")
            weight_label.setObjectName("ModuleWeight")
            if weight is None:
                weight_label.setToolTip("Aucun poids indiqué dans la maquette.")
            identity.addWidget(weight_label, alignment=Qt.AlignVCenter)
            row_layout.addLayout(identity, 1)

            grade_input = QLineEdit()
            grade_input.setObjectName("ModuleGrade")
            grade_input.setFixedWidth(78)
            grade_input.setAlignment(Qt.AlignCenter)
            grade_input.setPlaceholderText("Note")
            grade_input.setValidator(validator)
            grade_input.textChanged.connect(self.on_input_changed)
            grade_input.setAccessibleName(f"Note sur 20 · {module['name']}")
            grade_input.setToolTip("Saisissez une note de 0 à 20. Entrée passe au module suivant.")
            if module.get("status_only"):
                grade_input.setEnabled(False)
                grade_input.setPlaceholderText("—")
                grade_input.setToolTip("Suivi par état uniquement.")
            elif weight is None:
                grade_input.setToolTip("Note suivie séparément de la moyenne.")
            status_selector = QComboBox()
            status_selector.setObjectName("ModuleStatus")
            status_selector.setSizeAdjustPolicy(QComboBox.AdjustToContents)
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
            target_label.setObjectName("ModuleTarget")
            target_label.setAlignment(Qt.AlignCenter)
            target_label.setToolTip(
                "Note moyenne à viser dans les modules non notés pour atteindre 10/20."
            )

            fields = QGridLayout()
            fields.setHorizontalSpacing(12)
            fields.setVerticalSpacing(3)
            fields.setAlignment(Qt.AlignLeft)
            for column, (text, widget) in enumerate((
                ("Note /20", grade_input), ("État", status_selector), ("Objectif", target_label),
            )):
                caption = QLabel(text)
                caption.setObjectName("ModuleFieldLabel")
                fields.addWidget(caption, 0, column, Qt.AlignHCenter)
                fields.addWidget(widget, 1, column)
            fields.setColumnMinimumWidth(2, 58)
            row_layout.addLayout(fields)
            details_layout.addWidget(row)
            self.inputs[module["name"]] = {
                "row": row,
                "weight": weight,
                "input": grade_input,
                "status": status_selector,
                "target_lbl": target_label,
            }
            if grade_input.isEnabled():
                input_index = len(self.grade_input_order)
                self.grade_input_order.append(grade_input)
                grade_input.returnPressed.connect(
                    lambda index=input_index: self.focus_next_grade(index)
                )
            self.update_module_status_style(status_selector, MODULE_STATUSES[0])

        total_weight = sum(item["weight"] for _, item in self.weighted_modules())
        if total_weight and total_weight != 100:
            note = QLabel(
                f"Total des coefficients de la maquette : {total_weight:g} %. "
                "La moyenne du bloc est calculée sur ce total."
            )
            note.setProperty("class", "Muted")
            note.setWordWrap(True)
            details_layout.addWidget(note)
        layout.addWidget(self.details_widget)
        self.recalculate()

    def on_module_status_changed(self, selector, status):
        self.update_module_status_style(selector, status)
        self.on_input_changed()

    def focus_grade_for_status(self, module_name, status):
        grade_input = self.inputs[module_name]["input"]
        if status == "En cours" and grade_input.isEnabled() and not grade_input.text().strip():
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
        count = len(self.grade_input_order)
        for offset in range(1, count):
            field = self.grade_input_order[(current_index + offset) % count]
            if field.isVisible():
                field.setFocus()
                field.selectAll()
                return

    def resizeEvent(self, event):
        super().resizeEvent(event)
        direction = QBoxLayout.LeftToRight if self.width() >= 590 else QBoxLayout.TopToBottom
        for item in self.inputs.values():
            item["row"].layout().setDirection(direction)

    def toggle_details(self, expanded):
        self.details_widget.setVisible(expanded)
        self.btn_toggle.setText("Réduire" if expanded else "Détails")

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
        if not self.block_data["ects"]:
            done = sum(item["status"].currentText() == "Terminé" for item in self.inputs.values())
            self.lbl_completion.setText(f"Suivi : {done}/{len(self.inputs)}")
            self.lbl_target_info.setText("Élément suivi séparément de la moyenne et des ECTS.")
            return

        metrics = self.get_block_metrics()
        missing_count = metrics["missing_count"]
        for _, item in self.weighted_modules():
            value = self.parse_grade(item["input"].text())
            if value is None:
                item["input"].setStyleSheet("")
                item["input"].setToolTip(
                    "Aucune note saisie. Entrez une note de 0 à 20."
                )
                item["target_lbl"].setText("—")
            else:
                grade_color = "#ef4444" if value < 8 else "#f59e0b" if value < 10 else "#10b981"
                item["input"].setStyleSheet(
                    f"QLineEdit {{ border: 1px solid {grade_color}; }}"
                )
                item["input"].setToolTip(
                    f"Note saisie : {value:g}/20 · "
                    + ("sous 8/20" if value < 8 else "sous le seuil indicatif de 10/20" if value < 10 else "seuil indicatif atteint")
                )
                item["target_lbl"].setText("Saisi")

        current_avg = metrics["provisional_average"]
        completion = metrics["completion_pct"]
        self.lbl_completion.setText(f"Notes : {completion:.0f} %")
        self.lbl_completion.setToolTip(f"{metrics['entered_count']}/{metrics['module_count']} modules pondérés renseignés")
        if current_avg is None:
            self.lbl_average.setText("— / 20")
            self.progress.setValue(0)
        else:
            self.lbl_average.setText(f"{current_avg:.2f} / 20")
            self.progress.setValue(round(current_avg * 10))
        self.update_badge_style(current_avg)

        needed = metrics["target_needed"]
        dark = (self.settings_provider() or DEFAULT_SETTINGS).get("theme", "Sombre") == "Sombre"
        success_color = "#6ee7b7" if dark else "#047857"
        if needed is not None:
            if needed <= 0:
                target_text, color = "Objectif déjà atteint", success_color
            elif needed > 20:
                target_text = f"Impossible : {needed:.2f}/20 requis"
                color = "#fca5a5" if dark else "#b91c1c"
            else:
                target_text = f"Viser {needed:.2f}/20 sur les modules restants"
                color = "#7dd3fc" if dark else "#0369a1"
            self.lbl_target_info.setText(f"{missing_count} module(s) sans note · {target_text}")
            self.lbl_target_info.setStyleSheet(f"color: {color}; font-weight: 600;")
            for _, item in self.weighted_modules():
                if self.parse_grade(item["input"].text()) is None:
                    item["target_lbl"].setText("—" if needed > 20 else ("0" if needed <= 0 else f"{needed:.2f}"))
        else:
            self.lbl_target_info.setText("Bloc complet : toutes les notes sont renseignées." if missing_count == 0 else "Aucune note renseignée pour le moment.")
            self.lbl_target_info.setStyleSheet(
                f"color: {success_color}; font-weight: 600;" if missing_count == 0 else ""
            )

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

    def weighted_modules(self):
        return (
            (name, item) for name, item in self.inputs.items() if item["weight"] is not None
        )

    def get_block_metrics(self, target=10.0, module_minimum=None):
        weighted_values = [
            (item["weight"], self.parse_grade(item["input"].text()))
            for _, item in self.weighted_modules()
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
        self.blocks_by_semester = {}
        self.module_scrolls = {}
        self.semester_tabs = None
        self.uses_annual_alternance = bool(year_config.get("alternance_ects", 23))
        self.view_mode = "Confortable"
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 14, 16, 14)
        main_layout.setSpacing(14)

        summary_card = QFrame()
        summary_card.setObjectName("Card")
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(15, 12, 15, 12)
        top_line = QHBoxLayout()
        self.lbl_complete_avg = QLabel("Moyenne éléments complets : — / 20")
        self.lbl_complete_avg.setWordWrap(True)
        self.lbl_complete_avg.setStyleSheet("font-size: 14px; font-weight: 700;")
        self.lbl_status = QLabel("En attente de notes")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet("font-weight: 700; color: #94a3b8;")
        top_line.addWidget(self.lbl_complete_avg, 1)
        top_line.addWidget(self.lbl_status)
        summary_layout.addLayout(top_line)
        self.lbl_ects_info = QLabel("ECTS évalués : 0 · ECTS acquis estimés : 0 · Complétude : 0 %")
        self.lbl_ects_info.setWordWrap(True)
        self.lbl_ects_info.setProperty("class", "Muted")
        summary_layout.addWidget(self.lbl_ects_info)
        main_layout.addWidget(summary_card)
        self.lbl_complete_avg.setToolTip(
            "Moyenne calculée à partir des blocs entièrement notés et de l'alternance notée."
            if self.uses_annual_alternance else
            "Moyenne calculée à partir des blocs entièrement notés des deux semestres."
        )
        self.lbl_ects_info.setToolTip(
            "Les ECTS évalués et acquis sont estimatifs et ne remplacent pas la validation officielle."
        )

        general_card = QFrame()
        general_card.setObjectName("Card")
        general_layout = QHBoxLayout(general_card)
        general_layout.setContentsMargins(15, 10, 15, 10)
        general_layout.setSpacing(12)
        self.lbl_alternance = QLabel(
            "<b>Alternance (/20)</b>" if self.uses_annual_alternance
            else "<b>Ancienne note d'alternance</b>"
        )
        general_layout.addWidget(self.lbl_alternance)
        self.inp_alternance = QLineEdit()
        self.inp_alternance.setFixedWidth(90)
        self.inp_alternance.setAlignment(Qt.AlignCenter)
        self.inp_alternance.setPlaceholderText("—")
        alt_validator = QDoubleValidator(0.0, 20.0, 2, self)
        alt_validator.setLocale(QLocale())
        self.inp_alternance.setValidator(alt_validator)
        self.inp_alternance.textChanged.connect(self.on_internal_changed)
        general_layout.addWidget(self.inp_alternance)
        if not self.uses_annual_alternance:
            self.inp_alternance.setReadOnly(True)
            self.inp_alternance.setToolTip(
                "Note issue de l'ancienne maquette, conservée hors de la moyenne. "
                "Les nouvelles notes se saisissent dans le bloc Apprentissage du semestre."
            )
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

        for block_data in self.year_config["blocks"]:
            block = BlockCardWidget(
                block_data, self.on_internal_changed, self.settings_provider
            )
            self.block_widgets.append(block)
            self.blocks_by_semester.setdefault(block_data.get("semester"), []).append(block)

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
        if None not in self.blocks_by_semester:
            self.semester_tabs = QTabWidget()
            self.semester_tabs.setObjectName("SemesterTabs")
            self.semester_tabs.setAccessibleName("Semestres de la troisième année")
            main_layout.addWidget(self.semester_tabs, 1)
        for index, semester in enumerate(self.blocks_by_semester, start=1):
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            self.module_scrolls[semester] = scroll
            if self.semester_tabs is None:
                main_layout.addWidget(scroll, 1)
            else:
                self.semester_tabs.addTab(scroll, f"Semestre {index} · S{semester}")
        if self.semester_tabs is not None:
            self.semester_tabs.currentChanged.connect(self.apply_module_filters)
        self.set_view_mode(self.view_mode)
        self.update_year_summary()

    def set_view_mode(self, mode):
        self.view_mode = mode
        grid_mode = mode == "Grille (2 colonnes)"
        card_mode = "Confortable" if grid_mode else mode
        for semester, blocks in self.blocks_by_semester.items():
            new_container = QWidget()
            new_container.setObjectName("ModuleList")
            new_layout = QGridLayout(new_container) if grid_mode else QVBoxLayout(new_container)
            new_layout.setContentsMargins(1, 5, 8, 4)
            new_layout.setSpacing(14)
            for index, block in enumerate(blocks):
                block.setParent(new_container)
                block.set_view_mode(card_mode)
                if grid_mode:
                    new_layout.addWidget(block, index // 2, index % 2, Qt.AlignTop)
                else:
                    new_layout.addWidget(block)
            if grid_mode:
                new_layout.setRowStretch((len(blocks) + 1) // 2, 1)
            else:
                new_layout.addStretch(1)
            self.module_scrolls[semester].setWidget(new_container)
        self.apply_module_filters()

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
        active_semester = None
        if self.semester_tabs is not None:
            active_scroll = self.semester_tabs.currentWidget()
            active_semester = next(
                (semester for semester, scroll in self.module_scrolls.items() if scroll is active_scroll),
                None,
            )
        for block in self.block_widgets:
            block_matches = 0
            in_active_semester = block.block_data.get("semester") == active_semester
            for module_name, item in block.inputs.items():
                total_modules += in_active_semester
                grade_entered = bool(item["input"].text().strip())
                matches = (
                    query in module_name.casefold()
                    and (
                        selected_status == "all"
                        or item["status"].currentText() == selected_status
                        or (selected_status == "no_grade" and not grade_entered)
                    )
                )
                item["row"].setVisible(matches)
                if matches:
                    visible_modules += in_active_semester
                    block_matches += 1
            block.setVisible(block_matches > 0)
        if hasattr(self, "lbl_module_count"):
            self.lbl_module_count.setText(
                f"{visible_modules}/{total_modules} modules"
            )

    def update_year_summary(self):
        show_alternance = self.uses_annual_alternance or bool(self.inp_alternance.text().strip())
        self.lbl_alternance.setVisible(show_alternance)
        self.inp_alternance.setVisible(show_alternance)
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
        complete = metrics["complete_average"]
        if complete is None:
            self.lbl_complete_avg.setText("Moyenne éléments complets : — / 20")
        else:
            self.lbl_complete_avg.setText(f"Moyenne éléments complets : {complete:.2f} / 20")

        total_blocks = len(metrics["blocks"])
        complete_blocks = metrics["complete_blocks"]
        failing_complete = metrics["complete_blocks_below_threshold"] + (1 if metrics["alternance_grade"] is not None and metrics["alternance_grade"] < float(settings.get("validation_threshold", 10.0)) else 0)
        self.lbl_ects_info.setText(
            f"ECTS évalués : {metrics['ects_evaluated']:.0f} · "
            f"ECTS acquis estimés : {metrics['ects_acquired_estimated']:.0f} · "
            f"Blocs complets : {complete_blocks}/{total_blocks} · "
            f"Complétude : {metrics['completion_pct']:.0f} %"
        )
        if metrics["ects_evaluated"] <= 0:
            self.lbl_status.setText("Aucun bloc complet")
            self.lbl_status.setStyleSheet("color: #94a3b8; font-weight: 700;")
        elif failing_complete:
            self.lbl_status.setText(f"{failing_complete} élément(s) complet(s) ne satisfaisant pas les critères indicatifs")
            self.lbl_status.setStyleSheet("color: #ef4444; font-weight: 700;")
        elif complete_blocks < total_blocks or (
            self.uses_annual_alternance and metrics["alternance_grade"] is None
        ):
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
            ects = float(block.block_data["ects"])
            if not ects:
                continue
            block_metrics = block.get_block_metrics(target=threshold, module_minimum=module_minimum)
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
        alt = BlockCardWidget.parse_grade(self.inp_alternance.text()) if alt_ects else None
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
            name = block.block_data["name"]
            legacy_name = block.block_data.get("legacy_name")
            block.import_data(block_data.get(name, block_data.get(legacy_name, {})))
        self.update_year_summary()
