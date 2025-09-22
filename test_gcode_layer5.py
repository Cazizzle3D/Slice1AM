import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import re
import numpy as np
from mpl_toolkits.mplot3d import Axes3D

def parse_gcode_simple(gcode_file):
    """Simple G-code parser"""
    layer_dict = {}
    current_z = 0.0
    last_x, last_y = None, None

    with open(gcode_file, 'r') as f:
        for line in f:
            if line.startswith('G1'):
                x_match = re.search(r'X([-]?[0-9]+\.?[0-9]*)', line)
                y_match = re.search(r'Y([-]?[0-9]+\.?[0-9]*)', line)
                z_match = re.search(r'Z([-]?[0-9]+\.?[0-9]*)', line)
                e_match = re.search(r'E', line)

                if x_match:
                    last_x = float(x_match.group(1))
                if y_match:
                    last_y = float(y_match.group(1))
                if z_match:
                    current_z = float(z_match.group(1))

                if e_match and last_x and last_y:
                    if current_z not in layer_dict:
                        layer_dict[current_z] = []
                    layer_dict[current_z].append((last_x, last_y))

    return layer_dict

# Parse the G-code
print("Parsing G-code...")
gcode_path = "/mnt/d/papers/UNET and Meta Pseduolabeling/crazyfrog.gcode"
layers = parse_gcode_simple(gcode_path)
sorted_layers = sorted(layers.keys())
print(f"Found {len(sorted_layers)} layers")
print(f"Layer Z heights: {sorted_layers}")

# Select layer 5 to visualize
target_layer = 5
if target_layer >= len(sorted_layers):
    print(f"Layer {target_layer} not found, using last layer {len(sorted_layers)-1}")
    target_layer = len(sorted_layers) - 1

print(f"Visualizing layer {target_layer} (Z={sorted_layers[target_layer]:.2f}mm)")
print(f"Layer has {len(layers[sorted_layers[target_layer]])} points")

# Create visualization
fig = plt.figure(figsize=(20, 5))

# Plot 1: 3D view with cumulative layers
ax1 = fig.add_subplot(141, projection='3d')
for i in range(target_layer + 1):
    z = sorted_layers[i]
    points = layers[z]

    if i < target_layer:
        color = '#ff9900'
        alpha = 0.3
    else:
        color = '#ff3300'
        alpha = 1.0

    x_pts = [p[0] for p in points]
    y_pts = [p[1] for p in points]
    z_pts = [z] * len(points)

    if x_pts:
        ax1.scatter(x_pts, y_pts, z_pts, c=color, alpha=alpha, s=0.1)

ax1.set_title(f'a) Layer {target_layer} with history')
ax1.set_xlabel('X')
ax1.set_ylabel('Y')
ax1.set_zlabel('Z')
ax1.view_init(elev=25, azim=45)

# Plot 2: Current layer blueprint (white on black)
ax2 = fig.add_subplot(142)
ax2.set_facecolor('black')
current_points = layers[sorted_layers[target_layer]]
x_pts = [p[0] for p in current_points]
y_pts = [p[1] for p in current_points]
ax2.scatter(x_pts, y_pts, c='white', s=0.5)
ax2.set_title(f'b) Layer {target_layer} blueprint')
ax2.set_aspect('equal')

# Plot 3: Isolated current layer (orange on gray)
ax3 = fig.add_subplot(143)
ax3.set_facecolor('#d0d0d0')
ax3.scatter(x_pts, y_pts, c='#ff6600', s=1)
ax3.set_title(f'c) Layer {target_layer} isolated')
ax3.set_aspect('equal')

# Plot 4: Binary mask (cyan on black)
ax4 = fig.add_subplot(144)
ax4.set_facecolor('black')
ax4.scatter(x_pts, y_pts, c='cyan', s=2)
ax4.set_title(f'd) Layer {target_layer} mask')
ax4.set_aspect('equal')

plt.tight_layout()
output_file = "gcode_layer5_visualization.png"
plt.savefig(output_file, dpi=150)
print(f"Saved to {output_file}")
plt.close()