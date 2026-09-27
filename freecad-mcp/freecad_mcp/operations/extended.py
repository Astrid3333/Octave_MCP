"""Operaciones nuevas del fork FreeCAD MCP (todas vía snippets en FreeCAD).

Cada operación construye un fragmento de Python que corre dentro de FreeCAD a
través de ``execute_code`` (XML-RPC), emite un dict por el marcador
``<<<MCP_JSON>>>...<<<MCP_END>>>`` y aquí se convierte en respuesta MCP.

Motivo de diseño: el addon FreeCADMCP solo expone ~12 métodos RPC; en lugar
de parchear el addon (se perdería al actualizar), las tools nuevas se
implementan como wrappers sobre ``execute_code``, que ya existe en el RPC.
"""

import json

from ..freecad_client import (
    _build_capture_code,
    _CAM_HELPERS,
    _FIX_RANGE_BODY,
    _SCENE_BBOX_HELPER,
    _SNIPPET_PREAMBLE,
)
from ..freecad_client import FreeCADConnection
from ..responses import ImageContent, ToolResponse, json_response, text_response


def _respond(data: dict | None, err: str | None, label: str) -> ToolResponse:
    if err:
        return text_response(f"{label}: {err}")
    if not data or not data.get("success", False):
        detail = (data or {}).get("error", "error desconocido")
        return text_response(f"{label} fallo: {detail}")
    payload = {k: v for k, v in data.items() if k not in ("image_b64",)}
    return json_response(payload)


def _run(freecad: FreeCADConnection, injected: str, body: str, label: str) -> ToolResponse:
    data, err = freecad.run_snippet(_SNIPPET_PREAMBLE + injected + body)
    return _respond(data, err, label)


# ---------------------------------------------------------------------------
# Documentos
# ---------------------------------------------------------------------------

_SAVE_BODY = '''
try:
    import os
    doc = FreeCAD.getDocument(DOC)
    if PATH:
        _dir = os.path.dirname(os.path.abspath(PATH))
        if _dir:
            os.makedirs(_dir, exist_ok=True)
        doc.saveAs(PATH)
    else:
        if not doc.FileName:
            raise ValueError("El documento nunca se guardo; pasa 'path'")
        doc.save()
    _mcp_emit({"success": True, "path": doc.FileName})
except Exception as e:
    _mcp_emit({"success": False, "error": str(e)})
'''


def save_document_operation(
    freecad: FreeCADConnection, doc_name: str, path: str | None = None
) -> ToolResponse:
    return _run(freecad, f"DOC = {doc_name!r}\nPATH = {path!r}\n", _SAVE_BODY, "save_document")


_OPEN_BODY = '''
try:
    import os
    p = os.path.abspath(PATH)
    if not os.path.exists(p):
        raise ValueError("No existe el archivo: " + p)
    doc = FreeCAD.openDocument(p)
    _mcp_emit({"success": True, "document": doc.Name,
               "documents": list(FreeCAD.listDocuments().keys())})
except Exception as e:
    _mcp_emit({"success": False, "error": str(e)})
'''


def open_document_operation(freecad: FreeCADConnection, path: str) -> ToolResponse:
    return _run(freecad, f"PATH = {path!r}\n", _OPEN_BODY, "open_document")


_CLOSE_BODY = '''
try:
    FreeCAD.closeDocument(NAME)
    _mcp_emit({"success": True, "documents": list(FreeCAD.listDocuments().keys())})
except Exception as e:
    _mcp_emit({"success": False, "error": str(e)})
'''


def close_document_operation(freecad: FreeCADConnection, doc_name: str) -> ToolResponse:
    return _run(freecad, f"NAME = {doc_name!r}\n", _CLOSE_BODY, "close_document")


# ---------------------------------------------------------------------------
# Exportación
# ---------------------------------------------------------------------------

