import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import re
import numpy as np
from mpl_toolkits.mplot3d import Axes3D

def parse_gcode_with_lines(gcode_file):
    """Parse G-code to extract extrusion paths as line segments"""
    layer_dict = {}
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

                # Update coordinates
                x = float(x_match.group(1)) if x_match else last_x
                y = float(y_match.group(1)) if y_match else last_y

                if z_match:
                    current_z = float(z_match.group(1))

                # Check if extruding (E value present and positive)
                is_extruding = e_match is not None

                if is_extruding and x is not None and y is not None and last_x is not None and last_y is not None:
                    if current_z not in layer_dict:
                        layer_dict[current_z] = []
                    # Store as line segment
                    layer_dict[current_z].append(((last_x, last_y), (x, y)))

                last_x, last_y = x, y

    return layer_dict

# Parse the G-code
print("Parsing G-code...")
gcode_path = "/mnt/d/papers/UNET and Meta Pseduolabeling/crazyfrog.gcode"
layers = parse_gcode_with_lines(gcode_path)
sorted_layers = sorted(layers.keys())
print(f"Found {len(sorted_layers)} layers")

# Select layer 5
target_layer = 5
if target_layer >= len(sorted_layers):
    target_layer = len(sorted_layers) - 1

print(f"Visualizing layer {target_layer} (Z={sorted_layers[target_layer]:.2f}mm)")
print(f"Layer has {len(layers[sorted_layers[target_layer]])} line segments")

# Create visualization with proper line rendering
fig = plt.figure(figsize=(20, 5))

# Plot 1: 3D view with cumulative layers
ax1 = fig.add_subplot(141, projection='3d')
for i in range(target_layer + 1):
    z = sorted_layers[i]
    segments = layers[z]

    if i < target_layer:
        color = '#ff9900'
        alpha = 0.5
        lw = 0.3
    else:
        color = '#ff3300'
        alpha = 1.0
        lw = 0.8

    for (start, end) in segments:
        ax1.plot([start[0], end[0]],
                [start[1], end[1]],
                [z, z],
                color=color, alpha=alpha, linewidth=lw)

ax1.set_title(f'a) Layer {target_layer} with history (Z={sorted_layers[target_layer]:.2f}mm)')
ax1.set_xlabel('X (mm)')
ax1.set_ylabel('Y (mm)')
ax1.set_zlabel('Z (mm)')
ax1.view_init(elev=25, azim=45)

# Set gray background for 3D view
ax1.xaxis.pane.fill = True
ax1.yaxis.pane.fill = True
ax1.zaxis.pane.fill = True
ax1.xaxis.pane.set_facecolor('#e0e0e0')
ax1.yaxis.pane.set_facecolor('#e0e0e0')
ax1.zaxis.pane.set_facecolor('#e0e0e0')

# Plot 2: Current layer blueprint (white on black)
ax2 = fig.add_subplot(142)
ax2.set_facecolor('black')
current_segments = layers[sorted_layers[target_layer]]
for (start, end) in current_segments:
    ax2.plot([start[0], end[0]], [start[1], end[1]], 'w-', linewidth=0.8)
ax2.set_title(f'b) Layer {target_layer} blueprint')
ax2.set_aspect('equal')
ax2.set_xlim(60, 160)
ax2.set_ylim(60, 160)

# Plot 3: Isolated current layer (orange on gray)
ax3 = fig.add_subplot(143)
ax3.set_facecolor('#d0d0d0')
for (start, end) in current_segments:
    ax3.plot([start[0], end[0]], [start[1], end[1]], color='#ff6600', linewidth=1.2)
ax3.set_title(f'c) Layer {target_layer} isolated')
ax3.set_aspect('equal')
ax3.set_xlim(60, 160)
ax3.set_ylim(60, 160)

# Plot 4: Binary mask (cyan on black)
ax4 = fig.add_subplot(144)
ax4.set_facecolor('black')
for (start, end) in current_segments:
    ax4.plot([start[0], end[0]], [start[1], end[1]], color='cyan', linewidth=1.5)
ax4.set_title(f'd) Layer {target_layer} mask')
ax4.set_aspect('equal')
ax4.set_xlim(60, 160)
ax4.set_ylim(60, 160)

plt.tight_layout()
output_file = "gcode_layer5_lines.png"
plt.savefig(output_file, dpi=150, bbox_inches='tight')
print(f"Saved to {output_file}")
plt.close()