import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, Literal

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ImageContent, TextContent

from .freecad_client import FreeCADConnection
from .operations import (
    apply_chamfer_operation,
    apply_fillet_operation,
    boolean_op_operation,
    close_document_operation,
    create_document_operation,
    create_object_operation,
    delete_object_operation,
    edit_object_operation,
    execute_code_operation,
    export_model_operation,
    fit_view_operation,
    get_camera_operation,
    get_example_operation,
    get_object_operation,
    get_objects_operation,
    get_parts_list_operation,
    get_view_operation,
    insert_part_from_library_operation,
    list_documents_operation,
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
from .prompt_text import ASSET_CREATION_STRATEGY
from .server_state import ServerState


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("FreeCADMCPserver")

state = ServerState()


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    try:
        logger.info("FreeCADMCP server starting up")
        try:
            _ = get_freecad_connection()
            logger.info("Successfully connected to FreeCAD on startup")
        except Exception as e:
            logger.warning(f"Could not connect to FreeCAD on startup: {str(e)}")
            logger.warning(
                "Make sure the FreeCAD addon is running before using FreeCAD resources or tools"
            )
        yield {}
    finally:
        if state.freecad_connection:
            logger.info("Disconnecting from FreeCAD on shutdown")
            state.freecad_connection.disconnect()
            state.freecad_connection = None
        logger.info("FreeCADMCP server shut down")


mcp = FastMCP(
    "FreeCADMCP",
    instructions="FreeCAD integration through the Model Context Protocol",
    lifespan=server_lifespan,
)


def get_freecad_connection() -> FreeCADConnection:
    """Get or create a persistent FreeCAD connection"""
    if state.freecad_connection is None:
        state.freecad_connection = FreeCADConnection(host=state.rpc_host, port=9875)
        if not state.freecad_connection.ping():
            logger.error("Failed to ping FreeCAD")
            state.freecad_connection = None
            raise Exception(
                "Failed to connect to FreeCAD. Make sure the FreeCAD addon is running."
            )
    return state.freecad_connection


@mcp.tool()
def create_document(ctx: Context, name: str) -> list[TextContent]:
    """Create a new document in FreeCAD.

    Args:
        name: The name of the document to create.

    Returns:
        A message indicating the success or failure of the document creation.

    Examples:
        If you want to create a document named "MyDocument", you can use the following data.
        ```json
        {
            "name": "MyDocument"
        }
        ```
    """
    return create_document_operation(get_freecad_connection(), name)


@mcp.tool()
def create_object(
    ctx: Context,
    doc_name: str,
    obj_type: str,
    obj_name: str,
    analysis_name: str | None = None,
    obj_properties: dict[str, Any] = None,
) -> list[TextContent | ImageContent]:
    """Create a new object in FreeCAD.
    Object type is starts with "Part::" or "Draft::" or "PartDesign::" or "Fem::".

    Args:
        doc_name: The name of the document to create the object in.
        obj_type: The type of the object to create (e.g. 'Part::Box', 'Part::Cylinder', 'Draft::Circle', 'PartDesign::Body', etc.).
        obj_name: The name of the object to create.
        obj_properties: The properties of the object to create.

    Returns:
        A message indicating the success or failure of the object creation and a screenshot of the object.

    Examples:
        If you want to create a cylinder with a height of 30 and a radius of 10, you can use the following data.
        ```json
        {
            "doc_name": "MyCylinder",
            "obj_name": "Cylinder",
            "obj_type": "Part::Cylinder",
            "obj_properties": {
                "Height": 30,
                "Radius": 10,
                "Placement": {
                    "Base": {
                        "x": 10,
                        "y": 10,
                        "z": 0
                    },
                    "Rotation": {
                        "Axis": {
                            "x": 0,
                            "y": 0,
                            "z": 1
                        },
                        "Angle": 45
                    }
                },
                "ViewObject": {
                    "ShapeColor": [0.5, 0.5, 0.5, 1.0]
                }
            }
        }
        ```

        If you want to create a circle with a radius of 10, you can use the following data.
        ```json
        {
            "doc_name": "MyCircle",
            "obj_name": "Circle",
            "obj_type": "Draft::Circle",
        }
        ```

        If you want to create a FEM analysis, you can use the following data.
        ```json
        {
            "doc_name": "MyFEMAnalysis",
            "obj_name": "FemAnalysis",
            "obj_type": "Fem::AnalysisPython",
        }
        ```

        If you want to create a FEM constraint, you can use the following data.
        ```json
        {
            "doc_name": "MyFEMConstraint",
            "obj_name": "FemConstraint",
            "obj_type": "Fem::ConstraintFixed",
            "analysis_name": "MyFEMAnalysis",
            "obj_properties": {
                "References": [
                    {
                        "object_name": "MyObject",
                        "face": "Face1"
                    }
                ]
            }
        }
        ```

        If you want to create a FEM mechanical material, you can use the following data.
        ```json
        {
            "doc_name": "MyFEMAnalysis",
            "obj_name": "FemMechanicalMaterial",
            "obj_type": "Fem::MaterialCommon",
            "analysis_name": "MyFEMAnalysis",
            "obj_properties": {
                "Material": {
                    "Name": "MyMaterial",
                    "Density": "7900 kg/m^3",
                    "YoungModulus": "210 GPa",
                    "PoissonRatio": 0.3
                }
            }
        }
        ```

        If you want to create a FEM mesh, you can use the following data.
        The `Part` property is required.
        ```json
        {
            "doc_name": "MyFEMMesh",
            "obj_name": "FemMesh",
            "obj_type": "Fem::FemMeshGmsh",
            "analysis_name": "MyFEMAnalysis",
            "obj_properties": {
                "Part": "MyObject",
                "ElementSizeMax": 10,
                "ElementSizeMin": 0.1,
                "MeshAlgorithm": 2
            }
        }
        ```
    """
    return create_object_operation(
        get_freecad_connection(),
        state.only_text_feedback,
        doc_name,
        obj_type,
        obj_name,
        analysis_name,
        obj_properties,
    )


@mcp.tool()
def edit_object(
    ctx: Context, doc_name: str, obj_name: str, obj_properties: dict[str, Any]
) -> list[TextContent | ImageContent]:
    """Edit an object in FreeCAD.
    This tool is used when the `create_object` tool cannot handle the object creation.

    Args:
        doc_name: The name of the document to edit the object in.
        obj_name: The name of the object to edit.
        obj_properties: The properties of the object to edit.

    Returns:
        A message indicating the success or failure of the object editing and a screenshot of the object.
    """
    return edit_object_operation(
        get_freecad_connection(),
        state.only_text_feedback,
        doc_name,
        obj_name,
        obj_properties,
    )


@mcp.tool()
def delete_object(ctx: Context, doc_name: str, obj_name: str) -> list[TextContent | ImageContent]:
    """Delete an object in FreeCAD.

    Args:
        doc_name: The name of the document to delete the object from.
        obj_name: The name of the object to delete.

    Returns:
        A message indicating the success or failure of the object deletion and a screenshot of the object.
    """
    return delete_object_operation(
        get_freecad_connection(),
        state.only_text_feedback,
        doc_name,
        obj_name,
    )


@mcp.tool()
def execute_code(ctx: Context, code: str) -> list[TextContent | ImageContent]:
    """Execute arbitrary Python code in FreeCAD.

    Args:
        code: The Python code to execute.

    Returns:
        A message indicating the success or failure of the code execution, the output of the code execution, and a screenshot of the object.
    """
    return execute_code_operation(get_freecad_connection(), state.only_text_feedback, code)


@mcp.tool()
def get_view(
    ctx: Context,
    view_name: Literal["Isometric", "Front", "Top", "Right", "Back", "Left", "Bottom", "Dimetric", "Trimetric"],
    width: int | None = None,
    height: int | None = None,
    focus_object: str | None = None,
) -> list[ImageContent | TextContent]:
    """Get a screenshot of the active view.

    Args:
        view_name: The name of the view to get the screenshot of.
        The following views are available:
        - "Isometric"
        - "Front"
        - "Top"
        - "Right"
        - "Back"
        - "Left"
        - "Bottom"
        - "Dimetric"
        - "Trimetric"
        width: The width of the screenshot in pixels. If not specified, uses the viewport width.
        height: The height of the screenshot in pixels. If not specified, uses the viewport height.
        focus_object: The name of the object to focus on. If not specified, fits all objects in the view.

    Returns:
        A screenshot of the active view.
    """
    return get_view_operation(get_freecad_connection(), view_name, width, height, focus_object)


@mcp.tool()
def insert_part_from_library(ctx: Context, relative_path: str) -> list[TextContent | ImageContent]:
    """Insert a part from the parts library addon.

    Args:
        relative_path: The relative path of the part to insert.

    Returns:
        A message indicating the success or failure of the part insertion and a screenshot of the object.
    """
    return insert_part_from_library_operation(
        get_freecad_connection(),
        state.only_text_feedback,
        relative_path,
    )


@mcp.tool()
def get_objects(ctx: Context, doc_name: str) -> list[TextContent | ImageContent]:
    """Get all objects in a document.
    You can use this tool to get the objects in a document to see what you can check or edit.

    Args:
        doc_name: The name of the document to get the objects from.

    Returns:
        A list of objects in the document and a screenshot of the document.
    """
    return get_objects_operation(get_freecad_connection(), state.only_text_feedback, doc_name)


@mcp.tool()
def get_object(ctx: Context, doc_name: str, obj_name: str) -> list[TextContent | ImageContent]:
    """Get an object from a document.
    You can use this tool to get the properties of an object to see what you can check or edit.

    Args:
        doc_name: The name of the document to get the object from.
        obj_name: The name of the object to get.

    Returns:
        The object and a screenshot of the object.
    """
    return get_object_operation(
        get_freecad_connection(),
        state.only_text_feedback,
        doc_name,
        obj_name,
    )


@mcp.tool()
def get_parts_list(ctx: Context) -> list[TextContent]:
    """Get the list of parts in the parts library addon.
    """
    return get_parts_list_operation(get_freecad_connection())


@mcp.tool()
def list_documents(ctx: Context) -> list[TextContent]:
    """Get the list of open documents in FreeCAD.

    Returns:
        A list of document names.
    """
    return list_documents_operation(get_freecad_connection())


@mcp.tool()
def save_document(ctx: Context, doc_name: str, path: str | None = None) -> list[TextContent]:
    """Save a FreeCAD document to disk (.FCStd).

    Args:
        doc_name: Name of the open document to save.
        path: Absolute path of the .FCStd file. If omitted, saves to the
            current file name (fails if the document was never saved).

    Returns:
        Confirmation with the final file path.
    """
    return save_document_operation(get_freecad_connection(), doc_name, path)


@mcp.tool()
def open_document(ctx: Context, path: str) -> list[TextContent]:
    """Open a FreeCAD document (.FCStd) from disk.

    Args:
        path: Absolute path of the .FCStd file to open.

    Returns:
        Confirmation with the list of open documents.
    """
    return open_document_operation(get_freecad_connection(), path)


@mcp.tool()
def close_document(ctx: Context, doc_name: str) -> list[TextContent]:
    """Close an open FreeCAD document without saving.

    Args:
        doc_name: Name of the document to close.

    Returns:
        Confirmation with the remaining open documents.
    """
    return close_document_operation(get_freecad_connection(), doc_name)


@mcp.tool()
def export_model(
    ctx: Context,
    doc_name: str,
    file_path: str,
    objects: list[str] | None = None,
) -> list[TextContent]:
    """Export objects from a document to STEP, IGES, STL, OBJ, PLY, OFF,
    AMF, 3MF, BREP or FCStd.

    Args:
        doc_name: Name of the document containing the objects.
        file_path: Absolute output path; the format is chosen from the
            extension (.step, .stp, .iges, .igs, .stl, .obj, .ply, .off,
            .amf, .3mf, .brep, .brp, .FCStd).
        objects: Object names to export. If omitted, exports every object
            with a non-null Shape.

    Returns:
        Confirmation with output path and size in bytes.
    """
    return export_model_operation(get_freecad_connection(), doc_name, file_path, objects)


@mcp.tool()
def get_camera(ctx: Context) -> list[TextContent]:
    """Get the current camera state (type, position, orientation, clip
    distances, ortho height) plus the scene bounding box center and diagonal.

    Returns:
        JSON with the camera parameters in OpenInventor format
        (orientation = [axis_x, axis_y, axis_z, angle_rad]).
    """
    return get_camera_operation(get_freecad_connection())


@mcp.tool()
def set_camera(
    ctx: Context,
    position: list[float] | None = None,
    orientation: list[float] | None = None,
    camera_type: str | None = None,
    height: float | None = None,
    near_distance: float | None = None,
    far_distance: float | None = None,
    focal_distance: float | None = None,
    aspect_ratio: float | None = None,
) -> list[TextContent]:
    """Set camera parameters without changing anything that is not passed.

    Args:
        position: Camera position [x, y, z] in mm (translates the camera,
            keeping the current viewing direction).
        orientation: [axis_x, axis_y, axis_z, angle_rad], unit axis and
            angle in radians (same format as get_camera).
        camera_type: "Orthographic" or "Perspective".
        height: Orthographic viewport height in mm (zoom for ortho cameras).
        near_distance: Near clip distance. Objects closer than this are cut.
        far_distance: Far clip distance. Objects farther than this are cut;
            if geometry appears clipped, increase this value.
        focal_distance: Perspective focal distance in mm.
        aspect_ratio: Viewport aspect ratio.

    Returns:
        Confirmation listing which fields were applied and which were
        ignored (e.g. "height" on a perspective camera).
    """
    return set_camera_operation(
        get_freecad_connection(),
        position,
        orientation,
        camera_type,
        height,
        near_distance,
        far_distance,
        focal_distance,
        aspect_ratio,
    )


@mcp.tool()
def fit_view(
    ctx: Context,
    view_name: str | None = None,
    focus_object: str | None = None,
    margin: float = 1.15,
) -> list[TextContent]:
    """Frame the geometry: optionally set a standard view, fit all (or a
    specific object) and repair near/far clip distances using the real
    scene bounding box (fixes models being cut off by a too-small
    farDistance after fitAll).

    Args:
        view_name: Optional standard view: "Isometric", "Front", "Top",
            "Right", "Back", "Left", "Bottom", "Dimetric", "Trimetric".
            If omitted, the current camera orientation is preserved.
        focus_object: Optional object name to focus on instead of all.
        margin: Safety margin for the clip range and ortho height
            (default 1.15 = 15% padding).

    Returns:
        JSON with the applied camera fixes (nearDistance, farDistance,
        height, scene diagonal, camera distance).
    """
    return fit_view_operation(get_freecad_connection(), view_name, focus_object, margin)


@mcp.tool()
def screenshot_current(
    ctx: Context, width: int | None = None, height: int | None = None
) -> list[ImageContent | TextContent]:
    """Capture the current viewport exactly as it is, WITHOUT moving or
    refitting the camera (unlike get_view, which applies a view preset).

    Args:
        width: Image width in pixels. Defaults to the viewport size.
        height: Image height in pixels. Defaults to the viewport size.

    Returns:
        The screenshot plus a JSON summary of the camera fix state.
    """
    return screenshot_current_operation(get_freecad_connection(), width, height)


@mcp.tool()
def set_color(
    ctx: Context,
    doc_name: str,
    obj_name: str,
    color: list[float] | None = None,
    transparency: int | None = None,
    line_color: list[float] | None = None,
) -> list[TextContent]:
    """Set the display color of an object (tuples of floats 0..1 are used
    internally; pass a list, it is converted).

    Args:
        doc_name: Document name.
        obj_name: Object name.
        color: [r, g, b] or [r, g, b, alpha], each 0..1. With alpha,
            transparency is derived as round((1-alpha)*100).
        transparency: 0 (opaque) to 100 (fully transparent).
        line_color: [r, g, b] for the edge/line color.

    Returns:
        Confirmation with the applied values.
    """
    return set_color_operation(
        get_freecad_connection(), doc_name, obj_name, color, transparency, line_color
    )


@mcp.tool()
def apply_fillet(
    ctx: Context,
    doc_name: str,
    obj_name: str,
    radius: float,
    edges: list[int] | None = None,
) -> list[TextContent]:
    """Round the edges of an object with a fillet (Part::Feature objects;
    the shape is replaced in place).

    Args:
        doc_name: Document name.
        obj_name: Object whose shape receives the fillet.
        radius: Fillet radius in mm.
        edges: 1-based edge numbers (Edge3 = 3, as shown in the FreeCAD
            UI). If omitted, all edges are filleted.

    Returns:
        Confirmation with volume and validity of the result.
    """
    return apply_fillet_operation(get_freecad_connection(), doc_name, obj_name, radius, edges)


@mcp.tool()
def apply_chamfer(
    ctx: Context,
    doc_name: str,
    obj_name: str,
    distance: float,
    edges: list[int] | None = None,
) -> list[TextContent]:
    """Chamfer the edges of an object (Part::Feature objects; the shape is
    replaced in place).

    Args:
        doc_name: Document name.
        obj_name: Object whose shape receives the chamfer.
        distance: Chamfer distance in mm.
        edges: 1-based edge numbers. If omitted, all edges are chamfered.

    Returns:
        Confirmation with volume and validity of the result.
    """
    return apply_chamfer_operation(get_freecad_connection(), doc_name, obj_name, distance, edges)


@mcp.tool()
def boolean_op(
    ctx: Context,
    doc_name: str,
    base_object: str,
    tool_object: str,
    operation: str,
    new_name: str | None = None,
    delete_inputs: bool = False,
) -> list[TextContent]:
    """Boolean operation between two objects; creates a new Part::Feature
    with the result.

    Args:
        doc_name: Document name.
        base_object: Base object name.
        tool_object: Tool object name.
        operation: "union" (fuse), "cut" (subtract tool from base) or
            "intersect" (common).
        new_name: Name for the resulting object (default
            base_op_tool).
        delete_inputs: Delete the two input objects after the operation.

    Returns:
        Confirmation with the result name, volume and validity.
    """
    return boolean_op_operation(
        get_freecad_connection(), doc_name, base_object, tool_object, operation,
        new_name, delete_inputs,
    )


@mcp.tool()
def measure(
    ctx: Context,
    doc_name: str,
    object_name: str | None = None,
    object2_name: str | None = None,
) -> list[TextContent]:
    """Measure geometry: properties of one object, distance between two
    objects, or the bounding box of the whole scene.

    Args:
        doc_name: Document name.
        object_name: First object. With object2_name: distance between
            both; alone: volume/area/bbox/center of mass of the object.
        object2_name: Second object for a distance measurement.

    Returns:
        JSON with the measurement (no units: FreeCAD works in mm).
    """
    return measure_operation(
        get_freecad_connection(), doc_name, object_name, object2_name
    )


@mcp.tool()
def transform_object(
    ctx: Context,
    doc_name: str,
    obj_name: str,
    translate: list[float] | None = None,
    rotate_axis: list[float] | None = None,
    rotate_angle_deg: float | None = None,
    rotate_center: list[float] | None = None,
) -> list[TextContent]:
    """Move/rotate an object through its Placement (rotation is applied
    first, then translation in global coordinates).

    Args:
        doc_name: Document name.
        obj_name: Object to transform.
        translate: [dx, dy, dz] translation in mm (global axes).
        rotate_axis: [x, y, z] rotation axis (does not need to be unit).
        rotate_angle_deg: Rotation angle in degrees.
        rotate_center: [x, y, z] rotation center; if omitted, rotates
            around the global origin.

    Returns:
        Confirmation with the resulting placement.
    """
    return transform_object_operation(
        get_freecad_connection(), doc_name, obj_name, translate,
        rotate_axis, rotate_angle_deg, rotate_center,
    )


@mcp.tool()
def set_visibility(
    ctx: Context,
    doc_name: str,
    objects: list[str] | str,
    visible: bool = True,
) -> list[TextContent]:
    """Show or hide objects in the 3D view.

    Args:
        doc_name: Document name.
        objects: Object name or list of object names.
        visible: True to show, False to hide.

    Returns:
        Confirmation listing the updated objects.
    """
    return set_visibility_operation(get_freecad_connection(), doc_name, objects, visible)


@mcp.tool()
def list_examples(ctx: Context) -> list[TextContent]:
    """List saved design examples registered in the MCP examples registry.

    Returns:
        JSON with the count, the registry path and a summary of each
        example (id, name, description, units, objects, previews, approved).
    """
    return list_examples_operation()


@mcp.tool()
def get_example(ctx: Context, example_id: str) -> list[TextContent]:
    """Get a full design example from the registry: metadata, components,
    metrics and absolute paths to its FCStd file and preview images.

    Args:
        example_id: Example id (e.g. 'protesis-deportiva') or exact name.

    Returns:
        JSON with the complete example entry; file_exists/previews_exist
        report whether the files are present on disk.
    """
    return get_example_operation(example_id)


@mcp.tool()
def load_example(ctx: Context, example_id: str) -> list[TextContent]:
    """Open the FCStd file of a registered design example in FreeCAD.

    Args:
        example_id: Example id (e.g. 'protesis-deportiva') or exact name.

    Returns:
        Confirmation with the opened document plus example_id and the
        absolute file path that was loaded.
    """
    return load_example_operation(get_freecad_connection(), example_id)


@mcp.tool()
def mirror_object(
    ctx: Context,
    doc_name: str,
    obj_name: str,
    plane: Literal["XY", "XZ", "YZ"],
    offset: float = 0.0,
) -> list[TextContent]:
    """Mirror an object's shape across a plane, creating a new object.

    Args:
        doc_name: Document name.
        obj_name: Object to mirror.
        plane: Mirror plane: 'XY' (z=offset), 'XZ' (y=offset) or
            'YZ' (x=offset).
        offset: Distance of the plane from the origin along its normal
            (mm, default 0).

    Returns:
        Confirmation with the new object name, validity, volume and bbox.
    """
    return mirror_object_operation(get_freecad_connection(), doc_name, obj_name, plane, offset)


@mcp.prompt()
def asset_creation_strategy() -> str:
    return ASSET_CREATION_STRATEGY


def _validate_host(value: str) -> str:
    """Validate that *value* is a valid IP address or hostname.

    Used as the ``type`` callback for the ``--host`` argparse argument.
    Raises ``argparse.ArgumentTypeError`` on invalid input.
    """
    import argparse

    import validators

    if validators.ipv4(value) or validators.ipv6(value) or validators.hostname(value):
        return value
    raise argparse.ArgumentTypeError(
        f"Invalid host: '{value}'. Must be a valid IP address or hostname."
    )


def main():
    """Run the MCP server"""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--only-text-feedback", action="store_true", help="Only return text feedback")
    parser.add_argument("--host", type=_validate_host, default="localhost", help="Host address of the FreeCAD RPC server to connect to (default: localhost)")
    args = parser.parse_args()
    state.only_text_feedback = args.only_text_feedback
    state.rpc_host = args.host
    logger.info(f"Only text feedback: {state.only_text_feedback}")
    logger.info(f"Connecting to FreeCAD RPC server at: {state.rpc_host}")
    mcp.run()
