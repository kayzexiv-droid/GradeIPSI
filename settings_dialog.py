from copy import deepcopy

from PySide6.QtGui import QColor, QFont

from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QComboBox, QDialog, QFormLayout, QFontComboBox, QSpinBox, QDoubleSpinBox, QDialogButtonBox, QColorDialog, QCheckBox


class SettingsDialog(QDialog):
    """Dialogue des réglages visuels : thème, accent, police et taille."""
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Paramètres d'affichage")
        self.setModal(True)
        self.settings = deepcopy(settings)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Sombre", "Clair"])
        self.theme_combo.setCurrentText(self.settings.get("theme", "Sombre"))
        form.addRow("Thème", self.theme_combo)

        self.accent_button = QPushButton("Choisir la couleur…")
        self.accent_button.clicked.connect(self.choose_accent)
        self._refresh_accent_button()
        form.addRow("Couleur d'accentuation", self.accent_button)

        self.font_combo = QFontComboBox()
        self.font_combo.setCurrentFont(QFont(self.settings.get("font_family", "Segoe UI")))
        form.addRow("Police", self.font_combo)

        self.font_size = QSpinBox()
        self.font_size.setRange(9, 18)
        self.font_size.setValue(int(self.settings.get("font_size", 10)))
        self.font_size.setSuffix(" px")
        form.addRow("Taille du texte", self.font_size)

        self.ui_scale = QSpinBox()
        self.ui_scale.setRange(70, 150)
        self.ui_scale.setSingleStep(5)
        self.ui_scale.setValue(int(self.settings.get("ui_scale", 100)))
        self.ui_scale.setSuffix(" %")
        form.addRow("Mise à l'échelle de l'interface", self.ui_scale)

        self.validation_threshold = QDoubleSpinBox()
        self.validation_threshold.setRange(0.0, 20.0)
        self.validation_threshold.setDecimals(1)
        self.validation_threshold.setSingleStep(0.5)
        self.validation_threshold.setSuffix(" / 20")
        self.validation_threshold.setValue(float(self.settings.get("validation_threshold", 10.0)))
        form.addRow("Seuil indicatif bloc / alternance", self.validation_threshold)

        self.module_minimum_enabled = QCheckBox("Appliquer aussi une note minimale à chaque module")
        self.module_minimum_enabled.setChecked(bool(self.settings.get("enforce_module_minimum", False)))
        form.addRow("Règle complémentaire", self.module_minimum_enabled)
        self.module_minimum = QDoubleSpinBox()
        self.module_minimum.setRange(0.0, 20.0)
        self.module_minimum.setDecimals(1)
        self.module_minimum.setSingleStep(0.5)
        self.module_minimum.setSuffix(" / 20")
        self.module_minimum.setValue(float(self.settings.get("module_minimum", 6.0)))
        self.module_minimum.setEnabled(self.module_minimum_enabled.isChecked())
        self.module_minimum_enabled.toggled.connect(self.module_minimum.setEnabled)
        form.addRow("Note minimale par module", self.module_minimum)

        self.toeic_target = QSpinBox()
        self.toeic_target.setRange(0, 990)
        self.toeic_target.setValue(int(self.settings.get("toeic_target", 785)))
        self.toeic_target.setSuffix(" points")
        form.addRow("Objectif TOEIC", self.toeic_target)

        policy_note = QLabel("Les seuils servent à estimer les ECTS. Activez la note minimale par module uniquement si elle figure dans votre règlement de formation. Ces paramètres ne remplacent pas le règlement officiel ni la décision du jury.")
        policy_note.setWordWrap(True)
        policy_note.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(policy_note)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def choose_accent(self):
        color = QColorDialog.getColor(QColor(self.settings.get("accent", "#3b82f6")), self, "Couleur d'accentuation")
        if color.isValid():
            self.settings["accent"] = color.name()
            self._refresh_accent_button()

    def _refresh_accent_button(self):
        color = self.settings.get("accent", "#3b82f6")
        self.accent_button.setStyleSheet(f"background-color: {color}; color: white; font-weight: 700; padding: 8px;")
        self.accent_button.setText(f"{color.upper()} · Modifier")

    def get_settings(self):
        self.settings["theme"] = self.theme_combo.currentText()
        self.settings["font_family"] = self.font_combo.currentFont().family()
        self.settings["font_size"] = self.font_size.value()
        self.settings["ui_scale"] = self.ui_scale.value()
        self.settings["validation_threshold"] = self.validation_threshold.value()
        self.settings["enforce_module_minimum"] = self.module_minimum_enabled.isChecked()
        self.settings["module_minimum"] = self.module_minimum.value()
        self.settings["toeic_target"] = self.toeic_target.value()
        return self.settings
