import re
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.collections import LineCollection
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Line3DCollection
from PIL import Image

def parse_gcode_full(gcode_file):
    """Parse G-code file to extract all movements with Z coordinates"""
    layer_dict = {}
    current_z = 0.0
    last_x, last_y = None, None
    is_extruding = False

    with open(gcode_file, 'r') as file:
        for line in file:
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith(';'):
                continue

            if line.startswith('G1') or line.startswith('G0'):
                # Parse coordinates
                x_match = re.search(r'X([-]?[0-9]+\.?[0-9]*)', line)
                y_match = re.search(r'Y([-]?[0-9]+\.?[0-9]*)', line)
                z_match = re.search(r'Z([-]?[0-9]+\.?[0-9]*)', line)
                e_match = re.search(r'E([-]?[0-9]+\.?[0-9]*)', line)

                x = float(x_match.group(1)) if x_match else last_x
                y = float(y_match.group(1)) if y_match else last_y

                if z_match:
                    current_z = float(z_match.group(1))

                # Check if extruding
                is_extruding = e_match is not None and float(e_match.group(1)) > 0

                if is_extruding and x is not None and y is not None:
                    if current_z not in layer_dict:
                        layer_dict[current_z] = []
                    if last_x is not None and last_y is not None:
                        layer_dict[current_z].append({
                            'start': (last_x, last_y),
                            'end': (x, y),
                            'z': current_z
                        })

                last_x, last_y = x, y

    return layer_dict

def render_layer_cumulative_3d(layer_dict, target_layer_idx, figsize=(15, 5), line_width=0.4):
    """
    Render G-code with:
    a) 3D view with previous layers + current layer
    b) Current layer blueprint (top view)
    c) Isolated current layer
    d) Binary mask of current layer
    """
    sorted_layers = sorted(layer_dict.keys())

    if target_layer_idx >= len(sorted_layers):
        print(f"Layer {target_layer_idx} not found. Max layer: {len(sorted_layers)-1}")
        return

    target_z = sorted_layers[target_layer_idx]

    # Create figure with 4 subplots
    fig = plt.figure(figsize=figsize)

    # Calculate bounding box
    all_x, all_y = [], []
    for paths in layer_dict.values():
        for path in paths:
            all_x.extend([path['start'][0], path['end'][0]])
            all_y.extend([path['start'][1], path['end'][1]])

    x_min, x_max = min(all_x), max(all_x)
    y_min, y_max = min(all_y), max(all_y)
    x_center = (x_min + x_max) / 2
    y_center = (y_min + y_max) / 2
    max_range = max(x_max - x_min, y_max - y_min) / 2

    # Subplot a) 3D cumulative view (cross-sectional perspective)
    ax1 = fig.add_subplot(141, projection='3d')

    # Draw all layers up to and including target layer
    for i in range(target_layer_idx + 1):
        z = sorted_layers[i]
        paths = layer_dict[z]

        if i < target_layer_idx:
            # Previous layers in orange/red with lower alpha
            color = '#ff6600'
            alpha = 0.3 + 0.4 * (i / target_layer_idx)  # Fade older layers
            lw = 0.5
        else:
            # Current layer in bright orange/red
            color = '#ff3300'
            alpha = 1.0
            lw = 1.0

        for path in paths:
            ax1.plot([path['start'][0], path['end'][0]],
                    [path['start'][1], path['end'][1]],
                    [z, z],
                    color=color, alpha=alpha, linewidth=lw)

    ax1.set_xlim(x_center - max_range, x_center + max_range)
    ax1.set_ylim(y_center - max_range, y_center + max_range)
    ax1.set_zlim(0, sorted_layers[target_layer_idx] + 1)
    ax1.set_xlabel('X (mm)', fontsize=8)
    ax1.set_ylabel('Y (mm)', fontsize=8)
    ax1.set_zlabel('Z (mm)', fontsize=8)
    ax1.set_title(f'a) Layer {target_layer_idx} with history', fontsize=10)
    ax1.view_init(elev=20, azim=45)

    # Set gray background for 3D view
    ax1.xaxis.pane.fill = True
    ax1.yaxis.pane.fill = True
    ax1.zaxis.pane.fill = True
    ax1.xaxis.pane.set_facecolor('#d0d0d0')
    ax1.yaxis.pane.set_facecolor('#d0d0d0')
    ax1.zaxis.pane.set_facecolor('#d0d0d0')

    # Subplot b) Current layer blueprint (white on black)
    ax2 = fig.add_subplot(142)
    ax2.set_facecolor('black')

    current_paths = layer_dict[target_z]
    for path in current_paths:
        ax2.plot([path['start'][0], path['end'][0]],
                [path['start'][1], path['end'][1]],
                'w-', linewidth=1.5)

    ax2.set_xlim(x_center - max_range, x_center + max_range)
    ax2.set_ylim(y_center - max_range, y_center + max_range)
    ax2.set_aspect('equal')
    ax2.set_title(f'b) Layer {target_layer_idx} blueprint', fontsize=10)
    ax2.set_xticks([])
    ax2.set_yticks([])

    # Subplot c) Isolated current layer (orange on gray)
    ax3 = fig.add_subplot(143)
    ax3.set_facecolor('#d0d0d0')

    for path in current_paths:
        ax3.plot([path['start'][0], path['end'][0]],
                [path['start'][1], path['end'][1]],
                color='#ff6600', linewidth=2)

    ax3.set_xlim(x_center - max_range, x_center + max_range)
    ax3.set_ylim(y_center - max_range, y_center + max_range)
    ax3.set_aspect('equal')
    ax3.set_title(f'c) Layer {target_layer_idx} isolated', fontsize=10)
    ax3.set_xticks([])
    ax3.set_yticks([])

    # Subplot d) Binary mask (cyan on black)
    ax4 = fig.add_subplot(144)
    ax4.set_facecolor('black')

    for path in current_paths:
        ax4.plot([path['start'][0], path['end'][0]],
                [path['start'][1], path['end'][1]],
                color='cyan', linewidth=3)

    ax4.set_xlim(x_center - max_range, x_center + max_range)
    ax4.set_ylim(y_center - max_range, y_center + max_range)
    ax4.set_aspect('equal')
    ax4.set_title(f'd) Layer {target_layer_idx} mask', fontsize=10)
    ax4.set_xticks([])
    ax4.set_yticks([])

    plt.tight_layout()

    # Save figure instead of showing
    output_file = f"layer_{target_layer_idx:04d}_visualization.png"
    fig.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"Saved visualization to {output_file}")
    plt.close(fig)

    return fig

