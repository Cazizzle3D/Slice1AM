"""
G-code to 3D mesh renderer - creates Blender-style renders of G-code layers
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import re
from matplotlib import cm
from matplotlib.colors import LightSource

def parse_gcode_with_extrusion_width(gcode_file, layer_height=0.2, extrusion_width=0.4):
    """Parse G-code and create 3D geometry for each extrusion"""
    layers_3d = {}
    current_z = 0.0
    last_x, last_y = None, None

    with open(gcode_file, 'r') as f:
        for line in f:
            line = line.strip()

            if line.startswith('G1') or line.startswith('G0'):
                x_match = re.search(r'X([-]?[0-9]+\.?[0-9]*)', line)
                y_match = re.search(r'Y([-]?[0-9]+\.?[0-9]*)', line)
                z_match = re.search(r'Z([-]?[0-9]+\.?[0-9]*)', line)
                e_match = re.search(r'E([-]?[0-9]+\.?[0-9]*)', line)

                x = float(x_match.group(1)) if x_match else last_x
                y = float(y_match.group(1)) if y_match else last_y

                if z_match:
                    current_z = float(z_match.group(1))

                # Check if extruding
                is_extruding = e_match is not None

                if is_extruding and x is not None and y is not None and last_x is not None and last_y is not None:
                    if current_z not in layers_3d:
                        layers_3d[current_z] = []

                    # Create a 3D box for each extrusion segment
                    # This simulates the actual extruded plastic
                    segment = create_extrusion_segment(
                        (last_x, last_y, current_z),
                        (x, y, current_z),
                        extrusion_width,
                        layer_height
                    )
                    layers_3d[current_z].append(segment)

                last_x, last_y = x, y

    return layers_3d

def create_extrusion_segment(start, end, width, height):
    """Create a 3D box representing an extrusion segment"""
    x1, y1, z = start
    x2, y2, _ = end

    # Calculate perpendicular direction for width
    dx = x2 - x1
    dy = y2 - y1
    length = np.sqrt(dx**2 + dy**2)

    if length == 0:
        return None

    # Perpendicular unit vector
    perp_x = -dy / length * width/2
    perp_y = dx / length * width/2

    # Create 8 vertices of the box (rectangular prism)
    vertices = np.array([
        [x1 - perp_x, y1 - perp_y, z],              # bottom corner 1
        [x1 + perp_x, y1 + perp_y, z],              # bottom corner 2
        [x2 + perp_x, y2 + perp_y, z],              # bottom corner 3
        [x2 - perp_x, y2 - perp_y, z],              # bottom corner 4
        [x1 - perp_x, y1 - perp_y, z + height],     # top corner 1
        [x1 + perp_x, y1 + perp_y, z + height],     # top corner 2
        [x2 + perp_x, y2 + perp_y, z + height],     # top corner 3
        [x2 - perp_x, y2 - perp_y, z + height],     # top corner 4
    ])

    # Define the 6 faces of the box
    faces = [
        [vertices[0], vertices[1], vertices[2], vertices[3]],  # bottom
        [vertices[4], vertices[5], vertices[6], vertices[7]],  # top
        [vertices[0], vertices[1], vertices[5], vertices[4]],  # side 1
        [vertices[2], vertices[3], vertices[7], vertices[6]],  # side 2
        [vertices[1], vertices[2], vertices[6], vertices[5]],  # front
        [vertices[0], vertices[3], vertices[7], vertices[4]],  # back
    ]

    return faces

def render_gcode_3d_blender_style(layers_3d, target_layer_idx, layer_height=0.2):
    """Create Blender-style 3D renders of G-code layers"""

    sorted_layers = sorted(layers_3d.keys())
    if target_layer_idx >= len(sorted_layers):
        return None

    fig = plt.figure(figsize=(20, 5))

    # Calculate bounds
    all_vertices = []
    for layer_segments in layers_3d.values():
        for segment in layer_segments:
            if segment:
                for face in segment:
                    all_vertices.extend(face)

    if not all_vertices:
        return None

    all_vertices = np.array(all_vertices)
    x_min, x_max = all_vertices[:, 0].min(), all_vertices[:, 0].max()
    y_min, y_max = all_vertices[:, 1].min(), all_vertices[:, 1].max()
    z_min, z_max = 0, sorted_layers[target_layer_idx] + layer_height

    center_x = (x_min + x_max) / 2
    center_y = (y_min + y_max) / 2
    max_range = max(x_max - x_min, y_max - y_min) * 0.6

    # Create light source for shading
    light = LightSource(azdeg=315, altdeg=45)

    # --- Panel A: 3D cumulative view (Blender-style with shading) ---
    ax1 = fig.add_subplot(141, projection='3d', computed_zorder=False)

    # Render all layers up to target
    for i in range(target_layer_idx + 1):
        z = sorted_layers[i]
        segments = layers_3d[z]

        if i < target_layer_idx:
            # Previous layers - darker orange
            color = '#cc6600'
            alpha = 0.6
        else:
            # Current layer - bright orange
            color = '#ff3300'
            alpha = 0.9

        # Draw each segment as 3D boxes
        for segment in segments:
            if segment:
                poly3d = Poly3DCollection(segment, alpha=alpha,
                                        facecolors=color,
                                        edgecolors='none',
                                        linewidth=0)
                ax1.add_collection3d(poly3d)

    ax1.set_xlim(center_x - max_range, center_x + max_range)
    ax1.set_ylim(center_y - max_range, center_y + max_range)
    ax1.set_zlim(z_min, z_max)
    ax1.set_xlabel('X (mm)')
    ax1.set_ylabel('Y (mm)')
    ax1.set_zlabel('Z (mm)')
    ax1.set_title(f'a) Layer {target_layer_idx} - 3D Build')
    ax1.view_init(elev=25, azim=45)

    # Set gray background
    ax1.xaxis.pane.fill = True
    ax1.yaxis.pane.fill = True
    ax1.zaxis.pane.fill = True
    ax1.xaxis.pane.set_facecolor('#e8e8e8')
    ax1.yaxis.pane.set_facecolor('#e8e8e8')
    ax1.zaxis.pane.set_facecolor('#e8e8e8')
    ax1.grid(True, alpha=0.3)

    # --- Panel B: Current layer blueprint (top view, white on black) ---
    ax2 = fig.add_subplot(142)
    ax2.set_facecolor('black')

    current_segments = layers_3d[sorted_layers[target_layer_idx]]
    for segment in current_segments:
        if segment and len(segment) > 0:
            # Get top face vertices for top-down view
            top_face = segment[1]  # Top face of the box
            if len(top_face) >= 4:
                xs = [v[0] for v in top_face] + [top_face[0][0]]
                ys = [v[1] for v in top_face] + [top_face[0][1]]
                ax2.fill(xs, ys, color='white', alpha=0.9)

    ax2.set_xlim(center_x - max_range, center_x + max_range)
    ax2.set_ylim(center_y - max_range, center_y + max_range)
    ax2.set_aspect('equal')
    ax2.set_title(f'b) Layer {target_layer_idx} blueprint')
    ax2.axis('off')

    # --- Panel C: 3D isolated current layer (Blender-style) ---
    ax3 = fig.add_subplot(143, projection='3d', computed_zorder=False)

    # Only render current layer with nice shading
    current_z = sorted_layers[target_layer_idx]
    for segment in current_segments:
        if segment:
            poly3d = Poly3DCollection(segment, alpha=0.95,
                                    facecolors='#ff6600',
                                    edgecolors='#cc3300',
                                    linewidth=0.5)
            ax3.add_collection3d(poly3d)

    ax3.set_xlim(center_x - max_range, center_x + max_range)
    ax3.set_ylim(center_y - max_range, center_y + max_range)
    ax3.set_zlim(current_z - layer_height, current_z + layer_height * 2)
    ax3.set_xlabel('X (mm)')
    ax3.set_ylabel('Y (mm)')
    ax3.set_zlabel('Z (mm)')
    ax3.set_title(f'c) Layer {target_layer_idx} - 3D Isolated')
    ax3.view_init(elev=30, azim=45)

    # Light gray background
    ax3.xaxis.pane.fill = True
    ax3.yaxis.pane.fill = True
    ax3.zaxis.pane.fill = True
    ax3.xaxis.pane.set_facecolor('#f0f0f0')
    ax3.yaxis.pane.set_facecolor('#f0f0f0')
    ax3.zaxis.pane.set_facecolor('#f0f0f0')
    ax3.grid(True, alpha=0.2)

    # --- Panel D: Binary mask (cyan on black) ---
    ax4 = fig.add_subplot(144)
    ax4.set_facecolor('black')

    for segment in current_segments:
        if segment and len(segment) > 0:
            top_face = segment[1]
            if len(top_face) >= 4:
                xs = [v[0] for v in top_face] + [top_face[0][0]]
                ys = [v[1] for v in top_face] + [top_face[0][1]]
                ax4.fill(xs, ys, color='cyan', alpha=1.0)

    ax4.set_xlim(center_x - max_range, center_x + max_range)
    ax4.set_ylim(center_y - max_range, center_y + max_range)
    ax4.set_aspect('equal')
    ax4.set_title(f'd) Layer {target_layer_idx} mask')
    ax4.axis('off')

    plt.tight_layout()
    return fig

# Main execution
if __name__ == "__main__":
    print("Parsing G-code and creating 3D geometry...")
    gcode_path = "/mnt/d/papers/UNET and Meta Pseduolabeling/crazyfrog.gcode"

    # Parse with 3D geometry
    layers_3d = parse_gcode_with_extrusion_width(
        gcode_path,
        layer_height=0.2,
        extrusion_width=0.4
    )

    sorted_layers = sorted(layers_3d.keys())
    print(f"Found {len(sorted_layers)} layers")

    # Render layer 5
    target_layer = 5
    print(f"Rendering layer {target_layer} with 3D Blender-style visualization...")

    fig = render_gcode_3d_blender_style(layers_3d, target_layer, layer_height=0.2)

    if fig:
        output_file = "gcode_layer5_blender_style.png"
        fig.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"Saved to {output_file}")
        plt.close(fig)
    else:
        print("Failed to create visualization")