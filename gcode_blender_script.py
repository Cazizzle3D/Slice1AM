"""
G-code to Blender renderer - converts G-code to 3D mesh and renders like blender_script.py
"""

import argparse
import json
import math
import os
import re
import sys
from typing import Dict, List, Tuple

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector

def parse_gcode_to_segments(gcode_file, default_layer_height=0.2, default_extrusion_width=0.4):
    """Parse G-code file and extract extrusion segments with 3D coordinates"""
    segments = []
    current_z = 0.0
    last_x, last_y = None, None
    last_z = None
    detected_layer_height = default_layer_height
    detected_extrusion_width = default_extrusion_width

    # Try to detect actual slicer settings from comments
    with open(gcode_file, 'r') as f:
        for line_num, line in enumerate(f):
            line = line.strip()

            # Look for slicer settings in comments (first 100 lines)
            if line_num < 100 and line.startswith(';'):
                if 'layer_height' in line.lower() or 'layer height' in line.lower():
                    height_match = re.search(r'([-]?[0-9]+\.?[0-9]*)', line)
                    if height_match:
                        detected_layer_height = float(height_match.group(1))
                        print(f"Detected layer height: {detected_layer_height}")

                if 'extrusion_width' in line.lower() or 'extrusion width' in line.lower():
                    width_match = re.search(r'([-]?[0-9]+\.?[0-9]*)', line)
                    if width_match:
                        detected_extrusion_width = float(width_match.group(1))
                        print(f"Detected extrusion width: {detected_extrusion_width}")

            if line.startswith('G1') or line.startswith('G0'):
                # Parse coordinates
                x_match = re.search(r'X([-]?[0-9]+\.?[0-9]*)', line)
                y_match = re.search(r'Y([-]?[0-9]+\.?[0-9]*)', line)
                z_match = re.search(r'Z([-]?[0-9]+\.?[0-9]*)', line)
                e_match = re.search(r'E([-]?[0-9]+\.?[0-9]*)', line)

                x = float(x_match.group(1)) if x_match else last_x
                y = float(y_match.group(1)) if y_match else last_y

                if z_match:
                    new_z = float(z_match.group(1))
                    # Try to detect layer height from Z movements
                    if last_z is not None and new_z > last_z:
                        z_diff = new_z - last_z
                        if 0.1 <= z_diff <= 1.0:  # Reasonable layer height range
                            detected_layer_height = z_diff
                    last_z = current_z
                    current_z = new_z

                # Check if extruding (positive E movement)
                is_extruding = e_match is not None and float(e_match.group(1)) > 0

                if is_extruding and x is not None and y is not None and last_x is not None and last_y is not None:
                    segments.append({
                        'start': (last_x, last_y, current_z),
                        'end': (x, y, current_z),
                        'width': detected_extrusion_width,
                        'height': detected_layer_height
                    })

                last_x, last_y = x, y

    print(f"Parsed {len(segments)} segments with layer_height={detected_layer_height}, extrusion_width={detected_extrusion_width}")
    return segments

