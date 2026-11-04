import bpy
from pathlib import Path

# Create a plane using eye_*.png as an image sequence and drive the image
# texture's Offset with the controller bone's local pose-mode Y translation.

ASSET_DIR = Path(__file__).resolve().parent / "eye_mouth"
FILE_PREFIX = "eye_"
PLANE_NAME = "EyeSequence_Plane"
ARMATURE_NAME = "EyeSequence_Controller"
BONE_NAME = "Offset_Control"
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


def create_controller():
    arm_data = bpy.data.armatures.new(ARMATURE_NAME)
    armature = bpy.data.objects.new(ARMATURE_NAME, arm_data)
    bpy.context.collection.objects.link(armature)
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bone = arm_data.edit_bones.new(BONE_NAME)
    bone.head = (0.0, 0.0, 0.0)
    bone.tail = (0.0, 0.0, 1.0)
    bpy.ops.object.mode_set(mode="OBJECT")
    return armature


def add_offset_driver(texture_node, armature):
    # Offset is an integer image-user property. Bone Y movement times ten
    # provides a convenient control range; round to whole image frames.
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
    driver.expression = "round(bone_y * 10)"


def main():
    files = image_files()
    image = make_sequence_image(files)
    plane, texture_node = create_plane(image, len(files))
    armature = create_controller()
    add_offset_driver(texture_node, armature)
    bpy.context.view_layer.objects.active = plane
    plane.select_set(True)
    armature.select_set(False)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT_BLEND))
    print(f"Created {PLANE_NAME} with {len(files)} eye sequence frames and {ARMATURE_NAME}.")
    print(f"Saved Blender file: {OUTPUT_BLEND}")


if __name__ == "__main__":
    main()
