"""
Custom functionality dialogs for YTSage application.
Contains dialogs for custom commands, cookies, time ranges, and other special features.
"""

import threading
from pathlib import Path
from typing import TYPE_CHECKING, cast

from PySide6.QtCore import Q_ARG, QMetaObject, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..ytsage_smooth_tab_widget import SmoothTabWidget
from ...core.ytsage_utils import update_auto_update_settings
from ...utils.ytsage_config_manager import ConfigManager
from ...utils.ytsage_localization import LocalizationManager, _
from ...utils.ytsage_logger import logger
from .ytsage_dialogs_updater import UpdaterTabWidget

if TYPE_CHECKING:
    from ..ytsage_gui_main import YTSageApp  # only for type hints (no runtime import)




class CustomOptionsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._parent: YTSageApp = cast("YTSageApp", self.parent())  # cast will help with auto complete and type hint checking.
        self.setWindowTitle(_("dialogs.custom_options"))
        self.setMinimumSize(550, 400)  # Made even shorter
        layout = QVBoxLayout(self)

        # Create tab widget to organize content
        self.tab_widget = SmoothTabWidget()
        layout.addWidget(self.tab_widget)

        # === Cookies Tab ===
        cookies_tab = QWidget()

        cookies_layout = QVBoxLayout(cookies_tab)

        # Help text
        help_text = QLabel(_('cookies.help_text'))
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: #607d8b; padding: 10px;")
        cookies_layout.addWidget(help_text)

        # Cookie source selection
        cookie_source_group = QGroupBox(_('cookies.cookie_source'))
        cookie_source_layout = QVBoxLayout(cookie_source_group)

        # Radio buttons for cookie source
        self.cookie_browser_radio = QRadioButton(_('cookies.extract_from_browser') + f" ({_('cookies.recommended')})")
        self.cookie_browser_radio.setChecked(True)
        self.cookie_browser_radio.toggled.connect(self.on_cookie_source_changed)
        cookie_source_layout.addWidget(self.cookie_browser_radio)

        self.cookie_file_radio = QRadioButton(_('cookies.use_cookie_file'))
        self.cookie_file_radio.toggled.connect(self.on_cookie_source_changed)
        cookie_source_layout.addWidget(self.cookie_file_radio)

        cookies_layout.addWidget(cookie_source_group)

        # Cookie file section
        self.cookie_file_group = QGroupBox(_('cookies.cookie_file'))
        file_layout = QVBoxLayout(self.cookie_file_group)

        # File path input and browse button
        path_layout = QHBoxLayout()
        self.cookie_path_input = QLineEdit()
        self.cookie_path_input.setPlaceholderText(_('cookies.cookie_file_placeholder'))
        if hasattr(self._parent, "cookie_file_path") and self._parent.cookie_file_path:
            # Convert Path to string properly and validate
            cookie_path_str = str(self._parent.cookie_file_path)
            # Only set if it looks like a valid path (more than just a drive letter)
            if len(cookie_path_str) > 3 and not cookie_path_str.endswith(":"):
                self.cookie_path_input.setText(cookie_path_str)
        path_layout.addWidget(self.cookie_path_input)

        self.browse_button = QPushButton(_('buttons.browse'))
        self.browse_button.clicked.connect(self.browse_cookie_file)
        path_layout.addWidget(self.browse_button)
        file_layout.addLayout(path_layout)

        cookies_layout.addWidget(self.cookie_file_group)

        # Browser selection section
        self.cookie_browser_group = QGroupBox(_('cookies.browser_selection'))
        browser_layout = QVBoxLayout(self.cookie_browser_group)

        browser_help = QLabel(_('cookies.browser_help'))
        browser_help.setWordWrap(True)
        browser_help.setStyleSheet("color: #607d8b; font-size: 11px;")
        browser_layout.addWidget(browser_help)

        browser_select_layout = QHBoxLayout()
        browser_select_layout.addWidget(QLabel(_('cookies.browser_label')))

        self.browser_combo = QComboBox()
        self.browser_combo.addItems(["chrome", "firefox", "safari", "edge", "opera", "brave", "chromium", "vivaldi"])
        browser_select_layout.addWidget(self.browser_combo)
        browser_layout.addLayout(browser_select_layout)

        # Optional profile field
        profile_layout = QHBoxLayout()
        profile_layout.addWidget(QLabel(_('cookies.profile_label')))
        self.profile_input = QLineEdit()
        self.profile_input.setPlaceholderText(_('cookies.profile_placeholder'))
        profile_layout.addWidget(self.profile_input)
        browser_layout.addLayout(profile_layout)

        cookies_layout.addWidget(self.cookie_browser_group)

        # Initially show browser group (recommended default) and hide file group
        self.cookie_file_group.setVisible(False)

        # Remember Cookie Settings Checkbox
        self.remember_cb = QCheckBox(_("cookies.remember_settings"))
        remember_val = ConfigManager.get("cookie_remember")
        self.remember_cb.setChecked(True if remember_val is None else remember_val)  # Default to True
        self.remember_cb.setStyleSheet(
            """
            QCheckBox {
                color: #1a1a2e;
                padding: 10px 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 9px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #78909c;
                background: #ffffff;
                border-radius: 9px;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #0984e3;
                background: #0984e3;
                border-radius: 9px;
            }
            QCheckBox:disabled { color: #78909c; }
            }
            """
        )
        # Connect state change directly to config save to make it work immediately without Apply button dependency if needed
        self.remember_cb.toggled.connect(lambda checked: ConfigManager.set("cookie_remember", checked))
        cookies_layout.addWidget(self.remember_cb)
        self.cookie_browser_group.setVisible(True)

        # Apply button and status indicator
        apply_layout = QHBoxLayout()
        
        # Status indicator for active cookies
        self.cookies_active_status = QLabel()
        self._update_cookies_active_status()
        apply_layout.addWidget(self.cookies_active_status)
        
        apply_layout.addStretch()
        
        # Apply button
        self.apply_cookies_btn = QPushButton(_('buttons.apply'))
        self.apply_cookies_btn.clicked.connect(self.apply_cookies)
        self.apply_cookies_btn.setStyleSheet(
            """
            QPushButton {
                padding: 8px 20px;
                background-color: #0984e3;
                border: none;
                border-radius: 4px;
                color: white;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #0773c5;
            }
        """
        )
        apply_layout.addWidget(self.apply_cookies_btn)
        
        cookies_layout.addLayout(apply_layout)

        cookies_layout.addStretch()


        # === Proxy Tab ===
        proxy_tab = QWidget()
        proxy_layout = QVBoxLayout(proxy_tab)

        # Help text
        proxy_help_text = QLabel(_('proxy.help_text'))
        proxy_help_text.setWordWrap(True)
        proxy_help_text.setStyleSheet("color: #607d8b; padding: 10px;")
        proxy_layout.addWidget(proxy_help_text)

        # Main Proxy section
        main_proxy_group = QGroupBox(_('proxy.main_proxy'))
        main_proxy_layout = QVBoxLayout(main_proxy_group)

        main_proxy_help = QLabel(_('proxy.main_proxy_help'))
        main_proxy_help.setWordWrap(True)
        main_proxy_help.setStyleSheet("color: #607d8b; font-size: 11px;")
        main_proxy_layout.addWidget(main_proxy_help)

        # Main proxy input
        main_proxy_input_layout = QHBoxLayout()
        main_proxy_input_layout.addWidget(QLabel(_('proxy.proxy_url_label')))
        self.proxy_url_input = QLineEdit()
        self.proxy_url_input.setPlaceholderText(_('proxy.proxy_url_placeholder'))
        self.proxy_url_input.textChanged.connect(self.validate_proxy_inputs)
        main_proxy_input_layout.addWidget(self.proxy_url_input)
        main_proxy_layout.addLayout(main_proxy_input_layout)

        # Example text
        example_label = QLabel(_('proxy.proxy_examples'))
        example_label.setStyleSheet("color: #546e7a; font-size: 10px; font-style: italic;")
        main_proxy_layout.addWidget(example_label)

        proxy_layout.addWidget(main_proxy_group)

        # Geo-verification Proxy section
        geo_proxy_group = QGroupBox(_('proxy.geo_proxy'))
        geo_proxy_layout = QVBoxLayout(geo_proxy_group)

        geo_proxy_help = QLabel(_('proxy.geo_proxy_help'))
        geo_proxy_help.setWordWrap(True)
        geo_proxy_help.setStyleSheet("color: #607d8b; font-size: 11px;")
        geo_proxy_layout.addWidget(geo_proxy_help)

        # Geo proxy input
        geo_proxy_input_layout = QHBoxLayout()
        geo_proxy_input_layout.addWidget(QLabel(_('proxy.geo_proxy_url_label')))
        self.geo_proxy_url_input = QLineEdit()
        self.geo_proxy_url_input.setPlaceholderText(_('proxy.geo_proxy_url_placeholder'))
        self.geo_proxy_url_input.textChanged.connect(self.validate_proxy_inputs)
        geo_proxy_input_layout.addWidget(self.geo_proxy_url_input)
        geo_proxy_layout.addLayout(geo_proxy_input_layout)

        proxy_layout.addWidget(geo_proxy_group)

        # Proxy status indicator
        self.proxy_status = QLabel("")
        self.proxy_status.setStyleSheet("color: #607d8b; font-style: italic;")
        proxy_layout.addWidget(self.proxy_status)

        # Clear buttons
        clear_layout = QHBoxLayout()
        clear_main_proxy_btn = QPushButton(_('proxy.clear_main_proxy'))
        clear_main_proxy_btn.clicked.connect(lambda: self.proxy_url_input.clear())
        clear_main_proxy_btn.setStyleSheet(
            """
            QPushButton {
                padding: 6px 12px;
                background-color: #444444;
                border: none;
                border-radius: 4px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """
        )
        clear_layout.addWidget(clear_main_proxy_btn)

        clear_geo_proxy_btn = QPushButton(_('proxy.clear_geo_proxy'))
        clear_geo_proxy_btn.clicked.connect(lambda: self.geo_proxy_url_input.clear())
        clear_geo_proxy_btn.setStyleSheet(
            """
            QPushButton {
                padding: 6px 12px;
                background-color: #444444;
                border: none;
                border-radius: 4px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """
        )
        clear_layout.addWidget(clear_geo_proxy_btn)

        clear_layout.addStretch()
        proxy_layout.addLayout(clear_layout)

        proxy_layout.addStretch()

        # === Language Tab ===
        language_tab = QWidget()
        language_layout = QVBoxLayout(language_tab)

        # Help text
        language_help_text = QLabel(_("language.select_language"))
        language_help_text.setWordWrap(True)
        language_help_text.setStyleSheet("color: #1a1a2e; font-size: 14px; font-weight: bold; padding: 10px;")
        language_layout.addWidget(language_help_text)

        # Current language info
        current_lang = ConfigManager.get("language") or "en"
        available_languages = LocalizationManager.get_available_languages()
        current_lang_display = available_languages.get(current_lang, current_lang.upper())
        
        current_lang_label = QLabel(_("language.current_language", language=current_lang_display))
        current_lang_label.setWordWrap(True)
        current_lang_label.setStyleSheet("color: #607d8b; padding: 10px;")
        language_layout.addWidget(current_lang_label)

        # Language selection group
        language_group = QGroupBox(_("language.select_language"))
        language_group_layout = QVBoxLayout(language_group)

        # Language selection combo box
        language_select_layout = QHBoxLayout()
        language_select_layout.addWidget(QLabel(_("language.select_language") + ":"))

        self.language_combo = QComboBox()
        
        # Populate language combo with available languages
        for lang_code, display_name in available_languages.items():
            self.language_combo.addItem(display_name, lang_code)
        
        # Set current selection
        current_index = self.language_combo.findData(current_lang)
        if current_index >= 0:
            self.language_combo.setCurrentIndex(current_index)

        # Connect language change event
        self.language_combo.currentIndexChanged.connect(self.on_language_changed)
        
        language_select_layout.addWidget(self.language_combo)
        language_group_layout.addLayout(language_select_layout)

        language_layout.addWidget(language_group)

        # Restart notice
        self.restart_notice = QLabel(_("language.restart_required"))
        self.restart_notice.setWordWrap(True)
        self.restart_notice.setStyleSheet(
            "color: #ffaa00; font-style: italic; padding: 10px; "
            "background-color: #d0e4fa; border-radius: 6px; margin: 10px;"
        )
        self.restart_notice.setVisible(False)  # Initially hidden
        language_layout.addWidget(self.restart_notice)

        language_layout.addStretch()

        # === LLM Tab ===
        llm_tab = QWidget()
        llm_layout = QVBoxLayout(llm_tab)

        # Help text
        llm_help = QLabel(_("llm.help_text"))
        llm_help.setWordWrap(True)
        llm_help.setStyleSheet("color: #455a64; padding: 10px;")
        llm_layout.addWidget(llm_help)

        # Mode selection
        mode_group = QGroupBox(_("llm.mode_title"))
        mode_layout = QVBoxLayout(mode_group)
        self.llm_mode_llm = QRadioButton(_("llm.mode_llm"))
        self.llm_mode_rule = QRadioButton(_("llm.mode_rule"))
        saved_mode = ConfigManager.get("llm_mode") or "rule"
        if saved_mode == "llm":
            self.llm_mode_llm.setChecked(True)
        else:
            self.llm_mode_rule.setChecked(True)
        mode_layout.addWidget(self.llm_mode_llm)
        mode_layout.addWidget(self.llm_mode_rule)
        llm_layout.addWidget(mode_group)

        # API settings group
        api_group = QGroupBox(_("llm.api_title"))
        api_layout = QVBoxLayout(api_group)

        # API URL
        api_url_layout = QHBoxLayout()
        api_url_layout.addWidget(QLabel(_("llm.api_url")))
        self.llm_url_input = QLineEdit()
        self.llm_url_input.setText(ConfigManager.get("llm_url") or "http://localhost:8000")
        self.llm_url_input.setPlaceholderText(_("llm.api_url_placeholder"))
        api_url_layout.addWidget(self.llm_url_input)
        api_layout.addLayout(api_url_layout)

        # API Key
        api_key_layout = QHBoxLayout()
        api_key_layout.addWidget(QLabel(_("llm.api_key")))
        self.llm_api_key_input = QLineEdit()
        self.llm_api_key_input.setText(ConfigManager.get("llm_api_key") or "")
        self.llm_api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.llm_api_key_input.setPlaceholderText(_("llm.api_key_placeholder"))
        api_key_layout.addWidget(self.llm_api_key_input)
        api_layout.addLayout(api_key_layout)

        # Model
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel(_("llm.model")))
        self.llm_model_input = QLineEdit()
        self.llm_model_input.setText(ConfigManager.get("llm_model") or "gpt-4.1")
        model_layout.addWidget(self.llm_model_input)
        api_layout.addLayout(model_layout)

        # Temperature + Max Workers row
        params_row1 = QHBoxLayout()
        params_row1.addWidget(QLabel(_("llm.temperature")))
        self.llm_temperature_input = QLineEdit()
        self.llm_temperature_input.setText(str(ConfigManager.get("llm_temperature") or 0.1))
        self.llm_temperature_input.setMaximumWidth(80)
        params_row1.addWidget(self.llm_temperature_input)
        params_row1.addStretch()
        params_row1.addWidget(QLabel(_("llm.max_workers")))
        self.llm_max_workers_input = QLineEdit()
        self.llm_max_workers_input.setText(str(ConfigManager.get("llm_max_workers") or 10))
        self.llm_max_workers_input.setMaximumWidth(80)
        params_row1.addWidget(self.llm_max_workers_input)
        api_layout.addLayout(params_row1)

        # Timeout + Max Retries row
        params_row2 = QHBoxLayout()
        params_row2.addWidget(QLabel(_("llm.timeout")))
        self.llm_timeout_input = QLineEdit()
        self.llm_timeout_input.setText(str(ConfigManager.get("llm_timeout") or 60))
        self.llm_timeout_input.setMaximumWidth(80)
        params_row2.addWidget(self.llm_timeout_input)
        params_row2.addStretch()
        params_row2.addWidget(QLabel(_("llm.max_retries")))
        self.llm_max_retries_input = QLineEdit()
        self.llm_max_retries_input.setText(str(ConfigManager.get("llm_max_retries") or 3))
        self.llm_max_retries_input.setMaximumWidth(80)
        params_row2.addWidget(self.llm_max_retries_input)
        api_layout.addLayout(params_row2)

        llm_layout.addWidget(api_group)

        # Segmentation parameters group
        seg_group = QGroupBox(_("llm.seg_title"))
        seg_layout = QVBoxLayout(seg_group)

        seg_params = QHBoxLayout()
        seg_params.addWidget(QLabel(_("llm.soft_limit")))
        self.llm_soft_limit = QLineEdit()
        self.llm_soft_limit.setText(str(ConfigManager.get("llm_segmentation_soft_limit") or 70))
        self.llm_soft_limit.setMaximumWidth(60)
        seg_params.addWidget(self.llm_soft_limit)
        seg_params.addStretch()
        seg_params.addWidget(QLabel(_("llm.hard_limit")))
        self.llm_hard_limit = QLineEdit()
        self.llm_hard_limit.setText(str(ConfigManager.get("llm_segmentation_hard_limit") or 85))
        self.llm_hard_limit.setMaximumWidth(60)
        seg_params.addWidget(self.llm_hard_limit)
        seg_params.addStretch()
        seg_params.addWidget(QLabel(_("llm.target_cps")))
        self.llm_target_cps = QLineEdit()
        self.llm_target_cps.setText(str(ConfigManager.get("llm_segmentation_target_cps") or 14))
        self.llm_target_cps.setMaximumWidth(60)
        seg_params.addWidget(self.llm_target_cps)
        seg_params.addStretch()
        seg_params.addWidget(QLabel(_("llm.limit_cps")))
        self.llm_limit_cps = QLineEdit()
        self.llm_limit_cps.setText(str(ConfigManager.get("llm_segmentation_limit_cps") or 18))
        self.llm_limit_cps.setMaximumWidth(60)
        seg_params.addWidget(self.llm_limit_cps)
        seg_layout.addLayout(seg_params)

        llm_layout.addWidget(seg_group)
        llm_layout.addStretch()

        # === Updater Tab ===
        self.updater_tab = UpdaterTabWidget(self)

        # Add tabs to the tab widget
        self.tab_widget.addTab(cookies_tab, _("tabs.cookies"))
        self.tab_widget.addTab(proxy_tab, _("tabs.proxy"))
        self.tab_widget.addTab(llm_tab, _("llm.tab_title"))
        self.tab_widget.addTab(self.updater_tab, _("tabs.updater"))
        self.tab_widget.addTab(language_tab, _("tabs.language"))

        # Dialog buttons
        button_box = QDialogButtonBox()
        ok_button = button_box.addButton(_("buttons.ok"), QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_button = button_box.addButton(_("buttons.cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Apply global styles (Daylight theme)
        self.setStyleSheet(
            """
            QDialog {
                background-color: #f5f6fa;
            }
            QFrame#tabContent {
                border: 1px solid #b0bec5;
                background-color: #f5f6fa;
            }
            QTabBar::tab {
                background-color: #ffffff;
                color: #546e7a;
                padding: 8px 12px;
                border: 1px solid #b0bec5;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #0984e3;
                color: white;
            }
            QTabBar::tab:hover:!selected {
                background-color: #d0e4fa;
            }
            QLabel {
                color: #1a1a2e;
            }
            QGroupBox {
                border: 1px solid #b0bec5;
                border-radius: 4px;
                margin-top: 1.5ex;
                color: #1a1a2e;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
            }
            QRadioButton {
                color: #1a1a2e;
                padding: 5px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
                border-radius: 9px;
            }
            QRadioButton::indicator:unchecked {
                border: 2px solid #78909c;
                background: #ffffff;
                border-radius: 9px;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #0984e3;
                background: #0984e3;
                border-radius: 9px;
            }
            QComboBox {
                padding: 8px;
                border: 2px solid #78909c;
                border-radius: 4px;
                background-color: #ffffff;
                color: #2d3436;
                min-width: 150px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                border: none;
                width: 12px;
                height: 12px;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #2d3436;
                border: 1px solid #b0bec5;
                selection-background-color: #0984e3;
                selection-color: white;
            }
            QLineEdit {
                padding: 8px;
                border: 2px solid #78909c;
                border-radius: 4px;
                background-color: #ffffff;
                color: #2d3436;
            }
            QPushButton {
                padding: 8px 15px;
                background-color: #0984e3;
                border: none;
                border-radius: 4px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0773c5;
            }
        """
        )

        # Initialize dialog with current settings (after all widgets and styles are set)
        self._initialize_cookie_settings()
        self._initialize_proxy_settings()

    def _initialize_cookie_settings(self) -> None:
        """Initialize the dialog with current cookie settings from config"""
        # Load saved cookie settings from ConfigManager
        saved_source = ConfigManager.get("cookie_source") or "browser"
        saved_browser = ConfigManager.get("cookie_browser") or "chrome"
        saved_profile = ConfigManager.get("cookie_browser_profile") or ""
        saved_file_path = ConfigManager.get("cookie_file_path")
        
        # Set the cookie source radio button
        if saved_source == "file":
            self.cookie_file_radio.setChecked(True)
        else:
            self.cookie_browser_radio.setChecked(True)
        
        # Set browser selection
        index = self.browser_combo.findText(saved_browser)
        if index >= 0:
            self.browser_combo.setCurrentIndex(index)
        
        # Set profile
        self.profile_input.setText(saved_profile)
        
        # Set file path if saved
        if saved_file_path:
            self.cookie_path_input.setText(str(saved_file_path))
        
        # Update visibility based on selection
        self.on_cookie_source_changed()
    
    def _update_cookies_active_status(self) -> None:
        """Update the status indicator showing if cookies are currently active"""
        if hasattr(self._parent, "browser_cookies_option") and self._parent.browser_cookies_option:
            self.cookies_active_status.setText(
                _("cookies.active_browser", browser=self._parent.browser_cookies_option)
            )
            self.cookies_active_status.setStyleSheet("color: #00cc00; font-weight: bold;")
        elif hasattr(self._parent, "cookie_file_path") and self._parent.cookie_file_path:
            self.cookies_active_status.setText(
                _("cookies.active_file", file=self._parent.cookie_file_path.name)
            )
            self.cookies_active_status.setStyleSheet("color: #00cc00; font-weight: bold;")
        else:
            self.cookies_active_status.setText(_("cookies.none_active"))
            self.cookies_active_status.setStyleSheet("color: #607d8b; font-style: italic;")

    def _initialize_proxy_settings(self) -> None:
        """Initialize the dialog with current proxy settings from config"""
        # Load proxy settings from config
        proxy_url = ConfigManager.get("proxy_url")
        geo_proxy_url = ConfigManager.get("geo_proxy_url")
        
        # Set proxy field values if they exist
        if proxy_url:
            self.proxy_url_input.setText(proxy_url)
        
        if geo_proxy_url:
            self.geo_proxy_url_input.setText(geo_proxy_url)
            
        # Update validation status
        self.validate_proxy_inputs()

    def on_cookie_source_changed(self) -> None:
        """Handle cookie source radio button changes"""
        if self.cookie_file_radio.isChecked():
            self.cookie_file_group.setVisible(True)
            self.cookie_browser_group.setVisible(False)
        else:
            self.cookie_file_group.setVisible(False)
            self.cookie_browser_group.setVisible(True)

    def apply_cookies(self) -> None:
        """Apply cookie settings when user clicks Apply button"""
        # Handle cookies
        cookie_path = self.get_cookie_file_path()
        browser_cookies = self.get_browser_cookies_option()

        # Clear both first to avoid conflicts
        self._parent.cookie_file_path = None
        self._parent.browser_cookies_option = None

        # Save settings to ConfigManager for persistence
        ConfigManager.set("cookie_remember", self.remember_cb.isChecked())
        if self.cookie_file_radio.isChecked():
            ConfigManager.set("cookie_source", "file")
            ConfigManager.set("cookie_file_path", str(cookie_path) if cookie_path else None)
        else:
            ConfigManager.set("cookie_source", "browser")
            ConfigManager.set("cookie_browser", self.browser_combo.currentText())
            ConfigManager.set("cookie_browser_profile", self.profile_input.text().strip())

        if cookie_path:
            self._parent.cookie_file_path = cookie_path
            ConfigManager.set("cookie_active", True)
            logger.info(f"Applied cookie file: {self._parent.cookie_file_path}")
            QMessageBox.information(
                self,
                _("cookies.file_selected_title"),
                _("cookies.file_applied_message", path=str(cookie_path)),
            )
        elif browser_cookies:
            self._parent.browser_cookies_option = browser_cookies
            ConfigManager.set("cookie_active", True)
            logger.info(f"Applied browser cookies: {self._parent.browser_cookies_option}")
            QMessageBox.information(
                self,
                _("cookies.browser_selected_title"),
                _("cookies.browser_applied_message", browser=browser_cookies),
            )
        else:
            # Clear cookies
            ConfigManager.set("cookie_active", False)
            ConfigManager.set("cookie_source", "browser")  # Reset to default
            ConfigManager.set("cookie_file_path", None)
            logger.info("Cookies cleared")
            QMessageBox.information(
                self,
                _("cookies.cleared_title"),
                _("cookies.cleared_message"),
            )
        
        # Update the status indicator
        self._update_cookies_active_status()

    def browse_cookie_file(self) -> None:
        # Open file dialog to select cookie file
        selected_files, _filter = QFileDialog.getOpenFileName(self, _("cookies.select_file_title"), "", _("cookies.file_filter"))

        if selected_files:
            # Ensure we have a valid full path
            cookie_path = Path(selected_files).resolve()
            self.cookie_path_input.setText(str(cookie_path))

    def get_cookie_file_path(self) -> Path | None:
        # Return the selected cookie file path if it's not empty and using file mode
        if self.cookie_file_radio.isChecked():
            path_text = self.cookie_path_input.text().strip()
            if path_text:
                path = Path(path_text)
                if path.exists() and path.is_file():
                    return path
                else:
                    # File doesn't exist or is not a file - still return path for user feedback
                    return path if len(path_text) > 3 else None  # Avoid single letters like 'C'
        return None

    def get_browser_cookies_option(self) -> str | None:
        """Returns the --cookies-from-browser option string if browser mode is selected"""
        if self.cookie_browser_radio.isChecked():
            browser = self.browser_combo.currentText()
            profile = self.profile_input.text().strip()

            if profile:
                return f"{browser}:{profile}"
            else:
                return browser
        return None

    def is_using_browser_cookies(self) -> bool:
        """Returns True if browser cookies mode is selected"""
        return self.cookie_browser_radio.isChecked()
    
    def get_proxy_url(self) -> str | None:
        """Returns the main proxy URL if specified"""
        proxy_url = self.proxy_url_input.text().strip()
        return proxy_url if proxy_url else None

    def get_geo_proxy_url(self) -> str | None:
        """Returns the geo-verification proxy URL if specified"""
        geo_proxy_url = self.geo_proxy_url_input.text().strip()
        return geo_proxy_url if geo_proxy_url else None

    def validate_proxy_url(self, url: str) -> bool:
        """Basic validation for proxy URL format"""
        if not url:
            return True  # Empty is OK
        
        # Check if it starts with a valid scheme
        valid_schemes = ['http://', 'https://', 'socks5://', 'socks4://']
        if not any(url.lower().startswith(scheme) for scheme in valid_schemes):
            return False
        
        # Basic URL format check (contains at least host:port)
        try:
            # Remove the scheme to check host:port part
            for scheme in valid_schemes:
                if url.lower().startswith(scheme):
                    host_port = url[len(scheme):]
                    break
            
            # Skip user:pass@ part if present
            if '@' in host_port:
                host_port = host_port.split('@')[1]
            
            # Should have at least host:port
            if ':' in host_port:
                host, port = host_port.split(':', 1)
                if host and port.isdigit():
                    return True
            
            return False
        except:
            return False

    def validate_proxy_inputs(self) -> None:
        """Validate proxy inputs and update status"""
        main_proxy = self.proxy_url_input.text().strip()
        geo_proxy = self.geo_proxy_url_input.text().strip()
        
        if not main_proxy and not geo_proxy:
            # Check if there are saved settings
            saved_main = ConfigManager.get("proxy_url")
            saved_geo = ConfigManager.get("geo_proxy_url")
            
            if saved_main or saved_geo:
                status_parts = []
                if saved_main:
                    status_parts.append(_("proxy.saved_main", proxy=saved_main))
                if saved_geo:
                    status_parts.append(_("proxy.saved_geo", proxy=saved_geo))
                self.proxy_status.setText(" | ".join(status_parts))
                self.proxy_status.setStyleSheet("color: #607d8b; font-style: italic;")
            else:
                self.proxy_status.setText("")
            return
            
        issues = []
        
        if main_proxy and not self.validate_proxy_url(main_proxy):
            issues.append(_("proxy.invalid_main_url"))
            
        if geo_proxy and not self.validate_proxy_url(geo_proxy):
            issues.append(_("proxy.invalid_geo_url"))
        
        if issues:
            self.proxy_status.setText(" | ".join(issues))
            self.proxy_status.setStyleSheet("color: #ff6666; font-style: italic;")
        else:
            status_parts = []
            if main_proxy:
                status_parts.append(_("proxy.main_configured"))
            if geo_proxy:
                status_parts.append(_("proxy.geo_configured"))
            
            self.proxy_status.setText(" | ".join(status_parts))
            self.proxy_status.setStyleSheet("color: #00cc00; font-style: italic;")


    def on_output_received(self, text: str):
        """Slot for receiving output from the worker"""
        self.log_output.append(text)

    def on_command_finished(self, success: bool, exit_code: int):
        """Slot for when command finishes"""
        self.run_btn.setEnabled(True)
        self.run_btn.setText(_("command.run_command"))

    def on_error_occurred(self, error_msg: str):
        """Slot for handling errors"""
        self.log_output.append(error_msg)
        self.run_btn.setEnabled(True)
        self.run_btn.setText(_("buttons.run_command"))

    def on_language_changed(self) -> None:
        """Handle language selection change"""
        selected_lang_code = self.language_combo.currentData()
        if selected_lang_code:
            current_lang = ConfigManager.get("language") or "en"
            if selected_lang_code != current_lang:
                # Save the new language preference
                ConfigManager.set("language", selected_lang_code)
                
                # Update LocalizationManager
                LocalizationManager.set_language(selected_lang_code)
                
                # Show restart notice
                self.restart_notice.setVisible(True)
                
                logger.info(f"Language changed to: {selected_lang_code}")
    
    def accept(self) -> None:
        """Override accept to save auto-update settings from the updater tab."""
        logger.info("CustomOptionsDialog.accept() called")
        try:
            # Save auto-update settings from the updater tab
            enabled, frequency = self.updater_tab.get_auto_update_settings()
            logger.info(f"Saving auto-update settings: enabled={enabled}, frequency={frequency}")
            result = update_auto_update_settings(enabled, frequency)
            logger.info(f"Auto-update settings save result: {result}")

            # Save beta update setting
            beta_enabled = self.updater_tab.get_beta_update_setting()
            ConfigManager.set("check_beta_updates", beta_enabled)
            logger.info(f"Saved beta updates setting: {beta_enabled}")

            # Save app update checker setting
            app_updates_enabled = self.updater_tab.get_app_update_checker_setting()
            ConfigManager.set("check_app_updates", app_updates_enabled)
            logger.info(f"Saved app updates checker setting: {app_updates_enabled}")

        except Exception as e:
            logger.exception(f"Error saving auto-update settings: {e}")

        # Save LLM settings
        try:
            llm_mode = "llm" if self.llm_mode_llm.isChecked() else "rule"
            ConfigManager.set("llm_mode", llm_mode)
            ConfigManager.set("llm_url", self.llm_url_input.text().strip())
            ConfigManager.set("llm_api_key", self.llm_api_key_input.text().strip())
            ConfigManager.set("llm_model", self.llm_model_input.text().strip())
            ConfigManager.set("llm_temperature", float(self.llm_temperature_input.text() or 0.1))
            ConfigManager.set("llm_max_workers", int(self.llm_max_workers_input.text() or 10))
            ConfigManager.set("llm_timeout", int(self.llm_timeout_input.text() or 60))
            ConfigManager.set("llm_max_retries", int(self.llm_max_retries_input.text() or 3))
            ConfigManager.set("llm_segmentation_soft_limit", int(self.llm_soft_limit.text() or 70))
            ConfigManager.set("llm_segmentation_hard_limit", int(self.llm_hard_limit.text() or 85))
            ConfigManager.set("llm_segmentation_target_cps", int(self.llm_target_cps.text() or 14))
            ConfigManager.set("llm_segmentation_limit_cps", int(self.llm_limit_cps.text() or 18))
            logger.info(f"Saved LLM settings: mode={llm_mode}")
        except Exception as e:
            logger.exception(f"Error saving LLM settings: {e}")

        # Call the parent accept method to close the dialog
        super().accept()
