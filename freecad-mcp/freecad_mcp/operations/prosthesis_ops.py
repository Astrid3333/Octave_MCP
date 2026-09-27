"""Generación paramétrica de prótesis (tools de creación de prótesis).

Implementa ``create_prosthesis`` como wrapper sobre ``execute_code`` del RPC
del addon FreeCADMCP (mismo patrón que ``extended.py``).

Tipos soportados:
  - ``transradial``: prótesis de antebrazo (socket + adaptador de muñeca +
    muñeca + mano estática con pulgar), con lado (izq/der) y escala.
"""

from __future__ import annotations

from ..freecad_client import _SNIPPET_PREAMBLE, FreeCADConnection
from ..responses import ToolResponse, json_response, text_response

SUPPORTED_TYPES = ("transradial",)

_TRANSRADIAL_BODY = '''
try:
    import math
    K = SCALE
    RIGHT = (SIDE == "right")

    NAME = "Protesis_Transradial_%s" % ("Der" if RIGHT else "Izq")
    if NAME in FreeCAD.listDocuments():
        doc = FreeCAD.getDocument(NAME)
        for _o in list(doc.Objects):
            doc.removeObject(_o.Name)
    else:
        doc = FreeCAD.newDocument(NAME)

    def _elipse_wire(rx, ry, z):
        edge = Part.Ellipse(FreeCAD.Vector(0, 0, z), rx, ry).toShape()
        return Part.Wire(edge)

    def _fillet_vert(shape, r):
        try:
            eds = [e for e in shape.Edges
                   if len(e.Vertexes) == 2
                   and abs(e.Vertexes[0].Point.z - e.Vertexes[1].Point.z) > 1e-6]
            if not eds:
                return shape
            out = shape.makeFillet(r, eds)
            if out.isValid() and out.Volume <= shape.Volume + 1.0:
                return out
        except Exception:
            pass
        return shape

    # --- socket transradial (loft de elipses + cavidad) ------------------
    secs = [(150, 30, 26), (170, 32, 27), (195, 35, 29),
            (220, 38, 31), (245, 42, 33), (270, 45, 35)]
    cav = [(154, 26.3, 22.3), (170, 28, 23), (195, 31, 25),
           (220, 34, 27), (245, 38, 29), (270, 41, 31)]
    outer = [_elipse_wire(rx * K, ry * K, z * K) for (z, rx, ry) in secs]
    inner = [_elipse_wire(rx * K, ry * K, z * K) for (z, rx, ry) in cav]
    socket = Part.makeLoft(outer, True).cut(Part.makeLoft(inner, True))
    o = doc.addObject("Part::Feature", "Socket_Transradial")
    o.Shape = socket
    o.ViewObject.ShapeColor = (0.92, 0.9, 0.86)

    # --- adaptador de muñeca (caja con chaflan) --------------------------
    ad = Part.makeBox(36 * K, 32 * K, 14 * K, Vector(-18 * K, -16 * K, 136 * K))
    try:
        eds = [e for e in ad.Edges
               if len(e.Vertexes) == 2
               and abs(e.Vertexes[0].Point.z - e.Vertexes[1].Point.z) > 1e-6]
        ad2 = ad.makeChamfer(2 * K, eds)
        if ad2.isValid():
            ad = ad2
    except Exception:
        pass
    o = doc.addObject("Part::Feature", "Adapter_Muneca")
    o.Shape = ad
    o.ViewObject.ShapeColor = (0.55, 0.55, 0.58)

    # --- eje de muñeca ---------------------------------------------------
    pin = Part.makeCylinder(8 * K, 20 * K, Vector(0, 0, 116 * K))
    o = doc.addObject("Part::Feature", "Muneca")
    o.Shape = pin
    o.ViewObject.ShapeColor = (0.4, 0.4, 0.42)

    # --- mano estática (palma + 4 dedos escalonados + pulgar) ------------
    palm = Part.makeBox(44 * K, 18 * K, 46 * K, Vector(-22 * K, -9 * K, 70 * K))
    try:
        eds = [e for e in palm.Edges
               if len(e.Vertexes) == 2
               and abs(e.Vertexes[0].Point.z - e.Vertexes[1].Point.z) > 1e-6]
        if eds:
            p2 = palm.makeFillet(5 * K, eds)
            if p2.isValid():
                palm = p2
        top = [e for e in palm.Edges
               if len(e.Vertexes) == 2
               and all(abs(v.Point.z - 116 * K) < 1e-3 for v in e.Vertexes)]
        if top:
            p3 = palm.makeFillet(4 * K, top)
            if p3.isValid():
                palm = p3
    except Exception:
        pass
    hand = palm
    # dedos escalonados con punta esferica (indice en +x, pulgar del lado +x)
    for (cx, w, tip) in ((16.0, 11.0, 22.0), (5.0, 11.0, 18.0),
                         (-6.5, 10.0, 24.0), (-17.0, 9.0, 32.0)):
        f = Part.makeBox(w * K, 16 * K, (70 - tip) * K,
                         Vector((cx - w / 2) * K, -8 * K, tip * K))
        try:
            cap = Part.makeSphere(w / 2.0 * K, Vector(cx * K, 0, tip * K))
            f = f.fuse(cap)
        except Exception:
            pass
        hand = hand.fuse(f)
    # pulgar oponible: se construye a la derecha (45° abajo-afuera) y se
    # refleja si side=left para garantizar simetría exacta
    thumb = Part.makeBox(12 * K, 15 * K, 34 * K, Vector(0, -7.5 * K, 0))
    thumb.Placement = FreeCAD.Placement(
        FreeCAD.Vector(0, 0, 0), FreeCAD.Rotation(FreeCAD.Vector(0, 1, 0), 135.0))
    thumb.translate(FreeCAD.Vector(18 * K, 0, 90 * K))
    try:
        thumb = thumb.fuse(
            Part.makeSphere(6 * K, Vector(37.8 * K, 0, 61.7 * K)))
    except Exception:
        pass
    if not RIGHT:
        thumb = thumb.mirror(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(1, 0, 0))
    hand = hand.fuse(thumb)
    try:
        hand = hand.removeSplitter()
    except Exception:
        pass
    o = doc.addObject("Part::Feature", "Mano")
    o.Shape = hand
    o.ViewObject.ShapeColor = (0.87, 0.62, 0.48)

    doc.recompute()

    objs = []
    total = 0.0
    for name in ("Socket_Transradial", "Adapter_Muneca", "Muneca", "Mano"):
        sh = doc.getObject(name).Shape
        if sh.isNull() or not sh.isValid() or sh.Volume <= 0:
            raise ValueError("forma invalida en %s" % name)
        b = sh.BoundBox
        v = round(sh.Volume, 1)
        total += sh.Volume
        objs.append({"name": name, "volume": v,
                     "bbox": [round(b.XMin, 1), round(b.XMax, 1),
                              round(b.YMin, 1), round(b.YMax, 1),
                              round(b.ZMin, 1), round(b.ZMax, 1)]})

    _mcp_emit({"success": True, "prosthesis_type": "transradial",
               "document": doc.Name, "side": SIDE, "scale": SCALE,
               "objects": objs, "total_volume": round(total, 1)})
except Exception as _e:
    import traceback
    _mcp_emit({"success": False,
               "error": type(_e).__name__ + ": " + str(_e),
               "trace": traceback.format_exc()[-400:]})
'''


