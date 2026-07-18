# -*- coding: utf-8 -*-
"""
Widget animation helpers for SageDLP GUI.

`WidgetAnimationMixin` provides reusable fade / shake / cross-fade animations
and the dialog overlay used across the main window.
"""

from typing import TYPE_CHECKING, cast

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtWidgets import QDialog, QLabel, QGraphicsOpacityEffect, QWidget

if TYPE_CHECKING:
    from .sage_gui_main import SageApp


class WidgetAnimationMixin:
    """Reusable widget animations shared across the main window."""

    def animate_widget_fade_in(self: "SageApp", widget: QWidget, duration: int = 300) -> None:
        """Fade in a widget using opacity animation."""
        # Check if the main window has a graphics effect (blur) active.
        # If so, animating a child widget with another effect causes QPainter conflicts.
        # NOTE: With the new Screenshot Overlay method, 'self.graphicsEffect()' on the MainWindow isn't used.
        # However, we should still be careful if the widget itself already has an effect.

        # Stop fade out if running
        if hasattr(widget, '_fade_out_anim'):
             try:
                 if widget._fade_out_anim.state() == QPropertyAnimation.State.Running:
                     widget._fade_out_anim.stop()
             except RuntimeError:
                 pass

        if widget.isVisible() and widget.graphicsEffect() is None:
            return

        # Setup opacity effect if not present
        effect = widget.graphicsEffect()
        if not effect or not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)

        # Determine start value (current opacity if previously animating)
        start_val = effect.opacity() if widget.isVisible() else 0.0
        end_val = 1.0

        # Setup animation
        anim = QPropertyAnimation(effect, b"opacity", widget)
        anim.setDuration(duration)
        anim.setStartValue(start_val)
        anim.setEndValue(end_val)
        anim.setEasingCurve(QEasingCurve.Type.OutQuad)

        # Show widget before animation
        widget.setVisible(True)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

        # Keep reference to avoid garbage collection
        widget._fade_anim = anim

    def animate_widget_fade_out(self: "SageApp", widget: QWidget, duration: int = 300) -> None:
        """Fade out a widget and then hide it."""

        # Stop fade in if running
        if hasattr(widget, '_fade_anim'):
             try:
                 if widget._fade_anim.state() == QPropertyAnimation.State.Running:
                     widget._fade_anim.stop()
             except RuntimeError:
                 pass

        if not widget.isVisible():
            return

        effect = widget.graphicsEffect()
        if not effect or not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)
            effect.setOpacity(1.0)

        start_val = effect.opacity()

        anim = QPropertyAnimation(effect, b"opacity", widget)
        anim.setDuration(duration)
        anim.setStartValue(start_val)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InQuad)

        def on_finished():
            widget.setVisible(False)
            widget.setGraphicsEffect(None) # Remove effect to restore normal painting

        anim.finished.connect(on_finished)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

        widget._fade_out_anim = anim # Keep reference

    def set_widget_visible_animated(self: "SageApp", widget: QWidget, visible: bool) -> None:
        """Toggle widget visibility with fade animation."""
        if visible:
            self.animate_widget_fade_in(widget)
        else:
            self.animate_widget_fade_out(widget)

    def animate_widget_shake(self: "SageApp", widget: QWidget) -> None:
        """Shake a widget left and right to indicate an error or invalid input."""
        # Stop shake if running
        if hasattr(widget, '_shake_anim'):
             try:
                 if widget._shake_anim.state() == QPropertyAnimation.State.Running:
                     return
             except RuntimeError:
                 pass

        # Use current position as baseline
        pos = widget.pos()
        x = pos.x()
        y = pos.y()

        anim = QPropertyAnimation(widget, b"pos", widget)
        anim.setDuration(300)
        anim.setLoopCount(1)

        # Create keyframes for shake effect
        anim.setKeyValueAt(0, QPoint(x, y))
        anim.setKeyValueAt(0.2, QPoint(x - 5, y))
        anim.setKeyValueAt(0.4, QPoint(x + 5, y))
        anim.setKeyValueAt(0.6, QPoint(x - 5, y))
        anim.setKeyValueAt(0.8, QPoint(x + 5, y))
        anim.setKeyValueAt(1.0, QPoint(x, y))

        widget._shake_anim = anim
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def set_status_message_animated(self: "SageApp", message: str) -> None:
        """Update status label with a cross-fade animation."""
        if self.status_label.text() == message:
             return

        # If previous animation is running, stop it
        if hasattr(self.status_label, '_status_anim'):
            try:
                if self.status_label._status_anim.state() == QPropertyAnimation.State.Running:
                    self.status_label._status_anim.stop()
            except RuntimeError:
                pass  # Animation object already deleted

        # Create effect if needed
        effect = self.status_label.graphicsEffect()
        if not effect or not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(self.status_label)
            self.status_label.setGraphicsEffect(effect)

        # 1. Fade OUT
        anim1 = QPropertyAnimation(effect, b"opacity", self.status_label)
        anim1.setDuration(150)
        anim1.setStartValue(1.0)
        anim1.setEndValue(0.0)
        anim1.setEasingCurve(QEasingCurve.Type.OutQuad)

        # 2. Change Text & Fade IN
        anim2 = QPropertyAnimation(effect, b"opacity", self.status_label)
        anim2.setDuration(150)
        anim2.setStartValue(0.0)
        anim2.setEndValue(1.0)
        anim2.setEasingCurve(QEasingCurve.Type.InQuad)

        def on_fade_out_finished():
            self.status_label.setText(message)
            anim2.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

        anim1.finished.connect(on_fade_out_finished)
        anim1.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

        # Store ref
        self.status_label._status_anim = anim1
        self.status_label._status_anim2 = anim2

    def run_dialog_with_blur(self: "SageApp", dialog: QDialog) -> int:
        """Run a dialog with a semi-transparent overlay (no blur to avoid QPainter/QGraphicsScene crashes)."""

        # Create a simple semi-transparent dark overlay
        overlay = QLabel(self)
        overlay.setStyleSheet("background-color: rgba(0, 0, 0, 80);")
        overlay.setGeometry(0, 0, self.width(), self.height())
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        overlay.show()

        # Animate overlay Fade In
        opacity_effect = QGraphicsOpacityEffect(overlay)
        overlay.setGraphicsEffect(opacity_effect)

        anim = QPropertyAnimation(opacity_effect, b"opacity", overlay)
        anim.setDuration(200)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

        # Run the dialog
        result = dialog.exec()

        # Remove overlay
        overlay.deleteLater()

        return result