_EXPORT_BODY = '''
try:
    import os
    ext = os.path.splitext(PATH)[1].lower()
    doc = FreeCAD.getDocument(DOC)
    if OBJECTS:
        objs, missing = [], []
        for n in OBJECTS:
            o = doc.getObject(n)
            if o is None:
                missing.append(n)
            else:
                objs.append(o)
        if missing:
            raise ValueError("Objetos inexistentes: " + ", ".join(missing))
    else:
        objs = [o for o in doc.Objects if hasattr(o, "Shape") and not o.Shape.isNull()]
    if not objs:
        raise ValueError("No hay objetos con Shape para exportar")
    _dir = os.path.dirname(os.path.abspath(PATH))
    if _dir:
        os.makedirs(_dir, exist_ok=True)
    if ext in (".step", ".stp", ".iges", ".igs"):
        import Import
        Import.export(objs, PATH)
    elif ext in (".stl", ".obj", ".ply", ".off", ".amf", ".3mf"):
        import Mesh
        Mesh.export(objs, PATH)
    elif ext in (".brep", ".brp"):
        import Part
        shapes = [o.Shape for o in objs]
        if len(shapes) == 1:
            shapes[0].exportBrep(PATH)
        else:
            Part.Compound(shapes).exportBrep(PATH)
    elif ext in (".fcstd",):
        doc.saveAs(PATH)
    else:
        raise ValueError(
            "Formato no soportado: " + ext + " (usa .step/.stp/.iges/.igs/"
            ".stl/.obj/.ply/.off/.amf/.3mf/.brep/.brp/.FCStd)")
    _mcp_emit({"success": True, "path": os.path.abspath(PATH),
               "bytes": os.path.getsize(PATH),
               "objects": [o.Name for o in objs]})
except Exception as e:
    _mcp_emit({"success": False, "error": str(e)})
'''


def export_model_operation(
    freecad: FreeCADConnection,
    doc_name: str,
    file_path: str,
    objects: list[str] | None = None,
) -> ToolResponse:
    injected = (
        f"DOC = {doc_name!r}\nPATH = {file_path!r}\nOBJECTS = {objects!r}\n"
    )
    return _run(freecad, injected, _EXPORT_BODY, "export_model")


# ---------------------------------------------------------------------------
# Cámara y vistas
# ---------------------------------------------------------------------------

_GET_CAMERA_BODY = _SCENE_BBOX_HELPER + _CAM_HELPERS + '''
try:
    ad = FreeCADGui.ActiveDocument
    view = ad.ActiveView if ad else None
    if view is None:
        raise RuntimeError("No hay vista activa")
    c = view.getCamera()
    bb = _mcp_scene_bbox()
    _mcp_emit({
        "success": True,
        "camera_type": view.getCameraType(),
        "position": _mcp_cam_vec(c, "position", 3),
        "orientation": _mcp_cam_vec(c, "orientation", 4),
        "nearDistance": _mcp_cam_num(c, "nearDistance"),
        "farDistance": _mcp_cam_num(c, "farDistance"),
        "height": _mcp_cam_num(c, "height"),
        "heightAngle": _mcp_cam_num(c, "heightAngle"),
        "focalDistance": _mcp_cam_num(c, "focalDistance"),
        "aspectRatio": _mcp_cam_num(c, "aspectRatio"),
        "scene": ({"center": [round(v, 3) for v in bb[0]],
                   "diag": round(bb[1], 3)} if bb else None),
    })
except Exception as e:
    _mcp_emit({"success": False, "error": str(e)})
'''


def get_camera_operation(freecad: FreeCADConnection) -> ToolResponse:
    return _run(freecad, "", _GET_CAMERA_BODY, "get_camera")


_SET_CAMERA_BODY = _CAM_HELPERS + '''
try:
    import time as _time
    ad = FreeCADGui.ActiveDocument
    view = ad.ActiveView if ad else None
    if view is None:
        raise RuntimeError("No hay vista activa")
    if CAM_TYPE:
        if CAM_TYPE not in ("Orthographic", "Perspective"):
            raise ValueError("camera_type debe ser 'Orthographic' o 'Perspective'")
        view.setCameraType(CAM_TYPE)
    c = view.getCamera()
    applied, ignored = {}, []
    if POSITION is not None:
        c2 = _mcp_cam_set_vec(c, "position", [float(v) for v in POSITION])
        if c2 is None:
            ignored.append("position")
        else:
            c = c2
            applied["position"] = POSITION
    if ORIENTATION is not None:
        if len(ORIENTATION) != 4:
            raise ValueError("orientation debe ser [axis_x, axis_y, axis_z, angle_rad]")
        c2 = _mcp_cam_set_vec(c, "orientation", [float(v) for v in ORIENTATION])
        if c2 is None:
            ignored.append("orientation")
        else:
            c = c2
            applied["orientation"] = ORIENTATION
    for key, val in (("height", HEIGHT), ("nearDistance", NEAR),
                     ("farDistance", FAR), ("focalDistance", FOCAL),
                     ("aspectRatio", ASPECT)):
        if val is not None:
            c2 = _mcp_cam_set_num(c, key, float(val))
            if c2 is None:
                ignored.append(key)
            else:
                c = c2
                applied[key] = float(val)
    view.setCamera(c)
    FreeCADGui.updateGui()
    _time.sleep(0.2)
    _mcp_emit({"success": True, "applied": applied, "ignored_fields": ignored,
               "camera": _mcp_cam_readback(view),
               "note": "near/far pueden ser reajustados automaticamente por Coin "
                       "(viewportMapping ADJUST_CAMERA) en el siguiente render"})
except Exception as e:
    _mcp_emit({"success": False, "error": str(e)})
'''


