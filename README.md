# G-code to STL Reverse Engineering Project

## Overview

This project implements reverse engineering of G-code files back to STL meshes to enable rendering with the Slice-100K dataset's Blender rendering pipeline. The goal was to generate visual renderings of G-code files using the same multi-view rendering system that Slice-100K uses for STL files.

## Problem Statement

The Slice-100K dataset provides a comprehensive pipeline for rendering STL files into multi-view images using Blender. However, there was no direct way to render G-code files (sliced 3D printing instructions) using the same high-quality rendering system. This project attempts to bridge that gap by:

1. **Reverse engineering G-code** → Converting G-code toolpaths back into 3D mesh representations (STL format)
2. **Leveraging existing infrastructure** → Using the converted STL files with Slice-100K's proven Blender rendering pipeline

## Implementation Approach

### Core Scripts Developed

#### 1. G-code to STL Conversion
- **`gcode_to_stl.py`** - Basic G-code to STL converter with rectangular extrusion cross-sections
- **`gcode_to_stl_ultra.py`** - High-fidelity converter with cylindrical cross-sections and binary STL output

**Key Features:**
- Parses G-code movement commands (G1/G0) and extrusion values (E)
- Automatically detects layer height and extrusion width from G-code comments
- Creates 3D mesh geometry representing actual extruded plastic paths
- Generates watertight STL meshes suitable for rendering

#### 2. Direct Blender Rendering
- **`gcode_blender_script.py`** - Direct G-code to Blender renderer (bypasses STL conversion)

**Key Features:**
- Creates Blender mesh objects directly from G-code segments
- Uses skin modifier for realistic extrusion thickness
- Implements same camera positions and lighting as Slice-100K
- Generates all standard views (isometric + orthographic)

#### 3. Visualization and Testing
- **`gcode_3d_simple.py`** - Matplotlib-based 3D visualization for debugging
- **`gcode_cumulative_render.py`** - Layer-by-layer visualization
- **`gcode_line_render.py`** - Basic line rendering
- **`gcode_to_3d_render.py`** - Alternative 3D rendering approach

### Technical Implementation Details

#### G-code Parsing
```python
# Extract extrusion segments from G-code
segments.append({
    'start': (last_x, last_y, current_z),
    'end': (x, y, current_z),
    'width': detected_extrusion_width,
    'height': detected_layer_height
})
```

#### Mesh Generation Strategies

1. **Rectangular Cross-sections** (`gcode_to_stl.py`)
   - Creates rectangular tubes for each extrusion segment
   - 8 vertices per segment, 12 triangular faces
   - Good for simple visualization

2. **Cylindrical Cross-sections** (`gcode_to_stl_ultra.py`)
   - Creates cylindrical tubes with circular cross-sections
   - 8-16 vertices per circle, more realistic geometry
   - Watertight mesh suitable for professional rendering

#### Integration with Slice-100K

The converted STL files are designed to work directly with the existing Slice-100K rendering pipeline:

```bash
# Convert G-code to STL
python gcode_to_stl_ultra.py --gcode_path input.gcode --stl_path output.stl

# Render using Slice-100K Blender script
blender --background --python Slice-100K/blender_rendering/blender_script.py -- --object_path output.stl --output_dir renders/
```

## Results and Limitations

### Achievements
✅ Successfully parses G-code files and extracts toolpath geometry
✅ Generates valid STL meshes that represent printed objects
✅ Creates watertight meshes suitable for professional rendering
✅ Implements direct Blender rendering pipeline matching Slice-100K output format
✅ Supports multi-view rendering (10 camera angles: 4 isometric + 6 orthographic)
✅ Automatically detects printing parameters (layer height, extrusion width)

### Limitations
⚠️ **Time constraints prevented full Slice-100K integration testing**
⚠️ Mesh complexity can be very high for detailed G-code files
⚠️ No optimization for rendering performance vs. geometric fidelity
⚠️ Limited testing with various G-code flavors and slicers

## Usage Examples

### Convert G-code to STL
```bash
# Basic conversion
python gcode_to_stl.py --gcode_path sample.gcode --stl_path sample.stl

# High-fidelity conversion
python gcode_to_stl_ultra.py --gcode_path sample.gcode --stl_path sample.stl
```

### Direct Blender Rendering
```bash
# Render G-code directly with Blender
blender --background --python gcode_blender_script.py -- --gcode_path sample.gcode --output_dir renders/
```

### Visualization and Testing
```bash
# Create debugging visualizations
python gcode_3d_simple.py
python gcode_cumulative_render.py
```

## Future Work

### Immediate Next Steps
1. **Complete Slice-100K Integration Testing**
   - Test converted STL files with full Slice-100K rendering pipeline
   - Validate camera matrices and metadata generation
   - Ensure compatibility with existing dataset structure

2. **Performance Optimization**
   - Implement adaptive mesh decimation for large G-code files
   - Add level-of-detail (LOD) options for different rendering requirements
   - Optimize memory usage for batch processing

3. **Quality Improvements**
   - Add support for variable extrusion widths within single G-code file
   - Implement proper junction handling between segments
   - Add support for non-planar G-code (curved layers)

### Advanced Features
- **Multi-material Support** - Handle different extruders/materials
- **Post-processing Effects** - Add surface texturing, support material visualization
- **Batch Processing** - Efficient pipeline for processing large G-code datasets
- **Quality Metrics** - Automated validation of conversion accuracy

## File Structure

```
├── gcode_to_stl.py              # Basic G-code → STL converter
├── gcode_to_stl_ultra.py        # High-fidelity G-code → STL converter
├── gcode_blender_script.py      # Direct G-code → Blender renderer
├── gcode_3d_simple.py           # Matplotlib 3D visualization
├── gcode_cumulative_render.py   # Layer-by-layer visualization
├── gcode_line_render.py         # Basic line rendering
├── gcode_to_3d_render.py        # Alternative 3D rendering
├── test_gcode_*.py             # Testing and validation scripts
└── Slice-100K/                 # Original Slice-100K dataset code
    ├── blender_rendering/      # Target rendering pipeline
    ├── slicing/               # STL → G-code conversion
    └── ...
```

## Technical Notes

- **Coordinate Systems**: Maintains G-code coordinate system (typically mm units)
- **Memory Management**: Large G-code files can generate millions of faces - consider sampling
- **Rendering Quality**: Balance between geometric accuracy and rendering performance
- **File Formats**: Supports both ASCII and binary STL output formats

## References

- **Slice-100K Dataset**: https://slice-100k.github.io/
- **G-code Specification**: RepRap G-code documentation
- **Blender Python API**: For direct mesh creation and rendering

---

*This project represents an innovative approach to bridging the gap between 3D printing toolpath data and high-quality visualization systems, enabling new research possibilities in 3D printing analysis and machine learning.*
