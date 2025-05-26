# SpriteScaler
A tool to upscale, outline, and recolor pixel art or sprites with precision. It combines advanced scaling algorithms, flexible outlining, and intuitive color adjustment to help you polish and perfect your sprites 

## How to Use Sprite Scaler
Prepare Your Sprites

For best results, first cut up your sprite sheet into individual frames or images. This allows for more precise scaling and editing.
Load Your Files

Click the "Load File(s)" button to import one or more sprite images (PNG, GIF, etc).

### Set Transparency
Use the "Transparency Color" button to pick the color that should be treated as transparent in your sprites.
The "View Color" checkbox lets you toggle the display of the transparency color in the preview.

### Preview and Background
The preview area shows your current sprite. You can set a custom background image for better visualization.

### Scaling
Choose a scaling filter (Lanczos, Magic Kernel, Nearest Neighbor, Bicubic Sharper) and set your desired scale percentage.
Click "Apply Scale" to upscale or downscale your sprite.

### Outlining
Enable outlining to add a border around your sprite. You can customize outline color(s), thickness, direction, and use gradients for advanced effects.

### Change Color
Use the "Pick color" button to select a color from your sprite.
Adjust the color using the sliders for tolerance, hue, saturation, brightness, sharpness, and contrast.
Tip: Increasing the sharpness can help with color tolerance, making color replacement more precise.
Apply changes to the current frame or all frames.

### Undo/Redo
All major actions (scaling, outlining, color changes) support undo/redo for easy experimentation.

### Save
Choose your output folder and save the processed images.


## Why Use Sprite Scaler?
This unique combination of advanced scaling, flexible outlining, and powerful color adjustment gives you full control to polish your sprites—making them crisp, vibrant, and ready for any game or animation project.

## Previews:

Quick color change:

![change color_powerfull](https://github.com/user-attachments/assets/ae1c041a-2fd9-43c5-b311-d807a38b56cb)


Outlining:
![outlining](https://github.com/user-attachments/assets/b66cbc5e-26ad-436d-b4b8-f45bc9607af8)

Quick touch-up:

![final_touchup](https://github.com/user-attachments/assets/453e47c2-0f4d-42f4-8eab-9e0569889cc0)


## Requirements

1. Python 3.8 or higher
2. Required Python packages (install via pip)
3. ImageMagick (optional, for enhanced scaling)

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. ImageMagick Installation (Optional but recommended):

For Windows:
- Download and install from: https://imagemagick.org/script/download.php
- Make sure to check "Install legacy utilities" during installation
- Add ImageMagick to system PATH if not done automatically

For Linux:
```bash
sudo apt-get install imagemagick
```

For macOS:
```bash
brew install imagemagick
```

## Running the Tool

```bash
python main.py
```

## Features

- Multiple scaling algorithms including MagicKernelSharp for pixel art
- Palette management with color quantization
- Transparency support
- Frame-by-frame animation support
- Zoom controls
- LAB color space matching for accurate palette application

## Troubleshooting

1. If you get "ModuleNotFoundError":
   - Make sure you've installed all requirements: `pip install -r requirements.txt`

2. If enhanced scaling features are not available:
   - Check that ImageMagick is properly installed
   - Verify Wand can find ImageMagick: `python -c "from wand.image import Image"`

3. If you get memory errors with large images:
   - Try reducing the palette colors (default max is 256)
   - Process frames individually for animated GIFs 
