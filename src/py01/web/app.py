"""HTML-Oberfläche (Werkstatt, Galerie) und Auslieferung gespeicherter SVGs."""

from __future__ import annotations

import base64
import logging
import re
from collections.abc import Callable
from typing import Any, Protocol

from flask import Flask, Response, redirect, render_template, request
from werkzeug.exceptions import BadRequest, NotFound, RequestEntityTooLarge

from py01.generator import ParamError, Params, Source, generate
from py01.store import Image, NotFoundError, Variant

log = logging.getLogger(__name__)

MAX_FORM_BYTES = 2 * 1024 * 1024  # Obergrenze für einen Formular-Body
MAX_SVG_BYTES = 1024 * 1024  # Obergrenze für ein zu speicherndes SVG
MAX_ID = 2**63 - 1
_ID = re.compile(r"[+-]?[0-9]+")


class StoreLike(Protocol):
    """Die vom Web-Paket genutzte Teilmenge des Stores."""

    def list_variants(self) -> list[Variant]: ...
    def get_variant(self, id: int) -> Variant: ...
    def create_variant(self, name: str, params: str, parent_id: int = 0) -> int: ...
    def save_image(self, variant_id: int, svg: str) -> int: ...
    def list_images(self, variant_id: int = 0) -> list[Image]: ...
    def get_image(self, id: int) -> Image: ...


def parse_id(s: str | None) -> int | None:
    """Positive int64-ID wie Gos strconv.ParseInt mit id > 0, sonst None."""
    if s is None or not _ID.fullmatch(s):
        return None
    n = int(s)
    return n if 0 < n <= MAX_ID else None


def _text(body: str, status: int) -> Response:
    """Klartext-Antwort wie Gos http.Error."""
    return Response(body + "\n", status, content_type="text/plain; charset=utf-8")


def create_app(store: StoreLike, new_source: Callable[[], Source]) -> Flask:
    """Baut die Anwendung; new_source liefert pro Aufruf eine frische
    Zufallsquelle für das Generieren."""
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_FORM_BYTES
    app.config["MAX_FORM_MEMORY_SIZE"] = MAX_FORM_BYTES

    def variant_or_404(id_str: str | None) -> Variant:
        vid = parse_id(id_str)
        if vid is None:
            raise NotFound()
        try:
            return store.get_variant(vid)
        except NotFoundError:
            raise NotFound() from None

    def workbench(selected: Variant | None = None) -> dict[str, Any]:
        data: dict[str, Any] = {
            "title": "Werkstatt",
            "active": "werkstatt",
            "variants": store.list_variants(),
            "selected": None,
            "params": "",
            "name": "",
            "error": "",
            "preview": "",
            "svg": "",
        }
        if selected is not None:
            data.update(
                selected=selected, params=selected.params, name=selected.name + " (neu)"
            )
        return data

    def page(data: dict[str, Any], status: int = 200) -> tuple[str, int]:
        template = "werkstatt.html" if data["active"] == "werkstatt" else "galerie.html"
        return render_template(template, **data), status

    @app.errorhandler(RequestEntityTooLarge)
    def too_large(_: RequestEntityTooLarge) -> Response:
        return _text("Anfrage zu groß", 413)

    @app.errorhandler(BadRequest)
    def bad_request(_: BadRequest) -> Response:
        return _text("Ungültige Formulardaten", 400)

    @app.errorhandler(NotFound)
    def not_found(_: NotFound) -> Response:
        return _text("404 page not found", 404)

    @app.errorhandler(Exception)
    def server_error(e: Exception) -> Response:
        if hasattr(e, "code") and isinstance(e.code, int) and e.code < 500:
            return e  # type: ignore[return-value]  # HTTP-Fehler wie 405
        log.exception("request failed")
        return _text("Interner Fehler", 500)

    @app.get("/")
    def root() -> Any:
        return redirect("/werkstatt", 303)

    @app.get("/werkstatt")
    def werkstatt() -> tuple[str, int]:
        id_str = request.args.get("variant")
        if id_str:
            return page(workbench(variant_or_404(id_str)))
        variants = store.list_variants()
        return page(workbench(variants[0] if variants else None))

    @app.post("/werkstatt/generate")
    def generate_preview() -> tuple[str, int]:
        v = variant_or_404(request.form.get("variant_id"))
        data = workbench(v)
        data["params"] = request.form.get("params", "")
        try:
            svg = generate(Params.parse(data["params"]), new_source())
        except ParamError as e:
            data["error"] = str(e)
            return page(data, 422)
        data["svg"] = svg
        data["preview"] = "data:image/svg+xml;base64," + base64.b64encode(
            svg.encode()
        ).decode("ascii")
        return page(data)

    @app.post("/werkstatt/save-image")
    def save_image() -> Any:
        v = variant_or_404(request.form.get("variant_id"))
        svg = request.form.get("svg", "")
        if not svg.startswith("<svg ") or len(svg.encode()) > MAX_SVG_BYTES:
            data = workbench(v)
            data["error"] = (
                "Das Bild ist kein gültiges SVG oder zu groß "
                "und wurde nicht gespeichert."
            )
            return page(data, 422)
        store.save_image(v.id, svg)
        return redirect(f"/galerie?variant={v.id}", 303)

    @app.post("/werkstatt/save-variant")
    def save_variant() -> Any:
        parent = variant_or_404(request.form.get("variant_id"))
        name = request.form.get("name", "").strip()
        params = request.form.get("params", "")

        def fail(msg: str) -> tuple[str, int]:
            data = workbench(parent)
            data.update(params=params, name=name, error=msg)
            return page(data, 422)

        if not name:
            return fail("Bitte einen Namen für die neue Variante angeben.")
        try:
            Params.parse(params)
        except ParamError as e:
            return fail(str(e))
        new_id = store.create_variant(name, params, parent.id)
        return redirect(f"/werkstatt?variant={new_id}", 303)

    @app.get("/galerie")
    def galerie() -> tuple[str, int]:
        variants = store.list_variants()
        filter_id = 0
        id_str = request.args.get("variant")
        if id_str:
            filter_id = variant_or_404(id_str).id
        names = {v.id: v.name for v in variants}
        images = [
            {
                "id": img.id,
                "variant_name": names.get(img.variant_id, ""),
                "created": img.created_at.strftime("%Y-%m-%d %H:%M"),
            }
            for img in store.list_images(filter_id)
        ]
        data = {
            "title": "Galerie",
            "active": "galerie",
            "error": "",
            "variants": variants,
            "filter_id": filter_id,
            "images": images,
        }
        return page(data)

    @app.get("/bilder/<file>")
    def bild(file: str) -> Response:
        """Liefert ein gespeichertes SVG. Der Inhalt gilt als fremd: CSP und
        nosniff verhindern, dass darin enthaltene Skripte ausgeführt werden."""
        if not file.endswith(".svg"):
            raise NotFound()
        iid = parse_id(file.removesuffix(".svg"))
        if iid is None:
            raise NotFound()
        try:
            img = store.get_image(iid)
        except NotFoundError:
            raise NotFound() from None
        resp = Response(img.svg, 200)
        resp.headers["Content-Type"] = "image/svg+xml"
        resp.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'unsafe-inline'"
        )
        resp.headers["X-Content-Type-Options"] = "nosniff"
        return resp

    return app
