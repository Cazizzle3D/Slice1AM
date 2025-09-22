# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This repository contains the Slice-100K dataset implementation - a multimodal dataset of over 100,000 G-code files, tessellated CAD models, LVIS categories, and STL renderings for 3D printing research.

## Common Development Tasks

### STL Slicing to G-code
```bash
# Environment setup
conda env create -f Slice-100K/slicing/llm.yml
conda activate llm

# Run slicing (edit paths in slice_binary_gcode.py first)
python Slice-100K/slicing/slice_binary_gcode.py

# For batch processing on cluster
sbatch Slice-100K/slicing/example_slice.txt
```
Note: Requires PrusaSlicer v2.7.1 and libbgcode for bgcode/gcode conversion.

### G-code Visualization
```bash
# Interactive visualization (edit file path in gcode_render.py)
python Slice-100K/gcode_rendering/gcode_render.py
```

### Blender Rendering
```bash
# Environment setup
conda env create -f Slice-100K/blender_rendering/blender.yml

# Update paths in custom_main.py (lines 149, 351, 440-441)
# For batch rendering
sbatch Slice-100K/blender_rendering/slurm_batch.txt
```

### Category Generation
```bash
# Install requirements
pip install -r Slice-100K/Category_Generation/requirements.txt

# Generate categories from renderings
python Slice-100K/Category_Generation/Category_Generation.py /path/to/parent_folder
```

### Translation Experiments
```bash
# Install requirements
pip install -r Slice-100K/translation_experiments/requirements.txt

# Data preprocessing
python Slice-100K/translation_experiments/gcode_preprocessing/create_dataset.py

# Model training
python Slice-100K/translation_experiments/model_training/sft.py

# Evaluation
python Slice-100K/translation_experiments/model_eval/eval_model.py
```

## Key Architecture Components

### Data Pipeline
- **Slicing Module** (`slicing/`): Converts STL files to binary G-code using PrusaSlicer
- **Rendering Module** (`blender_rendering/`): Generates multi-view renderings of STL models
- **Category Generation** (`Category_Generation/`): Uses vision models to classify STL renderings into LVIS categories
- **G-code Visualization** (`gcode_rendering/`): Interactive layer-by-layer G-code viewer

### Translation Experiments
- **Preprocessing** (`translation_experiments/gcode_preprocessing/`): Tools for chunking, contour processing, and extrusion handling
- **Model Training** (`translation_experiments/model_training/`): Supervised fine-tuning implementation
- **Evaluation** (`translation_experiments/model_eval/`): Model evaluation and autoregressive generation tools

## Dataset Resources
- Dataset access: https://figshare.com/s/9d084ff84f3822d2bf17
- Dataset explorer: https://slice-100k.github.io/
- License: CC-BY-4.0