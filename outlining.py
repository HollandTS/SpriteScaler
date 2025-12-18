import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_dilation, binary_erosion
import threading

def on_transparency_color_changed(app):
    """Notify outlining logic that the transparency color has changed. Update color swatch borders if needed."""
    print(f"[DEBUG] Transparency color changed to: {getattr(app.palette_handler, 'transparency_color', None)}")
    color1 = getattr(app, 'outline_color1', None)
    color2 = getattr(app, 'outline_color2', None)
    transparency_color = getattr(app.palette_handler, 'transparency_color', None)
    # Helper to compare colors with tolerance
    def _within_tol(ca, cb, tol):
        return abs(ca[0] - cb[0]) <= tol and abs(ca[1] - cb[1]) <= tol and abs(ca[2] - cb[2]) <= tol

    ttol = int(getattr(app.palette_handler, 'transparency_tolerance', 0))
    # Update outline color1 canvas border
    if color1 is not None and transparency_color is not None and _within_tol(color1, transparency_color, ttol):
        app.outline_color1_canvas.config(highlightbackground='#ff0000', highlightthickness=2)
    else:
        app.outline_color1_canvas.config(highlightbackground='#888888', highlightthickness=1)
    # Update outline color2 canvas border
    if color2 is not None and transparency_color is not None and _within_tol(color2, transparency_color, ttol):
        app.outline_color2_canvas.config(highlightbackground='#ff0000', highlightthickness=2)
    else:
        app.outline_color2_canvas.config(highlightbackground='#888888', highlightthickness=1)

def pad_image_with_transparent_border(img, border=2):
    """Pad the image with a transparent border (default 2px) on all sides."""
    # Ensure input image is RGBA
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    w, h = img.size
    new_img = Image.new('RGBA', (w + 2*border, h + 2*border), (0, 0, 0, 0)) # Fully transparent background
    new_img.paste(img, (border, border))
    return new_img

def restore_transparency_color(img, transparency_color):
    """Convert all fully transparent pixels (alpha=0) to the transparency color (with alpha=255)."""
    # This function is not used in the core outlining logic flow, but kept for completeness
    arr = np.array(img.convert('RGBA'))
    mask = arr[..., 3] == 0
    arr[..., 0][mask] = transparency_color[0]
    arr[..., 1][mask] = transparency_color[1]
    arr[..., 2][mask] = transparency_color[2]
    arr[..., 3][mask] = 255
    return Image.fromarray(arr, 'RGBA')

def apply_transparency_color(img, transparency_color, tolerance=0):
    """Convert all pixels matching transparency_color to alpha=0 (transparent)."""
    # Ensure input image is RGBA
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    arr = np.array(img) # Already RGBA, no need for convert('RGBA') again
    rgb = arr[..., :3]
    if transparency_color is None:
        return img
    tc = np.array(transparency_color, dtype=np.int16)
    rgb_int = rgb.astype(np.int16)
    if not tolerance:
        mask = np.all(rgb_int == tc, axis=-1)
    else:
        mask = np.all(np.abs(rgb_int - tc) <= int(tolerance), axis=-1)
    arr[mask, 3] = 0 # Set alpha to 0 for those pixels
    return Image.fromarray(arr, 'RGBA')

def set_outlining_controls_state(app, enabled):
    state = "normal" if enabled else "disabled"
    app.outline_color1_btn.config(state=state)
    app.outline_color2_btn.config(state="normal" if (enabled and app.outline_use_gradient_var.get()) else "disabled")
    app.outline_use_gradient_cb.config(state=state)
    app.outline_amount_slider.config(state=state)
    app.outline_amount_entry.config(state=state)
    app.outline_thickness_entry.config(state=state)
    app.apply_outline_btn.config(state=state)

def on_outline_enable_toggle(app):
    enabled = app.outline_enabled_var.get()
    set_outlining_controls_state(app, enabled)

def on_outline_gradient_toggle(app):
    if app.outline_enabled_var.get():
        app.outline_color2_btn.config(state="normal" if app.outline_use_gradient_var.get() else "disabled")

def pick_outline_color(app, which):
    from tkinter.colorchooser import askcolor
    initial = app.outline_color1 if which == 1 else app.outline_color2
    rgb, hexstr = askcolor(color="#%02x%02x%02x" % initial, title="Pick outline color")
    if rgb:
        rgb_tuple = tuple(int(x) for x in rgb[:3])
        if which == 1:
            app.outline_color1 = rgb_tuple
        else:
            app.outline_color2 = rgb_tuple
        update_outline_color_canvas(app, which)

def update_outline_color_canvas(app, which):
    color = app.outline_color1 if which == 1 else app.outline_color2
    canvas = app.outline_color1_canvas if which == 1 else app.outline_color2_canvas
    canvas.config(bg="#%02x%02x%02x" % color)

