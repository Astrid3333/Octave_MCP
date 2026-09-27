#!/usr/bin/env python3
"""Tests E2E del fork FreeCAD MCP contra FreeCAD corriendo (RPC localhost:9875).

Ejecutar con FreeCAD abierto y el addon FreeCADMCP activo:

    /home/astrid/.local/share/pipx/venvs/freecad-mcp/bin/python test_extended_tools.py

Cubre las 15 tools nuevas del fork (las 11 upstream se validan por separado).
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from freecad_mcp.freecad_client import FreeCADConnection
from freecad_mcp.operations import (  # noqa: E402
    apply_fillet_operation,
    boolean_op_operation,
    close_document_operation,
    create_prosthesis_operation,
    export_model_operation,
    fit_view_operation,
    get_camera_operation,
    get_example_operation,
    list_examples_operation,
    load_example_operation,
    measure_operation,
    mirror_object_operation,
    open_document_operation,
    save_document_operation,
    screenshot_current_operation,
    set_camera_operation,
    set_color_operation,
    set_visibility_operation,
    transform_object_operation,
)

DOC = "MCP_Test"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_test_out")

RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def payload(resp) -> dict:
    """Extrae el JSON de una ToolResponse de texto."""
    for item in resp:
        if getattr(item, "type", None) == "text":
            try:
                return json.loads(item.text)
            except json.JSONDecodeError:
                return {"_text": item.text}
    return {}


def has_image(resp) -> bool:
    return any(getattr(i, "type", None) == "image" for i in resp)


def stable_position(conn, tries: int = 12, delay: float = 0.4):
    """Posición de cámara estable (dos lecturas consecutivas iguales).

    El fitAll de fit_view puede surtir efecto con retardo (evento diferido
    tras create_object), así que se espera estabilidad antes de medir.
    """
    prev = None
    for _ in range(tries):
        p = payload(get_camera_operation(conn)).get("position")
        if p is not None and prev == p:
            return p
        prev = p
        time.sleep(delay)
    return prev


def main() -> int:
    conn = FreeCADConnection()
    if not conn.ping():
        print("FAIL: FreeCAD RPC no responde en localhost:9875")
        return 1

    os.makedirs(OUT_DIR, exist_ok=True)
    t0 = time.time()

    # Limpieza de corridas previas: cerrar todos los documentos
    for name in conn.list_documents():
        conn.server.execute_code(f"FreeCAD.closeDocument({name!r})")

    # --- documentos -------------------------------------------------------
    resp = conn.create_document(DOC)
    record("create_document", resp.get("success") is True, str(resp.get("document_name")))

    box_data = {"Name": "Base", "Type": "Part::Box",
                "Properties": {"Length": 40, "Width": 30, "Height": 20}, "Analysis": None}
    resp = conn.create_object(DOC, box_data)
    record("create_object(box)", resp.get("success") is True, str(resp.get("error", "")))

    cyl_data = {"Name": "Tool", "Type": "Part::Cylinder",
                "Properties": {"Radius": 8, "Height": 50,
                               "Placement": {"Base": {"x": 20, "y": 15, "z": -15},
                                             "Rotation": {"Axis": {"x": 0, "y": 0, "z": 1},
                                                          "Angle": 0}}},
                "Analysis": None}
    resp = conn.create_object(DOC, cyl_data)
    record("create_object(cylinder)", resp.get("success") is True, str(resp.get("error", "")))

    # --- cámara ------------------------------------------------------------
    from freecad_mcp.freecad_client import _SNIPPET_PREAMBLE
    data, err = conn.run_snippet(_SNIPPET_PREAMBLE + "_mcp_emit({'success': True})\n")
    record("run_snippet(preamble)", err is None and data.get("success") is True, str(err))

    resp = get_camera_operation(conn)
    cam = payload(resp)
    record("get_camera", cam.get("success") is True,
           f"type={cam.get('camera_type')} far={cam.get('farDistance')} scene={cam.get('scene')}")

    resp = fit_view_operation(conn, view_name="Isometric")
    fit = payload(resp)
    fix = fit.get("camera_fix", {})
    record("fit_view", fit.get("success") is True and fix.get("applied") is True,
           f"far={fix.get('farDistance')} height={fix.get('height')} diag={fix.get('scene_diag')}")
    fit_pos = stable_position(conn)

    resp = screenshot_current_operation(conn, width=480, height=360)
    record("screenshot_current", has_image(resp), "")

    pos2 = stable_position(conn)
    # screenshot no debe mover la cámara: posición estable tras fit vs tras screenshot
    same_pos = fit_pos is not None and pos2 is not None and all(
        abs(a - b) < 1e-6 for a, b in zip(fit_pos, pos2)
    )
    record("screenshot no mueve camara", same_pos,
           f"pos {fit_pos} -> {pos2}")

    # set_camera: position/orientation deben persistir (near/far los reajusta Coin)
    resp = set_camera_operation(
        conn, position=[150.0, -150.0, 120.0],
        orientation=[0.35355339, 0.35355339, 0.8660254, 1.5707963],
        far_distance=100000.0,
    )
    sc = payload(resp)
    rb = sc.get("camera") or {}
    pos_rb = rb.get("position")
    ok_pos = pos_rb is not None and all(
        abs(a - b) < 1e-3 for a, b in zip(pos_rb, [150.0, -150.0, 120.0])
    )
    record("set_camera", sc.get("success") is True and ok_pos,
           f"applied={sc.get('applied')} readback_pos={pos_rb} "
           f"far_in_readback={rb.get('farDistance')}")

    # restaurar encuadre
    fit_view_operation(conn, view_name="Isometric")

    # --- medida ------------------------------------------------------------
    resp = measure_operation(conn, DOC, "Base")
    m1 = payload(resp)
    record("measure(propiedades)", m1.get("success") is True and abs(m1.get("volume", 0) - 24000) < 1e-6,
           f"volume={m1.get('volume')}")

    resp = measure_operation(conn, DOC, "Base", "Tool")
    m2 = payload(resp)
    record("measure(distancia)", m2.get("success") is True and "distance" in m2,
           f"distance={m2.get('distance')}")

    resp = measure_operation(conn, DOC)
    m3 = payload(resp)
    record("measure(escena)", m3.get("success") is True and m3.get("kind") == "scene",
           f"diag={m3.get('diag')}")

    # --- apariencia --------------------------------------------------------
    resp = set_color_operation(conn, DOC, "Base", color=[0.2, 0.4, 0.8], transparency=25)
    c1 = payload(resp)
    record("set_color", c1.get("success") is True and c1.get("applied", {}).get("ShapeColor") == [0.2, 0.4, 0.8],
           str(c1.get("applied")))

    # --- booleano ----------------------------------------------------------
    resp = boolean_op_operation(conn, DOC, "Base", "Tool", "cut", new_name="BaseCut",
                                delete_inputs=False)
    b = payload(resp)
    record("boolean_op(cut)", b.get("success") is True and b.get("valid") is True,
           f"vol={b.get('volume')}")

    # --- fillet ------------------------------------------------------------
    resp = apply_fillet_operation(conn, DOC, "BaseCut", radius=2.0)
    f = payload(resp)
    record("apply_fillet", f.get("success") is True and f.get("valid") is True,
           f"vol={f.get('volume')} edges={len(f.get('edges', []))}")

    # --- transformación ----------------------------------------------------
    resp = transform_object_operation(conn, DOC, "Tool", translate=[0, 0, 7],
                                      rotate_axis=[0, 0, 1], rotate_angle_deg=45)
    tr = payload(resp)
    record("transform_object", tr.get("success") is True and tr.get("applied", {}).get("rotate_deg") == 45,
           f"base={tr.get('placement', {}).get('base')}")

    # --- visibilidad -------------------------------------------------------
    resp = set_visibility_operation(conn, DOC, ["Tool"], visible=False)
    v = payload(resp)
    record("set_visibility", v.get("success") is True and v.get("updated") == ["Tool"], str(v))

    # --- exportación -------------------------------------------------------
    step_path = os.path.join(OUT_DIR, "test_model.step")
    stl_path = os.path.join(OUT_DIR, "test_model.stl")
    resp = export_model_operation(conn, DOC, step_path, objects=["BaseCut"])
    e1 = payload(resp)
    record("export_model(step)", e1.get("success") is True and os.path.exists(step_path),
           f"bytes={e1.get('bytes')}")

    resp = export_model_operation(conn, DOC, stl_path, objects=["BaseCut"])
    e2 = payload(resp)
    record("export_model(stl)", e2.get("success") is True and os.path.exists(stl_path),
           f"bytes={e2.get('bytes')}")

    # --- guardado / apertura / cierre -------------------------------------
    fcstd_path = os.path.join(OUT_DIR, "test_model.FCStd")
    resp = save_document_operation(conn, DOC, fcstd_path)
    s1 = payload(resp)
    record("save_document", s1.get("success") is True and os.path.exists(fcstd_path),
           str(s1.get("path")))

    conn.server.execute_code(f"FreeCAD.closeDocument({DOC!r})")
    resp = open_document_operation(conn, fcstd_path)
    o1 = payload(resp)
    opened = o1.get("document")
    record("open_document", o1.get("success") is True and opened in (o1.get("documents") or []),
           str(o1.get("documents")))

    resp = measure_operation(conn, opened or DOC, "BaseCut")
    m4 = payload(resp)
    record("documento reabierto", m4.get("success") is True, f"vol={m4.get('volume')}")

    # --- espejo ------------------------------------------------------------
    doc_open = opened or DOC
    resp = measure_operation(conn, doc_open, "BaseCut")
    mb = payload(resp)
    bmin = mb.get("bbox", {}).get("min", [])
    bmax = mb.get("bbox", {}).get("max", [])
    v0 = mb.get("volume", 0)
    resp = mirror_object_operation(conn, doc_open, "BaseCut", plane="XZ")
    mi = payload(resp)
    bb = mi.get("bbox") or []
    ok_mirror = (
        mi.get("success") is True
        and mi.get("valid") is True
        and len(bb) == 6
        and abs(mi.get("volume", 0) - v0) < 1e-3
        and len(bmin) == 3
        and abs(bb[2] + bmax[1]) < 1e-6
        and abs(bb[3] + bmin[1]) < 1e-6
        and abs(bb[0] - bmin[0]) < 1e-6
        and abs(bb[1] - bmax[0]) < 1e-6
    )
    record("mirror_object", ok_mirror,
           f"valid={mi.get('valid')} vol={mi.get('volume')} bbox={bb}")

    # limpieza: cerrar doc de prueba
    if opened:
        close_document_operation(conn, opened)

    # --- registro de ejemplos (local, sin RPC) ----------------------------
    resp = list_examples_operation()
    lx = payload(resp)
    ids = [e.get("id") for e in lx.get("examples", [])]
    record("list_examples", lx.get("success") is True and lx.get("count", 0) >= 2
           and {"protesis-deportiva", "pierna-transfemoral"} <= set(ids),
           f"count={lx.get('count')} ids={ids}")

    resp = get_example_operation("protesis-deportiva")
    gx = payload(resp)
    record("get_example", gx.get("success") is True and gx.get("file_exists") is True
           and gx.get("metrics", {}).get("total_volume_mm3", 0) > 0,
           f"file={gx.get('file_exists')} previews={gx.get('previews_exist')}")

    resp = get_example_operation("pierna-transfemoral")
    gx2 = payload(resp)
    record("get_example(pierna)", gx2.get("success") is True and gx2.get("file_exists") is True
           and gx2.get("metrics", {}).get("total_volume_mm3", 0) > 0
           and all(gx2.get("previews_exist", [])),
           f"file={gx2.get('file_exists')} previews={gx2.get('previews_exist')}")

    resp = load_example_operation(conn, "protesis-deportiva")
    ld = payload(resp)
    record("load_example", ld.get("success") is True
           and ld.get("example_id") == "protesis-deportiva",
           f"doc={ld.get('document')} file={bool(ld.get('example_file'))}")
    if ld.get("document"):
        close_document_operation(conn, ld["document"])

    # --- create_prosthesis (transradial) ---------------------------------
    resp = create_prosthesis_operation(conn, "transradial", "right", 1.0)
    cp = payload(resp)
    objs_r = cp.get("objects") or []
    bb_r = (next((o for o in objs_r if o.get("name") == "Mano"), {}) or {}).get("bbox") or []
    ok_r = (cp.get("success") is True and len(objs_r) >= 4
            and all(o.get("volume", 0) > 0 for o in objs_r)
            and len(bb_r) == 6 and bb_r[1] > 22.0)
    record("create_prosthesis(der)", ok_r,
           f"doc={cp.get('document')} objs={len(objs_r)} "
           f"total={cp.get('total_volume')} mano_bbox={bb_r}")

    resp2 = create_prosthesis_operation(conn, "transradial", "left", 0.8)
    cp2 = payload(resp2)
    objs_l = cp2.get("objects") or []
    bb_l = (next((o for o in objs_l if o.get("name") == "Mano"), {}) or {}).get("bbox") or []
    ok_l = (cp2.get("success") is True and len(objs_l) >= 4
            and len(bb_l) == 6 and bb_l[0] < -22.0
            and cp2.get("total_volume", 0) < cp.get("total_volume", 0))
    record("create_prosthesis(izq, escala 0.8)", ok_l,
           f"doc={cp2.get('document')} objs={len(objs_l)} "
           f"total={cp2.get('total_volume')} mano_bbox={bb_l}")

    for dname in (cp.get("document"), cp2.get("document")):
        if dname:
            close_document_operation(conn, dname)

    elapsed = time.time() - t0
    fails = [r for r in RESULTS if not r[1]]
    print(f"\n{len(RESULTS) - len(fails)}/{len(RESULTS)} PASS en {elapsed:.1f}s")
    if fails:
        print("FALLAS:")
        for name, _, detail in fails:
            print(f"  - {name}: {detail}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
