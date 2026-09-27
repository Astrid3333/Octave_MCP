"""Registro de ejemplos de diseño del fork (`examples/examples.json`).

Operaciones puramente locales: leen el manifest del directorio `examples/`
del paquete y no requieren FreeCAD ni conexión RPC.
"""

from __future__ import annotations

import json
import os

from ..responses import ToolResponse, json_response, text_response

_SCHEMA = "freecad-mcp-examples/1"


def _examples_dir() -> str:
    """freecad_mcp/operations/examples_ops.py -> freecad-mcp/examples"""
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(os.path.dirname(here))
    return os.path.join(root, "examples")


def _registry_path() -> str:
    return os.path.join(_examples_dir(), "examples.json")


def load_registry() -> dict:
    path = _registry_path()
    if not os.path.exists(path):
        return {"schema": _SCHEMA, "examples": []}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _find(registry: dict, example_id: str) -> dict | None:
    for ex in registry.get("examples", []):
        if ex.get("id") == example_id or ex.get("name") == example_id:
            return ex
    return None


def list_examples_operation() -> ToolResponse:
    """Lista los ejemplos registrados (resumen: id, nombre, descripción)."""
    try:
        registry = load_registry()
    except Exception as exc:  # noqa: BLE001
        return text_response(f"list_examples: {exc}")
    summaries = [
        {
            "id": ex.get("id"),
            "name": ex.get("name"),
            "description": ex.get("description", ""),
            "units": ex.get("units", "mm"),
            "objects": len(ex.get("objects", [])),
            "previews": len(ex.get("previews", [])),
            "approved": bool(ex.get("approved", False)),
        }
        for ex in registry.get("examples", [])
    ]
    return json_response(
        {
            "success": True,
            "count": len(summaries),
            "registry": _registry_path(),
            "examples": summaries,
        }
    )


def get_example_operation(example_id: str) -> ToolResponse:
    """Devuelve un ejemplo completo con rutas absolutas al FCStd y previews."""
    try:
        registry = load_registry()
    except Exception as exc:  # noqa: BLE001
        return text_response(f"get_example: {exc}")
    ex = _find(registry, example_id)
    if ex is None:
        available = [e.get("id") for e in registry.get("examples", [])]
        return text_response(
            f"get_example: ejemplo no encontrado: {example_id!r}; "
            f"disponibles: {available}"
        )
    exdir = _examples_dir()
    file_path = os.path.join(exdir, ex.get("file", ""))
    preview_paths = [os.path.join(exdir, p) for p in ex.get("previews", [])]
    out = dict(ex)
    out["success"] = True
    out["file_path"] = file_path
    out["file_exists"] = os.path.exists(file_path)
    out["preview_paths"] = preview_paths
    out["previews_exist"] = [os.path.exists(p) for p in preview_paths]
    return json_response(out)


def load_example_operation(freecad, example_id: str) -> ToolResponse:
    """Abre el FCStd de un ejemplo registrado en FreeCAD (delega en
    ``open_document_operation``) y devuelve los datos del ejemplo."""
    try:
        registry = load_registry()
    except Exception as exc:  # noqa: BLE001
        return text_response(f"load_example: {exc}")
    ex = _find(registry, example_id)
    if ex is None:
        available = [e.get("id") for e in registry.get("examples", [])]
        return text_response(
            f"load_example: ejemplo no encontrado: {example_id!r}; "
            f"disponibles: {available}"
        )
    file_path = os.path.join(_examples_dir(), ex.get("file", ""))
    if not os.path.exists(file_path):
        return text_response(f"load_example: archivo no existe: {file_path}")
    from .extended import open_document_operation

    resp = open_document_operation(freecad, file_path)
    try:
        data = json.loads(resp[0].text)
    except Exception:  # noqa: BLE001 - open_document devolvio texto plano
        return resp
    if isinstance(data, dict):
        data["example_id"] = ex.get("id")
        data["example_file"] = file_path
    return json_response(data)