def set_camera_operation(
    freecad: FreeCADConnection,
    position: list[float] | None = None,
    orientation: list[float] | None = None,
    camera_type: str | None = None,
    height: float | None = None,
    near_distance: float | None = None,
    far_distance: float | None = None,
    focal_distance: float | None = None,
    aspect_ratio: float | None = None,
) -> ToolResponse:
    injected = (
        f"POSITION = {position!r}\n"
        f"ORIENTATION = {orientation!r}\n"
        f"CAM_TYPE = {camera_type!r}\n"
        f"HEIGHT = {height!r}\n"
        f"NEAR = {near_distance!r}\n"
        f"FAR = {far_distance!r}\n"
        f"FOCAL = {focal_distance!r}\n"
        f"ASPECT = {aspect_ratio!r}\n"
    )
    return _run(freecad, injected, _SET_CAMERA_BODY, "set_camera")


_FIT_VIEW_BODY = _FIX_RANGE_BODY + '''
try:
    import time as _time
    ad = FreeCADGui.ActiveDocument
    view = ad.ActiveView if ad else None
    if view is None:
        raise RuntimeError("No hay vista activa")
    if VIEW_NAME:
        fn = {"Isometric": "viewIsometric", "Front": "viewFront", "Top": "viewTop",
              "Right": "viewRight", "Back": "viewRear", "Left": "viewLeft",
              "Bottom": "viewBottom", "Dimetric": "viewDimetric",
              "Trimetric": "viewTrimetric"}.get(VIEW_NAME)
        if fn is None:
            raise ValueError("Vista invalida: " + str(VIEW_NAME))
        getattr(view, fn)()
    if FOCUS:
        doc = FreeCAD.ActiveDocument
        obj = doc.getObject(FOCUS) if doc else None
        if obj is None:
            raise ValueError("Objeto no existe: " + str(FOCUS))
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.addSelection(obj)
        FreeCADGui.SendMsgToActiveView("ViewSelection")
    else:
        view.fitAll()
    FreeCADGui.updateGui()
    _time.sleep(0.3)
    fix = _mcp_fix_range(view, MARGIN)
    _mcp_emit({"success": True, "view": VIEW_NAME, "focus": FOCUS,
               "camera_fix": fix, "camera": _mcp_cam_readback(view),
               "camera_type": view.getCameraType()})
except Exception as e:
    _mcp_emit({"success": False, "error": str(e)})
'''


def fit_view_operation(
    freecad: FreeCADConnection,
    view_name: str | None = None,
    focus_object: str | None = None,
    margin: float = 1.15,
) -> ToolResponse:
    injected = f"VIEW_NAME = {view_name!r}\nFOCUS = {focus_object!r}\nMARGIN = {margin!r}\n"
    return _run(freecad, injected, _FIT_VIEW_BODY, "fit_view")


def screenshot_current_operation(
    freecad: FreeCADConnection, width: int | None = None, height: int | None = None
) -> ToolResponse:
    """Captura la vista actual sin mover la cámara (saveImage puro)."""
    code = _build_capture_code(None, width, height, None, fit=False, fix=False, margin=1.15)
    data, err = freecad.run_snippet(code)
    if err:
        return text_response(f"screenshot_current: {err}")
    if not data or not data.get("success"):
        return text_response(
            f"screenshot_current fallo: {(data or {}).get('error', 'error desconocido')}"
        )
    text = json.dumps(
        {k: v for k, v in data.items() if k != "image_b64"},
        ensure_ascii=False, indent=2, default=str,
    )
    return [
        text_response(text)[0],
        ImageContent(type="image", data=data["image_b64"], mimeType="image/png"),
    ]


