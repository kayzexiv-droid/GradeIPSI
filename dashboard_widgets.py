import math

from PySide6.QtCore import Qt, QPointF, QRectF, QLocale

from PySide6.QtGui import QBrush, QColor, QDoubleValidator, QFont, QPainter, QPen, QPolygonF

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QBoxLayout, QGridLayout, QLabel, QLineEdit, QFrame, QScrollArea, QPushButton, QComboBox, QDoubleSpinBox, QSizePolicy, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView

from app_data import CURRICULUM_DATA, DEFAULT_SETTINGS, MODULE_STATUSES, calculate_weighted_metrics

from grade_widgets import KpiTile, BlockCardWidget


class RadarChartWidget(QWidget):
    """Graphique araignée dessiné nativement avec QPainter (sans dépendance externe)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.labels = []
        self.values = []
        self.accent = QColor("#3b82f6")
        self.text_color = QColor("#e2e8f0")
        self.grid_color = QColor("#475569")
        self.setMinimumSize(420, 350)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_chart_data(self, labels, values, settings):
        self.labels = list(labels)
        self.values = list(values)
        self.accent = QColor(settings.get("accent", "#3b82f6"))
        if settings.get("theme", "Sombre") == "Sombre":
            self.text_color = QColor("#e2e8f0")
            self.grid_color = QColor("#475569")
        else:
            self.text_color = QColor("#334155")
            self.grid_color = QColor("#cbd5e1")
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), Qt.transparent)
        if len(self.labels) < 3 or len(self.values) != len(self.labels):
            painter.setPen(self.text_color)
            painter.drawText(self.rect(), Qt.AlignCenter, "Ajoutez des notes à au moins 3 blocs\npour afficher le graphique araignée.")
            return

        width = self.width()
        height = self.height()
        center = QPointF(width / 2, height / 2 + 3)
        radius = max(70.0, min(width * 0.31, height * 0.34))
        count = len(self.labels)
        angles = [-math.pi / 2 + (2 * math.pi * i / count) for i in range(count)]

        painter.setPen(QPen(self.grid_color, 1))
        painter.setBrush(Qt.NoBrush)
        for level in (0.25, 0.50, 0.75, 1.0):
            points = [QPointF(center.x() + radius * level * math.cos(a), center.y() + radius * level * math.sin(a)) for a in angles]
            painter.drawPolygon(QPolygonF(points))
        painter.setPen(QPen(self.grid_color, 1))
        for angle in angles:
            end = QPointF(center.x() + radius * math.cos(angle), center.y() + radius * math.sin(angle))
            painter.drawLine(center, end)

        painter.setPen(self.text_color)
        painter.setFont(QFont(self.font().family(), max(8, self.font().pointSize() - 1)))
        for index, (label, angle) in enumerate(zip(self.labels, angles)):
            label_radius = radius + 20
            x = center.x() + label_radius * math.cos(angle)
            y = center.y() + label_radius * math.sin(angle)
            short = label if len(label) <= 23 else label[:20].rstrip() + "…"
            rect = QRectF(x - 64, y - 17, 128, 34)
            painter.drawText(rect, Qt.AlignCenter | Qt.TextWordWrap, short)

        polygon_points = []
        for angle, value in zip(angles, self.values):
            bounded = max(0.0, min(20.0, float(value))) / 20.0
            polygon_points.append(QPointF(center.x() + radius * bounded * math.cos(angle), center.y() + radius * bounded * math.sin(angle)))
        fill = QColor(self.accent)
        fill.setAlpha(65)
        painter.setBrush(QBrush(fill))
        painter.setPen(QPen(self.accent, 2.5))
        painter.drawPolygon(QPolygonF(polygon_points))
        painter.setBrush(QBrush(self.accent))
        for point in polygon_points:
            painter.drawEllipse(point, 4, 4)

        painter.setPen(self.text_color)
        painter.setFont(QFont(self.font().family(), 9, QFont.Bold))
        painter.drawText(QRectF(center.x() - 35, center.y() - 12, 70, 24), Qt.AlignCenter, "/20")

class YearBlockBarsWidget(QWidget):
    """Comparaison lisible des moyennes et de la couverture par bloc."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows = []
        self.accent = QColor("#3b82f6")
        self.track_color = QColor("#334155")
        self.text_color = QColor("#e2e8f0")
        self.muted_color = QColor("#94a3b8")
        self.setMinimumWidth(240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

    def set_chart_data(self, rows, settings):
        self.rows = list(rows)
        self.accent = QColor(settings.get("accent", "#3b82f6"))
        if settings.get("theme", "Sombre") == "Sombre":
            self.track_color = QColor("#334155")
            self.text_color = QColor("#e2e8f0")
            self.muted_color = QColor("#94a3b8")
        else:
            self.track_color = QColor("#e2e8f0")
            self.text_color = QColor("#1e293b")
            self.muted_color = QColor("#64748b")
        self.setMinimumHeight(max(120, len(self.rows) * 55 + 22))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), Qt.transparent)
        if not self.rows:
            painter.setPen(self.muted_color)
            painter.drawText(self.rect(), Qt.AlignCenter, "Aucun bloc dans cette année.")
            return

        left = 12
        right = 58
        available_width = max(1, self.width() - left - right)
        painter.setFont(QFont(self.font().family(), max(8, self.font().pointSize())))
        for index, row in enumerate(self.rows):
            top = 8 + index * 55
            name = row["name"]
            average = row["provisional_average"]
            completion = max(0.0, min(100.0, float(row["completion_pct"])))
            painter.setPen(self.text_color)
            painter.drawText(QRectF(left, top, available_width, 17), Qt.AlignLeft | Qt.AlignVCenter, name)
            painter.setPen(self.muted_color)
            average_text = "— / 20" if average is None else f"{average:.2f} / 20"
            painter.drawText(QRectF(self.width() - right, top, right - 8, 17), Qt.AlignRight | Qt.AlignVCenter, average_text)

            bar_top = top + 21
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(self.track_color))
            painter.drawRoundedRect(QRectF(left, bar_top, available_width, 10), 5, 5)
            if average is not None:
                score_width = available_width * max(0.0, min(20.0, float(average))) / 20.0
                painter.setBrush(QBrush(self.accent))
                painter.drawRoundedRect(QRectF(left, bar_top, score_width, 10), 5, 5)

            coverage_top = bar_top + 13
            painter.setBrush(QBrush(self.track_color))
            painter.drawRoundedRect(QRectF(left, coverage_top, available_width, 4), 2, 2)
            if completion:
                painter.setBrush(QBrush(self.muted_color))
                painter.drawRoundedRect(
                    QRectF(left, coverage_top, available_width * completion / 100.0, 4), 2, 2
                )

