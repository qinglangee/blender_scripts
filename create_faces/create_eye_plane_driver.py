import bpy
import argparse
from pathlib import Path
import sys

# Create a plane using eye_*.png as an image sequence and drive the image
# texture's Offset with the controller bone's local pose-mode Y translation.

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_ASSET_DIR = SCRIPT_DIR / "eye_mouth"
DEFAULT_FILE_PREFIX = "eye_"
PLANE_NAME = "EyeSequence_Plane"
ARMATURE_NAME = "EyeSequence_Controller"
BONE_NAME = "Offset_Control"
COLLECTION_NAME = "Expression"
CONTROLLER_X = 1.8
TICK_X = 2.35
TICK_HALF_WIDTH = 0.28
TICK_SPACING = 0.1
TICK_Y = 0.0
TICK_START_Z = -0.5  # Frame 1 aligns with the control bone head.
OUTPUT_BLEND = Path(__file__).resolve().parent / "eye_sequence_driver.blend"


def create_expression_collection():
    collection = bpy.data.collections.new(COLLECTION_NAME)
    bpy.context.scene.collection.children.link(collection)
    return collection


def move_to_collection(obj, collection):
    for existing_collection in tuple(obj.users_collection):
        existing_collection.objects.unlink(obj)
    collection.objects.link(obj)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create a Blender image-sequence plane and bone-driven frame controller."
    )
    parser.add_argument(
        "--image-dir", "-d", type=Path, default=DEFAULT_ASSET_DIR,
        help=f"Directory containing sequence images (default: {DEFAULT_ASSET_DIR})",
    )
    parser.add_argument(
        "--prefix", "-p", default=DEFAULT_FILE_PREFIX,
        help=f"Image filename prefix (default: {DEFAULT_FILE_PREFIX!r})",
    )
    parser.add_argument(
        "--output", "-o", type=Path, default=OUTPUT_BLEND,
        help=f"Output .blend path (default: {OUTPUT_BLEND})",
    )
    args_list = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(args_list)


def image_files(asset_dir, file_prefix):
    asset_dir = asset_dir.expanduser().resolve()
    files = sorted(
        (path for path in asset_dir.iterdir()
         if path.is_file() and path.name.lower().startswith(file_prefix.lower())
         and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".exr"}),
        key=lambda p: p.name.lower(),
    ) if asset_dir.is_dir() else []
    if not files:
        raise RuntimeError(f"No {file_prefix!r} image files found in: {asset_dir}")
    return files


def make_sequence_image(files):
    # Blender sequence images expect numbered filenames such as eye_01.png.
    image = bpy.data.images.load(str(files[0]), check_existing=False)
    image.name = "Eye_Image_Sequence"
    image.source = "SEQUENCE"
    image.filepath = "//eye_mouth/" + files[0].name
    return image


def create_plane(image, frame_count, collection):
    bpy.ops.mesh.primitive_plane_add(size=2.0, location=(0.0, 0.0, 0.0))
    plane = bpy.context.object
    plane.name = PLANE_NAME
    move_to_collection(plane, collection)
    # A Blender plane lies in local XY with its normal along local +Z.
    # Rotate it so its front faces the front orthographic view (-Y).
    plane.rotation_euler[0] = 1.5707963267948966

    material = bpy.data.materials.new("EyeSequence_Material")
    material.use_nodes = True
    plane.data.materials.clear()
    plane.data.materials.append(material)

    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (500, 0)
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    shader.location = (220, 0)
    texture = nodes.new("ShaderNodeTexImage")
    texture.location = (-100, 0)
    texture.image = image
    texture.image_user.use_auto_refresh = True
    texture.image_user.frame_duration = frame_count
    texture.image_user.frame_start = 1
    texture.image_user.frame_offset = 0
    texture.image_user.use_cyclic = True
    texture.label = "Eye Sequence (Offset driven by bone)"
    links.new(texture.outputs["Color"], shader.inputs["Base Color"])
    links.new(texture.outputs["Alpha"], shader.inputs["Alpha"])
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])

    # Show the transparent PNG cutout in the viewport/render where supported.
    material.surface_render_method = "DITHERED"
    return plane, texture