# ---------------------------------------------------------------------------
# Apariencia y modificación de formas
# ---------------------------------------------------------------------------

_SET_COLOR_BODY = '''
try:
    doc = FreeCAD.getDocument(DOC)
    o = doc.getObject(OBJ)
    if o is None:
        raise ValueError("Objeto no existe: " + OBJ)
    vo = getattr(o, "ViewObject", None)
    if vo is None:
        raise ValueError("El objeto no tiene ViewObject (requiere GUI)")
    applied = {}
    if COLOR:
        c = tuple(float(x) for x in COLOR)
        if len(c) not in (3, 4):
            raise ValueError("color debe ser [r,g,b] o [r,g,b,alpha] en 0..1")
        if any(v < 0 or v > 1 for v in c):
            raise ValueError("valores de color fuera de rango 0..1")
        vo.ShapeColor = c[:3]  # FreeCAD exige tupla, no lista
        applied["ShapeColor"] = list(c[:3])
        if len(c) == 4:
            vo.Transparency = int(round((1.0 - c[3]) * 100))
            applied["Transparency"] = vo.Transparency
    if TRANSP is not None:
        vo.Transparency = int(max(0, min(100, int(TRANSP))))
        applied["Transparency"] = vo.Transparency
    if LINE:
        lc = tuple(float(x) for x in LINE)[:3]
        vo.LineColor = lc
        applied["LineColor"] = list(lc)
    _mcp_emit({"success": True, "object": OBJ, "applied": applied})
except Exception as e:
    _mcp_emit({"success": False, "error": str(e)})
'''


def set_color_operation(
    freecad: FreeCADConnection,
    doc_name: str,
    obj_name: str,
    color: list[float] | None = None,
    transparency: int | None = None,
    line_color: list[float] | None = None,
) -> ToolResponse:
    injected = (
        f"DOC = {doc_name!r}\nOBJ = {obj_name!r}\nCOLOR = {color!r}\n"
        f"TRANSP = {transparency!r}\nLINE = {line_color!r}\n"
    )
    return _run(freecad, injected, _SET_COLOR_BODY, "set_color")


_FILLET_BODY = '''
try:
    doc = FreeCAD.getDocument(DOC)
    o = doc.getObject(OBJ)
    if o is None:
        raise ValueError("Objeto no existe: " + OBJ)
    sh = getattr(o, "Shape", None)
    if sh is None or sh.isNull():
        raise ValueError("El objeto no tiene Shape")
    if EDGES:
        idx = []
        for e in EDGES:
            i = int(e) - 1  # notacion UI: Edge1 -> indice 0
            if i < 0 or i >= len(sh.Edges):
                raise ValueError("Edge" + str(e) + " fuera de rango (1.." + str(len(sh.Edges)) + ")")
            idx.append(i)
    else:
        idx = list(range(len(sh.Edges)))
    if not idx:
        raise ValueError("El objeto no tiene aristas")
    new = sh.makeFillet(float(RADIUS), [sh.Edges[i] for i in idx])
    o.Shape = new
    doc.recompute()
    _mcp_emit({"success": True, "object": OBJ, "radius": float(RADIUS),
               "edges": [i + 1 for i in idx],
               "volume": round(new.Volume, 4), "valid": new.isValid()})
except Exception as e:
    _mcp_emit({"success": False, "error": str(e)})
'''


def apply_fillet_operation(
    freecad: FreeCADConnection,
    doc_name: str,
    obj_name: str,
    radius: float,
    edges: list[int] | None = None,
) -> ToolResponse:
    injected = f"DOC = {doc_name!r}\nOBJ = {obj_name!r}\nRADIUS = {radius!r}\nEDGES = {edges!r}\n"
    return _run(freecad, injected, _FILLET_BODY, "apply_fillet")


