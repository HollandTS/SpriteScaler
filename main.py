import outlining
# filepath: c:\Users\its_m\Documents\SpriteScaler\main.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
import json
import logging
from frame_viewer import FrameViewer
from palette_handler import PaletteHandler
from PIL import Image, ImageDraw

os.environ['MAGICK_HOME'] = os.path.join(os.path.dirname(__file__), 'imagemagick')

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
    def _fill_transparency_with_color(self, frame, fill_color):
        """Return a copy of frame with all transparent pixels filled with fill_color (RGB tuple)."""
        if frame.mode != 'RGBA':
            frame = frame.convert('RGBA')
        background = Image.new('RGBA', frame.size, fill_color + (255,))
        background.paste(frame, mask=frame.split()[3])  # Use alpha channel as mask
        return background.convert('RGB')
    
    def sync_preview_to_frame_viewer(self, *args, **kwargs):
        # No-op: frame_viewer removed, keep for compatibility
        pass
    
    def __init__(self, root):
        try:
            self.root = root
            self.root.title("Sprite Scaler")
            self.palette_handler = PaletteHandler()
            self.scaled_palette_handler = PaletteHandler()  # Ensure this is always initialized
            self.color_picking_mode = False
            self.bg_image_path = None  # Path to the background image for preview
            self.bg_image = None  # Store the background image (fixes AttributeError)
            self.transparency_color = None # The actual picked transparency color (RGB tuple)

            # Initialize variables
            self.setup_ui()
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

            # Undo/Redo stacks for various operations
            self._color_edit_undo_stack = []
            self._color_edit_redo_stack = []
            self._scale_undo_stack = []
            self._scale_redo_stack = []
            self._outline_undo_stack = []
            self._outline_redo_stack = []

        except Exception as e:
            logging.error(f"Error initializing: {e}", exc_info=True)

    def setup_ui(self):
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

        self.load_file_button = ttk.Button(file_frame, text="Load File(s)", command=self.load_file_dialog)
        self.load_file_button.pack(padx=5, pady=5)



        # Transparency Controls
        transparency_frame = ttk.LabelFrame(control_panel, text="Transparency")
        transparency_frame.pack(fill="x", pady=(0, 5))

        self.transparency_button = ttk.Button(transparency_frame, text="Transparency Color", command=self.start_color_picking_mode)
        self.transparency_button.pack(side="left", padx=5, pady=5)
        self.color_indicator = tk.Canvas(transparency_frame, width=20, height=20, bg='white')
        self.color_indicator.pack(side="left", padx=5, pady=5)
        self.picking_status_label = ttk.Label(transparency_frame, text="")
        self.picking_status_label.pack(side="left", padx=5, pady=5)
        
        # New "View Color" checkbox
        self.view_transparency_color_var = tk.BooleanVar(value=True) # Default to True
        self.view_transparency_color_cb = ttk.Checkbutton(transparency_frame, text="View Color", variable=self.view_transparency_color_var, command=self.update_preview_with_bg)
        self.view_transparency_color_cb.pack(side="left", padx=5, pady=5)


        # --- Preview area (now on the left, below controls) ---
        preview_label = ttk.Label(left_panel, text="Preview:", font=("Segoe UI", 10, "bold"))
        preview_label.grid(row=1, column=0, sticky="w", padx=(2,0), pady=(8,0))
        self.preview_viewer = FrameViewer(left_panel)
        self.preview_viewer.grid(row=2, column=0, sticky="nsew", pady=(0, 8))
        left_panel.grid_rowconfigure(2, weight=1)
        # Add refresh button to preview (top right)
        self.preview_refresh_btn = tk.Button(left_panel, text="\u21bb", font=("Segoe UI", 10), width=2, command=self.refresh_preview, relief="flat", bg="#f0f0f0")
        self.preview_refresh_btn.place(relx=1.0, rely=0.0, anchor="ne", x=-2, y=180)  # Adjust y as needed
        # Add BG Image button next to refresh
        self.bg_image_btn = tk.Button(left_panel, text="BG Img", font=("Segoe UI", 9), width=6, command=self.select_bg_image, relief="flat", bg="#e0e0e0")
        self.bg_image_btn.place(relx=1.0, rely=0.0, anchor="ne", x=-60, y=180)  # Adjust y as needed

        # Right Panel - Scaling Controls
        right_panel = ttk.Frame(main_container)
        right_panel.grid(row=0, column=1, sticky="nsew")
        right_panel.grid_columnconfigure(0, weight=1)
        right_panel.grid_rowconfigure(1, weight=1)  # Make preview expand


        # Scale frame (renamed from Magic Kernel Upscale)
        upscale_frame = ttk.LabelFrame(right_panel, text="Scale")
        upscale_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))



        # Scale controls
        scale_controls_frame = ttk.Frame(upscale_frame) # New frame for scale controls + undo/redo
        scale_controls_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(scale_controls_frame, text="Scale %:").pack(side="left", padx=5)
        self.scale_var = tk.StringVar(value="100")
        self.scale_entry = ttk.Entry(scale_controls_frame, textvariable=self.scale_var, width=10)
        self.scale_entry.pack(side="left", padx=5)

        ttk.Button(scale_controls_frame, text="Apply Scale", command=self.apply_scale).pack(side="left", padx=5)

        # Undo/Redo buttons for scaling
        scale_undo_redo_frame = ttk.Frame(scale_controls_frame)
        scale_undo_redo_frame.pack(side="left", padx=(10, 0))
        self.undo_scale_button = ttk.Button(scale_undo_redo_frame, text="Undo", command=self.undo_scale_apply)
        self.undo_scale_button.pack(side="left", padx=(0, 5))
        self.redo_scale_button = ttk.Button(scale_undo_redo_frame, text="Redo", command=self.redo_scale_apply)
        self.redo_scale_button.pack(side="left")


        # Filter selection
        filter_frame = ttk.LabelFrame(upscale_frame, text="Scaling Filter")
        filter_frame.pack(fill="x", padx=5, pady=5)

        self.filter_var = tk.StringVar(value='magic-kernel')
        filters = [
            ('Smooth (Lanczos) – Enlarging', 'lanczos'),
            ('Enhanced Pixel Art (MagicKernelSharp2021) – Shrink & Enlarge', 'magic-kernel'),
            ('Nearest Neighbor – Shrinking', 'point'),
            ('Bicubic Sharper – Shrinking', 'bicubic-sharper'),
        ]

        for text, value in filters:
            ttk.Radiobutton(
                filter_frame,
                text=text,
                value=value,
                variable=self.filter_var
            ).pack(anchor=tk.W, padx=5)

        # Scaled Result Palette Controls

        # --- Outlining Group ---
        outlining_frame = ttk.LabelFrame(right_panel, text="Outlining")
        outlining_frame.grid(row=5, column=0, sticky="ew", pady=(5, 0))
        self.outline_collapsed = tk.BooleanVar(value=False)
        # ... (existing outlining code remains unchanged)

        # --- Scaled Result Palette and Save Controls (moved below Outlining) ---
        scaled_palette_frame = ttk.LabelFrame(right_panel, text="Apply Palette")
        scaled_palette_frame.grid(row=6, column=0, sticky="ew", pady=(5, 0))

        self.load_scaled_palette_button = ttk.Button(scaled_palette_frame, text="Load Palette", command=self.load_scaled_palette)
        self.load_scaled_palette_button.pack(side="left", padx=5, pady=5)

        self.remove_scaled_palette_button = ttk.Button(scaled_palette_frame, text="Remove Palette", command=self.remove_scaled_palette)
        self.remove_scaled_palette_button.pack(side="left", padx=5, pady=5)

        # Save button, folder picker, and transparency color checkbox
        save_frame = ttk.Frame(right_panel)
        save_frame.grid(row=7, column=0, sticky="ew", pady=5)

        # Checkbox: Put back transparency color
        self.put_back_transparency_var = tk.BooleanVar(value=True)
        self.put_back_transparency_checkbox = ttk.Checkbutton(
            save_frame,
            text="Keep transparency",
            variable=self.put_back_transparency_var
        )
        self.put_back_transparency_checkbox.pack(side="left", padx=(0, 8))

        # Folder picker for saving images
        self.save_folder = os.getcwd()
        self.save_folder_label_var = tk.StringVar(value=os.path.basename(self.save_folder))

        def pick_save_folder():
            folder = filedialog.askdirectory(title="Select Folder to Save Images", initialdir=self.save_folder)
            if folder:
                self.save_folder = folder
                self.save_folder_label_var.set(os.path.basename(folder))

        pick_folder_btn = ttk.Button(save_frame, text="Pick a folder", command=pick_save_folder)
        pick_folder_btn.pack(side="right", padx=(0, 8))
        folder_label = ttk.Label(save_frame, textvariable=self.save_folder_label_var, width=18, anchor="w")
        folder_label.pack(side="right", padx=(0, 8))

        ttk.Button(save_frame, text="Save Image(s)", command=self.save_scaled_image).pack(side="right")

        # --- Change Color Group ---
        change_color_frame = ttk.LabelFrame(right_panel, text="Change color")
        change_color_frame.grid(row=2, column=0, sticky="ew", pady=(5, 0))

        # Pick color (from preview) and show picked color (move to top)
        pick_color_row = ttk.Frame(change_color_frame)
        pick_color_row.pack(side="top", fill="x", pady=(2, 2))
        self.pick_color_button = ttk.Button(pick_color_row, text="Pick color", command=self.start_preview_color_pick)
        self.pick_color_button.pack(side="left", padx=5, pady=5)
        self.picked_color_canvas = tk.Canvas(pick_color_row, width=20, height=20, bg='white', highlightthickness=1, relief='ridge')
        self.picked_color_canvas.pack(side="left", padx=2)
        self.picked_color = None

        # --- Color Adjustment Sliders Group ---
        sliders_group = ttk.Frame(change_color_frame)
        sliders_group.pack(side="top", fill="x", padx=(10,0), pady=5)

        # Input Tolerance slider (for picked color) with entry for manual editing
        ttk.Label(sliders_group, text="Input Tolerance:").grid(row=0, column=0, sticky="w", padx=(0,2))
        self.input_tolerance_var = tk.IntVar(value=30)
        self.input_tolerance_slider = ttk.Scale(sliders_group, from_=0, to=1000, variable=self.input_tolerance_var, orient=tk.HORIZONTAL, length=320, command=self.update_live_color_preview)
        self.input_tolerance_slider.grid(row=0, column=1, sticky="ew", padx=2)
        self.input_tolerance_entry = ttk.Entry(sliders_group, textvariable=self.input_tolerance_var, width=5)
        self.input_tolerance_entry.grid(row=0, column=2, padx=2)
        self.input_tolerance_entry.bind('<Return>', lambda e: self.update_live_color_preview())

        # Hue
        ttk.Label(sliders_group, text="Hue:").grid(row=1, column=0, sticky="w", padx=(0,2))
        self.hue_var = tk.DoubleVar(value=0.0)
        self.hue_slider = ttk.Scale(sliders_group, from_=-180, to=180, variable=self.hue_var, orient=tk.HORIZONTAL, length=220, command=self.update_live_color_preview)
        self.hue_slider.grid(row=1, column=1, sticky="ew", padx=2)
        self.hue_entry = ttk.Entry(sliders_group, textvariable=self.hue_var, width=6)
        self.hue_entry.grid(row=1, column=2, padx=2)
        self.hue_entry.bind('<Return>', lambda e: self.update_live_color_preview())

        # Saturation
        ttk.Label(sliders_group, text="Saturation:").grid(row=2, column=0, sticky="w", padx=(0,2))
        self.sat_var = tk.DoubleVar(value=0.0)
        self.sat_slider = ttk.Scale(sliders_group, from_=-1.0, to=1.0, variable=self.sat_var, orient=tk.HORIZONTAL, length=220, command=self.update_live_color_preview)
        self.sat_slider.grid(row=2, column=1, sticky="ew", padx=2)
        self.sat_entry = ttk.Entry(sliders_group, textvariable=self.sat_var, width=6)
        self.sat_entry.grid(row=2, column=2, padx=2)
        self.sat_entry.bind('<Return>', lambda e: self.update_live_color_preview())

        # Brightness
        ttk.Label(sliders_group, text="Brightness:").grid(row=3, column=0, sticky="w", padx=(0,2))
        self.bri_var = tk.DoubleVar(value=0.0)
        self.bri_slider = ttk.Scale(sliders_group, from_=-1.0, to=1.0, variable=self.bri_var, orient=tk.HORIZONTAL, length=220, command=self.update_live_color_preview)
        self.bri_slider.grid(row=3, column=1, sticky="ew", padx=2)
        self.bri_entry = ttk.Entry(sliders_group, textvariable=self.bri_var, width=6)
        self.bri_entry.grid(row=3, column=2, padx=2)
        self.bri_entry.bind('<Return>', lambda e: self.update_live_color_preview())

        # Sharpness
        ttk.Label(sliders_group, text="Sharpness:").grid(row=4, column=0, sticky="w", padx=(0,2))
        self.sharpness_var = tk.DoubleVar(value=1.0)
        self.sharpness_slider = ttk.Scale(sliders_group, from_=0.0, to=3.0, variable=self.sharpness_var, orient=tk.HORIZONTAL, length=220, command=self.update_live_color_preview)
        self.sharpness_slider.grid(row=4, column=1, sticky="ew", padx=2)
        self.sharpness_entry = ttk.Entry(sliders_group, textvariable=self.sharpness_var, width=6)
        self.sharpness_entry.grid(row=4, column=2, padx=2)
        self.sharpness_entry.bind('<Return>', lambda e: self.update_live_color_preview())

        # Contrast
        ttk.Label(sliders_group, text="Contrast:").grid(row=5, column=0, sticky="w", padx=(0,2))
        self.contrast_var = tk.DoubleVar(value=0.0)
        self.contrast_slider = ttk.Scale(sliders_group, from_=-1.0, to=1.0, variable=self.contrast_var, orient=tk.HORIZONTAL, length=220, command=self.update_live_color_preview)
        self.contrast_slider.grid(row=5, column=1, sticky="ew", padx=2)
        self.contrast_entry = ttk.Entry(sliders_group, textvariable=self.contrast_var, width=6)
        self.contrast_entry.grid(row=5, column=2, padx=2)
        self.contrast_entry.bind('<Return>', lambda e: self.update_live_color_preview())

        # Apply/Reset buttons for color changing (move to bottom)
        button_frame = ttk.Frame(change_color_frame)
        button_frame.pack(side="bottom", fill="x", pady=(8,0))
        self.apply_color_change_button = ttk.Button(button_frame, text="Apply", command=self.apply_color_replacement)
        self.apply_color_change_button.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.reset_color_preview_button = ttk.Button(button_frame, text="Reset", command=self.reset_color_preview)
        self.reset_color_preview_button.pack(side="left", fill="x")
        # Checkbox: Apply to current frame only
        self.apply_to_current_frame_var = tk.BooleanVar(value=False)
        self.apply_to_current_frame_checkbox = ttk.Checkbutton(
            button_frame,
            text="Apply to current frame only",
            variable=self.apply_to_current_frame_var
        )
        self.apply_to_current_frame_checkbox.pack(side="left", padx=(12, 0))

        # Undo/Redo buttons (bottom right of change color group)
        color_undo_redo_frame = ttk.Frame(change_color_frame) # Renamed to avoid clash
        color_undo_redo_frame.pack(side="bottom", anchor="e", padx=8, pady=(2, 8))
        self.undo_color_button = ttk.Button(color_undo_redo_frame, text="Undo", command=self.undo_color_apply)
        self.undo_color_button.pack(side="left", padx=(0, 6))
        self.redo_color_button = ttk.Button(color_undo_redo_frame, text="Redo", command=self.redo_color_apply)
        self.redo_color_button.pack(side="left")


        # --- Outlining Group ---
        outlining_frame = ttk.LabelFrame(right_panel, text="Outlining")
        outlining_frame.grid(row=5, column=0, sticky="ew", pady=(5, 0))
        self.outline_collapsed = tk.BooleanVar(value=False)

        # Outlining helpers (must be defined before use in UI callbacks)
        self.set_outlining_controls_state = lambda enabled: outlining.set_outlining_controls_state(self, enabled)
        self.on_outline_enable_toggle = lambda: outlining.on_outline_enable_toggle(self)
        self.on_outline_gradient_toggle = lambda: outlining.on_outline_gradient_toggle(self)
        self.pick_outline_color = lambda which: outlining.pick_outline_color(self, which)
        self.update_outline_color_canvas = lambda which: outlining.update_outline_color_canvas(self, which)
        self.apply_outlining = lambda: self._apply_outlining_with_undo()

        def toggle_outline():
            if self.outline_collapsed.get():
                outline_content_frame.pack(fill="x", expand=True)
            else:
                outline_content_frame.pack_forget()
            self.outline_collapsed.set(not self.outline_collapsed.get())
        outline_header = ttk.Label(outlining_frame, text="Outlining", style="CollapsibleHeader.TLabel")
        outline_header.bind("<Button-1>", lambda e: toggle_outline())
        outline_header.pack(fill="x", padx=2, pady=2)
        outline_content_frame = ttk.Frame(outlining_frame)
        outline_content_frame.pack(fill="x", expand=True)

        # Enable outlining checkbox
        self.outline_enabled_var = tk.BooleanVar(value=False)
        self.outline_enable_cb = ttk.Checkbutton(outline_content_frame, text="Enable outlining", variable=self.outline_enabled_var, command=self.on_outline_enable_toggle)
        self.outline_enable_cb.pack(anchor="w", padx=10, pady=(5, 2))
        self.outline_enabled_var.trace_add('write', lambda *_: self.update_live_outline_preview())

        # Line color pickers
        color_row = ttk.Frame(outline_content_frame)
        color_row.pack(fill="x", padx=10, pady=(0, 2))
        ttk.Label(color_row, text="Line color:").pack(side="left")
        self.outline_color1_btn = ttk.Button(color_row, text="Pick", width=6, command=lambda: [self.pick_outline_color(1), self.update_live_outline_preview()])
        self.outline_color1_btn.pack(side="left", padx=(4, 8))
        self.outline_color1_canvas = tk.Canvas(color_row, width=20, height=20, bg="#000000", highlightthickness=1, relief='ridge')
        self.outline_color1_canvas.pack(side="left", padx=(0, 8))
        ttk.Label(color_row, text="Line color 2:").pack(side="left")
        self.outline_color2_btn = ttk.Button(color_row, text="Pick", width=6, command=lambda: [self.pick_outline_color(2), self.update_live_outline_preview()], state="disabled")
        self.outline_color2_btn.pack(side="left", padx=(4, 8))
        self.outline_color2_canvas = tk.Canvas(color_row, width=20, height=20, bg="#ffffff", highlightthickness=1, relief='ridge')
        self.outline_color2_canvas.pack(side="left")

        # Use gradient checkbox
        gradient_row = ttk.Frame(outline_content_frame)
        gradient_row.pack(fill="x", padx=10, pady=(0, 2))
        self.outline_use_gradient_var = tk.BooleanVar(value=False)
        self.outline_use_gradient_cb = ttk.Checkbutton(gradient_row, text="Use gradient", variable=self.outline_use_gradient_var, command=lambda: [self.on_outline_gradient_toggle(), self.update_live_outline_preview()])
        self.outline_use_gradient_cb.pack(anchor="w")

        # Direction radio buttons
        direction_row = ttk.Frame(outline_content_frame)
        direction_row.pack(fill="x", padx=10, pady=(0, 2))
        ttk.Label(direction_row, text="Direction:").pack(side="left")
        self.outline_direction_var = tk.StringVar(value="vertical")
        self.outline_direction_vertical_rb = ttk.Radiobutton(direction_row, text="Vertical", variable=self.outline_direction_var, value="vertical", command=self.update_live_outline_preview)
        self.outline_direction_vertical_rb.pack(side="left", padx=(4, 8))
        self.outline_direction_horizontal_rb = ttk.Radiobutton(direction_row, text="Horizontal", variable=self.outline_direction_var, value="horizontal", command=self.update_live_outline_preview)
        self.outline_direction_horizontal_rb.pack(side="left")

        # Amount slider
        amount_row = ttk.Frame(outline_content_frame)
        amount_row.pack(fill="x", padx=10, pady=(0, 2))
        ttk.Label(amount_row, text="Amount:").pack(side="left")
        self.outline_amount_var = tk.IntVar(value=100)
        self.outline_amount_slider = ttk.Scale(amount_row, from_=0, to=100, variable=self.outline_amount_var, orient=tk.HORIZONTAL, length=120, command=lambda e: self.update_live_outline_preview())
        self.outline_amount_slider.pack(side="left", padx=(4, 8), fill="x", expand=True)
        self.outline_amount_entry = ttk.Entry(amount_row, textvariable=self.outline_amount_var, width=5)
        self.outline_amount_entry.pack(side="left")
        self.outline_amount_var.trace_add('write', lambda *_: self.update_live_outline_preview())

        # Thickness number box and inside/outside radio
        thickness_row = ttk.Frame(outline_content_frame)
        thickness_row.pack(fill="x", padx=10, pady=(0, 2))
        ttk.Label(thickness_row, text="Thickness:").pack(side="left")
        self.outline_thickness_var = tk.IntVar(value=1)
        self.outline_thickness_entry = ttk.Entry(thickness_row, textvariable=self.outline_thickness_var, width=5)
        self.outline_thickness_entry.pack(side="left", padx=(4, 2))
        self.outline_thickness_var.trace_add('write', lambda *_: self.update_live_outline_preview())
        ttk.Label(thickness_row, text="px").pack(side="left")
        self.outline_side_var = tk.StringVar(value="outside")
        self.outline_side_outside_rb = ttk.Radiobutton(thickness_row, text="Outside", variable=self.outline_side_var, value="outside", command=self.update_live_outline_preview)
        self.outline_side_outside_rb.pack(side="left", padx=(8, 2))
        self.outline_side_inside_rb = ttk.Radiobutton(thickness_row, text="Inside", variable=self.outline_side_var, value="inside", command=self.update_live_outline_preview)
        self.outline_side_inside_rb.pack(side="left")

        # Apply outlining button with undo/redo (Layout adjusted)
        apply_outline_frame = ttk.Frame(outline_content_frame)
        apply_outline_frame.pack(pady=(6, 6), padx=10, fill="x")
        self.apply_outline_btn = ttk.Button(apply_outline_frame, text="Apply outlining", command=self.apply_outlining)
        self.apply_outline_btn.pack(side="left", fill="x", expand=True)

        # Undo/Redo buttons for outlining
        outline_undo_redo_frame = ttk.Frame(apply_outline_frame)
        outline_undo_redo_frame.pack(side="left", padx=(10, 0))
        self.undo_outline_button = ttk.Button(outline_undo_redo_frame, text="Undo", command=self.undo_outline_apply)
        self.undo_outline_button.pack(side="left", padx=(0, 5))
        self.redo_outline_button = ttk.Button(outline_undo_redo_frame, text="Redo", command=self.redo_outline_apply)
        self.redo_outline_button.pack(side="left")


        # Set initial outline colors
        self.outline_color1 = (0, 0, 0)
        self.outline_color2 = (255, 255, 255)
        self.update_outline_color_canvas(1)
        self.update_outline_color_canvas(2)
        self.set_outlining_controls_state(False)
        # Disable direction radios unless gradient is checked
        def update_direction_state(*_):
            state = "normal" if self.outline_use_gradient_var.get() else "disabled"
            self.outline_direction_vertical_rb.config(state=state)
            self.outline_direction_horizontal_rb.config(state=state)
        self.outline_use_gradient_var.trace_add('write', lambda *_: update_direction_state())
        update_direction_state()

        # (Outlining helpers already assigned above)

    def update_live_outline_preview(self, *_):
        """Live preview of outlining: applies outlining to preview frames if enabled, else restores original preview."""
        if not hasattr(self, '_original_preview_frames') or not self._original_preview_frames:
            return

        # Store current previewer background state to restore later
        original_preview_bg_image = self.preview_viewer.bg_image
        original_preview_transparency_color = self.preview_viewer.transparency_color

        if not self.outline_enabled_var.get():
            # Outlining not enabled: show original frames and restore previous preview settings
            self.preview_viewer.load_frames([frame.copy() for frame in self._original_preview_frames])
            self.preview_viewer.bg_image = original_preview_bg_image
            self.preview_viewer.transparency_color = original_preview_transparency_color
            self.preview_viewer.update_frame_display()
            return

        # Outlining enabled: apply outlining to preview frames (non-destructive)
        import outlining
        color1 = self.outline_color1
        use_gradient = self.outline_use_gradient_var.get()
        color2 = self.outline_color2 if use_gradient else self.outline_color1
        direction = self.outline_direction_var.get()
        try:
            amount = int(self.outline_amount_var.get())
        except Exception:
            amount = 100
        try:
            thickness = int(self.outline_thickness_var.get())
        except Exception:
            thickness = 1
        side = self.outline_side_var.get() if hasattr(self, 'outline_side_var') else 'outside'
        transparency_color_app_wide = getattr(self, 'transparency_color', None) # This is the app-wide transparency color

        if transparency_color_app_wide is None:
            # Can't preview outlining without a transparency color to define the sprite boundary
            self.preview_viewer.load_frames([frame.copy() for frame in self._original_preview_frames])
            self.preview_viewer.bg_image = original_preview_bg_image
            self.preview_viewer.transparency_color = original_preview_transparency_color
            self.preview_viewer.update_frame_display()
            messagebox.showwarning("Outlining Preview Issue", "Please set a transparency color first to define the sprite boundary for outlining.")
            return

        # IMPORTANT: If outline color matches transparency color, it will be invisible regardless of background fill.
        if tuple(color1) == tuple(transparency_color_app_wide) or (use_gradient and tuple(color2) == tuple(transparency_color_app_wide)):
            self.preview_viewer.load_frames([frame.copy() for frame in self._original_preview_frames])
            self.preview_viewer.bg_image = original_preview_bg_image
            self.preview_viewer.transparency_color = original_preview_transparency_color
            self.preview_viewer.update_frame_display()
            messagebox.showwarning("Outlining Preview Issue", "Outline color must not match the transparency color for preview visibility.")
            return

        # Temporarily override previewer background settings for outline preview
        # This will ensure the outline is visible against a clear background.
        if not original_preview_bg_image:
            # Create a simple checkerboard pattern for preview background
            checker_size = 16 # size of one square
            # Get actual size from the first frame or default
            w, h = self._original_preview_frames[0].size if self._original_preview_frames else (64, 64) # Use a reasonable default
            checker_img = Image.new('RGB', (w, h), (180, 180, 180)) # Light gray default
            pixels = checker_img.load()
            for y in range(h):
                for x in range(w):
                    if (x // checker_size + y // checker_size) % 2 == 0:
                        pixels[x, y] = (160, 160, 160) # Slightly darker gray
            self.preview_viewer.bg_image = checker_img.convert('RGBA') # Set checkerboard as temp background
        else:
            # If a user's background is already set, use it. But ensure it's RGBA
            self.preview_viewer.bg_image = original_preview_bg_image.convert('RGBA') 

        # IMPORTANT: Set FrameViewer's transparency_color to None for outlining preview.
        # This ensures the viewer composites the image with its (temp) background,
        # instead of filling transparent areas with the sprite's original transparency color.
        self.preview_viewer.transparency_color = None 

        new_frames = []
        for frame in self._original_preview_frames:
            # Step 1: Make original transparency color transparent (alpha 0)
            frame_for_outline = outlining.apply_transparency_color(frame, transparency_color_app_wide)
            
            # Step 2: Pad the image with a transparent border
            padded = outlining.pad_image_with_transparent_border(frame_for_outline, border=2)
            
            # Step 3: Apply outlining. This will draw the outline and should keep the rest transparent.
            outlined = outlining.outline_image(
                padded,
                color1,
                color2,
                use_gradient,
                direction,
                amount,
                thickness,
                side,
                transparency_color=transparency_color_app_wide # This transparency_color is for debugging/mask creation within outline_image, not final output transparency
            )
            
            # Step 4: Crop back to original size (remove border)
            w, h = frame_for_outline.size
            outlined_cropped = outlined.crop((2, 2, 2 + w, 2 + h)) # This should be RGBA
            new_frames.append(outlined_cropped)

        self.preview_viewer.load_frames(new_frames)
        # Restore frame index
        self.preview_viewer.current_frame_index = getattr(self.preview_viewer, 'current_frame_index', 0)
        self.preview_viewer.update_frame_display() # This will use the temporarily set bg_image.


    def _apply_outlining_with_undo(self):
        # Save current state for undo
        self._outline_undo_stack.append([frame.copy() for frame in self.preview_viewer.frames])
        self._outline_redo_stack.clear() # Clear redo stack on new action

        # Call the outlining logic which handles its own loading screen and preview updates
        import outlining
        outlining.apply_outlining(self) # This will load the new frames into preview_viewer
        # After outlining, preserve image paths
        if hasattr(self.preview_viewer, 'get_image_paths') and hasattr(self.preview_viewer, 'frames'):
            image_paths = self.preview_viewer.get_image_paths()
            self.preview_viewer.set_image_paths(image_paths)

        # The app.update_preview_with_bg() is called by outlining.apply_outlining's worker.on_done
        # So no need to call it here.

    def undo_outline_apply(self):
        if not self._outline_undo_stack:
            messagebox.showinfo("Undo Outlining", "Nothing to undo in outlining.")
            return
        
        # Save current state for redo
        self._outline_redo_stack.append([frame.copy() for frame in self.preview_viewer.frames])
        
        # Pop previous state from undo stack
        prev_frames = self._outline_undo_stack.pop()
        
        # Update both preview and originals, and force UI refresh
        self._original_preview_frames = [frame.copy() for frame in prev_frames]
        self.preview_viewer.load_frames([frame.copy() for frame in prev_frames])
        self.update_preview_with_bg()
        self.preview_viewer.update_frame_display()
        logging.info("Outlining action undone.")

    def redo_outline_apply(self):
        if not self._outline_redo_stack:
            messagebox.showinfo("Redo Outlining", "Nothing to redo in outlining.")
            return
        
        # Save current state for undo
        self._outline_undo_stack.append([frame.copy() for frame in self.preview_viewer.frames])
        
        # Pop next state from redo stack
        next_frames = self._outline_redo_stack.pop()
        
        # Load next frames into viewer
        self.preview_viewer.load_frames([frame.copy() for frame in next_frames])
        self._original_preview_frames = [frame.copy() for frame in next_frames] # Update originals
        self.update_preview_with_bg() # Force display update with correct BG settings
        logging.info("Outlining action redone.")


    def select_bg_image(self):
        """Open a file dialog to select a background image for the preview."""
        file_path = filedialog.askopenfilename(
            title="Select Background Image",
            filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.gif"), ("All Files", "*.*")]
        )
        if file_path:
            try:
                img = Image.open(file_path).convert("RGBA")
                self.bg_image = img
                self.bg_image_path = file_path
                self.update_preview_with_bg() # This will now draw it at original size
                self.save_config()  # Save config immediately when BG image changes
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load background image: {e}")
                self.bg_image = None
                self.bg_image_path = None

    def update_preview_with_bg(self, update_frames=True):
        """Set the preview background image for the preview_viewer and control transparency display.
        If update_frames is False, only update background and transparency, not the preview frames themselves."""
        cur_idx = self.preview_viewer.current_frame_index if hasattr(self.preview_viewer, 'current_frame_index') else 0
        cur_zoom = getattr(self.preview_viewer, 'zoom', 1.0)
        if not self.bg_image:
            self.preview_viewer.bg_image = None
        else:
            self.preview_viewer.bg_image = self.bg_image # Pass the actual PIL Image

        # Decide whether to show the transparency color or actual transparency
        # Only show transparency_color if it's set AND the "View Color" checkbox is ticked
        if self.view_transparency_color_var.get() and self.transparency_color is not None:
            self.preview_viewer.transparency_color = self.transparency_color # Show the color
        else:
            # Actively remove the transparency color from the preview (show true transparency)
            self.preview_viewer.transparency_color = None
            # If the preview frames have the transparency color filled in, convert it to alpha 0 for display
            if update_frames and hasattr(self, '_original_preview_frames') and self._original_preview_frames and self.transparency_color is not None:
                from outlining import apply_transparency_color
                frames = [apply_transparency_color(frame, self.transparency_color) for frame in self._original_preview_frames]
                self.preview_viewer.load_frames([frame.copy() for frame in frames])
        self.preview_viewer.current_frame_index = cur_idx
        self.preview_viewer.zoom = cur_zoom
        self.preview_viewer.update_frame_display()

    def refresh_preview(self):
        # Reload the current preview frame(s)
        if hasattr(self, 'preview_viewer') and self.preview_viewer.frames:
            # Re-trigger update_preview_with_bg to apply current settings
            self.update_preview_with_bg() 
            # ensure correct current frame is shown, but update_preview_with_bg already calls update_frame_display
            # so no extra action needed here unless specific frame index needs restoring.
            # current_frame_index should already be maintained by preview_viewer.
            logging.info("Preview refreshed manually.")

    def refresh_frame_viewer(self):
        # No-op: frame_viewer removed
        pass

    # (refresh_current_preview_frame removed to revert to before refresh button feature)
    def start_preview_color_pick(self):
        """Enable color picking mode for the preview area."""
        self.preview_color_picking = True
        self.preview_viewer.canvas.config(cursor="crosshair")
        self.preview_viewer.canvas.bind('<Button-1>', self.on_preview_canvas_click)
        self.pick_color_button.config(state="disabled")

    def stop_preview_color_pick(self):
        self.preview_color_picking = False
        self.picking_status_label.config(text="")
        self.preview_viewer.canvas.unbind('<Button-1>')
        self.pick_color_button.config(state="normal")

    def on_preview_canvas_click(self, event):
        if not getattr(self, 'preview_color_picking', False):
            return
        current_frame = self.preview_viewer.get_current_frame()
        if not current_frame:
            return
        img_x, img_y, is_valid = self.preview_viewer.get_click_image_coordinates(event.x, event.y)
        if not is_valid:
            return
        rgb_frame = current_frame.convert('RGB')
        color = rgb_frame.getpixel((img_x, img_y))
        self.picked_color = color
        hex_color = '#{:02x}{:02x}{:02x}'.format(*color)
        self.picked_color_canvas.config(bg=hex_color)
        self.stop_preview_color_pick()

    # Removed choose_replace_color, not needed with new sliders

    def apply_color_replacement(self):
        """Apply color replacement/adjustment to frames, always using original frames as base (no double-apply)."""
        import threading
        if not self.picked_color:
            messagebox.showwarning("Warning", "Please pick a color.")
            return
        input_tolerance = self.input_tolerance_var.get()
        hue_shift = self.hue_var.get()
        sat_shift = self.sat_var.get()
        bri_shift = self.bri_var.get()
        sharpness = self.sharpness_var.get() if hasattr(self, 'sharpness_var') else 1.0
        contrast = self.contrast_var.get() if hasattr(self, 'contrast_var') else 0.0
        # Always use _original_preview_frames as base to avoid double-application
        if not hasattr(self, '_original_preview_frames') or not self._original_preview_frames:
            base_frames = [frame.copy() for frame in self.preview_viewer.frames]
        else:
            base_frames = [frame.copy() for frame in self._original_preview_frames]

        # Save undo state before applying
        self._color_edit_undo_stack.append([frame.copy() for frame in self.preview_viewer.frames])
        self._color_edit_redo_stack.clear()

        apply_current_only = self.apply_to_current_frame_var.get() if hasattr(self, 'apply_to_current_frame_var') else False
        cur_idx = self.preview_viewer.current_frame_index if hasattr(self.preview_viewer, 'current_frame_index') else 0
        if apply_current_only:
            if not (0 <= cur_idx < len(base_frames)):
                messagebox.showerror("Error", "No valid current frame selected.")
                return
            from outlining import apply_transparency_color
            transparency_color_palette = getattr(self.palette_handler, 'transparency_color', None)
            new_frames = [frame.copy() for frame in base_frames]
            new_img = self.palette_handler.adjust_hsv_in_image(
                base_frames[cur_idx], self.picked_color, input_tolerance, hue_shift, sat_shift, bri_shift, sharpness, contrast
            )
            if transparency_color_palette is not None:
                new_img = apply_transparency_color(new_img, transparency_color_palette)
            new_frames[cur_idx] = new_img
            self.preview_viewer.load_frames(new_frames)
            self._original_preview_frames = [frame.copy() for frame in new_frames]
            # Restore frame index
            self.preview_viewer.current_frame_index = cur_idx
            self.preview_viewer.update_frame_display()
            # Reset sliders after apply
            self.input_tolerance_var.set(30)
            self.hue_var.set(0.0)
            self.sat_var.set(0.0)
            self.bri_var.set(0.0)
            self.sharpness_var.set(1.0)
            self.contrast_var.set(0.0)
            messagebox.showinfo("Done", "Color adjustment applied to current frame only.")
            return

        self._cancel_apply = False
        loading_win = tk.Toplevel(self.root)
        loading_win.title("Applying Color Change")
        loading_win.geometry("320x100")
        loading_win.transient(self.root)
        loading_win.grab_set()
        tk.Label(loading_win, text="Applying color change to all frames...", font=("Segoe UI", 11)).pack(pady=10)
        progress_var = tk.StringVar(value="0 / {}".format(len(base_frames)))
        progress_label = tk.Label(loading_win, textvariable=progress_var)
        progress_label.pack()
        def on_cancel():
            self._cancel_apply = True
        cancel_btn = ttk.Button(loading_win, text="Cancel", command=on_cancel)
        cancel_btn.pack(pady=5)

        def worker():
            from outlining import apply_transparency_color
            new_frames = []
            total = len(base_frames)
            transparency_color_palette = getattr(self.palette_handler, 'transparency_color', None)
            for i, frame in enumerate(base_frames):
                if self._cancel_apply:
                    break
                new_img = self.palette_handler.adjust_hsv_in_image(
                    frame, self.picked_color, input_tolerance, hue_shift, sat_shift, bri_shift, sharpness, contrast
                )
                if transparency_color_palette is not None:
                    new_img = apply_transparency_color(new_img, transparency_color_palette)
                new_frames.append(new_img)
                progress_var.set(f"{i+1} / {total}")
            def on_done():
                loading_win.grab_release()
                loading_win.destroy()
                if self._cancel_apply:
                    messagebox.showinfo("Cancelled", "Color adjustment cancelled.")
                    return
                image_paths = self.preview_viewer.get_image_paths() if hasattr(self.preview_viewer, 'get_image_paths') else [None] * len(new_frames)
                self.preview_viewer.load_frames(new_frames)
                self.preview_viewer.set_image_paths(image_paths)
                self._original_preview_frames = [frame.copy() for frame in new_frames]
                # Restore frame index
                self.preview_viewer.current_frame_index = cur_idx if 0 <= cur_idx < len(new_frames) else 0
                self.preview_viewer.update_frame_display()
                # Reset sliders after apply
                self.input_tolerance_var.set(30)
                self.hue_var.set(0.0)
                self.sat_var.set(0.0)
                self.bri_var.set(0.0)
                self.sharpness_var.set(1.0)
                self.contrast_var.set(0.0)
                messagebox.showinfo("Done", "Color adjustment applied to all frames.")
            self.root.after(0, on_done)

        threading.Thread(target=worker, daemon=True).start()
    def undo_color_apply(self):
        if not self._color_edit_undo_stack:
            messagebox.showinfo("Undo", "Nothing to undo.")
            return
        # Save current state for redo
        self._color_edit_redo_stack.append([frame.copy() for frame in self.preview_viewer.frames])
        prev_frames = self._color_edit_undo_stack.pop()
        self.preview_viewer.load_frames([frame.copy() for frame in prev_frames])
        self._original_preview_frames = [frame.copy() for frame in prev_frames]
        # Restore frame index if possible
        if hasattr(self.preview_viewer, 'current_frame_index') and self.preview_viewer.current_frame_index < len(prev_frames):
            self.preview_viewer.update_frame_display()

    def redo_color_apply(self):
        if not self._color_edit_redo_stack:
            messagebox.showinfo("Redo", "Nothing to redo.")
            return
        # Save current state for undo
        self._color_edit_undo_stack.append([frame.copy() for frame in self.preview_viewer.frames])
        next_frames = self._color_edit_redo_stack.pop()
        self.preview_viewer.load_frames([frame.copy() for frame in next_frames])
        self._original_preview_frames = [frame.copy() for frame in next_frames]
        # Restore frame index if possible
        if hasattr(self.preview_viewer, 'current_frame_index') and self.preview_viewer.current_frame_index < len(next_frames):
            self.preview_viewer.update_frame_display()


    def update_live_color_preview(self, *_):
        if not self.picked_color or not self.preview_viewer.frames:
            return
        input_tolerance = self.input_tolerance_var.get()
        hue_shift = self.hue_var.get()
        sat_shift = self.sat_var.get()
        bri_shift = self.bri_var.get()
        sharpness = self.sharpness_var.get() if hasattr(self, 'sharpness_var') else 1.0
        contrast = self.contrast_var.get() if hasattr(self, 'contrast_var') else 0.0
        # Use original frames for preview, if available
        if not hasattr(self, '_original_preview_frames'):
            self._original_preview_frames = [frame.copy() for frame in self.preview_viewer.frames]
        cur_idx = self.preview_viewer.current_frame_index if hasattr(self.preview_viewer, 'current_frame_index') else 0
        cur_zoom = getattr(self.preview_viewer, 'zoom', 1.0)
        # Copy all frames, but only modify the current one for live preview
        new_frames = [frame.copy() for frame in self._original_preview_frames]
        if 0 <= cur_idx < len(new_frames):
            new_img = self.palette_handler.adjust_hsv_in_image(
                self._original_preview_frames[cur_idx],
                self.picked_color, input_tolerance, hue_shift, sat_shift, bri_shift, sharpness, contrast
            )
            # Apply transparency color to preview
            from outlining import apply_transparency_color
            transparency_color_palette = getattr(self.palette_handler, 'transparency_color', None)
            if transparency_color_palette is not None:
                new_img = apply_transparency_color(new_img, transparency_color_palette)
            new_frames[cur_idx] = new_img
        self.preview_viewer.load_frames(new_frames)
        # Restore frame index and zoom
        self.preview_viewer.current_frame_index = cur_idx
        self.preview_viewer.zoom = cur_zoom
        # Always update background and transparency, but do not reload frames in update_preview_with_bg
        self.update_preview_with_bg(update_frames=False)

    def reset_color_preview(self):
        # Reset all sliders/entries to their default values
        self.input_tolerance_var.set(30)
        self.hue_var.set(0.0)
        self.sat_var.set(0.0)
        self.bri_var.set(0.0)
        self.sharpness_var.set(1.0)
        self.contrast_var.set(0.0)
        # Only reset the color preview: restore preview to the original preview frames
        if hasattr(self, '_original_preview_frames'):
            self.preview_viewer.load_frames([frame.copy() for frame in self._original_preview_frames])

    def load_file_dialog(self):
        """Open dialog to select image file(s) and load them into the preview viewer only, preserving original filenames."""
        try:
            file_paths = filedialog.askopenfilenames(
                title="Select Image File(s)",
                filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.gif"), ("All Files", "*.*")]
            )
            if file_paths:
                all_frames = []
                all_paths = []
                for file_path in file_paths:
                    frames = self.load_file(file_path)
                    if frames:
                        all_frames.extend(frames)
                        ext = os.path.splitext(file_path)[1].lower()
                        if ext == '.gif':
                            try:
                                with Image.open(file_path) as img:
                                    n = img.n_frames
                                    # Use the original filename for each frame, but append frame index for internal tracking
                                    for i in range(n):
                                        base, ext = os.path.splitext(file_path)
                                        # Store as (original_path, frame_index) tuple for GIFs
                                        all_paths.append((file_path, i))
                            except Exception:
                                n = len(frames)
                                for i in range(n):
                                    all_paths.append((file_path, i))
                        else:
                            all_paths.append(file_path)
                if all_frames:
                    self.preview_viewer.load_frames([frame.copy() for frame in all_frames])
                    self.preview_viewer.set_image_paths(list(all_paths))
                    self._original_preview_frames = [frame.copy() for frame in all_frames]
                    self._original_filenames = list(all_paths)  # Save for later use in saving

                    # Clear all undo/redo histories when new files are loaded
                    self._color_edit_undo_stack.clear()
                    self._color_edit_redo_stack.clear()
                    self._scale_undo_stack.clear()
                    self._scale_redo_stack.clear()
                    self._outline_undo_stack.clear()
                    self._outline_redo_stack.clear()

                    self.preview_refresh_btn.invoke()  # Simulate refresh button press
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
        """Reapply current palette to all loaded images in the preview viewer."""
        try:
            if hasattr(self.preview_viewer, 'frames') and self.preview_viewer.frames:
                new_frames = []
                for frame in self.preview_viewer.frames:
                    new_frames.append(self.palette_handler.apply_palette_to_image(frame))
                image_paths = self.preview_viewer.get_image_paths() if hasattr(self.preview_viewer, 'get_image_paths') else [None] * len(new_frames)
                self.preview_viewer.load_frames(new_frames)
                self.preview_viewer.set_image_paths(image_paths)
                self._original_preview_frames = [frame.copy() for frame in new_frames]
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
        # No-op: frame_viewer removed
        pass

    def save_config(self):
        try:
            config = {}
            if hasattr(self.preview_viewer, 'get_image_paths'):
                config["images"] = self.preview_viewer.get_image_paths()
            if getattr(self, 'bg_image_path', None):
                config["bg_image_path"] = self.bg_image_path
            with open("config.json", "w") as f:
                json.dump(config, f, indent=4)
            logging.info(f"Config saved. Images: {len(config.get('images', []))} BG image: {config.get('bg_image_path')}")
        except Exception as e:
            logging.error(f"Error saving config: {e}", exc_info=True)

    def load_config(self):
        try:
            logging.info(f"Loading config from config.json")
            if os.path.exists("config.json"):
                with open("config.json", "r") as f:
                    config_data = json.load(f)
                if isinstance(config_data, dict) and isinstance(config_data.get("images"), list):
                    # Restore background image if path is present and valid
                    bg_path = config_data.get("bg_image_path")
                    if bg_path and os.path.exists(bg_path):
                        try:
                            img = Image.open(bg_path).convert("RGBA")
                            self.bg_image = img
                            self.bg_image_path = bg_path
                            self.update_preview_with_bg()
                            logging.info(f"Restored background image from config: {bg_path}")
                        except Exception as e:
                            self.bg_image = None
                            self.bg_image_path = None
                            logging.error(f"Failed to load background image from config: {e}")
                    else:
                        self.bg_image = None
                        self.bg_image_path = None
                    return config_data
            # If no config or missing images, clear bg image
            self.bg_image = None
            self.bg_image_path = None
            return {}
        except json.JSONDecodeError as jde:
            logging.error(f"Error decoding config 'config.json': {jde}")
            self.bg_image = None
            self.bg_image_path = None
            return {}
        except Exception as e:
            logging.error(f"Error loading config: {e}", exc_info=True)
            self.bg_image = None
            self.bg_image_path = None
            return {}

    def on_closing(self):
        logging.info("WM_DELETE_WINDOW event.")
        self.save_config()
        self.root.destroy()

    def remove_palette(self):
        """Remove current palette and revert to original colors."""
        self.palette_handler.clear_palette()
        if hasattr(self, '_original_preview_frames'):
            self.preview_viewer.load_frames([frame.copy() for frame in self._original_preview_frames])
        logging.info("Palette removed")

    def start_color_picking_mode(self):
        """Enter color picking mode for transparency color (on preview)."""
        self.color_picking_mode = True
        self.picking_status_label.config(text="Click on a pixel to set transparency color")
        self.preview_viewer.canvas.bind('<Button-1>', self.on_canvas_click)
        self.transparency_button.config(state="disabled")
        self.preview_viewer.canvas.config(cursor="crosshair")

    def stop_color_picking_mode(self):
        """Exit color picking mode."""
        self.color_picking_mode = False
        self.picking_status_label.config(text="")
        self.preview_viewer.canvas.unbind('<Button-1>')
        self.transparency_button.config(state="normal")
        self.preview_viewer.canvas.config(cursor="")

    def on_canvas_click(self, event):
        """Handle canvas click for color picking (on preview)."""
        if not self.color_picking_mode:
            return
        current_frame = self.preview_viewer.get_current_frame()
        if not current_frame:
            return
        img_x, img_y, is_valid = self.preview_viewer.get_click_image_coordinates(event.x, event.y)
        if not is_valid:
            return
        rgb_frame = current_frame.convert('RGB')
        color = rgb_frame.getpixel((img_x, img_y))
        print(f"Picked color RGB{color} at position ({img_x}, {img_y})")
        hex_color = '#{:02x}{:02x}{:02x}'.format(*color)
        self.color_indicator.config(bg=hex_color)
        self.palette_handler.set_transparency_color(color)
        self.transparency_color = color  # Store the picked transparency color
        print(f"Set transparency color to {hex_color}")
        # Notify outlining logic of transparency color change
        if hasattr(outlining, 'on_transparency_color_changed'):
            outlining.on_transparency_color_changed(self)
        # Immediately set "View Color" to False and update preview to show transparency
        self.view_transparency_color_var.set(False) # Turn off "View Color" by default after picking
        # Always reload preview from originals to reflect new transparency color, and restore frame index
        if hasattr(self, '_original_preview_frames'):
            cur_idx = self.preview_viewer.current_frame_index if hasattr(self.preview_viewer, 'current_frame_index') else 0
            self.preview_viewer.load_frames([frame.copy() for frame in self._original_preview_frames])
            if 0 <= cur_idx < len(self._original_preview_frames):
                self.preview_viewer.current_frame_index = cur_idx
        self.update_preview_with_bg() # This will now display transparency by default
        self.stop_color_picking_mode()

    def update_frame_viewer(self):
        # No-op: frame_viewer removed
        pass

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
        """Save the scaled image to a file, always restoring the original filename for each frame."""
        try:
            if not self.preview_viewer.frames:
                messagebox.showwarning("Warning", "No scaled image to save!")
                return

            save_folder = getattr(self, 'save_folder', None)
            if not save_folder or not isinstance(save_folder, str) or not os.path.isdir(save_folder):
                messagebox.showwarning("Pick a folder", "Please pick a folder to save images first.")
                return

            # Use the original filenames as loaded (from self._original_filenames if available)
            original_paths = []
            if hasattr(self.preview_viewer, 'get_image_paths'):
                original_paths = self.preview_viewer.get_image_paths()
            # If all are None or empty, and we have _original_filenames, and frame count matches, use those
            if (
                (not original_paths or all(p is None for p in original_paths))
                and hasattr(self, '_original_filenames')
                and isinstance(self._original_filenames, (list, tuple))
                and len(getattr(self, '_original_filenames', [])) == len(self.preview_viewer.frames)
            ):
                original_paths = list(self._original_filenames)
            elif not original_paths or len(original_paths) != len(self.preview_viewer.frames):
                logging.warning("No original filenames found for saving. Using generic names.")
                original_paths = [None] * len(self.preview_viewer.frames)


            transparency = getattr(self.palette_handler, 'transparency_color', None)
            put_back_transparency = self.put_back_transparency_var.get() if hasattr(self, 'put_back_transparency_var') else True

            # If all originals are GIF and multiple frames, save as animated GIF with original name
            all_gif = all(
                (isinstance(p, (str, tuple)) and (
                    (isinstance(p, str) and os.path.splitext(p)[1].lower() == '.gif') or
                    (isinstance(p, tuple) and os.path.splitext(p[0])[1].lower() == '.gif')
                )) for p in original_paths
            ) if original_paths else False
            if len(self.preview_viewer.frames) > 1 and all_gif:
                # Use the original name of the first frame
                first_path = original_paths[0]
                if isinstance(first_path, tuple):
                    orig_name, orig_ext = os.path.splitext(os.path.basename(first_path[0]))
                elif isinstance(first_path, str):
                    orig_name, orig_ext = os.path.splitext(os.path.basename(first_path))
                else:
                    orig_name, orig_ext = "output", ".gif"
                gif_path = os.path.join(save_folder, f"{orig_name}{orig_ext}")
                frames_to_save = []
                for frame in self.preview_viewer.frames:
                    frame_to_save = frame
                    if transparency and put_back_transparency:
                        frame_to_save = self._apply_transparency_to_frame(frame, transparency)
                    frames_to_save.append(frame_to_save)
                # Find transparency index for GIF (if possible)
                transparency_index = None
                if transparency and put_back_transparency:
                    # Attempt to convert to P mode and find transparency index
                    try:
                        # Convert to P mode to find the index of the transparency color in the palette
                        # This conversion will quantize to a new palette, but we need the original transparency color's index.
                        # It's better to ensure the transparency color exists in the palette or force it.
                        # For simplicity and given the context, we'll try to use a common approach:
                        # Convert to P mode with a limited palette, then check if transparency color is in the new palette.
                        # A more robust solution might involve adding the transparency color to the palette explicitly
                        # before conversion if it's not present, or using a known-transparent color for the palette.
                        # For now, let's just attempt to find it if it exists.
                        pal_frame = frames_to_save[0].convert('P', palette=Image.ADAPTIVE, colors=256) # Max GIF colors
                        palette_data = pal_frame.getpalette()
                        # Convert the palette data (R,G,B,R,G,B...) to a list of (R,G,B) tuples
                        current_palette_colors = [(palette_data[i], palette_data[i+1], palette_data[i+2]) for i in range(0, len(palette_data), 3)]
                        
                        try:
                            # Try to find the index of the transparency color in the current frame's palette
                            # This will only work if the quantization process included the transparency color
                            transparency_index = current_palette_colors.index(transparency)
                        except ValueError:
                            # If not found, it means the transparency color wasn't chosen by the palette.
                            # In this case, either warn or let GIF handle it with default behavior (no explicit transparency index)
                            logging.warning(f"Transparency color {transparency} not found in quantized GIF palette. GIF transparency might not be exact.")
                            transparency_index = None # Fallback to no explicit transparency index
                            
                    except Exception as e:
                        logging.error(f"Error determining GIF transparency index: {e}")
                        transparency_index = None
                
                save_kwargs = dict(
                    save_all=True,
                    append_images=frames_to_save[1:],
                    optimize=False,
                    duration=100,  # 100ms per frame
                    loop=0
                )
                if transparency_index is not None:
                    save_kwargs['transparency'] = transparency_index
                
                # If frames_to_save[0] is not already 'P' mode, convert it to handle palette for GIF
                if frames_to_save[0].mode != 'P':
                    frames_to_save[0] = frames_to_save[0].quantize(colors=256, method=Image.WEB) # or Image.ADAPTIVE
                
                frames_to_save[0].save(
                    gif_path,
                    **save_kwargs
                )
                messagebox.showinfo("Success", f"Animated GIF saved as {gif_path}")
                logging.info(f"Animated GIF saved to: {gif_path}")
                return

            # Otherwise, save each frame as a separate file with original filename and extension (no _scaled, no renaming)
            for i, frame in enumerate(self.preview_viewer.frames):
                use_original = i < len(original_paths) and original_paths[i] is not None
                if use_original:
                    orig_path = original_paths[i]
                    if isinstance(orig_path, tuple):
                        # For GIFs, orig_path is (filepath, frame_index)
                        orig_name, orig_ext = os.path.splitext(os.path.basename(orig_path[0]))
                        frame_path = os.path.join(save_folder, f"{orig_name}_frame{orig_path[1]+1}{orig_ext}")
                    else:
                        orig_name, orig_ext = os.path.splitext(os.path.basename(orig_path))
                        frame_path = os.path.join(save_folder, f"{orig_name}{orig_ext}")
                else:
                    frame_path = os.path.join(save_folder, f"frame_{i+1}.png")
                frame_to_save = frame
                if transparency:
                    if put_back_transparency:
                        frame_to_save = self._apply_transparency_to_frame(frame, transparency)
                    else:
                        # Fill transparent pixels with the transparency color
                        frame_to_save = self._fill_transparency_with_color(frame, transparency)
                frame_to_save.save(frame_path)
            messagebox.showinfo("Success", f"All {len(self.preview_viewer.frames)} frames saved to {save_folder}!")
            logging.info(f"Scaled image(s) saved to: {save_folder}")
        except Exception as e:
            logging.error(f"Error saving scaled image: {e}")
            messagebox.showerror("Error", f"Failed to save image: {e}")

    def _apply_transparency_to_frame(self, frame, transparency_color):
        # Returns a copy of frame with the given RGB color set to transparent (for GIF/PNG)
        img = frame.convert('RGBA')
        datas = img.getdata()
        newData = []
        for item in datas:
            if item[:3] == transparency_color:
                newData.append((255, 255, 255, 0))
            else:
                newData.append(item)
        img.putdata(newData)
        return img

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
                    image_paths = self.preview_viewer.get_image_paths() if hasattr(self.preview_viewer, 'get_image_paths') else [None] * len(new_frames)
                    self.preview_viewer.load_frames(new_frames)
                    self.preview_viewer.set_image_paths(image_paths)
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
                image_paths = self.preview_viewer.get_image_paths() if hasattr(self.preview_viewer, 'get_image_paths') else [None] * len(new_frames)
                self.preview_viewer.load_frames(new_frames)
                self.preview_viewer.set_image_paths(image_paths)
            logging.info("Scaled palette removed")
        except Exception as e:
            logging.error(f"Error removing scaled palette: {e}")
            messagebox.showerror("Error", f"Failed to remove scaled palette: {e}")

    def apply_scale(self):
        """Apply the scaling to the current frames using available scaling method and selected scaling mode."""
        try:
            # Warn if a palette is loaded
            if self.palette_handler.palette_colors is not None:
                if not messagebox.askokcancel("Palette Warning", "A palette is loaded, if you continue it will apply the palette too"):
                    return
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

            if not self.preview_viewer.frames:
                messagebox.showwarning("Warning", "No frames loaded to scale.")
                return

            # Save current state for undo
            self._scale_undo_stack.append([frame.copy() for frame in self.preview_viewer.frames])
            self._scale_redo_stack.clear() # Clear redo stack on new action

            # --- Determine which frames to scale based on radio selection ---

            # Always use the currently edited frames (preview panel)
            current_frames_to_scale = [frame.copy() for frame in self.preview_viewer.frames]
            # Preserve image paths (if any) as they are associated with the "set of frames"
            image_paths = self.preview_viewer.get_image_paths()


            if not WAND_AVAILABLE:
                # Use PIL's scaling methods or custom
                filter_type = self.filter_var.get()
                filter_map = {
                    'point': Image.NEAREST,
                    'bicubic-sharper': Image.BICUBIC, # PIL's BICUBIC is quite good, sharpening can be applied afterwards
                    'lanczos': Image.LANCZOS,
                }
                scaled_frames = []
                if filter_type == 'bicubic-sharper':
                    # Bicubic with sharpening for shrinking
                    for frame in current_frames_to_scale:
                        new_size = (int(frame.width * scale_factor), int(frame.height * scale_factor))
                        scaled = frame.resize(new_size, Image.BICUBIC)
                        from PIL import ImageFilter
                        scaled = scaled.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3))
                        scaled_frames.append(scaled)
                elif filter_type == 'realesrgan':
                    messagebox.showerror("Not Implemented", "Real-ESRGAN is not implemented in this build.")
                    # Revert undo state if a non-implemented feature is chosen
                    if self._scale_undo_stack: # Only pop if it was pushed
                        self._scale_undo_stack.pop() 
                    return
                else:
                    pil_filter = filter_map.get(filter_type, Image.LANCZOS)
                    for frame in current_frames_to_scale:
                        new_size = (int(frame.width * scale_factor), int(frame.height * scale_factor))
                        scaled_frame = frame.resize(new_size, pil_filter)
                        scaled_frames.append(scaled_frame)
                self.preview_viewer.load_frames(scaled_frames)
                # If frame count matches, preserve mapping; else, fallback to None
                if len(scaled_frames) == len(image_paths):
                    self.preview_viewer.set_image_paths(image_paths)
                else:
                    logging.warning("Frame count changed after scaling; not all original filenames can be preserved.")
                    self.preview_viewer.set_image_paths([None] * len(scaled_frames))
                # Update _original_preview_frames to the newly scaled frames
                self._original_preview_frames = [frame.copy() for frame in scaled_frames]
                self.preview_refresh_btn.invoke()  # Simulate refresh button press
                logging.info(f"Applied PIL scaling ({filter_type}): {scale_percent}%")
                return

            # Scale frames using ImageMagick
            scaled_frames = []
            for frame in current_frames_to_scale:
                img_byte_arr = BytesIO()
                if frame.mode != 'RGBA':
                    frame = frame.convert('RGBA')
                frame.save(img_byte_arr, format='PNG')
                img_byte_arr = img_byte_arr.getvalue()
                with WandImage(blob=img_byte_arr) as wand_img:
                    new_width = int(wand_img.width * scale_factor)
                    new_height = int(wand_img.height * scale_factor)
                    transparency_color_palette = self.palette_handler.transparency_color # Use palette handler's color
                    if transparency_color_palette:
                        r, g, b = transparency_color_palette
                        color_str = f'rgb({r},{g},{b})'
                        wand_img.transparent_color(color_str, alpha=0, fuzz=0)
                    filter_type = self.filter_var.get()
                    if filter_type == 'magic-kernel':
                        try:
                            print("\nAttempting MagicKernelSharp2021 scaling...")
                            wand_img.artifacts['filter:filter'] = 'MagicKernelSharp2021'
                            wand_img.artifacts['filter:support'] = '1.0'
                            wand_img.artifacts['filter:window'] = 'Box'
                            wand_img.artifacts['filter:lobes'] = '2'
                            wand_img.artifacts['filter:blur'] = '0.8'
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
                        wand_img.resize(new_width, new_height, filter='point')
                    else:
                        wand_img.resize(new_width, new_height, filter='lanczos', blur=0.9)
                    img_buffer = BytesIO(wand_img.make_blob('png'))
                    scaled_frame = Image.open(img_buffer).convert('RGBA')
                    pixels = scaled_frame.load()
                    for y in range(scaled_frame.height):
                        for x in range(scaled_frame.width):
                            r, g, b, a = pixels[x, y]
                            if transparency_color_palette: # Use palette handler's color
                                if a < 128 or (r, g, b) == transparency_color_palette:
                                    pixels[x, y] = transparency_color_palette + (255,)
                                else:
                                    pixels[x, y] = (r, g, b, 255)
                            else:
                                if a >= 128:
                                    pixels[x, y] = (r, g, b, 255)
                                else:
                                    pixels[x, y] = (0, 0, 0, 0)
                    scaled_frames.append(scaled_frame.copy())
            self.preview_viewer.load_frames(scaled_frames)
            if len(scaled_frames) == len(image_paths):
                self.preview_viewer.set_image_paths(image_paths)
            else:
                logging.warning("Frame count changed after scaling; not all original filenames can be preserved.")
                self.preview_viewer.set_image_paths([None] * len(scaled_frames))
            # Update _original_preview_frames to the newly scaled frames
            self._original_preview_frames = [frame.copy() for frame in scaled_frames]
            self.preview_refresh_btn.invoke()  # Simulate refresh button press
            if self.scaled_palette_handler.palette_colors is not None:
                new_frames = []
                for frame in scaled_frames:
                    new_frames.append(self.scaled_palette_handler.apply_palette_to_image(frame))
                self.preview_viewer.load_frames(new_frames)
                if len(new_frames) == len(image_paths):
                    self.preview_viewer.set_image_paths(image_paths)
                else:
                    logging.warning("Frame count changed after palette application; not all original filenames can be preserved.")
                    self.preview_viewer.set_image_paths([None] * len(new_frames))
                # Also update _original_preview_frames to the palette-applied frames
                self._original_preview_frames = [frame.copy() for frame in new_frames]
            logging.info(f"Applied {filter_type} scaling: {scale_percent}%")
        except Exception as e:
            logging.error(f"Error applying scale: {e}")
            messagebox.showerror("Error", f"Failed to apply scaling: {str(e)}")
            # If an error occurs, revert the undo stack to prevent saving a broken state
            if self._scale_undo_stack:
                self._scale_undo_stack.pop()

    def undo_scale_apply(self):
        if not self._scale_undo_stack:
            messagebox.showinfo("Undo Scale", "Nothing to undo in scaling.")
            return
        # Save current state for redo
        self._scale_redo_stack.append([frame.copy() for frame in self.preview_viewer.frames])
        # Pop previous state from undo stack
        prev_frames = self._scale_undo_stack.pop()
        # Restore frame index
        cur_idx = self.preview_viewer.current_frame_index if hasattr(self.preview_viewer, 'current_frame_index') else 0
        self.preview_viewer.load_frames([frame.copy() for frame in prev_frames])
        self._original_preview_frames = [frame.copy() for frame in prev_frames]
        # Restore frame index if possible
        if 0 <= cur_idx < len(prev_frames):
            self.preview_viewer.current_frame_index = cur_idx
        self.update_preview_with_bg()
        self.preview_viewer.update_frame_display()
        logging.info("Scaling action undone.")

    def redo_scale_apply(self):
        if not self._scale_redo_stack:
            messagebox.showinfo("Redo Scale", "Nothing to redo in scaling.")
            return
        # Save current state for undo
        self._scale_undo_stack.append([frame.copy() for frame in self.preview_viewer.frames])
        # Pop next state from redo stack
        next_frames = self._scale_redo_stack.pop()
        # Restore frame index
        cur_idx = self.preview_viewer.current_frame_index if hasattr(self.preview_viewer, 'current_frame_index') else 0
        self.preview_viewer.load_frames([frame.copy() for frame in next_frames])
        self._original_preview_frames = [frame.copy() for frame in next_frames]
        if 0 <= cur_idx < len(next_frames):
            self.preview_viewer.current_frame_index = cur_idx
        self.update_preview_with_bg()
        self.preview_viewer.update_frame_display()
        logging.info("Scaling action redone.")


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