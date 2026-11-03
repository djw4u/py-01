"""Erzeugt aus JSON-Parametern SVG-Bilder; kennt weder HTTP noch Datenbank."""

from .generator import generate
from .params import Params
from .values import ParamError, Source

__all__ = ["ParamError", "Params", "Source", "generate"]
