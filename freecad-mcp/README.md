# FreeCAD MCP (fork local)

Fork local de [`freecad-mcp`](https://github.com/neka-nat/freecad-mcp) (MIT,
"Copyright (c) 2025 Shirokuma (k tanaka)") con **26 tools**: las 11 upstream de
creación/consulta/captura más **15 nuevas** de documentos, cámara, modelado,
medición y exportación.

## Componentes

| Pieza | Rol |
|---|---|
| `run_server.py` | Punto de entrada MCP (stdio) para opencode |
| `freecad_mcp/server.py` | Servidor FastMCP: expone las 26 tools |
| `freecad_mcp/freecad_client.py` | Cliente XML-RPC al addon FreeCADMCP (`localhost:9875`) + snippets de cámara/captura |
| `freecad_mcp/operations/core.py` | 11 operaciones upstream (con capturas modificadas) |
| `freecad_mcp/operations/extended.py` | 15 operaciones nuevas |
| `test_extended_tools.py` | Tests E2E (22 aserciones) contra FreeCAD real |

Requisito: FreeCAD (flatpak) con el addon **FreeCADMCP** activo
(`auto_start_rpc: true`, XML-RPC en `127.0.0.1:9875`).

## Tools nuevas (15)

`save_document`, `open_document`, `close_document`, `export_model`,
`get_camera`, `set_camera`, `fit_view`, `screenshot_current`, `set_color`,
`apply_fillet`, `apply_chamfer`, `boolean_op`, `measure`, `transform_object`,
`set_visibility`.

Catálogo completo en `../freecad_mcp_tools.json` (validador:
`../validate_freecad_mcp.py`).

## Modificaciones respecto al upstream

1. **Operaciones nuevas** en `operations/extended.py` (snippets Python que
   corren en el hilo GUI de FreeCAD vía `execute_code`, con `_mcp_emit` y
   marcadores JSON).
2. **Capturas con preservación de cámara** (`freecad_client.py`):
   - `saveImage(path, w, h)` redimensiona el widget y dispara un
     re-encuadre; ahora se guarda/restaura el string de cámara alrededor
     de la captura.
   - `screenshot_current` no aplica preset ni fit: respeta el estado actual.
   - `fit_view` hace `fitAll` (o foco en un objeto) y repara
     near/far/height con el bounding box real de la escena.
3. **Cámara (hallazgos verificados en FreeCAD 1.1.3)**:
   - El string OpenInventor usa `orientation` axis-angle (unitario, rad).
   - `viewportMapping` solo acepta `ADJUST_CAMERA`; `FIXED_NEAR`,
     `FIXED_FAR` y `NO_CLIPPING` rechazan con *"Camera settings failed to
     read"*.
   - Con `ADJUST_CAMERA`, Coin **recalcula near/far en cada render**: los
     valores manuales no persisten. Por eso `fit_view` reporta un readback
     post-ajuste y `set_camera` incluye nota de este comportamiento.
   - El `fitAll` puede surtir efecto con retardo (evento diferido tras
     `create_object`); los tests esperan posición estable antes de medir.
4. **Bug upstream conocido**: `process_gui_tasks()` en el addon no
   reprograma su `QTimer` si una tarea lanza excepción no capturada → la
   cola RPC queda muerta (`_queue.Empty`) hasta reiniciar FreeCAD.

## Instalación / uso

```bash
# servidor (opencode.json):
#   ["~/.local/share/pipx/venvs/freecad-mcp/bin/python",
#    ".../freecad-mcp/run_server.py"]

# tests (con FreeCAD abierto):
/home/astrid/.local/share/pipx/venvs/freecad-mcp/bin/python test_extended_tools.py
```

Flujo de cámara recomendado para capturas: modelar → `fit_view` (encuadra y
repara el rango) → `get_camera`/`set_camera` (ajuste fino) →
`screenshot_current` (no mueve nada).

## Licencia

MIT (heredada del upstream). Cambios locales: mismo repo que este workspace.
