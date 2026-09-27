#!/usr/bin/env python3
"""Validador del catalogo FreeCAD_MCP (freecad_mcp_tools.json).

Mismas reglas que validate_octave_mcp.py:
  - claves raiz obligatorias (mcpName, version, description, tools, designPrinciples)
  - tools con id 1..N sin huecos, nombres e ids unicos
  - description de cada tool con al menos 10 caracteres
  - description del MCP con al menos 20 caracteres
  - designPrinciples: hasta 20 entradas, cada una con al menos 20 caracteres
  - coherencia con las tools reales del servidor (si se puede importar)

Uso:
    python3 validate_freecad_mcp.py [ruta/al/freecad_mcp_tools.json]
"""

import json
import os
import sys

ROOT_KEYS = ("mcpName", "version", "description", "tools", "designPrinciples")


def validate_catalog(filepath: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not os.path.exists(filepath):
        return [f"no existe el archivo: {filepath}"], warnings

    try:
        with open(filepath, encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        return [f"JSON invalido: {exc}"], warnings

    for key in ROOT_KEYS:
        if key not in data:
            errors.append(f"falta la clave raiz: {key}")
    if errors:
        return errors, warnings

    if len(str(data["description"])) < 20:
        errors.append("description del MCP demasiado corta (< 20)")

    tools = data["tools"]
    if not isinstance(tools, list) or not tools:
        errors.append("tools debe ser una lista no vacia")
        return errors, warnings

    expected = set(range(1, len(tools) + 1))
    ids = [t.get("id") for t in tools]
    if set(ids) != expected:
        missing = sorted(expected - set(ids))
        extra = sorted(set(ids) - expected)
        errors.append(f"ids no secuenciales; faltan={missing} sobran={extra}")

    names = [t.get("name", "") for t in tools]
    if len(set(ids)) != len(ids):
        errors.append("ids duplicados")
    if len(set(names)) != len(names):
        dupes = sorted({n for n in names if names.count(n) > 1})
        errors.append(f"nombres duplicados: {dupes}")

    categories: list[str] = []
    for t in tools:
        tid = t.get("id")
        name = t.get("name", "")
        if not name:
            errors.append(f"tool id={tid} sin name")
        if not t.get("category"):
            errors.append(f"tool {name!r} sin category")
        else:
            categories.append(t["category"])
        if len(t.get("description", "")) < 10:
            errors.append(f"description demasiado corta en {name!r}")

    principles = data["designPrinciples"]
    if not isinstance(principles, list) or not principles:
        errors.append("designPrinciples debe ser una lista no vacia")
    else:
        if len(principles) > 20:
            warnings.append(f"designPrinciples tiene {len(principles)} (max recomendado: 20)")
        for i, p in enumerate(principles):
            if len(str(p)) < 20:
                errors.append(f"principio {i + 1} demasiado corto")

    return errors, warnings


def validate_against_server(filepath: str) -> tuple[list[str], list[str]]:
    """Compara los nombres del catalogo con los tools reales del servidor."""
    errors: list[str] = []
    warnings: list[str] = []
    try:
        base = os.path.dirname(os.path.abspath(filepath))
        sys.path.insert(0, os.path.join(base, "freecad-mcp"))
        sys.path.insert(0, base)
        import asyncio

        from freecad_mcp import server as srv  # type: ignore
    except Exception as exc:  # noqa: BLE001 - el servidor puede no estar en el path
        warnings.append(f"no se pudo importar el servidor para contrastar: {exc}")
        return errors, warnings

    with open(filepath, encoding="utf-8") as fh:
        catalog_names = {t["name"] for t in json.load(fh)["tools"]}

    try:
        live = asyncio.run(srv.mcp.list_tools())
        live_names = {t.name for t in live}
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"no se pudo listar tools del servidor: {exc}")
        return errors, warnings

    missing_in_catalog = sorted(live_names - catalog_names)
    missing_in_server = sorted(catalog_names - live_names)
    if missing_in_catalog:
        errors.append(f"tools del servidor ausentes en el catalogo: {missing_in_catalog}")
    if missing_in_server:
        errors.append(f"tools del catalogo inexistentes en el servidor: {missing_in_server}")
    return errors, warnings


def run_all(filepath: str) -> int:
    errors, warnings = validate_catalog(filepath)
    s_errors, s_warnings = validate_against_server(filepath)
    errors += s_errors
    warnings += s_warnings

    with open(filepath, encoding="utf-8") as fh:
        data = json.load(fh)
    tools = data["tools"]
    categories = sorted({t.get("category", "?") for t in tools})

    print(f"Archivo      : {filepath}")
    print(f"mcpName      : {data['mcpName']} v{data['version']}")
    print(f"Tools        : {len(tools)}")
    print(f"Categorias   : {len(categories)} -> {', '.join(categories)}")
    print(f"Principios   : {len(data['designPrinciples'])}")

    for w in warnings:
        print(f"[WARN] {w}")
    if errors:
        for e in errors:
            print(f"[FAIL] {e}")
        print("RESULTADO: FAIL")
        return 1
    print("RESULTADO: PASS")
    return 0


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "freecad_mcp_tools.json"
    sys.exit(run_all(path))
