"""Highscores module for displaying lap times."""
import os
import csv
from typing import List, Tuple, Optional
from datetime import datetime

from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt

from gui.ui.modules.base_module import BaseModule


class HighscoresModule(BaseModule):
    """Module for displaying highscores and lap times."""

    MODULE_NAME = "Highscores"
    MODULE_ICON = "🏆"

    def _setup_ui(self) -> None:
        # Header & Stats Container
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        header_title = QLabel("🏆 Hall of Fame")
        header_title.setStyleSheet("font-size: 24px; font-weight: bold; color: #ffd700;")
        header_layout.addWidget(header_title)
        
        header_layout.addStretch()
        
        # Stats Label (moved to top)
        self._stats_label = QLabel("Total Laps: 0 | Best Record: -")
        self._stats_label.setStyleSheet("font-size: 14px; color: #aaaaaa; font-weight: bold;")
        header_layout.addWidget(self._stats_label)
        
        self.add_widget(header_widget)
        
        # Filter controls
        filter_widget = QWidget()
        filter_layout = QHBoxLayout(filter_widget)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        
        # Environment Filter
        self._env_combo = QComboBox()
        self._env_combo.addItems([
            "donkey-mountain-track-v0",
            "donkey-warehouse-v0",
            "donkey-generated-roads-v0",
            "donkey-avc-sparkfun-v0",
            "donkey-generated-track-v0",
        ])
        self._env_combo.currentTextChanged.connect(self._load_data)
        
        filter_layout.addWidget(QLabel("Environment:"))
        filter_layout.addWidget(self._env_combo)
        
        filter_layout.addSpacing(20)
        
        # Run Filter
        self._run_combo = QComboBox()
        self._run_combo.addItem("All Runs")
        self._run_combo.currentTextChanged.connect(self._update_display)
        
        filter_layout.addWidget(QLabel("Run:"))
        filter_layout.addWidget(self._run_combo)
        filter_layout.setStretchFactor(self._run_combo, 1)
        
        filter_layout.addStretch()
        
        refresh_btn = QPushButton("🔄 Refresh Scores")
        refresh_btn.clicked.connect(self._load_data)
        filter_layout.addWidget(refresh_btn)
        
        self.add_widget(filter_widget)
        
        # Best Laps Table
        self.add_widget(QLabel("🚀 Best Laps (Top 50)"))
        self._best_table = QTableWidget()
        self._best_table.setColumnCount(4)
        self._best_table.setHorizontalHeaderLabels(["Rank", "Time (s)", "Run / Experiment", "Date"])
        
        # Column Resizing Logic
        header = self._best_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed) # Rank
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed) # Time
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch) # Run
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents) # Date
        
        self._best_table.setColumnWidth(0, 60)  # Rank Width
        self._best_table.setColumnWidth(1, 100) # Time Width
        
        self._best_table.verticalHeader().setVisible(False)
        self._best_table.setAlternatingRowColors(True)
        self._best_table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e1e;
                alternate-background-color: #2d2d2d;
                gridline-color: #3d3d3d;
            }
            QTableWidget::item {
                padding: 5px;
            }
        """)
        # Ensure plenty of height for top 10+ without scrolling
        self._best_table.setMinimumHeight(600)
        self.add_widget(self._best_table)
        
        self.add_stretch()
        
        # Internal data storage
        self._cached_laps = []

    def on_show(self) -> None:
        self._load_data()

    def _load_data(self) -> None:
        """Scan logs for highscores.csv, cache data, and populate run filter."""
        env_name = self._env_combo.currentText()
        repo_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        )
        logs_dir = os.path.join(repo_root, "logs")
        
        self._cached_laps = []
        found_runs = set()
        
        # Walk through logs to find highscores.csv
        for root, dirs, files in os.walk(logs_dir):
            if "highscores.csv" in files:
                folder_name = os.path.basename(root)
                folder_matches_env = env_name in folder_name
                
                csv_path = os.path.join(root, "highscores.csv")
                try:
                    with open(csv_path, 'r') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            csv_run_id = row.get("run_id", "")
                            
                            # Filter: Must match env (either by folder or by run_id)
                            run_id_matches_env = env_name in csv_run_id
                            
                            if not (folder_matches_env or run_id_matches_env):
                                continue
                            
                            # Determine Run Name
                            if not csv_run_id or csv_run_id == "unknown":
                                display_run = folder_name if folder_matches_env else "Unknown"
                                if "_" in folder_name:
                                    parts = folder_name.split("_")
                                    if parts[-1].isdigit():
                                        display_run = f"Exp {parts[-1]}"
                            else:
                                display_run = csv_run_id
                                # We no longer collapse "Training_..." or "enjoy_..." to generic names
                                # to allow filtering by specific runs.

                            found_runs.add(display_run)

                            try:
                                time_val = float(row["lap_time"])
                                timestamp = row["timestamp"]
                                self._cached_laps.append({
                                    "time": time_val,
                                    "run": display_run,
                                    "date": timestamp
                                })
                            except ValueError:
                                pass
                except Exception as e:
                    print(f"Error reading {csv_path}: {e}")

        # Update Run Filter
        current_run_filter = self._run_combo.currentText()
        self._run_combo.blockSignals(True)
        self._run_combo.clear()
        self._run_combo.addItem("All Runs")
        
        sorted_runs = sorted(list(found_runs))
        self._run_combo.addItems(sorted_runs)
        
        # Restore selection if possible, otherwise default to All
        index = self._run_combo.findText(current_run_filter)
        if index >= 0:
            self._run_combo.setCurrentIndex(index)
        else:
            self._run_combo.setCurrentIndex(0)
            
        self._run_combo.blockSignals(False)
        
        # Finally update the table view
        self._update_display()

    def _update_display(self) -> None:
        """Filter cached laps and update the table."""
        selected_run = self._run_combo.currentText()
        
        filtered_laps = []
        if selected_run == "All Runs":
            filtered_laps = self._cached_laps
        else:
            filtered_laps = [lap for lap in self._cached_laps if lap["run"] == selected_run]
        
        # Sort by time
        filtered_laps.sort(key=lambda x: x["time"])
        
        # Populate Table
        top_n = min(len(filtered_laps), 50) # Show top 50 matches
        self._best_table.setRowCount(top_n)
        
        for i in range(top_n):
            lap = filtered_laps[i]
            
            rank_item = QTableWidgetItem(f"#{i+1}")
            rank_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            time_item = QTableWidgetItem(f"{lap['time']:.3f}")
            time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # Highlight #1
            time_item.setForeground(Qt.GlobalColor.green if i == 0 else Qt.GlobalColor.white)
            
            run_item = QTableWidgetItem(lap['run'])
            run_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # Add tooltip in case run name is long
            run_item.setToolTip(lap['run'])
            
            date_item = QTableWidgetItem(lap['date'])
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            self._best_table.setItem(i, 0, rank_item)
            self._best_table.setItem(i, 1, time_item)
            self._best_table.setItem(i, 2, run_item)
            self._best_table.setItem(i, 3, date_item)
            
        # Update Stats
        total_laps = len(filtered_laps)
        best_time = f"{filtered_laps[0]['time']:.3f} s" if filtered_laps else "-"
        self._stats_label.setText(f"Total Completed Laps: {total_laps} | Best Record: {best_time}")
