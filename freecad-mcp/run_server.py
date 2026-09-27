#!/usr/bin/env python3
"""Punto de entrada del servidor FreeCAD MCP (fork local extendido).

Uso (desde la config de OpenCode):
    /home/astrid/.local/share/pipx/venvs/freecad-mcp/bin/python \
        /home/astrid/Documentos/OpenScience/sessions/2026-09-25-1821/freecad-mcp/run_server.py

Requiere el paquete `mcp` (usado el venv pipx de freecad-mcp instalado en el
sistema) y FreeCAD corriendo con el addon FreeCADMCP (RPC en localhost:9875).
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from freecad_mcp.server import main  # noqa: E402

if __name__ == "__main__":
    main()
