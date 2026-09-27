"""Generación paramétrica de prótesis (tools de creación de prótesis).

Implementa ``create_prosthesis`` como wrapper sobre ``execute_code`` del RPC
del addon FreeCADMCP (mismo patrón que ``extended.py``).

Tipos soportados:
  - ``transradial``: prótesis endoesqueletal modular según normas ISO
    (socket Muenster, adaptador OD30, pylon OD20, unidad de muneca OD50,
    mano pasiva con medidas ISO 7250-1 P50), con lado (izq/der) y escala.
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

    # ------------------------------------------------------------------
    # Protesis transradial modular (endoesqueletica) con dimensiones de
    # normas ISO y componentes estandar de catalogo (adulto P50, estatura
    # de referencia 1750 mm; scale=1).
    #   ISO 22523:2006  - requisitos/ensayos de protesis de miembro externo
    #   ISO 8548-3:2025 - descripcion del miembro residual transradial
    #   ISO 8549        - vocabulario (socket, unidad de muneca, TD)
    #   ISO 13405-3     - descripcion de componentes de miembro superior
    #   ISO 7250-1      - antropometria (mano 196x88 mm, pulgar 65 mm)
    # Componentes: socket Muenster autoportante; adaptador de socket
    # OD 30 mm; pylon/tubo de conexion OD 20 mm; unidad de muneca
    # OD 50 mm (2 in) altura 26 mm con rosca TD W-20 (1/2-20 UNF);
    # mano pasiva estatica.
    # ------------------------------------------------------------------

    # --- socket transradial Muenster (loft de elipses + cavidad) ---------
    # brim proximal a nivel de epicondilos + 25 mm de trimline (88x72);
    # extremo distal 56x48; pared 6 mm; largo total 135 mm
    secs = [(390, 28, 24), (425, 33, 28), (470, 40, 33), (525, 44, 36)]
    cav = [(396, 22, 18), (425, 27, 22), (470, 34, 27), (525, 38, 30)]
    outer = [_elipse_wire(rx * K, ry * K, z * K) for (z, rx, ry) in secs]
    inner = [_elipse_wire(rx * K, ry * K, z * K) for (z, rx, ry) in cav]
    socket = Part.makeLoft(outer, True).cut(Part.makeLoft(inner, True))
    o = doc.addObject("Part::Feature", "Socket_Transradial")
    o.Shape = socket
    o.ViewObject.ShapeColor = (0.92, 0.9, 0.86)

    # --- adaptador de socket (OD 30 mm, rosca M12, catalogo) -------------
    ad = Part.makeCylinder(15 * K, 12 * K, Vector(0, 0, 378 * K))
    o = doc.addObject("Part::Feature", "Adaptador_Socket")
    o.Shape = ad
    o.ViewObject.ShapeColor = (0.55, 0.55, 0.58)

    # --- pylon / tubo de conexion de antebrazo (OD 20 mm estandar) -------
    pylon = Part.makeCylinder(10 * K, 112 * K, Vector(0, 0, 266 * K))
    o = doc.addObject("Part::Feature", "Pylon_Antebrazo")
    o.Shape = pylon
    o.ViewObject.ShapeColor = (0.74, 0.75, 0.78)

    # --- unidad de muneca (OD 50 mm adulto, altura de construccion 26) ---
    wrist = Part.makeCylinder(25 * K, 26 * K, Vector(0, 0, 240 * K))
    o = doc.addObject("Part::Feature", "Unidad_Muneca")
    o.Shape = wrist
    o.ViewObject.ShapeColor = (0.35, 0.35, 0.38)

    # --- mano pasiva estatica (ISO 7250-1 P50: 196 x 88 x ~30 mm) --------
    # palma/metacarpos z132..240 (longitud de palma 108); MCP en z132
    palm = Part.makeBox(88 * K, 30 * K, 108 * K, Vector(-44 * K, -15 * K, 132 * K))
    try:
        eds = [e for e in palm.Edges
               if len(e.Vertexes) == 2
               and abs(e.Vertexes[0].Point.z - e.Vertexes[1].Point.z) > 1e-6]
        if eds:
            p2 = palm.makeFillet(10 * K, eds)
            if p2.isValid():
                palm = p2
        top = [e for e in palm.Edges
               if len(e.Vertexes) == 2
               and all(abs(v.Point.z - 240 * K) < 1e-3 for v in e.Vertexes)]
        if top:
            p3 = palm.makeFillet(5 * K, top)
            if p3.isValid():
                palm = p3
    except Exception:
        pass
    hand = palm
    # dedos desde MCP (z132): anchos/longitudes antropometricas P50
    # (indice 82, mayor 88, anular 78, menique 63); punta esferica
    for (cx, w, tip) in ((33.5, 21.0, 50.0), (9.5, 21.0, 44.0),
                         (-13.5, 19.0, 54.0), (-35.0, 18.0, 69.0)):
        f = Part.makeBox(w * K, 22 * K, (132 - tip) * K,
                         Vector((cx - w / 2) * K, -11 * K, tip * K))
        try:
            cap = Part.makeSphere(w / 2.0 * K,
                                  Vector(cx * K, 0, (tip + w / 2.0) * K))
            f = f.fuse(cap)
        except Exception:
            pass
        hand = hand.fuse(f)
    # pulgar (longitud 65 mm, ~30 grados abajo-afuera): construido a la
    # derecha y reflejado si side=left (simetria exacta)
    thumb = Part.makeBox(18 * K, 16 * K, 65 * K, Vector(0, -8 * K, 0))
    thumb.Placement = FreeCAD.Placement(
        FreeCAD.Vector(0, 0, 0), FreeCAD.Rotation(FreeCAD.Vector(0, 1, 0), 150.0))
    thumb.translate(FreeCAD.Vector(30 * K, 0, 205 * K))
    try:
        thumb = thumb.fuse(
            Part.makeSphere(9 * K, Vector(62.5 * K, 0, 148.7 * K)))
    except Exception:
        pass
    if not RIGHT:
        thumb = thumb.mirror(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(1, 0, 0))
    hand = hand.fuse(thumb)
    try:
        hand = hand.removeSplitter()
    except Exception:
        pass
    o = doc.addObject("Part::Feature", "Mano_Pasiva")
    o.Shape = hand
    o.ViewObject.ShapeColor = (0.87, 0.62, 0.48)

    doc.recompute()

    objs = []
    total = 0.0
    for name in ("Socket_Transradial", "Adaptador_Socket", "Pylon_Antebrazo",
                 "Unidad_Muneca", "Mano_Pasiva"):
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
               "objects": objs, "total_volume": round(total, 1),
               "standards": {
                   "framework": [
                       "ISO 22523:2006 (requisitos y ensayos de protesis "
                       "de miembro externo)",
                       "ISO 8548-3:2025 (descripcion del miembro residual "
                       "tras amputacion de miembro superior)",
                       "ISO 8549-1/-2/-4 (vocabulario de protesica)",
                       "ISO 13405-3 (componentes de protesis de miembro "
                       "superior)",
                       "ISO 7250-1:2017 (antropometria de la mano)",
                       "ISO 9999 (clasificacion 06 18-06 27)"],
                   "components": [
                       "socket Muenster supracondilar autoportante",
                       "adaptador de socket OD 30 mm, rosca M12",
                       "pylon/tubo de conexion OD 20 mm (catalogo "
                       "endoesqueletico)",
                       "unidad de muneca OD 50 mm (2 in), altura 26 mm, "
                       "rosca TD W-20 1/2-20 UNF / M12",
                       "mano pasiva estatica, medidas ISO 7250-1 P50"],
                   "dimensions_mm": {
                       "hand_length": round(196 * K, 1),
                       "hand_breadth": round(88 * K, 1),
                       "thumb_length": round(65 * K, 1),
                       "palm_length": round(108 * K, 1),
                       "wrist_unit_diameter": round(50 * K, 1),
                       "wrist_unit_build_height": round(26 * K, 1),
                       "pylon_od": round(20 * K, 1),
                       "adapter_od": round(30 * K, 1),
                       "socket_length": round(135 * K, 1),
                       "elbow_to_wrist": round(260 * K, 1),
                       "reference_stature": round(1750 * K, 1)},
                   "note": "scale=1 corresponde a adulto P50 (estatura "
                           "1750 mm); alineacion de muneca estandar: 5 "
                           "grados de flexion + 5 de desviacion radial"}})
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
