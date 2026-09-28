# FreeCAD MCP (fork local)

Fork local de [`freecad-mcp`](https://github.com/neka-nat/freecad-mcp) (MIT,
"Copyright (c) 2025 Shirokuma (k tanaka)") con **31 tools**: las 11 upstream de
creación/consulta/captura más **20 nuevas** de documentos, cámara, modelado,
medición, exportación, espejo, registro de ejemplos y protesises parametricas.

## Componentes

| Pieza | Rol |
|---|---|
| `run_server.py` | Punto de entrada MCP (stdio) para opencode |
| `freecad_mcp/server.py` | Servidor FastMCP: expone las 31 tools |
| `freecad_mcp/freecad_client.py` | Cliente XML-RPC al addon FreeCADMCP (`localhost:9875`) + snippets de cámara/captura |
| `freecad_mcp/operations/core.py` | 11 operaciones upstream (con capturas modificadas) |
| `freecad_mcp/operations/extended.py` | 16 operaciones nuevas (incluye `mirror_object`) |
| `freecad_mcp/operations/examples_ops.py` | 3 operaciones del registro de ejemplos (local; `load_example` abre el FCStd vía RPC) |
| `freecad_mcp/operations/prosthesis_ops.py` | `create_prosthesis`: protesis transradial modular segun normas ISO (socket Muenster, pylon OD20, muneca OD50, mano ISO 7250-1 P50; lado + escala) |
| `examples/` | Diseños registrados: `examples.json` (manifest) + FCStd + previews |
| `test_extended_tools.py` | Tests E2E (29 aserciones) contra FreeCAD real |

Requisito: FreeCAD (flatpak) con el addon **FreeCADMCP** activo
(`auto_start_rpc: true`, XML-RPC en `127.0.0.1:9875`).

## Tools nuevas (20)

`save_document`, `open_document`, `close_document`, `export_model`,
`get_camera`, `set_camera`, `fit_view`, `screenshot_current`, `set_color`,
`apply_fillet`, `apply_chamfer`, `boolean_op`, `measure`, `transform_object`,
`set_visibility`, `mirror_object`, `list_examples`, `get_example`,
`load_example`, `create_prosthesis`.

Catálogo completo en `../freecad_mcp_tools.json` (validador:
`../validate_freecad_mcp.py`).

## Registro de ejemplos

`examples/examples.json` guarda los diseños como ejemplos reutilizables
(metadatos, componentes, métricas, rutas al FCStd y a las previews). Se
sirven con `list_examples` (resumen), `get_example(id)` (ficha completa con
rutas absolutas) y `load_example(id)` (abre el FCStd en FreeCAD). Ejemplos
incluidos: `protesis-deportiva` (aprobada en 5 rondas) y
`pierna-transfemoral` (print-ready con STL, aprobada).

## 3. K-1 Hand (e-NABLE, GPLv3)

**Fuente**: K-1 Hand de Evan Kuester, proyecto e-NABLE, licencia GPLv3.
**Descripción**: Mano antropomórfica verificada, estéticamente elegante,
en uso en el catálogo e-NABLE y colección NIH 3D. No usa hardware metálico;
cordones embutidos. Requiere **atribución + nota de licencia GPLv3** para el
asset vendoreado (separado del código MIT del repo).

**Ensamblaje actual en FreeCAD** (doc `K1_Ensamble`, estado activo):
- 4 dedos (índice, mayor, anular, meñique) montados en ranuras knuckle de la palma
  con arco MCP anatómico (z‑top: índice 103.7, medio 105.6, anular 102.4,
  meñique 96). Bases sentadas en taladros ∥x del palm (y = 29.6/5.5 r≈2.7,
  y = 28.5; z = 60).
- Pulgar posicionado sobre post bracket palm (x world centro ≈199.07, y world
  centro ≈2.616, z 43–109, rotation identidad). Socket cuneiforme abierta hacia
  +z; abducción −30° alrededor X para tilt outward.
- Muñeca (Muneca): omitida del merge final; nuestro socket transradial cubre
  la articulación. Pieza original de cama: x[130.2,142.2] y[−27.7,−7.2] z[0,5.8].
- **Largo ensamblado aproximado**: 182 mm → escala factor 1.08 a 196 mm para P50
  (P50 = 1750 mm adulto). Factor de escala `scale=1` en `create_prosthesis`.

**Dimensiones ISO del emit** (mantener):
ISO 22523:2006, ISO 8548-3:2025, ISO 8549, ISO 13405-3, ISO 7250-1:2017,
ISO 9999 (06 18-06 27). ISO 10328 NO aplica (miembro inferior). Cotas estándar:
socket Muenster; adaptador OD30 M12; pylon OD20; muñeca Ø50 h26 TD W-20; mano
P50 196×88, palma 108, pulgar 65, dedos 82/88/78/63.

**Cita y licencia**: asset vendoreado debe incluir fichero `LICENSE` GPLv3 con
texto Atribución: "K-1 Hand by Evan Kuester, e-NABLE, GPLv3". El código del
repo sigue bajo licencia MIT.

**Estado de la integración**:
- Raw STLs (`Palm.stl`, `Finger_X.stl`, `Pinkie.stl`, `Thumb.stl`,
  `Wrist.stl`, `FingerPins.stl`) disponibles en `examples/stl/k1_hand/`
  (copia de trabajo; los originales estaban en `/tmp/opencode/proto/` de la
  sesión actual y no persisten en git).
- Merge offline + boolean union pendiente (next step): generar
  `mano_k1_ensamblada.stl`, actualizar `create_prosthesis` para importar malla
  → Part shape `Mano_Pasiva`, escalar a 196 mm (factor 1.08), orientar dedos
  −z / pulgar +x/+y, mirror X para `side=left`, actualizar asserts/standards.
- Tests actuales (`test_extended_tools.py` 29/29) siguen basándose en `Mano_Pasiva`
  diseño original; una vez mergeado y vendorizado el K-1 Hand, se actualizarán
  los asserts (der `xmax > 22`, izq `xmin < −22`, z 44..240) y los standards.

**Previews**: foto de referencia `K1_assembled.jpg` (descargada de NIH3D);
pueden generarse renders mediante `free-cad_get_view` (Isometric/ Front/ Right)
mientras el doc `K1_Ensamble` está activo.

**Cómo citar**: "K-1 Hand, Evan Kuester, e-NABLE, GPLv3". Ver `LICENSE` en el
directorio `examples/stl/k1_hand/` cuando esté vendorizado.

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