def create_extrusion_mesh(segments, mesh_name="gcode_print"):
    """Create a Blender mesh from G-code extrusion segments"""

    # Create new mesh and object
    mesh = bpy.data.meshes.new(mesh_name)
    obj = bpy.data.objects.new(mesh_name, mesh)

    # Link to scene
    bpy.context.collection.objects.link(obj)

    # Create bmesh instance
    bm = bmesh.new()

    # Simplify: just create line segments, then use skin modifier for thickness
    print(f"Creating line mesh from {len(segments)} segments...")

    # Sample every nth segment to reduce complexity
    step = max(1, len(segments) // 5000)  # Limit to ~5000 segments for performance
    sampled_segments = segments[::step]
    print(f"Using {len(sampled_segments)} segments (every {step})")

    # Create vertices and edges for each extrusion path
    for i, segment in enumerate(sampled_segments):
        if i % 500 == 0:
            print(f"Processing segment {i}/{len(sampled_segments)}")

        start = Vector(segment['start'])
        end = Vector(segment['end'])

        # Add vertices
        v1 = bm.verts.new(start)
        v2 = bm.verts.new(end)

        # Add edge
        bm.edges.new([v1, v2])

    # Ensure face indices are valid
    bm.normal_update()
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()

    # Update mesh
    bm.to_mesh(mesh)
    bm.free()

    # Add skin modifier for thickness
    skin_modifier = obj.modifiers.new(name="Skin", type='SKIN')
    skin_modifier.use_smooth_shade = True

    # Set skin thickness (approximately extrusion width)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')

    # Set skin thickness based on actual extrusion width
    bpy.ops.mesh.select_all(action='SELECT')
    # Use actual extrusion width - multiply by 50 for much better visibility
    actual_width = segments[0]['width'] * 50 if segments else 20.0
    print(f"Setting skin thickness to {actual_width} (extrusion_width={segments[0]['width'] if segments else 'unknown'} * 50)")
    bpy.ops.transform.skin_resize(value=(actual_width, actual_width, actual_width))

    bpy.ops.object.mode_set(mode='OBJECT')

    return obj

def reset_scene():
    """Reset Blender scene"""
    # Delete all mesh objects
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH':
            obj.select_set(True)
    bpy.ops.object.delete()

    # Delete all materials
    for material in bpy.data.materials:
        bpy.data.materials.remove(material, do_unlink=True)

def apply_orange_material(obj):
    """Apply orange material to object (like STL files get in blender_script.py)"""
    mat = bpy.data.materials.new(name="GcodeMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    principled_bsdf = nodes.get("Principled BSDF")
    if principled_bsdf:
        # Bright orange color like STL files get, more metallic for visibility
        principled_bsdf.inputs["Base Color"].default_value = (1.0, 0.5, 0.0, 1.0)
        principled_bsdf.inputs["Metallic"].default_value = 0.3
        principled_bsdf.inputs["Roughness"].default_value = 0.4
    obj.data.materials.append(mat)
    print(f"Applied material to object: {obj.name}, vertices: {len(obj.data.vertices)}")

def setup_camera_and_lighting():
    """Setup camera and lighting like blender_script.py"""
    # Reset cameras
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.object.select_by_type(type="CAMERA")
    bpy.ops.object.delete()

    # Create new camera
    bpy.ops.object.camera_add()
    camera = bpy.context.active_object
    camera.name = "Camera"
    bpy.context.scene.camera = camera

    # Camera settings
    camera.data.lens = 35
    camera.data.sensor_width = 32

    # Clear existing lights
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.object.select_by_type(type="LIGHT")
    bpy.ops.object.delete()

    # Create lighting setup (simplified version of randomize_lighting())
    lights = [
        {"name": "Key_Light", "type": "SUN", "location": (0, 0, 0),
         "rotation": (0.785398, 0, -0.785398), "energy": 4},
        {"name": "Fill_Light", "type": "SUN", "location": (0, 0, 0),
         "rotation": (0.785398, 0, 2.35619), "energy": 3},
        {"name": "Rim_Light", "type": "SUN", "location": (0, 0, 0),
         "rotation": (-0.785398, 0, -3.92699), "energy": 4},
        {"name": "Bottom_Light", "type": "SUN", "location": (0, 0, 0),
         "rotation": (3.14159, 0, 0), "energy": 2}
    ]

    for light_data in lights:
        light = bpy.data.lights.new(name=light_data["name"], type=light_data["type"])
        light_obj = bpy.data.objects.new(light_data["name"], light)
        bpy.context.collection.objects.link(light_obj)
        light_obj.location = light_data["location"]
        light_obj.rotation_euler = light_data["rotation"]
        light.energy = light_data["energy"]

def set_camera_position(pose, scale=1.5):
    """Set camera position like blender_script.py"""
    camera = bpy.data.objects["Camera"]
    camera.scale = (1.0, 1.0, 1.0)

    if pose == 'Front':
        camera.location = Vector((0, -scale, 0))
        camera.rotation_euler = Vector((np.radians(90), 0, 0))
    elif pose == 'Back':
        camera.location = Vector((0, scale, 0))
        camera.rotation_euler = Vector((np.radians(90), 0, np.radians(180)))
    elif pose == 'Left':
        camera.location = Vector((-scale, 0, 0))
        camera.rotation_euler = Vector((np.radians(90), 0, np.radians(-90)))
    elif pose == 'Right':
        camera.location = Vector((scale, 0, 0))
        camera.rotation_euler = Vector((np.radians(90), 0, np.radians(90)))
    elif pose == 'Top':
        camera.location = Vector((0, 0, scale))
        camera.rotation_euler = Vector((0, 0, 0))
    elif pose == 'Down':
        camera.location = Vector((0, 0, -scale))
        camera.rotation_euler = Vector((np.radians(180), 0, 0))
    elif pose == 'iso1':
        camera.location = Vector((scale, -scale, scale))
        camera.rotation_euler = Vector((np.radians(45), 0, np.radians(45)))
    elif pose == 'iso2':
        camera.location = Vector((-scale, -scale, scale))
        camera.rotation_euler = Vector((np.radians(45), 0, np.radians(-45)))
    elif pose == 'iso3':
        camera.location = Vector((scale, scale, scale))
        camera.rotation_euler = Vector((np.radians(45), 0, np.radians(135)))
    elif pose == 'iso4':
        camera.location = Vector((-scale, scale, scale))
        camera.rotation_euler = Vector((np.radians(45), 0, np.radians(-135)))

    return camera

def normalize_scene():
    """Normalize scene like blender_script.py"""
    # Get all mesh objects
    mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']

    if not mesh_objects:
        print("No mesh objects found for normalization!")
        return

    # Calculate bounding box
    bbox_min = Vector((float('inf'),) * 3)
    bbox_max = Vector((float('-inf'),) * 3)

    for obj in mesh_objects:
        for corner in obj.bound_box:
            world_corner = obj.matrix_world @ Vector(corner)
            bbox_min = Vector(min(bbox_min[i], world_corner[i]) for i in range(3))
            bbox_max = Vector(max(bbox_max[i], world_corner[i]) for i in range(3))

    # Calculate scale and offset - use much gentler scaling
    size = bbox_max - bbox_min
    scale = 2.0 / max(size)  # Use 2.0 instead of 0.5 for less aggressive scaling
    offset = -(bbox_min + bbox_max) / 2

    print(f"Object bounding box: min={bbox_min}, max={bbox_max}")
    print(f"Size: {size}, scale: {scale}, offset: {offset}")

    # Apply transformations
    for obj in mesh_objects:
        old_scale = obj.scale.copy()
        old_location = obj.location.copy()
        obj.scale = obj.scale * scale
        obj.location += offset * scale
        print(f"Object {obj.name}: scale {old_scale} -> {obj.scale}, location {old_location} -> {obj.location}")

def get_3x4_RT_matrix_from_blender(cam):
    """Get camera matrix like blender_script.py"""
    location, rotation = cam.matrix_world.decompose()[0:2]
    R_world2bcam = rotation.to_matrix().transposed()
    T_world2bcam = -1 * R_world2bcam @ location

    RT = Matrix((
        R_world2bcam[0][:] + (T_world2bcam[0],),
        R_world2bcam[1][:] + (T_world2bcam[1],),
        R_world2bcam[2][:] + (T_world2bcam[2],),
    ))
    return RT

def render_gcode(gcode_file, output_dir, engine="BLENDER_EEVEE"):
    """Main function to render G-code file"""

    print(f"Parsing G-code file: {gcode_file}")
    segments = parse_gcode_to_segments(gcode_file)
    print(f"Found {len(segments)} extrusion segments")

    if not segments:
        print("No extrusion segments found!")
        return

    # Reset scene
    reset_scene()

    # Create mesh from G-code
    print("Creating 3D mesh from G-code...")
    obj = create_extrusion_mesh(segments)
    apply_orange_material(obj)

    # Setup camera and lighting
    setup_camera_and_lighting()

    # Normalize scene with proper scaling
    normalize_scene()

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Set render settings
    scene = bpy.context.scene
    render = scene.render
    render.engine = engine
    render.image_settings.file_format = "PNG"
    render.image_settings.color_mode = "RGBA"
    render.resolution_x = 512
    render.resolution_y = 512
    render.resolution_percentage = 100

    # Render all views
    poses = [
        ('iso1', 'iso_000'),
        ('iso2', 'iso_001'),
        ('iso3', 'iso_002'),
        ('iso4', 'iso_003'),
        ('Top', 'ortho_000'),
        ('Down', 'ortho_001'),
        ('Left', 'ortho_002'),
        ('Right', 'ortho_003'),
        ('Front', 'ortho_004'),
        ('Back', 'ortho_005')
    ]

    for pose, filename in poses:
        print(f"Rendering {filename}...")
        camera = set_camera_position(pose)

        render_path = os.path.join(output_dir, f"{filename}.png")
        scene.render.filepath = render_path
        bpy.ops.render.render(write_still=True)

        # Save camera matrix
        rt_matrix = get_3x4_RT_matrix_from_blender(camera)
        matrix_path = os.path.join(output_dir, f"{filename}.npy")
        np.save(matrix_path, rt_matrix)

    # Save metadata
    metadata = {
        "file_size": os.path.getsize(gcode_file),
        "segment_count": len(segments),
        "source_type": "gcode"
    }

    metadata_path = os.path.join(output_dir, "metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, sort_keys=True, indent=2)

    print(f"Rendering complete! Files saved to {output_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--gcode_path", type=str, required=True, help="Path to G-code file")
    parser.add_argument("--output_dir", type=str, required=True, help="Output directory")
    parser.add_argument("--engine", type=str, default="BLENDER_EEVEE", choices=["CYCLES", "BLENDER_EEVEE"])

    argv = sys.argv[sys.argv.index("--") + 1:]
    args = parser.parse_args(argv)

    render_gcode(args.gcode_path, args.output_dir, args.engine)