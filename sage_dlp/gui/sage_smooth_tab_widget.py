from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QLabel,
    QStackedWidget,
    QTabBar,
    QVBoxLayout,
    QWidget,
)

class FadingStackedWidget(QStackedWidget):
    """
    A QStackedWidget that cross-fades between widgets.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fade_duration = 300 
        self.fade_easing = QEasingCurve.Type.OutQuad

    def setCurrentIndex(self, index):
        curr_index = self.currentIndex()
        if index == curr_index:
            return

        widget = self.widget(index)
        curr_widget = self.widget(curr_index)
        
        # If widget isn't visible or valid, just swap
        if not self.isVisible() or not curr_widget:
            super().setCurrentIndex(index)
            return

        # 1. Capture the current view (the "old" tab)
        # Use grab() for simplicity and reliability in PySide6
        pixmap = self.grab()
        
        # 2. Create an overlay label to hold this "old" view
        overlay = QLabel(self)
        overlay.setPixmap(pixmap)
        overlay.setGeometry(0, 0, self.width(), self.height())
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents) # Don't block clicks
        overlay.show()
        
        # 3. Switch the actual stack to the "new" view
        super().setCurrentIndex(index)
        
        # CRITICAL: Ensure overlay stays on top of the new widget
        overlay.raise_()
        
        # 4. Fade OUT the overlay, revealing the new view
        effect = QGraphicsOpacityEffect(overlay)
        overlay.setGraphicsEffect(effect)

        
        anim = QPropertyAnimation(effect, b"opacity", overlay)
        anim.setDuration(self.fade_duration)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(self.fade_easing)
        
        # Cleanup when done
        anim.finished.connect(lambda: self._cleanup(overlay))
        
        # Keep reference to prevent GC
        self._active_anim = anim 
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def _cleanup(self, overlay):
        overlay.hide()
        overlay.deleteLater()


class SmoothTabWidget(QWidget):
    """
    A unified Widget that behaves like a QTabWidget but uses smooth fading transitions.
    Includes a QTabBar and a FadingStackedWidget.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Main Layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Tab Bar
        self.tab_bar = QTabBar(self)
        self.tab_bar.setDrawBase(False) # We draw border on content instead
        self.tab_bar.currentChanged.connect(self.set_current_index)
        self.layout.addWidget(self.tab_bar)
        
        # Content Area (Frame) - Mimics QTabWidget::pane
        self.content_frame = QFrame(self)
        self.content_frame.setObjectName("tabContent") 
        
        # Layout inside the content frame
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        
        # The Stack
        self.stack = FadingStackedWidget(self.content_frame)
        self.content_layout.addWidget(self.stack)
        
        self.layout.addWidget(self.content_frame)

    def addTab(self, widget, label):
        """Add a tab with the given widget and label."""
        self.stack.addWidget(widget)
        self.tab_bar.addTab(label)

    def set_current_index(self, index):
        """Slot to handle tab bar clicks."""
        self.tab_bar.setCurrentIndex(index)
        self.stack.setCurrentIndex(index)

    def currentWidget(self):
        return self.stack.currentWidget()

    def currentIndex(self):
        return self.stack.currentIndex()