_CHAMFER_BODY = '''
try:
    doc = FreeCAD.getDocument(DOC)
    o = doc.getObject(OBJ)
    if o is None:
        raise ValueError("Objeto no existe: " + OBJ)
    sh = getattr(o, "Shape", None)
    if sh is None or sh.isNull():
        raise ValueError("El objeto no tiene Shape")
    if EDGES:
        idx = []
        for e in EDGES:
            i = int(e) - 1
            if i < 0 or i >= len(sh.Edges):
                raise ValueError("Edge" + str(e) + " fuera de rango (1.." + str(len(sh.Edges)) + ")")
            idx.append(i)
    else:
        idx = list(range(len(sh.Edges)))
    if not idx:
        raise ValueError("El objeto no tiene aristas")
    new = sh.makeChamfer(float(DIST), [sh.Edges[i] for i in idx])
    o.Shape = new
    doc.recompute()
    _mcp_emit({"success": True, "object": OBJ, "distance": float(DIST),
               "edges": [i + 1 for i in idx],
               "volume": round(new.Volume, 4), "valid": new.isValid()})
except Exception as e:
    _mcp_emit({"success": False, "error": str(e)})
'''


def apply_chamfer_operation(
    freecad: FreeCADConnection,
    doc_name: str,
    obj_name: str,
    distance: float,
    edges: list[int] | None = None,
) -> ToolResponse:
    injected = f"DOC = {doc_name!r}\nOBJ = {obj_name!r}\nDIST = {distance!r}\nEDGES = {edges!r}\n"
    return _run(freecad, injected, _CHAMFER_BODY, "apply_chamfer")


_BOOLEAN_BODY = '''
try:
    doc = FreeCAD.getDocument(DOC)
    b = doc.getObject(BASE)
    t = doc.getObject(TOOL)
    if b is None:
        raise ValueError("Objeto base no existe: " + BASE)
    if t is None:
        raise ValueError("Objeto tool no existe: " + TOOL)
    method = {"union": "fuse", "cut": "cut", "intersect": "common"}.get(OP)
    if method is None:
        raise ValueError("op debe ser union|cut|intersect")
    res = getattr(b.Shape, method)(t.Shape)
    name = NEW_NAME or (BASE + "_" + OP + "_" + TOOL)
    new = doc.addObject("Part::Feature", name)
    try:
        new.ViewObject.ShapeColor = b.ViewObject.ShapeColor
    except Exception:
        pass
    new.Shape = res
    if DELETE_IN:
        for nm in (BASE, TOOL):
            if doc.getObject(nm) is not None:
                doc.removeObject(nm)
    doc.recompute()
    _mcp_emit({"success": True, "object": new.Name, "operation": OP,
               "inputs": [] if DELETE_IN else [BASE, TOOL],
               "volume": round(res.Volume, 4), "valid": res.isValid(),
               "bbox_diag": round(res.BoundBox.DiagonalLength, 4)})
except Exception as e:
    _mcp_emit({"success": False, "error": str(e)})
'''


def boolean_op_operation(
    freecad: FreeCADConnection,
    doc_name: str,
    base_object: str,
    tool_object: str,
    operation: str,
    new_name: str | None = None,
    delete_inputs: bool = False,
) -> ToolResponse:
    injected = (
        f"DOC = {doc_name!r}\nBASE = {base_object!r}\nTOOL = {tool_object!r}\n"
        f"OP = {operation!r}\nNEW_NAME = {new_name!r}\nDELETE_IN = {delete_inputs!r}\n"
    )
    return _run(freecad, injected, _BOOLEAN_BODY, "boolean_op")


# ---------------------------------------------------------------------------
# Medición, transformación y visibilidad
# ---------------------------------------------------------------------------

