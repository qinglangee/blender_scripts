import bpy
from pathlib import Path

# Create a plane using eye_*.png as an image sequence and drive the image
# texture's Offset with the controller bone's local pose-mode Y translation.

ASSET_DIR = Path(__file__).resolve().parent / "eye_mouth"
FILE_PREFIX = "eye_"
PLANE_NAME = "EyeSequence_Plane"
ARMATURE_NAME = "EyeSequence_Controller"
BONE_NAME = "Offset_Control"
CONTROLLER_X = 1.8
TICK_X = 2.35
TICK_HALF_WIDTH = 0.28
TICK_SPACING = 0.1
TICK_Y = 0.0
OUTPUT_BLEND = Path(__file__).resolve().parent / "eye_sequence_driver.blend"


def image_files():
    files = sorted(
        (path for path in ASSET_DIR.iterdir()
         if path.is_file() and path.name.lower().startswith(FILE_PREFIX)
         and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".exr"}),
        key=lambda p: p.name.lower(),
    )
    if not files:
        raise RuntimeError(f"No {FILE_PREFIX} image files found in: {ASSET_DIR}")
    return files


def make_sequence_image(files):
    # Blender sequence images expect numbered filenames such as eye_01.png.
    image = bpy.data.images.load(str(files[0]), check_existing=False)
    image.name = "Eye_Image_Sequence"
    image.source = "SEQUENCE"
    image.filepath = "//eye_mouth/" + files[0].name
    return image


def create_plane(image, frame_count):
    bpy.ops.mesh.primitive_plane_add(size=2.0, location=(0.0, 0.0, 0.0))
    plane = bpy.context.object
    plane.name = PLANE_NAME
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


def create_controller(frame_count):
    arm_data = bpy.data.armatures.new(ARMATURE_NAME)
    armature = bpy.data.objects.new(ARMATURE_NAME, arm_data)
    bpy.context.collection.objects.link(armature)
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
    limit.max_y = (frame_count - 1) / 10.0
    limit.owner_space = "LOCAL"
    limit.use_transform_limit = True

    # Front-view triangle in the XZ plane, with its right-facing tip at the
    # bone origin. The bone's local Y movement maps to world Z.
    shape_mesh = bpy.data.meshes.new("Offset_Control_Shape_Mesh")
    shape_vertices = [
        (-0.38, 0.0, -0.18), (-0.38, 0.0, 0.18), (0.0, 0.0, 0.0),
    ]
    shape_mesh.from_pydata(shape_vertices, [], [(0, 1, 2)])
    shape_mesh.update()
    control_shape = bpy.data.objects.new("Offset_Control_Shape", shape_mesh)
    bpy.context.collection.objects.link(control_shape)
    control_shape.hide_render = True
    control_shape.hide_select = True
    control_shape.display_type = "WIRE"
    pose_bone.custom_shape = control_shape
    pose_bone.custom_shape_scale_xyz = (1.0, 1.0, 1.0)
    ruler_children = []

    # Bone local Y maps to world Z. Align the zero tick with the bone origin
    # at world Z=0, then place each successive frame 0.1 units above it.
    z_min = 0.0
    z_max = (frame_count - 1) / 10.0
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
    ruler_mesh.from_pydata(vertices, edges, [])
    ruler_mesh.update()
    ruler = bpy.data.objects.new("Frame_Ruler", ruler_mesh)
    bpy.context.collection.objects.link(ruler)
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
        label.location = (x_left + TICK_HALF_WIDTH * 0.76, TICK_Y, z - 0.035)
        label.rotation_euler[0] = 1.5707963267948966
        label.hide_render = True
        label.hide_select = True
        label.show_in_front = True
        ruler_children.append(label)

    # The ruler border is the parent of every ruler component. Preserve their
    # world transforms while establishing the hierarchy.
    for child in ruler_children:
        child.parent = ruler
        child.matrix_parent_inverse = ruler.matrix_world.inverted()

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
    files = image_files()
    image = make_sequence_image(files)
    plane, texture_node = create_plane(image, len(files))
    armature = create_controller(len(files))
    add_offset_driver(texture_node, armature)
    bpy.context.view_layer.objects.active = plane
    plane.select_set(True)
    armature.select_set(False)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT_BLEND))
    print(f"Created {PLANE_NAME} with {len(files)} eye sequence frames and {ARMATURE_NAME}.")
    print(f"Saved Blender file: {OUTPUT_BLEND}")


if __name__ == "__main__":
    main()
