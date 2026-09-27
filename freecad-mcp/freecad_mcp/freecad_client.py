"""Cliente XML-RPC del servidor FreeCADMCP.

Fork local de freecad-mcp 0.1.17 (MIT) con modificaciones:

- ``run_snippet``: ejecuta un fragmento de Python en FreeCAD y extrae el dict
  emitido por el marcador ``<<<MCP_JSON>>>...<<<MCP_END>>>``.
- ``capture_current_view``: captura la vista tal cual, sin mover la cámara.
- ``capture_fitted_view``: encuadra (fitAll) y corrige near/far/height con el
  bounding box real de la escena antes de capturar (arregla el bug de
  farDistance chico que recortaba modelos grandes).
- ``get_active_screenshot``: preset de vista + fit + fix de rango + captura.
"""

import json
import logging
import math
import xmlrpc.client
from typing import Any

logger = logging.getLogger("FreeCADMCPserver")

_MARKER_BEGIN = "<<<MCP_JSON>>>"
_MARKER_END = "<<<MCP_END>>>"

# Línea que inyecta el marcador JSON + utilidades mínimas en cada snippet.
_SNIPPET_PREAMBLE = f"""
import json as _json, re as _re, base64 as _b64, os as _os, tempfile as _tf, math as _math
import FreeCAD, FreeCADGui

def _mcp_emit(_d):
    print("{_MARKER_BEGIN}" + _json.dumps(_d, default=str) + "{_MARKER_END}")
"""

_VIEW_PRESETS = {
    "Isometric": "viewIsometric",
    "Front": "viewFront",
    "Top": "viewTop",
    "Right": "viewRight",
    "Back": "viewRear",
    "Left": "viewLeft",
    "Bottom": "viewBottom",
    "Dimetric": "viewDimetric",
    "Trimetric": "viewTrimetric",
}

# Devuelve (center, diag) del bounding box de todos los objetos con Shape
# visibles de todos los documentos abiertos, o None si no hay geometría.
_SCENE_BBOX_HELPER = '''
def _mcp_scene_bbox():
    xmin = ymin = zmin = float("inf")
    xmax = ymax = zmax = float("-inf")
    n = 0
    for _d in FreeCAD.listDocuments().values():
        for _o in _d.Objects:
            try:
                if not getattr(_o, "Visibility", True):
                    continue
                _sh = getattr(_o, "Shape", None)
                if _sh is None or _sh.isNull():
                    continue
                _b = _sh.BoundBox
                if _b.XLength == 0 and _b.YLength == 0 and _b.ZLength == 0:
                    continue
            except Exception:
                continue
            xmin = min(xmin, _b.XMin); xmax = max(xmax, _b.XMax)
            ymin = min(ymin, _b.YMin); ymax = max(ymax, _b.YMax)
            zmin = min(zmin, _b.ZMin); zmax = max(zmax, _b.ZMax)
            n += 1
    if n == 0:
        return None
    center = ((xmin + xmax) / 2.0, (ymin + ymax) / 2.0, (zmin + zmax) / 2.0)
    diag = _math.sqrt((xmax - xmin) ** 2 + (ymax - ymin) ** 2 + (zmax - zmin) ** 2)
    return center, diag
'''

# Parseo y edición de campos del string de cámara OpenInventor.
_CAM_HELPERS = '''
def _mcp_cam_num(c, key):
    m = _re.search(r"\\b" + key + r"\\s+([-\\d.eE]+)", c)
    return float(m.group(1)) if m else None

def _mcp_cam_vec(c, key, n):
    pat = r"\\b" + key + r"\\s+(" + r"\\s+".join([r"[-\\d.eE]+"] * n) + r")"
    m = _re.search(pat, c)
    return [float(x) for x in m.group(1).split()] if m else None

def _mcp_cam_set_num(c, key, val):
    if _re.search(r"\\b" + key + r"\\s+[-\\d.eE]+", c):
        return _re.sub(r"\\b" + key + r"\\s+[-\\d.eE]+",
                       key + " " + repr(round(float(val), 6)), c, count=1)
    return None

def _mcp_cam_set_vec(c, key, vals):
    pat = r"\\b" + key + r"\\s+" + r"\\s+".join([r"[-\\d.eE]+"] * len(vals))
    if _re.search(pat, c):
        return _re.sub(pat, key + " " + " ".join(repr(round(float(v), 6)) for v in vals),
                       c, count=1)
    return None

def _mcp_cam_set_str(c, key, val):
    if _re.search(r"\\b" + key + r"\\s+\\S+", c):
        return _re.sub(r"\\b" + key + r"\\s+\\S+", key + " " + str(val), c, count=1)
    return None

def _mcp_cam_readback(view):
    c = view.getCamera()
    rb = {}
    for k in ("position", "orientation", "height", "nearDistance",
              "farDistance", "focalDistance", "aspectRatio"):
        m = _re.search(r"\\b" + k + r"\\s+([^\\n\\}]+)", c)
        if m:
            toks = m.group(1).split()
            try:
                rb[k] = [float(t) for t in toks] if len(toks) > 1 else float(toks[0])
            except ValueError:
                rb[k] = m.group(1).strip()
    return rb
'''

