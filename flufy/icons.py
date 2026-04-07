"""Shared SVG icon loading and PNG conversion helpers."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer


def _render_svg(path: str, size: int = 64) -> QPixmap | None:
    """Render an SVG file to a QPixmap, or return None if invalid."""
    renderer = QSvgRenderer(path)
    if not renderer.isValid():
        return None

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return pixmap


def load_svg_icon(path: str, size: int = 64) -> QIcon:
    """Load an SVG file as a QIcon by rendering it to a QPixmap."""
    pixmap = _render_svg(path, size)
    return QIcon(pixmap) if pixmap is not None else QIcon()


def create_png_icon(svg_path: str, png_path: str, size: int = 64) -> None:
    """Render SVG to PNG for use in desktop file."""
    pixmap = _render_svg(svg_path, size)
    if pixmap is not None:
        pixmap.save(png_path, "PNG")