def create_prosthesis_operation(
    freecad: FreeCADConnection,
    prosthesis_type: str = "transradial",
    side: str = "right",
    scale: float = 1.0,
) -> ToolResponse:
    """Crea una prótesis paramétrica en un documento nuevo de FreeCAD."""
    ptype = (prosthesis_type or "").strip().lower()
    if ptype not in SUPPORTED_TYPES:
        return text_response(
            f"create_prosthesis: tipo no soportado: {prosthesis_type!r}; "
            f"disponibles: {list(SUPPORTED_TYPES)}"
        )
    side_n = (side or "").strip().lower()
    if side_n not in ("right", "left"):
        return text_response(
            f"create_prosthesis: side debe ser 'right' o 'left', recibido: {side!r}"
        )
    try:
        scale_f = float(scale)
    except (TypeError, ValueError):
        return text_response(f"create_prosthesis: scale no es numerico: {scale!r}")
    if not (0.5 <= scale_f <= 2.0):
        return text_response(
            f"create_prosthesis: scale fuera de rango [0.5, 2.0]: {scale_f}"
        )

    injected = (
        f"SCALE = {scale_f!r}\n"
        f"SIDE = {side_n!r}\n"
    )
    data, err = freecad.run_snippet(_SNIPPET_PREAMBLE + injected + _TRANSRADIAL_BODY)
    if err:
        return text_response(f"create_prosthesis: {err}")
    if not data or not data.get("success", False):
        detail = (data or {}).get("error", "error desconocido")
        trace = (data or {}).get("trace", "")
        return text_response(f"create_prosthesis fallo: {detail}\n{trace}")
    return json_response(data)