# Corrige nearDistance/farDistance/height de la cámara actual usando el
# bounding box real de la escena: far >= dist(camara,center) + diag*margin
# y near = dist - diag*margin (con suelo 0.01). Emite el resultado.
_FIX_RANGE_BODY = _SCENE_BBOX_HELPER + _CAM_HELPERS + '''
def _mcp_fix_range(view, margin=1.15):
    c = view.getCamera()
    pos = _mcp_cam_vec(c, "position", 3)
    bb = _mcp_scene_bbox()
    if not pos or not bb:
        return {"applied": False, "reason": "sin camara o sin geometria"}
    center, diag = bb
    dist = _math.sqrt(sum((pos[i] - center[i]) ** 2 for i in range(3)))
    far_act = _mcp_cam_num(c, "farDistance") or 0.0
    far_new = max(far_act, dist + diag * margin)
    near_new = max(0.01, dist - diag * margin)
    if near_new >= far_new:
        near_new = max(0.01, far_new * 0.001)
    out = {}
    c2 = _mcp_cam_set_num(c, "farDistance", far_new)
    if c2 is not None:
        out["farDistance"] = round(far_new, 3)
    else:
        c2 = c
    c3 = _mcp_cam_set_num(c2, "nearDistance", near_new)
    if c3 is not None:
        out["nearDistance"] = round(near_new, 3)
        c2 = c3
    h = _mcp_cam_num(c2, "height")
    if h is not None:
        h_new = max(h, diag * margin)
        c4 = _mcp_cam_set_num(c2, "height", h_new)
        if c4 is not None:
            out["height"] = round(h_new, 3)
            c2 = c4
    if _mcp_cam_num(c2, "focalDistance") is not None:
        c5 = _mcp_cam_set_num(c2, "focalDistance", dist)
        if c5 is not None:
            c2 = c5
    if c2 != c:
        view.setCamera(c2)
    out["applied"] = True
    out["scene_diag"] = round(diag, 3)
    out["cam_distance"] = round(dist, 3)
    return out
'''

# Cuerpo de captura: preset opcional, fit (focus o todos), fix de rango y
# saveImage → base64. Variables inyectadas: _VIEW_NAME, _WIDTH, _HEIGHT,
# _FOCUS, _FIT, _FIX, _MARGIN.
_CAPTURE_BODY = _FIX_RANGE_BODY + '''
try:
    _ad = FreeCADGui.ActiveDocument
    _view = _ad.ActiveView if _ad else None
    if _view is None or not hasattr(_view, "saveImage"):
        _mcp_emit({"success": False, "error": "No hay vista activa con soporte de captura"})
    else:
        if _VIEW_NAME:
            _fn = {"Isometric": "viewIsometric", "Front": "viewFront", "Top": "viewTop",
                   "Right": "viewRight", "Back": "viewRear", "Left": "viewLeft",
                   "Bottom": "viewBottom", "Dimetric": "viewDimetric",
                   "Trimetric": "viewTrimetric"}.get(_VIEW_NAME)
            if _fn is None:
                raise ValueError("Vista invalida: " + str(_VIEW_NAME))
            getattr(_view, _fn)()
        if _FIT:
            if _FOCUS:
                _doc = FreeCAD.ActiveDocument
                _obj = _doc.getObject(_FOCUS) if _doc else None
                if _obj is not None:
                    FreeCADGui.Selection.clearSelection()
                    FreeCADGui.Selection.addSelection(_obj)
                    FreeCADGui.SendMsgToActiveView("ViewSelection")
                else:
                    _view.fitAll()
            else:
                _view.fitAll()
        FreeCADGui.updateGui()
        _fix_result = _mcp_fix_range(_view, _MARGIN) if _FIX else {"applied": False}
        _fd, _path = _tf.mkstemp(suffix=".png")
        _os.close(_fd)
        # saveImage(path, w, h) redimensiona el widget y dispara un
        # re-encuadre (ADJUST_CAMERA); se guarda/restaura la cámara.
        _cam_before = _view.getCamera()
        try:
            if _WIDTH and _HEIGHT:
                _view.saveImage(_path, int(_WIDTH), int(_HEIGHT))
            else:
                _view.saveImage(_path)
            with open(_path, "rb") as _f:
                _img_b64 = _b64.b64encode(_f.read()).decode("ascii")
            _mcp_emit({"success": True, "image_b64": _img_b64,
                       "camera_fix": _fix_result})
        finally:
            try:
                _view.setCamera(_cam_before)
                FreeCADGui.updateGui()
            except Exception:
                pass
            if _os.path.exists(_path):
                _os.remove(_path)
except Exception as _e:
    _mcp_emit({"success": False, "error": type(_e).__name__ + ": " + str(_e)})
'''