def create_controller(frame_count, collection):
    arm_data = bpy.data.armatures.new(ARMATURE_NAME)
    armature = bpy.data.objects.new(ARMATURE_NAME, arm_data)
    bpy.context.collection.objects.link(armature)
    move_to_collection(armature, collection)
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bone = arm_data.edit_bones.new(BONE_NAME)
    # Place the single vertical control bone to the right of the plane.
    bone.head = (CONTROLLER_X, 0.0, -0.5)
    bone.tail = (CONTROLLER_X, 0.0, 0.5)
    bpy.ops.object.mode_set(mode="OBJECT")

    # Lock unused transforms and constrain the pose bone's local Y movement.
    # Unlike IK limits, LIMIT_LOCATION also clamps direct manual transforms.
    pose_bone = armature.pose.bones[BONE_NAME]
    pose_bone.lock_location = (True, False, True)
    pose_bone.lock_rotation = (True, True, True)
    pose_bone.lock_scale = (True, True, True)
    limit = pose_bone.constraints.new(type="LIMIT_LOCATION")
    limit.name = "Limit Sequence Offset Range"
    limit.use_min_x = limit.use_max_x = True
    limit.use_min_y = limit.use_max_y = False
    limit.use_min_z = limit.use_max_z = True
    limit.min_x = limit.max_x = 0.0
    limit.min_z = limit.max_z = 0.0
    limit.use_min_y = True
    limit.use_max_y = True
    limit.min_y = 0.0
    limit.max_y = (frame_count - 1) / 10.0 + 0.01
    limit.owner_space = "LOCAL"
    limit.use_transform_limit = True

    # Triangle pointer with its tip at the bone origin.
    shape_mesh = bpy.data.meshes.new("Offset_Control_Shape_Mesh")
    shape_vertices = [
        (-0.38, -0.18, 0.0), (-0.38, 0.18, 0.0), (0.0, 0.0, 0.0),
    ]
    shape_mesh.from_pydata(shape_vertices, [], [(2, 1, 0)])
    shape_mesh.update()
    control_shape = bpy.data.objects.new("Offset_Control_Shape", shape_mesh)
    bpy.context.collection.objects.link(control_shape)
    move_to_collection(control_shape, collection)
    control_shape.hide_render = True
    control_shape.hide_select = True
    control_shape.display_type = "SOLID"
    control_shape.color = (1.0, 0.25, 0.05, 0.1)
    pose_bone.custom_shape = control_shape
    pose_bone.custom_shape_scale_xyz = (1.0, 1.0, 1.0)
    ruler_children = []

    # Bone local Y maps to world Z. Align frame 1 (offset 0) with the bone
    # head at world Z=-0.5, then place each successive frame 0.1 units above.
    z_min = TICK_START_Z
    z_max = z_min + (frame_count - 1) * TICK_SPACING
    vertices = []
    edges = []

    def add_segment(a, b):
        start = len(vertices)
        vertices.extend((a, b))
        edges.append((start, start + 1))

    # Outer rectangular border and horizontal ticks in the front-facing XZ
    # plane (normal toward world -Y).
    x_left, x_right = TICK_X - TICK_HALF_WIDTH, TICK_X + TICK_HALF_WIDTH
    add_segment((x_left, TICK_Y, z_min - 0.06), (x_right, TICK_Y, z_min - 0.06))
    add_segment((x_right, TICK_Y, z_min - 0.06), (x_right, TICK_Y, z_max + 0.06))
    add_segment((x_right, TICK_Y, z_max + 0.06), (x_left, TICK_Y, z_max + 0.06))
    add_segment((x_left, TICK_Y, z_max + 0.06), (x_left, TICK_Y, z_min - 0.06))
    for i in range(frame_count):
        z = z_min + i * TICK_SPACING
        add_segment((x_left, TICK_Y, z), (x_left + TICK_HALF_WIDTH * 0.72, TICK_Y, z))

    ruler_mesh = bpy.data.meshes.new("Frame_Ruler_Mesh")
    ruler_center = (
        (x_left + x_right) * 0.5,
        TICK_Y,
        (z_min + z_max) * 0.5,
    )
    local_vertices = [
        (x - ruler_center[0], y - ruler_center[1], z - ruler_center[2])
        for x, y, z in vertices
    ]
    ruler_mesh.from_pydata(local_vertices, edges, [])
    ruler_mesh.update()
    ruler = bpy.data.objects.new("Frame_Ruler", ruler_mesh)
    bpy.context.collection.objects.link(ruler)
    move_to_collection(ruler, collection)
    # The object origin is the frame's geometric center; mesh vertices above
    # are stored relative to it, preserving the intended world placement.
    ruler.location = ruler_center
    ruler.hide_render = True
    ruler.hide_select = True
    ruler.display_type = "WIRE"
    ruler.show_in_front = True

    # Labels lie in the XZ plane so they face the front view like the plane.
    for i in range(frame_count):
        z = z_min + i * TICK_SPACING
        text_data = bpy.data.curves.new(f"Frame_{i + 1:02d}_Text", type="FONT")
        text_data.body = str(i + 1)
        text_data.size = 0.075
        text_data.align_x = "LEFT"
        label = bpy.data.objects.new(f"Frame_{i + 1:02d}", text_data)
        bpy.context.collection.objects.link(label)
        move_to_collection(label, collection)
        label.location = (x_left + TICK_HALF_WIDTH * 0.76, TICK_Y, z - 0.035)
        label.rotation_euler[0] = 1.5707963267948966
        label.hide_render = True
        label.hide_select = True
        label.show_in_front = True
        ruler_children.append(label)

    # Equivalent to Blender's Object (Keep Transform) parenting. Store the
    # parent's inverse world matrix so the child's existing transform remains
    # in the same world-space position after parenting.
    bpy.context.view_layer.update()
    ruler_world_inverse = ruler.matrix_world.inverted()
    for child in ruler_children:
        child_basis = child.matrix_basis.copy()
        child.parent = ruler
        child.matrix_parent_inverse = ruler_world_inverse
        child.matrix_basis = child_basis

    # Parent the armature and complete ruler group to the image plane, keeping
    # their current world placement. This lets the full rig follow the plane.
    for child in (armature, ruler):
        child.parent = bpy.data.objects.get(PLANE_NAME)
        child.matrix_parent_inverse = child.parent.matrix_world.inverted()
    return armature


