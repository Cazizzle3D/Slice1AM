"""
Simplified 3D G-code renderer with Blender-style visualization
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
import re

def parse_gcode_lines(gcode_file):
    """Parse G-code into line segments per layer"""
    layers = {}
    current_z = 0.0
    last_x, last_y = None, None

    with open(gcode_file, 'r') as f:
        for line in f:
            if line.startswith('G1'):
                x_match = re.search(r'X([-]?[0-9]+\.?[0-9]*)', line)
                y_match = re.search(r'Y([-]?[0-9]+\.?[0-9]*)', line)
                z_match = re.search(r'Z([-]?[0-9]+\.?[0-9]*)', line)
                e_match = re.search(r'E', line)

                x = float(x_match.group(1)) if x_match else last_x
                y = float(y_match.group(1)) if y_match else last_y

                if z_match:
                    current_z = float(z_match.group(1))

                if e_match and x and y and last_x and last_y:
                    if current_z not in layers:
                        layers[current_z] = []
                    layers[current_z].append(((last_x, last_y), (x, y)))

                last_x, last_y = x, y

    return layers

print("Parsing G-code...")
gcode_path = "/mnt/d/papers/UNET and Meta Pseduolabeling/crazyfrog.gcode"
layers = parse_gcode_lines(gcode_path)
sorted_layers = sorted(layers.keys())
print(f"Found {len(sorted_layers)} layers")

# Visualize layer 5
target_layer = 5
if target_layer >= len(sorted_layers):
    target_layer = len(sorted_layers) - 1

print(f"Rendering layer {target_layer}...")

fig = plt.figure(figsize=(20, 5))

# Calculate bounds
all_x, all_y = [], []
for layer_lines in layers.values():
    for (start, end) in layer_lines:
        all_x.extend([start[0], end[0]])
        all_y.extend([start[1], end[1]])

x_center = (min(all_x) + max(all_x)) / 2
y_center = (min(all_y) + max(all_y)) / 2
plot_range = max(max(all_x) - min(all_x), max(all_y) - min(all_y)) * 0.6

# Panel A: 3D cumulative view
ax1 = fig.add_subplot(141, projection='3d')

for i in range(target_layer + 1):
    z = sorted_layers[i]
    lines = layers[z]

    # Set color and style
    if i < target_layer:
        color = '#ff9900'
        alpha = 0.4 + 0.3 * (i / target_layer)
        lw = 1.5
    else:
        color = '#ff3300'
        alpha = 1.0
        lw = 3

    # Draw thick lines to simulate extrusion
    for (start, end) in lines:
        # Draw multiple parallel lines to create thickness effect
        for offset in np.linspace(-0.2, 0.2, 3):
            ax1.plot([start[0], end[0]],
                    [start[1], end[1]],
                    [z + offset, z + offset],
                    color=color, alpha=alpha, linewidth=lw)

ax1.set_xlim(x_center - plot_range, x_center + plot_range)
ax1.set_ylim(y_center - plot_range, y_center + plot_range)
ax1.set_zlim(0, sorted_layers[target_layer] + 0.5)
ax1.set_title(f'a) Layer {target_layer} - 3D Build (Z={sorted_layers[target_layer]:.2f}mm)')
ax1.set_xlabel('X (mm)')
ax1.set_ylabel('Y (mm)')
ax1.set_zlabel('Z (mm)')
ax1.view_init(elev=25, azim=45)

# Style like Blender
ax1.xaxis.pane.fill = True
ax1.yaxis.pane.fill = True
ax1.zaxis.pane.fill = True
ax1.xaxis.pane.set_facecolor('#e8e8e8')
ax1.yaxis.pane.set_facecolor('#e8e8e8')
ax1.zaxis.pane.set_facecolor('#e8e8e8')
ax1.grid(True, alpha=0.3)

# Panel B: Blueprint (white on black)
ax2 = fig.add_subplot(142)
ax2.set_facecolor('black')

current_lines = layers[sorted_layers[target_layer]]
for (start, end) in current_lines:
    ax2.plot([start[0], end[0]], [start[1], end[1]], 'w-', linewidth=1.0)

ax2.set_xlim(x_center - plot_range, x_center + plot_range)
ax2.set_ylim(y_center - plot_range, y_center + plot_range)
ax2.set_aspect('equal')
ax2.set_title(f'b) Layer {target_layer} blueprint')
ax2.axis('off')

# Panel C: 3D isolated layer
ax3 = fig.add_subplot(143, projection='3d')

z = sorted_layers[target_layer]
# Draw with 3D thickness effect
for (start, end) in current_lines:
    # Bottom and top of extrusion
    for z_offset in [0, 0.2]:
        ax3.plot([start[0], end[0]],
                [start[1], end[1]],
                [z + z_offset, z + z_offset],
                color='#ff6600', linewidth=2.5, alpha=0.9)

    # Vertical edges
    ax3.plot([start[0], start[0]], [start[1], start[1]], [z, z + 0.2],
            color='#ff6600', linewidth=1, alpha=0.7)
    ax3.plot([end[0], end[0]], [end[1], end[1]], [z, z + 0.2],
            color='#ff6600', linewidth=1, alpha=0.7)

ax3.set_xlim(x_center - plot_range, x_center + plot_range)
ax3.set_ylim(y_center - plot_range, y_center + plot_range)
ax3.set_zlim(z - 0.2, z + 0.4)
ax3.set_title(f'c) Layer {target_layer} - 3D Isolated')
ax3.set_xlabel('X (mm)')
ax3.set_ylabel('Y (mm)')
ax3.set_zlabel('Z (mm)')
ax3.view_init(elev=30, azim=45)

# Light background
ax3.xaxis.pane.fill = True
ax3.yaxis.pane.fill = True
ax3.zaxis.pane.fill = True
ax3.xaxis.pane.set_facecolor('#f5f5f5')
ax3.yaxis.pane.set_facecolor('#f5f5f5')
ax3.zaxis.pane.set_facecolor('#f5f5f5')
ax3.grid(True, alpha=0.2)

# Panel D: Binary mask
ax4 = fig.add_subplot(144)
ax4.set_facecolor('black')

for (start, end) in current_lines:
    ax4.plot([start[0], end[0]], [start[1], end[1]], 'c-', linewidth=2.0)

ax4.set_xlim(x_center - plot_range, x_center + plot_range)
ax4.set_ylim(y_center - plot_range, y_center + plot_range)
ax4.set_aspect('equal')
ax4.set_title(f'd) Layer {target_layer} mask')
ax4.axis('off')

plt.tight_layout()
output_file = "gcode_layer5_3d_blender.png"
plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
print(f"Saved to {output_file}")
plt.close()