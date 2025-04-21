import tkinter as tk
from PIL import Image, ImageTk
import logging
import math

def clear_grid(grid_window):
    """Clear all widgets from the grid."""
    try:
        for widget in grid_window.inner_frame.winfo_children():
            widget.destroy()
        grid_window.thumbnails.clear()
        grid_window.image_positions.clear()
        grid_window.selection_boxes.clear()
    except Exception as e:
        logging.error(f"Error clearing grid: {e}", exc_info=True)

def create_thumbnails(grid_window):
    """Create thumbnails for all images."""
    try:
        for path, data in grid_window.images_data.items():
            if not data.get('thumbnail'):
                try:
                    img = data['pil_image']
                    thumb = create_thumbnail(img, grid_window.grid_size)
                    data['thumbnail'] = ImageTk.PhotoImage(thumb)
                except Exception as e:
                    logging.error(f"Error creating thumbnail for {path}: {e}", exc_info=True)
    except Exception as e:
        logging.error(f"Error in create_thumbnails: {e}", exc_info=True)

def create_thumbnail(image, size):
    """Create a thumbnail of the given size."""
    try:
        # Calculate thumbnail size maintaining aspect ratio
        width, height = image.size
        if width > height:
            new_width = size
            new_height = int(height * (size / width))
        else:
            new_height = size
            new_width = int(width * (size / height))
        
        # Create and return thumbnail
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    except Exception as e:
        logging.error(f"Error creating thumbnail: {e}", exc_info=True)
        return None

def layout_grid(grid_window):
    """Layout images in a grid pattern."""
    try:
        frame_width = grid_window.inner_frame.winfo_width()
        if frame_width == 1:  # Not yet properly initialized
            frame_width = grid_window.canvas.winfo_width()
        
        spacing = 10
        thumb_size = grid_window.grid_size
        items_per_row = max(1, (frame_width - spacing) // (thumb_size + spacing))
        
        for idx, (path, data) in enumerate(grid_window.images_data.items()):
            data['index'] = idx
            row = idx // items_per_row
            col = idx % items_per_row
            
            x = spacing + col * (thumb_size + spacing)
            y = spacing + row * (thumb_size + spacing)
            grid_window.image_positions[idx] = (x, y)
            
            frame = tk.Frame(grid_window.inner_frame)
            frame.place(x=x, y=y)
            
            label = tk.Label(frame, image=data['thumbnail'])
            label.pack()
            label.bind('<Button-1>', lambda e, i=idx: grid_window.on_item_click(e, i))
            
            # Store the frame in the data for future reference
            data['frame'] = frame
            
    except Exception as e:
        logging.error(f"Error in layout_grid: {e}", exc_info=True)

def update_selection(grid_window):
    """Update the visual selection state of all items."""
    try:
        # Clear existing selection boxes
        for box_id in grid_window.selection_boxes.values():
            if box_id:
                grid_window.canvas.delete(box_id)
        grid_window.selection_boxes.clear()
        
        # Create new selection boxes for selected items
        for idx in grid_window.selected_items:
            data = None
            for d in grid_window.images_data.values():
                if d.get('index') == idx:
                    data = d
                    break
                    
            if data and data.get('frame'):
                frame = data['frame']
                x = frame.winfo_x()
                y = frame.winfo_y()
                w = frame.winfo_width()
                h = frame.winfo_height()
                
                # Create selection box
                box_id = grid_window.canvas.create_rectangle(
                    x, y, x + w, y + h,
                    outline='blue',
                    width=2
                )
                grid_window.selection_boxes[idx] = box_id
                
    except Exception as e:
        logging.error(f"Error updating selection: {e}", exc_info=True) 