# SpriteScaler
A tool for scaling pixel art and sprites with advanced palette management and transparency handling

Usage:
- Load files: gif(s), or png's
- Select transparency color if needed (to prevent bleeding)
- Enter a resize and percentage Pick MagicKernelSharp2021
- Press 'Apply Scale'
- You can optionally load a palette to each: loaded images and scaled images.
- Press 'Save scaled image' to save as gif or loose png's

Includes the new 'MagicKernel'  resizer, which is perfect for resizing like 80% or 125%:

![sprite_scaler_gif_1](https://github.com/user-attachments/assets/843f9abe-dbd8-4590-8f28-4e421b899d6e)

Apply an optional palette: browse image to pick the closest colors  (handy for recoloring)

![sprite_scaler_gif_2](https://github.com/user-attachments/assets/eef93bb5-ef67-40f0-a5c3-d787260fecb1)


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
