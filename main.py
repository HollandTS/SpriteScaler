# --- main.py ---
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
import json
import logging
from frame_viewer import FrameViewer
from palette_handler import PaletteHandler
from PIL import Image

# Delete old log file if it exists
if os.path.exists('debug.log'):
    os.remove('debug.log')

# Setup logging
logging.basicConfig(
    filename='debug.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s'
)

# Try to import Wand, but make it optional
try:
    from wand.image import Image as WandImage
    from wand.version import MAGICK_VERSION
    WAND_AVAILABLE = True
    logging.info("ImageMagick is available")
except ImportError:
    WAND_AVAILABLE = False
    logging.warning("ImageMagick/Wand not available")

from io import BytesIO

class NewToolApp:
    def __init__(self, root):
        try:
            self.root = root
            self.root.title("Sprite Scaler")
            self.palette_handler = PaletteHandler()
            self.color_picking_mode = False
            
            # Initialize variables
            self.setup_ui()
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            
        except Exception as e:
            logging.error(f"Error initializing: {e}", exc_info=True)

    def setup_ui(self):
        try:
            # Main container using grid layout
            main_container = ttk.Frame(self.root)
            main_container.pack(fill="both", expand=True, padx=5, pady=5)
            main_container.grid_columnconfigure(0, weight=1)  # Left panel
            main_container.grid_columnconfigure(1, weight=1)  # Right panel
            
            # Left Panel - File, Palette, Transparency, and Frame Viewer
            left_panel = ttk.Frame(main_container)
            left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
            left_panel.grid_columnconfigure(0, weight=1)
            
            # Control Panel (Top of left panel)
            control_panel = ttk.Frame(left_panel)
            control_panel.grid(row=0, column=0, sticky="ew")
            
            # File Loading Controls
            file_frame = ttk.LabelFrame(control_panel, text="File")
            file_frame.pack(fill="x", pady=(0, 5))
            
            self.load_file_button = ttk.Button(file_frame, text="Load File", 
                                             command=self.load_file_dialog)
            self.load_file_button.pack(padx=5, pady=5)
            
            # Source Palette Controls
            palette_frame = ttk.LabelFrame(control_panel, text="Source Palette Controls")
            palette_frame.pack(fill="x", pady=(0, 5))
            
            self.load_palette_button = ttk.Button(palette_frame, text="Load Palette", 
                                                command=self.load_palette)
            self.load_palette_button.pack(side="left", padx=5, pady=5)

            self.remove_palette_button = ttk.Button(palette_frame, text="Remove Palette", 
                                                  command=self.remove_palette)
            self.remove_palette_button.pack(side="left", padx=5, pady=5)
            
            # Transparency Controls
            transparency_frame = ttk.LabelFrame(control_panel, text="Transparency")
            transparency_frame.pack(fill="x", pady=(0, 5))
            
            self.transparency_button = ttk.Button(transparency_frame, text="Transparency Color", 
                                                command=self.start_color_picking_mode)
            self.transparency_button.pack(side="left", padx=5, pady=5)

            self.color_indicator = tk.Canvas(transparency_frame, width=20, height=20, bg='white')
            self.color_indicator.pack(side="left", padx=5, pady=5)

            self.picking_status_label = ttk.Label(transparency_frame, text="")
            self.picking_status_label.pack(side="left", padx=5, pady=5)
            
            # Frame Viewer (Bottom of left panel)
            self.frame_viewer = FrameViewer(left_panel)
            self.frame_viewer.grid(row=1, column=0, sticky="nsew")
            left_panel.grid_rowconfigure(1, weight=1)
            
            # Right Panel - Scaling Controls
            right_panel = ttk.Frame(main_container)
            right_panel.grid(row=0, column=1, sticky="nsew")
            right_panel.grid_columnconfigure(0, weight=1)
            right_panel.grid_rowconfigure(1, weight=1)  # Make preview expand
            
            # Magic Kernel Upscale frame
            upscale_frame = ttk.LabelFrame(right_panel, text="Magic Kernel Upscale")
            upscale_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
            
            # Scale controls
            scale_frame = ttk.Frame(upscale_frame)
            scale_frame.pack(fill="x", padx=5, pady=5)
            
            ttk.Label(scale_frame, text="Scale %:").pack(side="left", padx=5)
            self.scale_var = tk.StringVar(value="100")
            self.scale_entry = ttk.Entry(scale_frame, textvariable=self.scale_var, width=10)
            self.scale_entry.pack(side="left", padx=5)
            
            ttk.Button(scale_frame, text="Apply Scale", command=self.apply_scale).pack(side="left", padx=5)
            
            # Filter selection
            filter_frame = ttk.LabelFrame(upscale_frame, text="Scaling Filter")
            filter_frame.pack(fill="x", padx=5, pady=5)
            
            self.filter_var = tk.StringVar(value='point')
            filters = [
                ('Nearest Neighbor', 'point'),
                ('Enhanced Pixel Art (MagicKernelSharp2021)', 'magic-kernel'),
                ('Smooth (Lanczos)', 'lanczos')
            ]
            
            for text, value in filters:
                ttk.Radiobutton(
                    filter_frame,
                    text=text,
                    value=value,
                    variable=self.filter_var
                ).pack(anchor=tk.W, padx=5)
            
            # Preview
            preview_frame = ttk.Frame(right_panel)
            preview_frame.grid(row=1, column=0, sticky="nsew")
            
            self.preview_viewer = FrameViewer(preview_frame)
            self.preview_viewer.pack(fill="both", expand=True)
            
            # Scaled Result Palette Controls
            scaled_palette_frame = ttk.LabelFrame(right_panel, text="Scaled Result Palette")
            scaled_palette_frame.grid(row=2, column=0, sticky="ew", pady=(5, 0))
            
            self.load_scaled_palette_button = ttk.Button(scaled_palette_frame, text="Load Palette", 
                                                       command=self.load_scaled_palette)
            self.load_scaled_palette_button.pack(side="left", padx=5, pady=5)

            self.remove_scaled_palette_button = ttk.Button(scaled_palette_frame, text="Remove Palette", 
                                                         command=self.remove_scaled_palette)
            self.remove_scaled_palette_button.pack(side="left", padx=5, pady=5)
            
            # Save button
            save_frame = ttk.Frame(right_panel)
            save_frame.grid(row=3, column=0, sticky="ew", pady=5)
            ttk.Button(save_frame, text="Save Scaled Image", 
                      command=self.save_scaled_image).pack(side="right")
            
            # Create second palette handler for scaled results
            self.scaled_palette_handler = PaletteHandler()
            
            # Bind color picking events
            self.root.bind('<Escape>', lambda e: self.stop_color_picking_mode())
            
        except Exception as e:
            logging.error(f"Error setting up UI: {e}")

    def load_file_dialog(self):
        """Open dialog to select image file(s)."""
        try:
            file_paths = filedialog.askopenfilenames(
                title="Select Image File(s)",
                filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.gif"), ("All Files", "*.*")]
            )
            if file_paths:
                all_frames = []
                for file_path in file_paths:
                    frames = self.load_file(file_path)
                    if frames:
                        all_frames.extend(frames)
                
                if all_frames:
                    self.frame_viewer.load_frames(all_frames)
                    logging.info(f"Loaded {len(all_frames)} frames from {len(file_paths)} files")
                    
        except Exception as e:
            logging.error(f"Error in file dialog: {e}")
            messagebox.showerror("Error", f"Failed to load files: {e}")

    def load_palette(self):
        """Open dialog to select a palette image."""
        try:
            file_path = filedialog.askopenfilename(
                title="Select Palette Image",
                filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.gif"), ("All Files", "*.*")]
            )
            if file_path and self.palette_handler.load_palette_from_image(file_path):
                # Reprocess all loaded images with new palette
                self.reapply_palette_to_all()
                messagebox.showinfo("Success", "Palette loaded and applied successfully!")
            else:
                messagebox.showerror("Error", "Failed to load palette from selected image.")
        except Exception as e:
            logging.error(f"Error loading palette: {e}")
            messagebox.showerror("Error", f"Failed to load palette: {e}")

    def reapply_palette_to_all(self):
        """Reapply current palette to all loaded images."""
        try:
            # Update grid window images
            if hasattr(self.frame_viewer, 'frames') and self.frame_viewer.frames:
                new_frames = []
                for frame in self.frame_viewer.frames:
                    new_frames.append(self.palette_handler.apply_palette_to_image(frame))
                self.frame_viewer.load_frames(new_frames)
                
        except Exception as e:
            logging.error(f"Error reapplying palette: {e}")

    def load_file(self, file_path):
        """Load a file (GIF or image) and return list of frames."""
        try:
            ext = os.path.splitext(file_path)[1].lower()
            frames = []
            
            if ext == '.gif':
                try:
                    with Image.open(file_path) as img:
                        for i in range(img.n_frames):
                            img.seek(i)
                            frame = img.copy()
                            if self.palette_handler.palette_colors is not None:
                                frame = self.palette_handler.apply_palette_to_image(frame)
                            frames.append(frame)
                    logging.info(f"Loaded GIF with {len(frames)} frames from {file_path}")
                except Exception as e:
                    logging.error(f"Error loading GIF {file_path}: {e}")
            else:
                # Regular image file
                try:
                    img = Image.open(file_path)
                    if self.palette_handler.palette_colors is not None:
                        img = self.palette_handler.apply_palette_to_image(img)
                    frames.append(img)
                    logging.info(f"Loaded image from {file_path}")
                except Exception as e:
                    logging.error(f"Error loading image {file_path}: {e}")
                    
            return frames
                
        except Exception as e:
            logging.error(f"Error loading file {file_path}: {e}")
            return []

    def delete_selected_files(self):
        try:
            if hasattr(self.frame_viewer, 'delete_selected_files'):
                self.frame_viewer.delete_selected_files()
        except Exception as e:
            logging.error(f"Error deleting grid items: {e}", exc_info=True)

    def save_config(self):
        try:
            if self.frame_viewer and hasattr(self.frame_viewer, 'get_image_paths'):
                config = {"images": self.frame_viewer.get_image_paths()}
                with open("config.json", "w") as f:
                    json.dump(config, f, indent=4)
                logging.info(f"Config saved with {len(config['images'])} paths.")
            else:
                logging.error("Cannot save config: frame_viewer missing.")
        except Exception as e:
            logging.error(f"Error saving config: {e}", exc_info=True)

    def load_config(self):
        try:
            logging.info(f"Loading config from config.json")
            if os.path.exists("config.json"):
                with open("config.json", "r") as f:
                    config_data = json.load(f)
                if isinstance(config_data, dict) and isinstance(config_data.get("images"), list):
                    return config_data
            return {}
        except json.JSONDecodeError as jde:
            logging.error(f"Error decoding config 'config.json': {jde}")
            return {}
        except Exception as e:
            logging.error(f"Error loading config: {e}", exc_info=True)
            return {}

    def on_closing(self):
        logging.info("WM_DELETE_WINDOW event.")
        self.save_config()
        self.root.destroy()

    def remove_palette(self):
        """Remove current palette and revert to original colors."""
        self.palette_handler.clear_palette()
        self.update_frame_viewer()  # Refresh the display
        logging.info("Palette removed")

    def start_color_picking_mode(self):
        """Enter color picking mode."""
        self.color_picking_mode = True
        self.picking_status_label.config(text="Click on a pixel to set transparency color")
        self.frame_viewer.canvas.bind('<Button-1>', self.on_canvas_click)
        self.transparency_button.config(state="disabled")
        self.frame_viewer.canvas.config(cursor="crosshair")

    def stop_color_picking_mode(self):
        """Exit color picking mode."""
        self.color_picking_mode = False
        self.picking_status_label.config(text="")
        self.frame_viewer.canvas.unbind('<Button-1>')
        self.transparency_button.config(state="normal")
        self.frame_viewer.canvas.config(cursor="")

    def on_canvas_click(self, event):
        """Handle canvas click for color picking."""
        if not self.color_picking_mode:
            return
            
        current_frame = self.frame_viewer.get_current_frame()
        if not current_frame:
            return
            
        # Get click coordinates in image space
        img_x, img_y, is_valid = self.frame_viewer.get_click_image_coordinates(event.x, event.y)
        if not is_valid:
            return
            
        # Get color at clicked position
        # Convert to RGB mode to ensure consistent color format
        rgb_frame = current_frame.convert('RGB')
        color = rgb_frame.getpixel((img_x, img_y))
        print(f"Picked color RGB{color} at position ({img_x}, {img_y})")
        
        # Update color indicator
        hex_color = '#{:02x}{:02x}{:02x}'.format(*color)
        self.color_indicator.config(bg=hex_color)
        
        # Set transparency color
        self.palette_handler.set_transparency_color(color)
        print(f"Set transparency color to {hex_color}")
        
        # Update the frame viewer with new transparency
        self.update_frame_viewer()
        
        # Exit color picking mode
        self.stop_color_picking_mode()

    def update_frame_viewer(self):
        """Refresh the frame viewer display with current frames."""
        try:
            if hasattr(self.frame_viewer, 'frames') and self.frame_viewer.frames:
                # Get current frames and reapply current palette (or lack thereof)
                new_frames = []
                for frame in self.frame_viewer.frames:
                    # Only create a new frame if it doesn't have an ID yet
                    if not hasattr(frame, 'palette_handler_id'):
                        new_frame = self.palette_handler.apply_palette_to_image(frame)
                    else:
                        # If it has an ID, just update the existing frame
                        new_frame = self.palette_handler.apply_palette_to_image(frame)
                        if hasattr(frame, 'palette_handler_id'):
                            new_frame.palette_handler_id = frame.palette_handler_id
                    new_frames.append(new_frame)
                
                # Update the display without creating new frame objects
                self.frame_viewer.load_frames(new_frames)
                logging.info("Frame viewer display updated")
        except Exception as e:
            logging.error(f"Error updating frame viewer: {e}")
            messagebox.showerror("Error", f"Failed to update display: {e}")

    def refresh_ui(self):
        """Restart the application."""
        try:
            # Save current state
            self.save_config()
            
            # Clear existing widgets
            for widget in self.root.winfo_children():
                widget.destroy()
                
            # Reinitialize
            self.palette_handler = PaletteHandler()
            self.color_picking_mode = False
            self.setup_ui()
            
            logging.info("Application refreshed")
            
        except Exception as e:
            logging.error(f"Error refreshing application: {e}")
            messagebox.showerror("Error", f"Failed to refresh: {e}")

    def destroy(self):
        """Clean up resources before destroying the window."""
        try:
            self.palette_handler.cleanup()
            super().destroy()
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")

    def save_scaled_image(self):
        """Save the scaled image to a file."""
        try:
            if not self.preview_viewer.frames:
                messagebox.showwarning("Warning", "No scaled image to save!")
                return
                
            file_path = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[
                    ("PNG files", "*.png"),
                    ("GIF files", "*.gif"),
                    ("All files", "*.*")
                ]
            )
            
            if file_path:
                base_path, ext = os.path.splitext(file_path)
                
                if len(self.preview_viewer.frames) > 1:
                    if ext.lower() == '.gif':
                        # Save as animated GIF
                        self.preview_viewer.frames[0].save(
                            file_path,
                            save_all=True,
                            append_images=self.preview_viewer.frames[1:],
                            optimize=False,
                            duration=100,  # 100ms per frame
                            loop=0
                        )
                        messagebox.showinfo("Success", "Animated GIF saved successfully!")
                    else:
                        # Save each frame as a separate PNG
                        for i, frame in enumerate(self.preview_viewer.frames):
                            frame_path = f"{base_path}_{i+1}{ext}"
                            frame.save(frame_path)
                        messagebox.showinfo("Success", f"All {len(self.preview_viewer.frames)} frames saved successfully!")
                else:
                    # Save single frame
                    self.preview_viewer.frames[0].save(file_path)
                    messagebox.showinfo("Success", "Image saved successfully!")
                    
                logging.info(f"Scaled image(s) saved to: {file_path}")
        except Exception as e:
            logging.error(f"Error saving scaled image: {e}")
            messagebox.showerror("Error", f"Failed to save image: {e}")

    def load_scaled_palette(self):
        """Open dialog to select a palette image for scaled results."""
        try:
            file_path = filedialog.askopenfilename(
                title="Select Palette Image",
                filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.gif"), ("All Files", "*.*")]
            )
            if file_path and self.scaled_palette_handler.load_palette_from_image(file_path):
                # Apply palette to scaled preview if it exists
                if hasattr(self.preview_viewer, 'frames') and self.preview_viewer.frames:
                    new_frames = []
                    for frame in self.preview_viewer.frames:
                        new_frames.append(self.scaled_palette_handler.apply_palette_to_image(frame))
                    self.preview_viewer.load_frames(new_frames)
                messagebox.showinfo("Success", "Palette loaded and applied to scaled result!")
            else:
                messagebox.showerror("Error", "Failed to load palette for scaled result.")
        except Exception as e:
            logging.error(f"Error loading scaled palette: {e}")
            messagebox.showerror("Error", f"Failed to load scaled palette: {e}")

    def remove_scaled_palette(self):
        """Remove palette from scaled result."""
        try:
            self.scaled_palette_handler.clear_palette()
            if hasattr(self.preview_viewer, 'frames') and self.preview_viewer.frames:
                new_frames = []
                for frame in self.preview_viewer.frames:
                    new_frames.append(self.scaled_palette_handler.apply_palette_to_image(frame))
                self.preview_viewer.load_frames(new_frames)
            logging.info("Scaled palette removed")
        except Exception as e:
            logging.error(f"Error removing scaled palette: {e}")
            messagebox.showerror("Error", f"Failed to remove scaled palette: {e}")

    def apply_scale(self):
        """Apply the scaling to the current frames using available scaling method."""
        try:
            # Validate scale percentage first
            try:
                scale_percent = float(self.scale_var.get())
                if scale_percent <= 0:
                    messagebox.showerror("Error", "Scale percentage must be positive")
                    return
            except ValueError:
                messagebox.showerror("Error", "Invalid scale percentage - must be a number")
                return
                
            scale_factor = scale_percent / 100.0
            current_frames = self.frame_viewer.frames
            if not current_frames:
                return
                
            if not WAND_AVAILABLE:
                # Use PIL's scaling methods
                filter_type = self.filter_var.get()
                filter_map = {
                    'nearest': Image.NEAREST,
                    'bilinear': Image.BILINEAR,
                    'bicubic': Image.BICUBIC
                }
                
                scaled_frames = []
                for frame in current_frames:
                    new_size = (int(frame.width * scale_factor), int(frame.height * scale_factor))
                    scaled_frame = frame.resize(new_size, filter_map[filter_type])
                    scaled_frames.append(scaled_frame)
                    
                self.preview_viewer.load_frames(scaled_frames)
                logging.info(f"Applied PIL scaling ({filter_type}): {scale_percent}%")
                return
                
            # Scale frames using ImageMagick
            scaled_frames = []
            for frame in current_frames:
                # Convert PIL image to bytes, preserving transparency
                img_byte_arr = BytesIO()
                if frame.mode != 'RGBA':
                    frame = frame.convert('RGBA')
                frame.save(img_byte_arr, format='PNG')
                img_byte_arr = img_byte_arr.getvalue()
                
                # Use Wand/ImageMagick for high-quality scaling
                with WandImage(blob=img_byte_arr) as wand_img:
                    new_width = int(wand_img.width * scale_factor)
                    new_height = int(wand_img.height * scale_factor)
                    
                    # If we have a transparency color, handle it before scaling
                    transparency_color = self.palette_handler.transparency_color
                    if transparency_color:
                        r, g, b = transparency_color
                        # Convert transparency color to string format
                        color_str = f'rgb({r},{g},{b})'
                        # Make this color transparent with no fuzz to prevent bleeding
                        wand_img.transparent_color(color_str, alpha=0, fuzz=0)
                    
                    # Apply the selected scaling filter
                    filter_type = self.filter_var.get()
                    if filter_type == 'magic-kernel':
                        try:
                            print("\nAttempting MagicKernelSharp2021 scaling...")
                            # Configure for pixel art scaling
                            wand_img.artifacts['filter:filter'] = 'MagicKernelSharp2021'
                            wand_img.artifacts['filter:support'] = '1.0'  # Tighter filter support for sharper edges
                            wand_img.artifacts['filter:window'] = 'Box'   # Box window for crisp edges
                            wand_img.artifacts['filter:lobes'] = '2'      # Fewer lobes for less ringing
                            wand_img.artifacts['filter:blur'] = '0.8'     # Slight sharpening
                            wand_img.resize(new_width, new_height)
                            print("Successfully used MagicKernelSharp2021")
                        except Exception as e1:
                            print(f"MagicKernelSharp2021 failed: {str(e1)}")
                            try:
                                print("Trying MagicKernelSharp2013...")
                                wand_img.artifacts['filter:filter'] = 'MagicKernelSharp2013'
                                wand_img.resize(new_width, new_height)
                                print("Successfully used MagicKernelSharp2013")
                            except Exception as e2:
                                print(f"MagicKernelSharp2013 failed: {str(e2)}")
                                print("Falling back to mitchell filter...")
                                wand_img.resize(new_width, new_height, filter='mitchell', blur=0.75)
                                print("Successfully used Mitchell filter")
                    elif filter_type == 'point':
                        # Nearest neighbor for perfect pixel scaling
                        wand_img.resize(new_width, new_height, filter='point')
                    else:
                        # Use Lanczos for smooth scaling with reduced blur
                        wand_img.resize(new_width, new_height, filter='lanczos', blur=0.9)
                    
                    # Convert back to PIL, preserving transparency
                    img_buffer = BytesIO(wand_img.make_blob('png'))
                    scaled_frame = Image.open(img_buffer).convert('RGBA')
                    
                    # Process pixels to ensure clean transparency and colors
                    pixels = scaled_frame.load()
                    for y in range(scaled_frame.height):
                        for x in range(scaled_frame.width):
                            r, g, b, a = pixels[x, y]
                            if transparency_color:
                                # If pixel is fully transparent or exactly matches transparency color
                                if a < 128 or (r, g, b) == transparency_color:
                                    pixels[x, y] = transparency_color + (255,)  # Make it the transparency color and fully opaque
                                else:
                                    # For non-transparent pixels, ensure full opacity
                                    pixels[x, y] = (r, g, b, 255)
                            else:
                                # If no transparency color, just ensure full opacity for non-transparent pixels
                                if a >= 128:
                                    pixels[x, y] = (r, g, b, 255)
                                else:
                                    pixels[x, y] = (0, 0, 0, 0)
                    
                    scaled_frames.append(scaled_frame.copy())
            
            # Update preview with scaled frames
            self.preview_viewer.load_frames(scaled_frames)
            
            # Apply scaled palette if one is loaded
            if self.scaled_palette_handler.palette_colors is not None:
                new_frames = []
                for frame in scaled_frames:
                    new_frames.append(self.scaled_palette_handler.apply_palette_to_image(frame))
                self.preview_viewer.load_frames(new_frames)
            
            logging.info(f"Applied {filter_type} scaling: {scale_percent}%")
            
        except Exception as e:
            logging.error(f"Error applying scale: {e}")
            messagebox.showerror("Error", f"Failed to apply scaling: {str(e)}")

if __name__ == "__main__":
    logging.info("="*20 + " Starting New Tool " + "="*20)
    try:
        root = tk.Tk()
        app = NewToolApp(root)
        root.mainloop()
    except Exception as e:
        logging.error(f"CRITICAL ERROR IN MAIN: {e}", exc_info=True)
        if sys.platform.startswith('win'):
            input("Press Enter to exit...")
    finally:
        logging.info("="*20 + " New Tool Exited " + "="*20 + "\n") 