"""
Convert G-code to STL format for rendering with the original blender_script.py
"""

import argparse
import re
import numpy as np
from typing import List, Tuple
import os


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
    return segments, detected_layer_height, detected_extrusion_width


def create_rectangular_extrusion_mesh(segments, layer_height, extrusion_width):
    """Create vertices and faces for rectangular extrusion paths"""
    vertices = []
    faces = []
    vertex_count = 0

    # Use much higher fidelity - minimal sampling
    step = max(1, len(segments) // 10000)  # Keep up to 10000 segments for high fidelity
    sampled_segments = segments[::step]
    print(f"Using {len(sampled_segments)} segments (every {step}) for high fidelity STL conversion")

    for i, segment in enumerate(sampled_segments):
        if i % 500 == 0:
            print(f"Processing segment {i}/{len(sampled_segments)}")

        start = np.array(segment['start'])
        end = np.array(segment['end'])

        # Skip very short segments but be more permissive for detail
        if np.linalg.norm(end - start) < 0.001:
            continue

        # Create rectangular cross-section for the extrusion
        direction = end - start
        length = np.linalg.norm(direction)
        if length < 0.001:
            continue

        direction = direction / length

        # Create perpendicular vectors for rectangular cross-section
        if abs(direction[2]) < 0.9:  # Not vertical
            up = np.array([0, 0, 1])
        else:
            up = np.array([1, 0, 0])

        right = np.cross(direction, up)
        right = right / np.linalg.norm(right)
        up = np.cross(right, direction)
        up = up / np.linalg.norm(up)

        # Scale by extrusion dimensions - make it smaller and more accurate
        right = right * (extrusion_width / 3)  # Smaller for better detail
        up = up * (layer_height / 3)  # Smaller for better detail

        # Create 8 vertices for rectangular tube with tighter geometry
        v1 = start - right - up
        v2 = start + right - up
        v3 = start + right + up
        v4 = start - right + up
        v5 = end - right - up
        v6 = end + right - up
        v7 = end + right + up
        v8 = end - right + up

        # Add vertices
        base_idx = vertex_count
        vertices.extend([v1, v2, v3, v4, v5, v6, v7, v8])
        vertex_count += 8

        # Add faces (12 triangular faces for rectangular tube)
        # Start face
        faces.extend([
            [base_idx, base_idx+1, base_idx+2],
            [base_idx, base_idx+2, base_idx+3]
        ])

        # End face
        faces.extend([
            [base_idx+4, base_idx+6, base_idx+5],
            [base_idx+4, base_idx+7, base_idx+6]
        ])

        # Side faces
        faces.extend([
            # Bottom
            [base_idx, base_idx+5, base_idx+1],
            [base_idx, base_idx+4, base_idx+5],
            # Top
            [base_idx+2, base_idx+6, base_idx+7],
            [base_idx+2, base_idx+7, base_idx+3],
            # Left
            [base_idx, base_idx+3, base_idx+7],
            [base_idx, base_idx+7, base_idx+4],
            # Right
            [base_idx+1, base_idx+6, base_idx+2],
            [base_idx+1, base_idx+5, base_idx+6]
        ])

    return np.array(vertices), faces


def write_stl(vertices, faces, filename):
    """Write vertices and faces to STL file"""
    print(f"Writing STL with {len(vertices)} vertices and {len(faces)} faces to {filename}")

    with open(filename, 'w') as f:
        f.write("solid gcode_converted\n")

        for face in faces:
            # Calculate normal vector
            v1 = vertices[face[1]] - vertices[face[0]]
            v2 = vertices[face[2]] - vertices[face[0]]
            normal = np.cross(v1, v2)
            normal = normal / np.linalg.norm(normal) if np.linalg.norm(normal) > 0 else normal

            f.write(f"  facet normal {normal[0]:.6f} {normal[1]:.6f} {normal[2]:.6f}\n")
            f.write("    outer loop\n")
            for vertex_idx in face:
                v = vertices[vertex_idx]
                f.write(f"      vertex {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            f.write("    endloop\n")
            f.write("  endfacet\n")

        f.write("endsolid gcode_converted\n")


def gcode_to_stl(gcode_file, stl_file):
    """Convert G-code file to STL format"""
    print(f"Converting {gcode_file} to {stl_file}")

    # Parse G-code
    segments, layer_height, extrusion_width = parse_gcode_to_segments(gcode_file)

    if not segments:
        print("No extrusion segments found in G-code!")
        return False

    # Create mesh
    vertices, faces = create_rectangular_extrusion_mesh(segments, layer_height, extrusion_width)

    if len(vertices) == 0:
        print("No valid geometry created!")
        return False

    # Write STL
    write_stl(vertices, faces, stl_file)
    print(f"Successfully converted G-code to STL: {stl_file}")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert G-code to STL for rendering")
    parser.add_argument("--gcode_path", type=str, required=True, help="Path to G-code file")
    parser.add_argument("--stl_path", type=str, required=True, help="Output STL file path")

    args = parser.parse_args()

    if not os.path.exists(args.gcode_path):
        print(f"Error: G-code file not found: {args.gcode_path}")
        exit(1)

    success = gcode_to_stl(args.gcode_path, args.stl_path)

    if success:
        print(f"Conversion complete! You can now render with:")
        print(f"blender --background --python blender_script.py -- --object_path {args.stl_path} --output_dir output_renders")
    else:
        print("Conversion failed!")
        exit(1)