_MEASURE_BODY = _SCENE_BBOX_HELPER + '''
try:
    def _bbox(sh):
        b = sh.BoundBox
        return {"min": [round(b.XMin, 4), round(b.YMin, 4), round(b.ZMin, 4)],
                "max": [round(b.XMax, 4), round(b.YMax, 4), round(b.ZMax, 4)],
                "size": [round(b.XLength, 4), round(b.YLength, 4), round(b.ZLength, 4)]}
    doc = FreeCAD.getDocument(DOC)
    if OBJ1 and OBJ2:
        o1, o2 = doc.getObject(OBJ1), doc.getObject(OBJ2)
        if o1 is None:
            raise ValueError("Objeto no existe: " + OBJ1)
        if o2 is None:
            raise ValueError("Objeto no existe: " + OBJ2)
        d, pts, _info = o1.Shape.distToShape(o2.Shape)
        p1, p2 = pts[0][0], pts[0][1]
        _mcp_emit({"success": True, "kind": "distance", "objects": [OBJ1, OBJ2],
                   "distance": round(float(d), 6),
                   "closest_points": {"on_" + OBJ1: [round(p1.x, 4), round(p1.y, 4), round(p1.z, 4)],
                                      "on_" + OBJ2: [round(p2.x, 4), round(p2.y, 4), round(p2.z, 4)]}})
    elif OBJ1:
        o = doc.getObject(OBJ1)
        if o is None:
            raise ValueError("Objeto no existe: " + OBJ1)
        sh = o.Shape
        if sh is None or sh.isNull():
            raise ValueError("El objeto no tiene Shape")
        try:
            com = [round(v, 4) for v in (sh.CenterOfMass.x, sh.CenterOfMass.y, sh.CenterOfMass.z)]
        except Exception:
            com = None
        _mcp_emit({"success": True, "kind": "properties", "object": OBJ1,
                   "bbox": _bbox(sh), "volume": round(sh.Volume, 4),
                   "area": round(float(getattr(sh, "Area", 0.0)), 4),
                   "center_of_mass": com,
                   "n_edges": len(sh.Edges), "n_faces": len(sh.Faces),
                   "n_vertices": len(sh.Vertexes), "valid": sh.isValid()})
    else:
        bb = _mcp_scene_bbox()
        if not bb:
            raise ValueError("No hay geometria en los documentos abiertos")
        center, diag = bb
        _mcp_emit({"success": True, "kind": "scene",
                   "center": [round(v, 4) for v in center],
                   "diag": round(diag, 4),
                   "documents": list(FreeCAD.listDocuments().keys())})
except Exception as e:
    _mcp_emit({"success": False, "error": str(e)})
'''


def measure_operation(
    freecad: FreeCADConnection,
    doc_name: str,
    object_name: str | None = None,
    object2_name: str | None = None,
) -> ToolResponse:
    injected = (
        f"DOC = {doc_name!r}\nOBJ1 = {object_name!r}\nOBJ2 = {object2_name!r}\n"
    )
    return _run(freecad, injected, _MEASURE_BODY, "measure")


_TRANSFORM_BODY = '''
try:
    doc = FreeCAD.getDocument(DOC)
    o = doc.getObject(OBJ)
    if o is None:
        raise ValueError("Objeto no existe: " + OBJ)
    pl = o.Placement
    applied = {}
    if R_AXIS is not None and R_ANGLE is not None:
        if len(R_AXIS) != 3:
            raise ValueError("rotate_axis debe ser [x, y, z]")
        axis = FreeCAD.Vector(float(R_AXIS[0]), float(R_AXIS[1]), float(R_AXIS[2]))
        rot = FreeCAD.Rotation(axis, float(R_ANGLE))
        if R_CENTER is not None:
            if len(R_CENTER) != 3:
                raise ValueError("rotate_center debe ser [x, y, z]")
            c = FreeCAD.Vector(float(R_CENTER[0]), float(R_CENTER[1]), float(R_CENTER[2]))
            pre = FreeCAD.Placement(c, rot) * FreeCAD.Placement(-c, FreeCAD.Rotation())
            pl = pre * pl
        else:
            pl = FreeCAD.Placement(FreeCAD.Vector(), rot) * pl
        applied["rotate_deg"] = float(R_ANGLE)
        applied["axis"] = R_AXIS
        if R_CENTER is not None:
            applied["center"] = R_CENTER
    if TRANSLATE is not None:
        if len(TRANSLATE) != 3:
            raise ValueError("translate debe ser [dx, dy, dz]")
        pl.Base = pl.Base + FreeCAD.Vector(
            float(TRANSLATE[0]), float(TRANSLATE[1]), float(TRANSLATE[2]))
        applied["translate"] = TRANSLATE
    if not applied:
        raise ValueError("Pasa translate y/o rotate_axis+rotate_angle_deg")
    o.Placement = pl
    doc.recompute()
    _mcp_emit({"success": True, "object": OBJ, "applied": applied,
               "placement": {
                   "base": [round(v, 4) for v in (pl.Base.x, pl.Base.y, pl.Base.z)],
                   "rotation_axis": [round(v, 6) for v in
                                     (pl.Rotation.Axis.x, pl.Rotation.Axis.y, pl.Rotation.Axis.z)],
                   "rotation_angle_rad": round(pl.Rotation.Angle, 6)}})
except Exception as e:
    _mcp_emit({"success": False, "error": str(e)})
'''