class YearRecapWidget(QWidget):
    """Vue annuelle graphique avec tuiles KPI et détail par bloc."""
    def __init__(self, year_tabs, settings_provider):
        super().__init__()
        self.year_tabs = year_tabs
        self.settings_provider = settings_provider
        self.block_rows = []
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Récapitulatif annuel")
        self.title = title
        title.setWordWrap(True)
        title.setStyleSheet("font-size: 22px; font-weight: 800;")
        subtitle = QLabel("Comparez les blocs, les ECTS évalués et la progression sur 20.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #94a3b8;")
        title_box = QVBoxLayout()
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box, 1)
        layout.addLayout(header)

        kpi_layout = QGridLayout()
        kpi_layout.setHorizontalSpacing(10)
        kpi_layout.setVerticalSpacing(10)
        self.kpi_average = KpiTile("Moyenne provisoire", "—", "notes disponibles")
        self.kpi_complete_average = KpiTile("Moyenne éléments complets", "—", "blocs complets + alternance notée")
        self.kpi_completion = KpiTile("Couverture des notes", "0 %", "pondérée par les ECTS")
        self.kpi_ects = KpiTile("ECTS évalués", "0", "blocs complets + alternance notée")
        self.kpi_acquired = KpiTile("ECTS acquis estimés", "0", "seuil indicatif configurable")
        self.kpi_toeic = KpiTile("TOEIC", "—", "objectif configurable")
        recap_tiles = (self.kpi_average, self.kpi_complete_average, self.kpi_completion,
                       self.kpi_ects, self.kpi_acquired, self.kpi_toeic)
        self.kpi_layout = kpi_layout
        self.recap_tiles = recap_tiles
        for index, tile in enumerate(recap_tiles):
            kpi_layout.addWidget(tile, index // 3, index % 3)
        self.kpi_average.setToolTip(
            "Moyenne provisoire basée sur les notes saisies, pondérées selon la couverture des modules."
        )
        self.kpi_complete_average.setToolTip(
            "Ne compte que les blocs intégralement notés et l'alternance lorsqu'elle est renseignée."
        )
        self.kpi_completion.setToolTip(
            "Part des ECTS configurés couverte par les notes saisies. Ce n'est pas un taux de réussite."
        )
        self.kpi_ects.setToolTip(
            "ECTS des blocs complètement notés et de l'alternance lorsqu'elle est notée."
        )
        self.kpi_acquired.setToolTip(
            "Estimation indicative basée sur le seuil des paramètres, sans valeur de validation officielle."
        )
        layout.addLayout(kpi_layout)

        content = QHBoxLayout()
        self.content_layout = content
        radar_card = QFrame()
        radar_card.setObjectName("Card")
        radar_layout = QVBoxLayout(radar_card)
        radar_heading = QLabel("Moyenne et couverture par bloc")
        radar_heading.setWordWrap(True)
        radar_heading.setStyleSheet("font-weight: 700; font-size: 14px;")
        radar_layout.addWidget(radar_heading)
        legend = QLabel("Barre bleue : moyenne /20 · barre fine : couverture des notes")
        legend.setWordWrap(True)
        legend.setProperty("class", "Muted")
        radar_layout.addWidget(legend)
        self.block_bars = YearBlockBarsWidget()
        radar_layout.addWidget(self.block_bars, 1)
        content.addWidget(radar_card, 3)

        breakdown_card = QFrame()
        breakdown_card.setObjectName("Card")
        breakdown_layout = QVBoxLayout(breakdown_card)
        breakdown_layout.setContentsMargins(14, 12, 14, 12)
        modules_header = QHBoxLayout()
        modules_header.addWidget(QLabel("<b>Détails des modules</b>"), 1)
        modules_header.addWidget(QLabel("Trier par :"))
        self.module_sort_selector = QComboBox()
        self.module_sort_selector.addItem("État", "status")
        self.module_sort_selector.addItem("Note croissante", "grade_asc")
        self.module_sort_selector.addItem("Note décroissante", "grade_desc")
        self.module_sort_selector.currentIndexChanged.connect(self._refresh_module_table)
        modules_header.addWidget(self.module_sort_selector)
        breakdown_layout.addLayout(modules_header)
        self.module_table_count = QLabel()
        self.module_table_count.setProperty("class", "Muted")
        breakdown_layout.addWidget(self.module_table_count)
        self.module_table = QTableWidget(0, 4)
        self.module_table.setHorizontalHeaderLabels(["Module", "Bloc", "État", "Note /20"])
        self.module_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.module_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.module_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.module_table.setAlternatingRowColors(True)
        self.module_table.verticalHeader().setVisible(False)
        self.module_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.module_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.module_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.module_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        breakdown_layout.addWidget(self.module_table, 1)
        content.addWidget(breakdown_card, 2)
        layout.addLayout(content, 1)
        self.scroll.setWidget(content_widget)
        page_layout.addWidget(self.scroll)
        self._update_content_direction()
        self._update_kpi_columns()
        self.refresh()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_content_direction()
        self._update_kpi_columns()

    def _update_kpi_columns(self):
        if not hasattr(self, "kpi_layout"):
            return
        columns = 2 if self.width() < 900 else 3
        while self.kpi_layout.count():
            self.kpi_layout.takeAt(0)
        for index, tile in enumerate(self.recap_tiles):
            self.kpi_layout.addWidget(tile, index // columns, index % columns)

    def _update_content_direction(self):
        if not hasattr(self, "content_layout"):
            return
        direction = QBoxLayout.TopToBottom if self.width() < 1050 else QBoxLayout.LeftToRight
        if self.content_layout.direction() != direction:
            self.content_layout.setDirection(direction)

    def refresh(self, *_):
        if not self.year_tabs:
            return
        selected_year = (self.settings_provider() or DEFAULT_SETTINGS).get(
            "dashboard_year", next(iter(self.year_tabs), "")
        )
        year_name = (
            selected_year
            if isinstance(selected_year, str) and selected_year in self.year_tabs
            else next(iter(self.year_tabs), "")
        )
        self.title.setText(f"Récapitulatif annuel · {year_name}")
        tab = self.year_tabs.get(year_name)
        if tab is None:
            return
        metrics = tab.get_year_metrics()
        provisional = metrics["provisional_average"]
        complete_average = metrics["complete_average"]
        if provisional is None:
            self.kpi_average.set_values("—", "Aucune note évaluée")
        else:
            self.kpi_average.set_values(f"{provisional:.2f}/20", "moyenne provisoire")
        self.kpi_complete_average.set_values("—" if complete_average is None else f"{complete_average:.2f}/20",
                                             "aucun bloc complet" if complete_average is None else "éléments complètement renseignés uniquement")
        self.kpi_completion.set_values(
            f"{metrics['completion_pct']:.0f} %",
            f"{metrics['blocks_with_any_grade']}/{len(tab.block_widgets)} blocs avec notes"
        )
        self.kpi_ects.set_values(f"{metrics['ects_evaluated']:.0f}", "ECTS de blocs complets + alternance notée")
        self.kpi_acquired.set_values(f"{metrics['ects_acquired_estimated']:.0f}",
                                     f"seuil indicatif : {float(self.settings_provider().get('validation_threshold', 10.0)):g}/20")
        toeic_target = int(self.settings_provider().get("toeic_target", 785))
        toeic = tab.inp_toeic.text().strip()
        if toeic:
            try:
                score = int(toeic)
                self.kpi_toeic.set_values(str(score), "objectif atteint ✓" if score >= toeic_target else f"{max(0, toeic_target - score)} points à gagner")
            except ValueError:
                self.kpi_toeic.set_values("—", "score non valide")
        else:
            self.kpi_toeic.set_values("—", f"objectif : {toeic_target} points")

        self.block_bars.set_chart_data(metrics["blocks"], self.settings_provider())
        self._refresh_module_table()

    def _refresh_module_table(self, *_):
        settings = self.settings_provider() or DEFAULT_SETTINGS
        selected_year = settings.get("dashboard_year", next(iter(self.year_tabs), ""))
        tab = self.year_tabs.get(selected_year) if isinstance(selected_year, str) else None
        rows = []
        if tab is not None:
            for block in tab.block_widgets:
                for module_name, item in block.inputs.items():
                    rows.append({
                        "module": module_name,
                        "block": block.block_data["name"],
                        "status": item["status"].currentText(),
                        "grade": BlockCardWidget.parse_grade(item["input"].text()),
                    })

        sort_mode = self.module_sort_selector.currentData()
        status_order = {status: index for index, status in enumerate(MODULE_STATUSES)}
        if sort_mode == "grade_asc":
            rows.sort(key=lambda row: (
                row["grade"] is None,
                row["grade"] if row["grade"] is not None else 0.0,
                row["module"].casefold(),
            ))
        elif sort_mode == "grade_desc":
            rows.sort(key=lambda row: (
                row["grade"] is None,
                -(row["grade"] if row["grade"] is not None else 0.0),
                row["module"].casefold(),
            ))
        else:
            rows.sort(key=lambda row: (
                status_order.get(row["status"], len(status_order)),
                row["module"].casefold(),
            ))

        self.module_table.setSortingEnabled(False)
        self.module_table.setRowCount(len(rows))
        dark = settings.get("theme", "Sombre") == "Sombre"
        status_colors = {
            "Pas commencé": ("#334155", "#e2e8f0") if dark else ("#e2e8f0", "#334155"),
            "En cours": ("#1e3a8a", "#dbeafe") if dark else ("#dbeafe", "#1e3a8a"),
            "Terminé": ("#064e3b", "#d1fae5") if dark else ("#dcfce7", "#065f46"),
        }
        for row_index, row in enumerate(rows):
            values = (
                row["module"],
                row["block"],
                row["status"],
                "—" if row["grade"] is None else f"{row['grade']:.2f}",
            )
            for column, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                if column == 2:
                    background, foreground = status_colors.get(
                        row["status"], status_colors["Pas commencé"]
                    )
                    table_item.setBackground(QColor(background))
                    table_item.setForeground(QColor(foreground))
                elif column == 3:
                    table_item.setTextAlignment(Qt.AlignCenter)
                    if row["grade"] is None:
                        table_item.setForeground(QColor("#94a3b8"))
                    elif row["grade"] < 8:
                        table_item.setForeground(QColor("#ef4444"))
                    elif row["grade"] < 10:
                        table_item.setForeground(QColor("#f59e0b"))
                    else:
                        table_item.setForeground(QColor("#10b981"))
                self.module_table.setItem(row_index, column, table_item)
        self.module_table_count.setText(
            f"{len(rows)} modules · année {tab.year_name}" if tab is not None else "Aucun module"
        )
        self.module_table.resizeRowsToContents()

class YearComparisonChartWidget(QWidget):
    """Compare pour chaque année la moyenne provisoire et celle des éléments complets."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows = []
        self.accent = QColor("#3b82f6")
        self.complete_color = QColor("#10b981")
        self.text_color = QColor("#e2e8f0")
        self.grid_color = QColor("#475569")
        self.setMinimumHeight(235)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_chart_data(self, rows, settings):
        self.rows = list(rows)
        self.accent = QColor(settings.get("accent", "#3b82f6"))
        self.complete_color = QColor("#10b981")
        if settings.get("theme", "Sombre") == "Sombre":
            self.text_color = QColor("#e2e8f0")
            self.grid_color = QColor("#475569")
        else:
            self.text_color = QColor("#334155")
            self.grid_color = QColor("#cbd5e1")
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), Qt.transparent)
        if not self.rows:
            painter.setPen(self.text_color)
            painter.drawText(self.rect(), Qt.AlignCenter, "Les moyennes apparaîtront lorsque des notes seront saisies.")
            return

        left, right, top, bottom = 45, 18, 34, 42
        plot_w = max(1, self.width() - left - right)
        plot_h = max(1, self.height() - top - bottom)
        base_y = top + plot_h
        painter.setFont(QFont(self.font().family(), 8))
        for tick in (0, 5, 10, 15, 20):
            y = base_y - (tick / 20.0) * plot_h
            painter.setPen(QPen(self.grid_color, 1))
            painter.drawLine(left, int(y), left + plot_w, int(y))
            painter.setPen(self.text_color)
            painter.drawText(QRectF(0, y - 9, left - 7, 18), Qt.AlignRight | Qt.AlignVCenter, str(tick))

        legend_y = 7
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self.accent))
        painter.drawRoundedRect(QRectF(left + 2, legend_y + 2, 12, 8), 2, 2)
        painter.setPen(self.text_color)
        painter.drawText(QRectF(left + 19, legend_y - 1, 130, 16), Qt.AlignLeft | Qt.AlignVCenter, "Provisoire")
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self.complete_color))
        painter.drawRoundedRect(QRectF(left + 111, legend_y + 2, 12, 8), 2, 2)
        painter.setPen(self.text_color)
        painter.drawText(QRectF(left + 128, legend_y - 1, 160, 16), Qt.AlignLeft | Qt.AlignVCenter, "Éléments complets")

        group_w = plot_w / max(1, len(self.rows))
        bar_w = min(25.0, max(8.0, group_w * 0.22))
        for index, row in enumerate(self.rows):
            center_x = left + group_w * (index + 0.5)
            values = [(row.get("provisional"), self.accent), (row.get("complete"), self.complete_color)]
            offset = bar_w / 2 + 2
            for shift, (value, color) in zip((-1, 1), values):
                if value is None:
                    continue
                value = max(0.0, min(20.0, float(value)))
                bar_h = value / 20.0 * plot_h
                rect = QRectF(center_x + shift * offset - bar_w / 2, base_y - bar_h, bar_w, bar_h)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(color))
                painter.drawRoundedRect(rect, 3, 3)
                painter.setPen(self.text_color)
                label_rect = QRectF(rect.x() - 11, rect.y() - 19, rect.width() + 22, 16)
                painter.drawText(label_rect, Qt.AlignCenter, f"{value:.1f}")
            painter.setPen(self.text_color)
            year_label = row.get("year", "")
            if len(year_label) > 20:
                year_label = year_label[:17] + "…"
            painter.drawText(QRectF(left + index * group_w, base_y + 6, group_w, 32), Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, year_label)

class StrategyDashboardWidget(QWidget):
    """Tableau de bord de l'année sélectionnée : KPI, comparaisons, carte thermique et priorités."""
    def __init__(self, year_tabs, settings_provider, on_year_changed):
        super().__init__()
        self.year_tabs = year_tabs
        self.settings_provider = settings_provider
        self.on_year_changed = on_year_changed
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        title_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Tableau de bord stratégique")
        title.setWordWrap(True)
        title.setStyleSheet("font-size: 23px; font-weight: 800;")
        subtitle = QLabel("Vision d'ensemble des moyennes, de la complétude et des points à travailler.")
        subtitle.setWordWrap(True)
        subtitle.setProperty("class", "Muted")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        title_row.addLayout(title_box, 1)
        self.year_selector = QComboBox()
        self.year_selector.addItems(list(year_tabs.keys()))
        selected_year = (settings_provider() or DEFAULT_SETTINGS).get(
            "dashboard_year", next(iter(year_tabs), "")
        )
        if not isinstance(selected_year, str) or selected_year not in year_tabs:
            selected_year = next(iter(year_tabs), "")
        self.year_selector.setMinimumWidth(130)
        self.year_selector.setCurrentText(selected_year)
        self.year_selector.currentTextChanged.connect(self.on_year_changed)
        jury_note = QLabel("Les ECTS acquis sont des estimations, pas une décision officielle du jury.")
        jury_note.setWordWrap(True)
        title_row.addWidget(jury_note)
        layout.addLayout(title_row)
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Année en cours :"))
        filter_row.addWidget(self.year_selector)
        filter_row.addStretch(1)
        layout.addLayout(filter_row)

        # Vérifie la cohérence du total ECTS configuré sans réécrire les données
        # du cursus : la maquette peut varier selon la promotion.
        ects_totals = {
            year_name: sum(float(block.get("ects", 0)) for block in config.get("blocks", []))
                       + float(config.get("alternance_ects", 0))
            for year_name, config in CURRICULUM_DATA.items()
        }
        ects_mismatches = [
            f"{year_name} : {total:g} ECTS configurés"
            for year_name, total in ects_totals.items()
            if abs(total - 60.0) > 1e-6
        ]
        self.curriculum_warning = QLabel()
        self.curriculum_warning.setWordWrap(True)
        self.curriculum_warning.setProperty("class", "Muted")
        if ects_mismatches:
            dark = (settings_provider() or DEFAULT_SETTINGS).get("theme", "Sombre") == "Sombre"
            bg = "#78350f" if dark else "#fef3c7"
            fg = "#fef3c7" if dark else "#92400e"
            border = "#f59e0b"
            self.curriculum_warning.setText(
                "⚠️ ECTS à vérifier dans les données du cursus : " + " ; ".join(ects_mismatches)
                + ". Référence usuelle : 60 ECTS par année. Les valeurs d'origine sont conservées ; "
                  "comparez-les à la maquette correspondant à votre promotion avant d'interpréter les ECTS estimés."
            )
            self.curriculum_warning.setStyleSheet(
                f"background-color: {bg}; color: {fg}; border: 1px solid {border}; "
                "border-radius: 8px; padding: 9px 12px; font-weight: 600;"
            )
            layout.addWidget(self.curriculum_warning)
        else:
            self.curriculum_warning.hide()

        kpi_grid = QGridLayout()
        kpi_grid.setHorizontalSpacing(10)
        kpi_grid.setVerticalSpacing(10)
        self.kpi_provisional = KpiTile("Moyenne provisoire de l'année", "—", "notes disponibles, pondérées au prorata de la complétude")
        self.kpi_complete = KpiTile("Moyenne annuelle éléments complets", "—", "blocs complets + alternance notée")
        self.kpi_completion = KpiTile("Complétude des notes", "0 %", "pondération par les ECTS configurés")
        self.kpi_evaluated = KpiTile("ECTS évalués", "0", "blocs complets + alternance notée")
        self.kpi_acquired = KpiTile("ECTS acquis estimés", "0", "seuil indicatif ajustable")
        self.kpi_attention = KpiTile("Blocs à compléter / surveiller", "0", "incomplets ou sous le seuil")
        tiles = (self.kpi_provisional, self.kpi_complete, self.kpi_completion,
                 self.kpi_evaluated, self.kpi_acquired, self.kpi_attention)
        for index, tile in enumerate(tiles):
            kpi_grid.addWidget(tile, index // 3, index % 3)
        layout.addLayout(kpi_grid)

        analysis_row = QHBoxLayout()
        chart_card = QFrame()
        chart_card.setObjectName("Card")
        chart_layout = QVBoxLayout(chart_card)
        chart_layout.setContentsMargins(14, 12, 14, 12)
        chart_layout.addWidget(QLabel("<b>Progression de l'année sélectionnée</b>"))
        self.comparison_chart = YearComparisonChartWidget()
        chart_layout.addWidget(self.comparison_chart, 1)
        analysis_row.addWidget(chart_card, 3)

        priority_card = QFrame()
        priority_card.setObjectName("Card")
        priority_layout = QVBoxLayout(priority_card)
        priority_layout.setContentsMargins(14, 12, 14, 12)
        priority_layout.addWidget(QLabel("<b>Priorités de travail</b>"))
        note = QLabel("Classement indicatif basé sur la moyenne provisoire et les notes manquantes.")
        note.setWordWrap(True)
        note.setProperty("class", "Muted")
        priority_layout.addWidget(note)
        self.priority_scroll = QScrollArea()
        self.priority_scroll.setWidgetResizable(True)
        self.priority_container = QWidget()
        self.priority_layout = QVBoxLayout(self.priority_container)
        self.priority_layout.setContentsMargins(0, 4, 0, 0)
        self.priority_layout.setSpacing(7)
        self.priority_scroll.setWidget(self.priority_container)
        priority_layout.addWidget(self.priority_scroll, 1)
        analysis_row.addWidget(priority_card, 2)
        layout.addLayout(analysis_row, 1)

        heatmap_card = QFrame()
        heatmap_card.setObjectName("Card")
        heatmap_layout = QVBoxLayout(heatmap_card)
        heatmap_layout.setContentsMargins(14, 12, 14, 12)
        heatmap_layout.addWidget(QLabel("<b>Carte thermique des blocs</b>"))
        hint = QLabel("Vert : seuil indicatif atteint sur un bloc complet · orange/rouge : notes faibles ou bloc sous le seuil · gris : notes insuffisantes pour conclure.")
        hint.setWordWrap(True)
        hint.setProperty("class", "Muted")
        heatmap_layout.addWidget(hint)
        self.heatmap = QTableWidget(0, 6)
        self.heatmap.setHorizontalHeaderLabels(["Année", "Bloc", "Moyenne provisoire", "Complétude", "ECTS", "Diagnostic indicatif"])
        self.heatmap.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.heatmap.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.heatmap.setAlternatingRowColors(False)
        self.heatmap.verticalHeader().setVisible(False)
        self.heatmap.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.heatmap.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.heatmap.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.heatmap.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.heatmap.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.heatmap.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.heatmap.setMinimumHeight(260)
        heatmap_layout.addWidget(self.heatmap)
        layout.addWidget(heatmap_card)

        self.scroll.setWidget(content)
        outer.addWidget(self.scroll)
        self.refresh()

    def _clear_priorities(self):
        while self.priority_layout.count():
            item = self.priority_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _theme_cell_colors(self, status):
        dark = self.settings_provider().get("theme", "Sombre") == "Sombre"
        palette = {
            "good": ("#064e3b", "#d1fae5") if dark else ("#dcfce7", "#166534"),
            "bad": ("#7f1d1d", "#fee2e2") if dark else ("#fee2e2", "#991b1b"),
            "warn": ("#78350f", "#fef3c7") if dark else ("#fef3c7", "#92400e"),
            "neutral": ("#334155", "#e2e8f0") if dark else ("#e2e8f0", "#334155"),
        }
        return palette[status]

    def refresh(self):
        settings = self.settings_provider() or DEFAULT_SETTINGS
        # La bannière de cohérence ECTS suit aussi le thème actif.
        if hasattr(self, "curriculum_warning") and self.curriculum_warning.text():
            dark = settings.get("theme", "Sombre") == "Sombre"
            bg = "#78350f" if dark else "#fef3c7"
            fg = "#fef3c7" if dark else "#92400e"
            self.curriculum_warning.setStyleSheet(
                f"background-color: {bg}; color: {fg}; border: 1px solid #f59e0b; "
                "border-radius: 8px; padding: 9px 12px; font-weight: 600;"
            )
        if not self.year_tabs:
            return
        threshold = float(settings.get("validation_threshold", 10.0))
        total_provisional_sum = 0.0
        total_provisional_weight = 0.0
        total_complete_sum = 0.0
        total_complete_ects = 0.0
        total_evaluated_ects = 0.0
        total_acquired_ects = 0.0
        possible_ects = 0.0
        completed_equivalent_ects = 0.0
        watch_count = 0
        priorities = []
        chart_rows = []
        heat_rows = []

        selected_year = self.year_selector.currentText()
        selected_tab = self.year_tabs.get(selected_year)
        if selected_tab is None:
            return
        for year_name, tab in ((selected_year, selected_tab),):
            metrics = tab.get_year_metrics(threshold=threshold)
            total_provisional_sum += metrics["provisional_weighted_sum"]
            total_provisional_weight += metrics["provisional_ects_equivalent"]
            total_complete_sum += metrics["complete_weighted_sum"]
            total_complete_ects += metrics["complete_ects"]
            total_evaluated_ects += metrics["ects_evaluated"]
            total_acquired_ects += metrics["ects_acquired_estimated"]
            possible_ects += metrics["total_possible_ects"]
            completed_equivalent_ects += metrics["completion_pct"] / 100.0 * metrics["total_possible_ects"]
            chart_rows.append({
                "year": year_name,
                "provisional": metrics["provisional_average"],
                "complete": metrics["complete_average"],
            })
            for entry in metrics["blocks"]:
                average = entry["provisional_average"]
                completion = entry["completion_pct"]
                complete_average = entry["complete_average"]
                is_complete = complete_average is not None
                if not is_complete or (complete_average is not None and not entry["validation_pass"]):
                    watch_count += 1
                    if is_complete:
                        score = 1000.0 + max(0.0, threshold - complete_average) * 10
                        if entry["module_minimum_met"] is False and complete_average >= threshold:
                            advice = f"La moyenne atteint {threshold:g}/20, mais au moins un module reste sous la note minimale configurée ({float(settings.get('module_minimum', 6.0)):g}/20). Vérifier que cette règle est bien applicable."
                        else:
                            advice = f"Moyenne complète {complete_average:.2f}/20, mais les critères indicatifs ne sont pas tous atteints. Vérifier les règles officielles de la formation."
                        level = "Priorité haute"
                    elif average is None:
                        score = 600.0 + (100.0 - completion)
                        advice = f"Aucune note disponible · complétude {completion:.0f} %. Commencer par renseigner les résultats connus."
                        level = "À renseigner"
                    elif average < threshold:
                        score = 800.0 + (threshold - average) * 10 + (100.0 - completion) * 0.2
                        advice = f"Moyenne provisoire {average:.2f}/20 · complétude {completion:.0f} %. Revoir les modules faibles et renseigner les notes restantes."
                        level = "Priorité haute"
                    else:
                        score = 300.0 + (100.0 - completion) * 0.2
                        advice = f"Moyenne provisoire {average:.2f}/20, mais le bloc reste incomplet ({completion:.0f} %). Compléter les notes avant de conclure."
                        level = "À compléter"
                    priorities.append((score, year_name, entry["name"], level, advice))

                if is_complete:
                    status = "good" if entry["validation_pass"] else "bad"
                    if entry["validation_pass"]:
                        diagnostic = "Critères indicatifs atteints"
                    elif entry["module_minimum_met"] is False and complete_average >= threshold:
                        diagnostic = "Note minimale par module non atteinte"
                    else:
                        diagnostic = "Sous le seuil indicatif"
                elif average is None:
                    status = "neutral"
                    diagnostic = "À renseigner"
                elif average < threshold:
                    status = "warn"
                    diagnostic = "Moyenne provisoire basse · incomplet"
                else:
                    status = "warn"
                    diagnostic = "Provisoire · notes manquantes"
                heat_rows.append((year_name, entry, status, diagnostic))

        provisional_avg = total_provisional_sum / total_provisional_weight if total_provisional_weight else None
        complete_avg = total_complete_sum / total_complete_ects if total_complete_ects else None
        completion_pct = completed_equivalent_ects / possible_ects * 100.0 if possible_ects else 0.0
        self.kpi_provisional.set_values("—" if provisional_avg is None else f"{provisional_avg:.2f}/20",
                                        "aucune note" if provisional_avg is None else "moyenne provisoire, pondérée par la couverture")
        self.kpi_complete.set_values("—" if complete_avg is None else f"{complete_avg:.2f}/20",
                                     "aucun bloc complet" if complete_avg is None else "éléments complètement renseignés uniquement")
        self.kpi_completion.set_values(f"{completion_pct:.0f} %", "couverture des notes disponibles")
        self.kpi_evaluated.set_values(f"{total_evaluated_ects:.0f}", "ECTS des blocs complets et de l'alternance notée")
        self.kpi_acquired.set_values(f"{total_acquired_ects:.0f}", f"estimation au seuil {threshold:g}/20")
        self.kpi_attention.set_values(str(watch_count), "blocs incomplets ou sous le seuil indicatif")
        self.comparison_chart.set_chart_data(chart_rows, settings)

        self.heatmap.setRowCount(len(heat_rows))
        for row_idx, (year_name, entry, status, diagnostic) in enumerate(heat_rows):
            average = entry["provisional_average"]
            completion = entry["completion_pct"]
            values = [
                year_name,
                entry["name"],
                "—" if average is None else f"{average:.2f}/20",
                f"{completion:.0f} %",
                f"{entry['ects']:.0f}",
                diagnostic,
            ]
            bg, fg = self._theme_cell_colors(status)
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setForeground(QBrush(QColor(fg)))
                if col in (2, 5):
                    item.setBackground(QBrush(QColor(bg)))
                if col in (2, 3, 4):
                    item.setTextAlignment(Qt.AlignCenter)
                self.heatmap.setItem(row_idx, col, item)
        self.heatmap.resizeRowsToContents()

        self._clear_priorities()
        priorities.sort(key=lambda record: record[0], reverse=True)
        for _, year_name, block_name, level, advice in priorities[:8]:
            card = QFrame()
            card.setObjectName("Card")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(9, 7, 9, 7)
            heading = QLabel(f"{level} · {year_name}")
            heading.setStyleSheet("font-weight: 800;")
            block_label = QLabel(block_name)
            block_label.setWordWrap(True)
            body = QLabel(advice)
            body.setWordWrap(True)
            body.setProperty("class", "Muted")
            body.setStyleSheet("font-size: 11px;")
            card_layout.addWidget(heading)
            card_layout.addWidget(block_label)
            card_layout.addWidget(body)
            self.priority_layout.addWidget(card)
        if not priorities:
            self.priority_layout.addWidget(QLabel("Aucune priorité détectée sur les blocs complets et renseignés."))
        self.priority_layout.addStretch(1)

class GradeSimulationWidget(QWidget):
    """Simulateur indépendant : les notes prévisionnelles n'écrivent jamais dans les notes réelles."""
    def __init__(self, year_tabs, settings_provider):
        super().__init__()
        self.year_tabs = year_tabs
        self.settings_provider = settings_provider
        self.scenario_inputs = {}
        self.selected_block = None

        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        content_widget = QWidget()
        outer = QVBoxLayout(content_widget)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(12)
        heading = QLabel("Simulateur de notes prévisionnelles")
        heading.setWordWrap(True)
        heading.setStyleSheet("font-size: 22px; font-weight: 800;")
        intro = QLabel("Testez des notes hypothétiques pour voir leur effet sur le bloc et l'année. Les notes réelles restent inchangées.")
        intro.setWordWrap(True)
        intro.setProperty("class", "Muted")
        intro.setToolTip(
            "La projection annuelle ne retient que les autres blocs complets et notés."
        )
        outer.addWidget(heading)
        outer.addWidget(intro)

        controls = QFrame()
        controls.setObjectName("Card")
        controls_layout = QGridLayout(controls)
        controls_layout.setContentsMargins(14, 10, 14, 10)
        self.lbl_selected_year = QLabel()
        self.lbl_selected_year.setStyleSheet("font-weight: 700;")
        self.block_selector = QComboBox()
        self.block_selector.setMinimumWidth(150)
        self.block_selector.currentIndexChanged.connect(self._load_block)
        self.target_spin = QDoubleSpinBox()
        self.target_spin.setRange(0.0, 20.0)
        self.target_spin.setDecimals(2)
        self.target_spin.setSingleStep(0.5)
        self.target_spin.setValue(10.0)
        self.target_spin.setSuffix(" / 20")
        self.target_spin.valueChanged.connect(self.update_simulation)
        self.year_target_spin = QDoubleSpinBox()
        self.year_target_spin.setRange(0.0, 20.0)
        self.year_target_spin.setDecimals(2)
        self.year_target_spin.setSingleStep(0.5)
        self.year_target_spin.setValue(12.0)
        self.year_target_spin.setSuffix(" / 20")
        self.year_target_spin.valueChanged.connect(self.update_simulation)
        controls_layout.addWidget(self.lbl_selected_year, 0, 0, 1, 2)
        controls_layout.addWidget(QLabel("Bloc :"), 1, 0)
        controls_layout.addWidget(self.block_selector, 1, 1)
        controls_layout.addWidget(QLabel("Objectif bloc :"), 1, 2)
        controls_layout.addWidget(self.target_spin, 1, 3)
        controls_layout.addWidget(QLabel("Objectif annuel :"), 2, 0)
        controls_layout.addWidget(self.year_target_spin, 2, 1)
        controls_layout.setColumnStretch(1, 1)
        controls_layout.setColumnStretch(3, 1)
        outer.addWidget(controls)

        kpi_grid = QGridLayout()
        kpi_grid.setHorizontalSpacing(10)
        kpi_grid.setVerticalSpacing(10)
        self.kpi_actual = KpiTile("Moyenne réelle provisoire", "—", "notes déjà enregistrées")
        self.kpi_scenario = KpiTile("Moyenne simulée", "—", "notes de scénario renseignées")
        self.kpi_needed = KpiTile("Note moyenne requise", "—", "pour l'objectif sélectionné")
        self.kpi_year = KpiTile("Projection annuelle", "—", "si le bloc simulé est complet")
        self.kpi_year_needed = KpiTile("Note requise · objectif annuel", "—", "scénario sur le bloc sélectionné")
        self.simulation_tiles = (
            self.kpi_actual, self.kpi_scenario, self.kpi_needed, self.kpi_year,
            self.kpi_year_needed,
        )
        self.kpi_layout = kpi_grid
        for index, tile in enumerate(self.simulation_tiles):
            kpi_grid.addWidget(tile, index // 3, index % 3)
        self.kpi_actual.setToolTip("Moyenne réelle provisoire du bloc sélectionné.")
        self.kpi_scenario.setToolTip("Moyenne basée uniquement sur les notes réelles ou simulées renseignées.")
        self.kpi_needed.setToolTip("Moyenne à viser sur chaque note manquante pour atteindre l'objectif du bloc.")
        self.kpi_year.setToolTip("Projection indicative basée sur le bloc simulé et les autres blocs complets.")
        self.kpi_year_needed.setToolTip("Projection de la note moyenne nécessaire pour atteindre l'objectif annuel.")
        outer.addLayout(kpi_grid)

        table_card = QFrame()
        table_card.setObjectName("Card")
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(14, 12, 14, 12)
        table_heading = QLabel("<b>État, notes réelles et scénario</b>")
        table_heading.setWordWrap(True)
        table_layout.addWidget(table_heading)
        self.grade_table = QTableWidget(0, 5)
        self.grade_table.setHorizontalHeaderLabels(
            ["Module", "Poids", "État", "Note réelle", "Note simulée /20"]
        )
        self.grade_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.grade_table.verticalHeader().setVisible(False)
        self.grade_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for col in (1, 2, 3, 4):
            self.grade_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.grade_table.setMinimumHeight(220)
        table_layout.addWidget(self.grade_table, 1)
        outer.addWidget(table_card, 1)

        button_row = QHBoxLayout()
        self.reset_scenario_button = QPushButton("Réinitialiser le scénario avec les notes réelles")
        self.reset_scenario_button.clicked.connect(self._load_block)
        button_row.addWidget(self.reset_scenario_button)
        button_row.addStretch(1)
        outer.addLayout(button_row)
        self.simulation_note = QLabel(
            "Projection indicative : les autres blocs incomplets sont exclus. "
            "Le simulateur ne modifie jamais les notes réelles."
        )
        self.simulation_note.setWordWrap(True)
        self.simulation_note.setProperty("class", "Muted")
        self.simulation_note.setToolTip(
            "Les projections ne remplacent pas le règlement des études ni la décision du jury."
        )
        outer.addWidget(self.simulation_note)
        self.scroll.setWidget(content_widget)
        page_layout.addWidget(self.scroll)
        self._load_blocks()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not hasattr(self, "simulation_tiles"):
            return
        columns = 2 if self.width() < 900 else 3
        while self.kpi_layout.count():
            self.kpi_layout.takeAt(0)
        for index, tile in enumerate(self.simulation_tiles):
            self.kpi_layout.addWidget(tile, index // columns, index % columns)

    def _current_tab(self):
        selected_year = (self.settings_provider() or DEFAULT_SETTINGS).get(
            "dashboard_year", next(iter(self.year_tabs), "")
        )
        return self.year_tabs.get(selected_year) if isinstance(selected_year, str) else None

    def _load_blocks(self, *_):
        tab = self._current_tab()
        self.lbl_selected_year.setText(
            f"Année simulée : {tab.year_name}" if tab is not None else "Aucune année sélectionnée"
        )
        self.block_selector.blockSignals(True)
        self.block_selector.clear()
        if tab is not None:
            self.block_selector.addItems([block.block_data["name"] for block in tab.block_widgets])
        self.block_selector.blockSignals(False)
        self._load_block()

    def _load_block(self, *_):
        tab = self._current_tab()
        if tab is None:
            return
        name = self.block_selector.currentText()
        self.selected_block = next((block for block in tab.block_widgets if block.block_data["name"] == name), None)
        self.scenario_inputs = {}
        self.grade_table.setRowCount(0)
        if self.selected_block is None:
            self.update_simulation()
            return

        self.grade_table.setRowCount(len(self.selected_block.inputs))
        self.scenario_input_order = []
        for row, (module_name, item) in enumerate(self.selected_block.inputs.items()):
            self.grade_table.setItem(row, 0, QTableWidgetItem(module_name))
            self.grade_table.setItem(row, 1, QTableWidgetItem(f"{item['weight']:g} %"))
            self.grade_table.setItem(row, 2, QTableWidgetItem(item["status"].currentText()))
            actual = item["input"].text().strip()
            actual_value = BlockCardWidget.parse_grade(actual)
            actual_item = QTableWidgetItem("—" if actual_value is None else f"{actual_value:g}")
            actual_item.setTextAlignment(Qt.AlignCenter)
            self.grade_table.setItem(row, 3, actual_item)
            scenario = QLineEdit()
            scenario.setAlignment(Qt.AlignCenter)
            scenario.setPlaceholderText("À prévoir")
            scenario.setFixedWidth(95)
            scenario.setAccessibleName(f"Note simulée · {module_name}")
            validator = QDoubleValidator(0.0, 20.0, 2, scenario)
            validator.setNotation(QDoubleValidator.StandardNotation)
            validator.setLocale(QLocale())
            scenario.setValidator(validator)
            scenario.setText(actual)
            scenario.textChanged.connect(self.update_simulation)
            self.grade_table.setCellWidget(row, 4, scenario)
            self.scenario_inputs[module_name] = {"weight": item["weight"], "input": scenario}
            self.scenario_input_order.append(scenario)
            scenario.returnPressed.connect(
                lambda index=row: self.focus_next_scenario(index)
            )
        self.grade_table.resizeRowsToContents()
        self.update_simulation()

    def refresh_from_data(self):
        """Met à jour les références aux notes réelles sans écraser le scénario courant."""
        if self.selected_block is None:
            self._load_blocks()
            return
        for row, (module_name, item) in enumerate(self.selected_block.inputs.items()):
            self.grade_table.setItem(row, 2, QTableWidgetItem(item["status"].currentText()))
            grade = BlockCardWidget.parse_grade(item["input"].text())
            actual_item = QTableWidgetItem("—" if grade is None else f"{grade:g}")
            actual_item.setTextAlignment(Qt.AlignCenter)
            self.grade_table.setItem(row, 3, actual_item)
        self.update_simulation()

    def focus_next_scenario(self, current_index):
        if not self.scenario_input_order:
            return
        next_index = (current_index + 1) % len(self.scenario_input_order)
        self.scenario_input_order[next_index].setFocus()
        self.scenario_input_order[next_index].selectAll()

    def refresh_for_year(self):
        self._load_blocks()

    def update_simulation(self, *_):
        tab = self._current_tab()
        block = self.selected_block
        if tab is None or block is None:
            self.kpi_actual.set_values("—", "aucun bloc sélectionné")
            self.kpi_scenario.set_values("—", "aucun scénario")
            self.kpi_needed.set_values("—", "aucun scénario")
            self.kpi_year.set_values("—", "aucun scénario")
            self.kpi_year_needed.set_values("—", "aucun scénario")
            return
        actual_metrics = block.get_block_metrics(target=self.target_spin.value())
        actual_avg = actual_metrics["provisional_average"]
        self.kpi_actual.set_values("—" if actual_avg is None else f"{actual_avg:.2f}/20",
                                   f"complétude réelle : {actual_metrics['completion_pct']:.0f} %")

        scenario_values = []
        for module_name, entry in self.scenario_inputs.items():
            value = BlockCardWidget.parse_grade(entry["input"].text())
            scenario_values.append((entry["weight"], value))
        target = self.target_spin.value()
        settings = self.settings_provider() or DEFAULT_SETTINGS
        module_minimum = (
            float(settings.get("module_minimum", 6.0))
            if bool(settings.get("enforce_module_minimum", False)) else None
        )
        simulated = calculate_weighted_metrics(
            scenario_values, target=target, module_minimum=module_minimum
        )
        sim_avg = simulated["provisional_average"]
        sim_complete_avg = simulated["complete_average"]
        self.kpi_scenario.set_values("—" if sim_avg is None else f"{sim_avg:.2f}/20",
                                     f"complétude du scénario : {simulated['completion_pct']:.0f} %")
        needed = simulated["target_needed"]
        if simulated["missing_count"] == 0:
            if sim_complete_avg is None:
                needed_text, needed_subtitle = "—", "aucune note simulée valide"
            elif sim_complete_avg >= target and simulated["validation_pass"]:
                needed_text, needed_subtitle = "Objectif atteint", f"{sim_complete_avg:.2f}/20 ≥ {target:.2f}/20"
            elif sim_complete_avg >= target and module_minimum is not None:
                needed_text = "Moyenne atteinte"
                needed_subtitle = (
                    f"Au moins un module est sous {module_minimum:g}/20 ; la règle complémentaire n'est pas satisfaite."
                )
            else:
                needed_text, needed_subtitle = "Non atteint", f"{sim_complete_avg:.2f}/20 < {target:.2f}/20"
        elif needed is None:
            needed_text, needed_subtitle = "—", "poids restant indisponible"
        elif needed <= 0:
            if module_minimum is None:
                needed_text, needed_subtitle = "Déjà atteint", "les notes saisies suffisent à l'objectif"
            else:
                needed_text, needed_subtitle = "Moyenne suffisante", f"vérifier aussi chaque module ≥ {module_minimum:g}/20"
        elif needed > 20:
            needed_text, needed_subtitle = "Impossible", f"il faudrait {needed:.2f}/20 sur les modules restants"
        else:
            needed_text = f"{needed:.2f}/20"
            needed_subtitle = "moyenne à viser sur chaque module restant"
            if module_minimum is not None:
                needed_subtitle += f" ; chaque module doit aussi atteindre {module_minimum:g}/20"
        self.kpi_needed.set_values(needed_text, needed_subtitle)

        metrics = tab.get_year_metrics()
        projected_sum = 0.0
        projected_ects = 0.0
        for other_block in tab.block_widgets:
            ects = float(other_block.block_data["ects"])
            if other_block is block:
                avg = sim_complete_avg
            else:
                avg = other_block.get_complete_average()
            if avg is not None:
                projected_sum += avg * ects
                projected_ects += ects
        alt = metrics["alternance_grade"]
        if alt is not None:
            projected_sum += alt * metrics["alternance_ects"]
            projected_ects += metrics["alternance_ects"]
        projected_avg = projected_sum / projected_ects if projected_ects else None
        if sim_complete_avg is None:
            self.kpi_year.set_values("—", "renseigner toutes les notes simulées du bloc")
        else:
            self.kpi_year.set_values("—" if projected_avg is None else f"{projected_avg:.2f}/20",
                                     f"sur {projected_ects:.0f} ECTS · blocs complets uniquement")

        # Note moyenne nécessaire dans les modules simulés encore vides pour atteindre
        # l'objectif annuel, en supposant que les autres blocs incomplets restent exclus.
        annual_target = self.year_target_spin.value()
        missing_weight = simulated["missing_weight"]
        total_weight = simulated["total_weight"]
        block_ects = float(block.block_data["ects"])
        base_sum = 0.0
        base_ects = block_ects
        for other_block in tab.block_widgets:
            if other_block is block:
                continue
            other_avg = other_block.get_complete_average()
            if other_avg is not None:
                other_ects = float(other_block.block_data["ects"])
                base_sum += other_avg * other_ects
                base_ects += other_ects
        if alt is not None:
            base_sum += alt * metrics["alternance_ects"]
            base_ects += metrics["alternance_ects"]

        if missing_weight <= 0 or total_weight <= 0:
            if projected_avg is None:
                annual_needed_text, annual_needed_subtitle = "—", "aucun ensemble évalué"
            elif projected_avg >= annual_target:
                annual_needed_text, annual_needed_subtitle = "Objectif atteint", f"projection {projected_avg:.2f}/20 ≥ {annual_target:.2f}/20"
            else:
                annual_needed_text, annual_needed_subtitle = "Non atteint", f"projection {projected_avg:.2f}/20 < {annual_target:.2f}/20"
        else:
            known_block_contribution = simulated["weighted_sum"] / total_weight * block_ects
            missing_contribution_factor = missing_weight / total_weight * block_ects
            annual_needed = (annual_target * base_ects - base_sum - known_block_contribution) / missing_contribution_factor if missing_contribution_factor > 0 else None
            if annual_needed is None:
                annual_needed_text, annual_needed_subtitle = "—", "calcul indisponible"
            elif annual_needed <= 0:
                annual_needed_text, annual_needed_subtitle = "Déjà atteint", "les notes saisies suffisent à l'objectif annuel"
            elif annual_needed > 20:
                annual_needed_text, annual_needed_subtitle = "Impossible", f"il faudrait {annual_needed:.2f}/20 sur les modules restants"
            else:
                annual_needed_text, annual_needed_subtitle = f"{annual_needed:.2f}/20", f"moyenne sur les modules restants pour viser {annual_target:.2f}/20 à l'année"
        if module_minimum is not None:
            annual_needed_subtitle += f" · vérifier aussi chaque module ≥ {module_minimum:g}/20"
        self.kpi_year_needed.set_values(annual_needed_text, annual_needed_subtitle)