def apply_outlining(app):
    if not app.outline_enabled_var.get():
        messagebox.showinfo("Outlining", "Enable outlining to apply.")
        return
    # Always use the original preview frames for outlining
    if not hasattr(app, '_original_preview_frames'):
        app._original_preview_frames = [frame.copy() for frame in app.preview_viewer.frames]
    color1 = app.outline_color1
    use_gradient = app.outline_use_gradient_var.get()
    color2 = app.outline_color2 if use_gradient else app.outline_color1
    direction = app.outline_direction_var.get()
    # Check for outline color matching transparency color
    transparency_color = getattr(app, 'transparency_color', None)
    if transparency_color is None:
        messagebox.showerror("Outlining Error", "You must set a transparency color before outlining. Use the 'Transparency Color' button to pick the background color of your sprite.")
        return
    # Consider transparency tolerance: if outline color is within tolerance of transparency color, it's effectively invisible
    ttol = int(getattr(app.palette_handler, 'transparency_tolerance', 0))
    def _within_tol(ca, cb, tol):
        return abs(ca[0] - cb[0]) <= tol and abs(ca[1] - cb[1]) <= tol and abs(ca[2] - cb[2]) <= tol
    if _within_tol(color1, transparency_color, ttol) or (use_gradient and _within_tol(color2, transparency_color, ttol)):
        messagebox.showerror("Outlining Error", "Outline color must not match (within tolerance) the transparency color! Please pick a different outline color.")
        return
    # Robustly get amount and thickness, fallback to defaults if blank/invalid
    try:
        amount = int(app.outline_amount_var.get())
    except Exception:
        amount = 100
    try:
        thickness = int(app.outline_thickness_var.get())
    except Exception:
        thickness = 1
    side = app.outline_side_var.get() if hasattr(app, 'outline_side_var') else 'outside'
    # Show loading window
    app._cancel_apply_outline = False
    loading_win = tk.Toplevel(app.root)
    loading_win.title("Applying Outlining")
    loading_win.geometry("320x100")
    loading_win.transient(app.root)
    loading_win.grab_set()
    tk.Label(loading_win, text="Applying outlining to all frames...", font=("Segoe UI", 11)).pack(pady=10)
    progress_var = tk.StringVar(value="0 / {}".format(len(app._original_preview_frames)))
    progress_label = tk.Label(loading_win, textvariable=progress_var)
    progress_label.pack()
    def on_cancel():
        app._cancel_apply_outline = True
    cancel_btn = ttk.Button(loading_win, text="Cancel", command=on_cancel)
    cancel_btn.pack(pady=5)

    def worker():
        new_frames = []
        total = len(app._original_preview_frames)
        transparency_color = getattr(app, 'transparency_color', None)
        for i, frame in enumerate(app._original_preview_frames):
            if app._cancel_apply_outline:
                break
            # Step 1: Make original transparency color transparent (alpha 0)
            ttol = int(getattr(app.palette_handler, 'transparency_tolerance', 0))
            frame_for_outline = apply_transparency_color(frame, transparency_color, ttol)
            # Step 2: Pad the image with a transparent border
            padded = pad_image_with_transparent_border(frame_for_outline, border=2)
            # Step 3: Apply outlining. This should return an RGBA image where only sprite+outline are opaque.
            outlined = outline_image(
                padded,
                color1,
                color2,
                use_gradient,
                direction,
                amount,
                thickness,
                side,
                transparency_color=transparency_color # For debug/internal masking within outline_image
            )
            # Step 4: Crop back to original size (remove border)
            w, h = frame_for_outline.size
            outlined_cropped = outlined.crop((2, 2, 2 + w, 2 + h))
            new_frames.append(outlined_cropped)
            progress_var.set(f"{i+1} / {total}")
        def on_done():
            loading_win.grab_release()
            loading_win.destroy()
            if app._cancel_apply_outline:
                messagebox.showinfo("Cancelled", "Outlining cancelled.")
                return
            app.preview_viewer.load_frames(new_frames)
            # Restore the preview viewer's background settings to their normal state (user's setting)
            app.update_preview_with_bg() 
            

            
            app._original_preview_frames = [frame.copy() for frame in new_frames]
            print("[DEBUG] Outlining applied, preview and originals updated.", file=sys.stderr)
            messagebox.showinfo("Done", "Outlining applied to all frames.")
        app.root.after(0, on_done)

    threading.Thread(target=worker, daemon=True).start()