def add_offset_driver(texture_node, armature):
    # Offset is an integer image-user property. Bone Y movement times ten
    # provides a convenient control range; int() truncates to whole frames.
    fcurve = texture_node.image_user.driver_add("frame_offset")
    driver = fcurve.driver
    driver.type = "SCRIPTED"
    variable = driver.variables.new()
    variable.name = "bone_y"
    variable.type = "TRANSFORMS"
    target = variable.targets[0]
    target.id = armature
    target.bone_target = BONE_NAME
    target.transform_type = "LOC_Y"
    target.transform_space = "LOCAL_SPACE"
    driver.expression = "int(bone_y * 10)"


def main():
    # Remove the default cube (and any other default scene objects) so the
    # generated project contains only the plane and its controller.
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    args = parse_args()
    files = image_files(args.image_dir, args.prefix)
    expression_collection = create_expression_collection()
    image = make_sequence_image(files)
    plane, texture_node = create_plane(image, len(files), expression_collection)
    armature = create_controller(len(files), expression_collection)
    add_offset_driver(texture_node, armature)
    bpy.context.view_layer.objects.active = plane
    plane.select_set(True)
    armature.select_set(False)

    # Store Material Preview as the startup shading mode in 3D View areas.
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.shading.type = "MATERIAL"

    output_path = args.output.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output_path))
    print(f"Created {PLANE_NAME} with {len(files)} eye sequence frames and {ARMATURE_NAME}.")
    print(f"Saved Blender file: {output_path}")


if __name__ == "__main__":
    main()