def transform_object_operation(
    freecad: FreeCADConnection,
    doc_name: str,
    obj_name: str,
    translate: list[float] | None = None,
    rotate_axis: list[float] | None = None,
    rotate_angle_deg: float | None = None,
    rotate_center: list[float] | None = None,
) -> ToolResponse:
    injected = (
        f"DOC = {doc_name!r}\nOBJ = {obj_name!r}\nTRANSLATE = {translate!r}\n"
        f"R_AXIS = {rotate_axis!r}\nR_ANGLE = {rotate_angle_deg!r}\n"
        f"R_CENTER = {rotate_center!r}\n"
    )
    return _run(freecad, injected, _TRANSFORM_BODY, "transform_object")


_VISIBILITY_BODY = '''
try:
    doc = FreeCAD.getDocument(DOC)
    updated, missing = [], []
    for n in OBJS:
        o = doc.getObject(n)
        if o is None:
            missing.append(n)
            continue
        o.Visibility = bool(VIS)
        updated.append(n)
    if missing:
        raise ValueError("Objetos inexistentes: " + ", ".join(missing))
    _mcp_emit({"success": True, "visible": bool(VIS), "updated": updated})
except Exception as e:
    _mcp_emit({"success": False, "error": str(e)})
'''


def set_visibility_operation(
    freecad: FreeCADConnection,
    doc_name: str,
    objects: list[str] | str,
    visible: bool = True,
) -> ToolResponse:
    objs = [objects] if isinstance(objects, str) else list(objects)
    injected = f"DOC = {doc_name!r}\nOBJS = {objs!r}\nVIS = {visible!r}\n"
    return _run(freecad, injected, _VISIBILITY_BODY, "set_visibility")


_MIRROR_BODY = '''
try:
    doc = FreeCAD.getDocument(DOC)
    o = doc.getObject(OBJ)
    if o is None:
        raise ValueError("Objeto no existe: " + OBJ)
    planes = {
        "XY": (FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1)),
        "XZ": (FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 1, 0)),
        "YZ": (FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(1, 0, 0)),
    }
    if PLANE not in planes:
        raise ValueError("plane debe ser XY, XZ o YZ")
    base, normal = planes[PLANE]
    if OFFSET:
        base = base + normal.multiply(float(OFFSET))
    mirrored = o.Shape.mirror(base, normal)
    if mirrored.isNull():
        raise ValueError("mirror devolvio una forma nula")
    if mirrored.Solids:
        mirrored = mirrored.Solids[0]
    name = (OBJ + "_mirror")
    if doc.getObject(name):
        doc.removeObject(name)
    new = doc.addObject("Part::Feature", name)
    new.Shape = mirrored
    if o.ViewObject is not None and new.ViewObject is not None:
        try:
            new.ViewObject.ShapeColor = o.ViewObject.ShapeColor
        except Exception:
            pass
    doc.recompute()
    _mcp_emit({
        "success": True, "object": new.Name, "source": OBJ, "plane": PLANE,
        "offset": float(OFFSET), "valid": mirrored.isValid(),
        "volume": mirrored.Volume,
        "bbox": [mirrored.BoundBox.XMin, mirrored.BoundBox.XMax,
                 mirrored.BoundBox.YMin, mirrored.BoundBox.YMax,
                 mirrored.BoundBox.ZMin, mirrored.BoundBox.ZMax],
    })
except Exception as e:
    _mcp_emit({"success": False, "error": str(e)})
'''


def mirror_object_operation(
    freecad: FreeCADConnection,
    doc_name: str,
    obj_name: str,
    plane: str,
    offset: float = 0.0,
) -> ToolResponse:
    injected = (
        f"DOC = {doc_name!r}\nOBJ = {obj_name!r}\n"
        f"PLANE = {plane!r}\nOFFSET = {offset!r}\n"
    )
    return _run(freecad, injected, _MIRROR_BODY, "mirror_object")