def outline_image(img, color1, color2, use_gradient, direction, amount, thickness, side='outside', transparency_color=None):
    # img: PIL Image (RGBA), color1/color2: (r,g,b), use_gradient: bool, direction: 'vertical'/'horizontal', amount: 0-100, thickness: px
    
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    arr = np.array(img)
    alpha = arr[..., 3]
    # Print alpha stats
    print(f"[DEBUG] alpha min: {alpha.min()}, max: {alpha.max()}, unique: {np.unique(alpha)}", file=sys.stderr)
    # Always use alpha channel for mask (image is preprocessed for transparency)
    mask = (alpha > 0).astype(np.uint8) # Binary mask: 1 for sprite pixels (alpha > 0), 0 for transparent background
    
    # Clamp and sanitize thickness and amount
    try:
        thickness = int(thickness)
    except Exception:
        thickness = 1
    if thickness < 1:
        thickness = 1
    try:
        amount = float(amount)
    except Exception:
        amount = 100.0
    if amount < 0:
        amount = 0
    if amount > 100:
        amount = 100

    # Print debug info about the mask
    print(f"[DEBUG] mask shape: {mask.shape}, unique: {np.unique(mask)}, sum: {mask.sum()}", file=sys.stderr)



    # Generate outline mask
    if side == 'outside':
        # Outline is dilation of sprite mask MINUS the original sprite mask
        outline_mask = binary_dilation(mask, iterations=thickness) & (~mask)
    else:  # 'inside'
        # Outline is original sprite mask MINUS erosion of sprite mask
        outline_mask = mask & (~binary_erosion(mask, iterations=thickness))
        
    outline_alpha_val = int(255 * (amount / 100.0)) # Alpha for the outline color


    # Print number of outline pixels and unique values
    print(f"[DEBUG] outline_mask sum: {outline_mask.sum()}, unique: {np.unique(outline_mask)}", file=sys.stderr)



    # If mask is all 1s (fully opaque), warn and overlay a yellow border for debug
    if np.all(mask == 1):
        print("[WARN] Mask is fully opaque (all 1s), outlining will not be visible.", file=sys.stderr)
        debug_img = Image.fromarray(arr.copy(), 'RGBA')
        draw = ImageDraw.Draw(debug_img)
        w, h = debug_img.size
        draw.rectangle([0, 0, w-1, h-1], outline=(255,255,0,255), width=3)
        return debug_img # Return debug image in case of full mask

    # Get image dimensions
    h, w = arr.shape[:2]

    # Create empty arrays for R, G, B channels, size (H, W)
    outline_r_channel = np.empty((h, w), dtype=np.uint8)
    outline_g_channel = np.empty((h, w), dtype=np.uint8)
    outline_b_channel = np.empty((h, w), dtype=np.uint8)

    # Calculate gradient colors if enabled
    if use_gradient:
        # Create a meshgrid to get X and Y coordinates for each pixel
        # This allows applying gradients across the full 2D array (H, W)
        Y, X = np.indices((h, w), dtype=np.float32)

        if direction == 'vertical':
            # Normalize Y coordinates (0 to h-1) to (0 to 1)
            grad_map = Y / (h - 1) if h > 1 else np.zeros((h, w), dtype=np.float32)
        else: # horizontal
            # Normalize X coordinates (0 to w-1) to (0 to 1)
            grad_map = X / (w - 1) if w > 1 else np.zeros((h, w), dtype=np.float32)
        
        # Apply gradient interpolation across the full (H,W) array
        outline_r_channel = (color1[0] * (1 - grad_map) + color2[0] * grad_map).astype(np.uint8)
        outline_g_channel = (color1[1] * (1 - grad_map) + color2[1] * grad_map).astype(np.uint8)
        outline_b_channel = (color1[2] * (1 - grad_map) + color2[2] * grad_map).astype(np.uint8)
    else:
        # Solid color for outline
        outline_r_channel.fill(color1[0])
        outline_g_channel.fill(color1[1])
        outline_b_channel.fill(color1[2])
    
    # Create the outline layer (an RGBA image filled with transparency initially)
    outline_layer = np.zeros_like(arr) 

    # Get the 1D indices (flat positions) where the outline_mask is True
    rows, cols = np.where(outline_mask)

    # Assign values using these 1D index arrays
    outline_layer[rows, cols, 0] = outline_r_channel[rows, cols]
    outline_layer[rows, cols, 1] = outline_g_channel[rows, cols]
    outline_layer[rows, cols, 2] = outline_b_channel[rows, cols]
    outline_layer[rows, cols, 3] = outline_alpha_val # Scalar value broadcasts correctly

    # Now, composite the original image (arr) and the new outline_layer
    out = arr.copy() 
    
    outline_pixels_to_draw = (outline_layer[..., 3] > 0)
    out[outline_pixels_to_draw, :4] = outline_layer[outline_pixels_to_draw, :4]

    # --- DEBUG: Print alpha stats for final 'out' image ---
    print(f"[DEBUG] out alpha min: {out[...,3].min()}, max: {out[...,3].max()}, unique: {np.unique(out[...,3])}", file=sys.stderr)

        
    return Image.fromarray(out, 'RGBA')