def render_all_layers_to_images(layer_dict, output_dir='gcode_renders', dpi=100):
    """
    Render all layers and save as images
    """
    import os
    os.makedirs(output_dir, exist_ok=True)

    sorted_layers = sorted(layer_dict.keys())

    for idx in range(len(sorted_layers)):
        print(f"Rendering layer {idx}/{len(sorted_layers)-1}")
        fig = render_layer_cumulative_3d(layer_dict, idx, figsize=(20, 5))

        if fig:
            fig.savefig(f"{output_dir}/layer_{idx:04d}.png", dpi=dpi, bbox_inches='tight')
            plt.close(fig)

def create_animation(layer_dict, output_file='gcode_animation.gif', fps=5):
    """
    Create an animated GIF of the printing process
    """
    from PIL import Image
    import os

    # First render all frames
    temp_dir = 'temp_frames'
    render_all_layers_to_images(layer_dict, output_dir=temp_dir, dpi=100)

    # Collect all images
    images = []
    sorted_layers = sorted(layer_dict.keys())

    for idx in range(len(sorted_layers)):
        img_path = f"{temp_dir}/layer_{idx:04d}.png"
        if os.path.exists(img_path):
            images.append(Image.open(img_path))

    if images:
        # Save as animated GIF
        images[0].save(output_file, save_all=True, append_images=images[1:],
                      duration=1000//fps, loop=0)
        print(f"Animation saved to {output_file}")

    # Clean up temp files
    import shutil
    shutil.rmtree(temp_dir)

# Main usage
if __name__ == "__main__":
    # UPDATE THIS PATH to your G-code file
    gcode_path = "/mnt/d/papers/UNET and Meta Pseduolabeling/crazyfrog.gcode"

    print("Parsing G-code file...")
    layer_dict = parse_gcode_full(gcode_path)
    print(f"Found {len(layer_dict)} layers")

    print("\nOptions:")
    print("1. View specific layer")
    print("2. Create animation of all layers")
    print("3. Interactive mode")

    choice = input("Enter choice (1-3): ")

    if choice == "1":
        layer_num = int(input(f"Enter layer number (0-{len(layer_dict)-1}): "))
        render_layer_cumulative_3d(layer_dict, layer_num)

    elif choice == "2":
        print("Creating animation...")
        create_animation(layer_dict, fps=5)

    elif choice == "3":
        layer_input = input(f"Enter layer number (0-{len(layer_dict)-1}) or 'exit': ")
        while layer_input != 'exit':
            try:
                render_layer_cumulative_3d(layer_dict, int(layer_input))
                layer_input = input(f"Enter layer number (0-{len(layer_dict)-1}) or 'exit': ")
            except:
                print("Invalid input")
                layer_input = input(f"Enter layer number (0-{len(layer_dict)-1}) or 'exit': ")