def _build_capture_code(
    view_name: str | None,
    width: int | None,
    height: int | None,
    focus_object: str | None,
    fit: bool,
    fix: bool,
    margin: float,
) -> str:
    return (
        _SNIPPET_PREAMBLE
        + f"_VIEW_NAME = {view_name!r}\n"
        + f"_WIDTH = {width!r}\n"
        + f"_HEIGHT = {height!r}\n"
        + f"_FOCUS = {focus_object!r}\n"
        + f"_FIT = {fit!r}\n"
        + f"_FIX = {fix!r}\n"
        + f"_MARGIN = {margin!r}\n"
        + _CAPTURE_BODY
    )


def _parse_marker(message: str) -> dict[str, Any] | None:
    if _MARKER_BEGIN not in message:
        return None
    raw = message.split(_MARKER_BEGIN, 1)[1].split(_MARKER_END, 1)[0]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


class FreeCADConnection:
    def __init__(self, host: str = "localhost", port: int = 9875):
        self.server = xmlrpc.client.ServerProxy(f"http://{host}:{port}", allow_none=True)

    def disconnect(self) -> None:
        transport = getattr(self.server, "_ServerProxy__transport", None)
        close = getattr(transport, "close", None)
        if callable(close):
            close()

    def ping(self) -> bool:
        return self.server.ping()

    # ------------------------------------------------------------------
    # Snippets: ejecutar Python en FreeCAD y leer el dict emitido
    # ------------------------------------------------------------------
    def run_snippet(self, code: str) -> tuple[dict[str, Any] | None, str | None]:
        """Ejecuta `code` (que debe llamar a _mcp_emit) y devuelve (dict, error)."""
        try:
            res = self.execute_code(code)
        except Exception as e:
            return None, f"error de conexion XML-RPC: {e}"
        if not res.get("success"):
            return None, str(res.get("error", "execute_code fallo"))
        data = _parse_marker(res.get("message", ""))
        if data is None:
            tail = res.get("message", "")[-300:]
            return None, f"el snippet no emitio JSON (salida: {tail})"
        return data, None

    # ------------------------------------------------------------------
    # Capturas de pantalla
    # ------------------------------------------------------------------
    def _capture(self, code: str) -> str | None:
        data, err = self.run_snippet(code)
        if err or not data or not data.get("success"):
            if err:
                logger.error(f"capture failed: {err}")
            else:
                logger.error(f"capture failed: {data}")
            return None
        return data.get("image_b64")

    def capture_current_view(self, width: int | None = None, height: int | None = None) -> str | None:
        """Captura la vista actual sin tocar la cámara (sin preset, sin fit)."""
        return self._capture(_build_capture_code(None, width, height, None, False, False, 1.15))

    def capture_fitted_view(self, width: int | None = None, height: int | None = None, margin: float = 1.15) -> str | None:
        """Encuadra la geometría (fitAll), corrige near/far/height y captura.

        Preserva la orientación de la cámara; solo ajusta distancia y rango
        de profundidad con el bounding box real de la escena.
        """
        return self._capture(_build_capture_code(None, width, height, None, True, True, margin))

    def get_active_screenshot(
        self,
        view_name: str = "Isometric",
        width: int | None = None,
        height: int | None = None,
        focus_object: str | None = None,
        margin: float = 1.15,
    ) -> str | None:
        """Preset de vista + encuadre + fix de rango + captura."""
        return self._capture(
            _build_capture_code(view_name, width, height, focus_object, True, True, margin)
        )

    # ------------------------------------------------------------------
    # API XML-RPC original (sin cambios respecto al upstream)
    # ------------------------------------------------------------------
    def create_document(self, name: str) -> dict[str, Any]:
        return self.server.create_document(name)

    def create_object(self, doc_name: str, obj_data: dict[str, Any]) -> dict[str, Any]:
        return self.server.create_object(doc_name, obj_data)

    def edit_object(self, doc_name: str, obj_name: str, obj_data: dict[str, Any]) -> dict[str, Any]:
        return self.server.edit_object(doc_name, obj_name, obj_data)

    def delete_object(self, doc_name: str, obj_name: str) -> dict[str, Any]:
        return self.server.delete_object(doc_name, obj_name)

    def insert_part_from_library(self, relative_path: str) -> dict[str, Any]:
        return self.server.insert_part_from_library(relative_path)

    def execute_code(self, code: str) -> dict[str, Any]:
        return self.server.execute_code(code)

    def get_objects(self, doc_name: str) -> list[dict[str, Any]]:
        return self.server.get_objects(doc_name)

    def get_object(self, doc_name: str, obj_name: str) -> dict[str, Any]:
        return self.server.get_object(doc_name, obj_name)

    def get_parts_list(self) -> list[str]:
        return self.server.get_parts_list()

    def list_documents(self) -> list[str]:
        return self.server.list_documents()
