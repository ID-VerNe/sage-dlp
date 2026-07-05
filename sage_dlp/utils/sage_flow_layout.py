"""
FlowLayout - Qt Flow Layout Implementation
============================================
Custom QLayout that automatically wraps items to the next row
when the container width is insufficient.

Based on the Qt FlowLayout example:
https://doc.qt.io/qt-6/qtwidgets-layouts-flowlayout-example.html
"""

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QLayout, QSizePolicy


class FlowLayout(QLayout):
    """Flow layout that wraps items to the next row when space runs out."""

    def __init__(self, parent=None, margin: int = -1, spacing: int = -1):
        super().__init__(parent)
        self._item_list = []
        if margin != -1:
            self.setContentsMargins(margin, margin, margin, margin)
        if spacing != -1:
            self.setSpacing(spacing)

    def __del__(self):
        while self._item_list:
            item = self._item_list.pop()
            item.widget().setParent(None) if item.widget() else None

    def addItem(self, item):
        self._item_list.append(item)

    def count(self) -> int:
        return len(self._item_list)

    def itemAt(self, index: int):
        if 0 <= index < len(self._item_list):
            return self._item_list[index]
        return None

    def takeAt(self, index: int):
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientations:
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), True)

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._item_list:
            minsize = item.minimumSize()
            size = size.expandedTo(minsize)
        margin = self.contentsMargins().left() + self.contentsMargins().right()
        size += QSize(margin, margin)
        return size

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def setGeometry(self, rect: QRect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        """Perform layout calculation. Returns total height if test_only is True."""
        margin_left, margin_top, margin_right, margin_bottom = self.getContentsMargins()
        effective_rect = rect.adjusted(+margin_left, +margin_top, -margin_right, -margin_bottom)
        x = effective_rect.x()
        y = effective_rect.y()
        line_height = 0
        spacing = self.spacing()
        if spacing < 0:
            spacing = 6  # default

        for item in self._item_list:
            widget = item.widget()
            if widget and not widget.isVisibleTo(self.parentWidget()):
                continue

            space_x = spacing
            space_y = spacing
            next_x = x + item.sizeHint().width() + space_x

            if next_x - space_x > effective_rect.right() and line_height > 0:
                x = effective_rect.x()
                y += line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y() + margin_bottom