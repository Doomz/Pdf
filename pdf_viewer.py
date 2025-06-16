import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageTk, ImageDraw
import fitz  # PyMuPDF
import os
import re
import collections

class PDFViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("Synchronized PDF Viewer")
        
        # Initialize variables
        self.zoom_level = 1.0
        self.current_page_left = 1
        self.current_page_right = 1
        self.left_filepath = None
        self.right_filepath = None
        self.panning = False
        self.last_x = 0
        self.last_y = 0
        self.sync_pages = tk.BooleanVar(value=True)  # For sync navigation
        self.highlights = { 'left': [], 'right': [] }
        self.compare_highlights = { 'left': [], 'right': [] }
        
        # Create main toolbar
        self.create_toolbar()
        
        # Create navigation frames
        self.create_navigation_frames()
        
        # Layout: two canvas widgets side by side, fill all space
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill='both', expand=True, padx=0, pady=0)
        self.left_canvas = self.create_scrollable_canvas(self.main_frame, side='left')
        self.right_canvas = self.create_scrollable_canvas(self.main_frame, side='right')
        
        # Status bar for page numbers and search results
        self.status_bar = tk.Label(self.root, text="", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Bind keyboard shortcuts and mouse events
        self.bind_shortcuts()
        self.bind_mouse_events()
        
        # Initialize image lists
        self.left_images = []
        self.right_images = []
        self.left_page_count = 0
        self.right_page_count = 0

    def create_toolbar(self):
        toolbar = tk.Frame(self.root, bd=1, relief=tk.RAISED)
        toolbar.pack(fill=tk.X, padx=2, pady=2)
        
        # File operations
        tk.Button(toolbar, text="Open Left PDF", command=self.open_left_pdf).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Open Right PDF", command=self.open_right_pdf).pack(side=tk.LEFT, padx=2)
        
        # Insert blank page buttons
        tk.Button(toolbar, text="Insert Blank Page Left", command=lambda: self.insert_blank_page('left')).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Insert Blank Page Right", command=lambda: self.insert_blank_page('right')).pack(side=tk.LEFT, padx=2)
        
        # Zoom controls
        tk.Button(toolbar, text="Zoom In (+)", command=lambda: self.zoom(1.1)).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Zoom Out (-)", command=lambda: self.zoom(0.9)).pack(side=tk.LEFT, padx=2)
        self.zoom_label = tk.Label(toolbar, text="Zoom: 100%")
        self.zoom_label.pack(side=tk.LEFT, padx=5)
        # Replace zoom entry with combobox
        tk.Label(toolbar, text="Set Zoom %:").pack(side=tk.LEFT, padx=2)
        zoom_values = [str(z) for z in range(50, 201, 10)]
        self.zoom_combo = ttk.Combobox(toolbar, values=zoom_values, width=5, state="readonly")
        self.zoom_combo.set("100")
        self.zoom_combo.pack(side=tk.LEFT, padx=2)
        self.zoom_combo.bind('<<ComboboxSelected>>', self.on_zoom_combo_change)
        
        # Highlighter color selection
        tk.Label(toolbar, text="Highlight:").pack(side=tk.LEFT, padx=2)
        self.highlight_color = tk.StringVar(value="yellow")
        colors = ["yellow", "green", "pink"]
        for color in colors:
            tk.Radiobutton(toolbar, text=color.capitalize(), variable=self.highlight_color, value=color, indicatoron=0, background=color).pack(side=tk.LEFT, padx=1)
        # Highlighter toggle button
        self.highlighter_on = tk.BooleanVar(value=False)
        self.highlighter_btn = tk.Button(toolbar, text="Highlighter OFF", command=self.toggle_highlighter, bg="lightgray")
        self.highlighter_btn.pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Clear Highlights", command=self.clear_highlights).pack(side=tk.LEFT, padx=2)
        
        # Export buttons
        tk.Button(toolbar, text="Export JPEG", command=self.export_jpeg).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Export PDF", command=self.export_pdf).pack(side=tk.LEFT, padx=2)
        
        # Compare Numbers button
        tk.Button(toolbar, text="Compare Numbers", command=self.compare_numbers).pack(side=tk.LEFT, padx=2)
        
        # Search functionality
        tk.Label(toolbar, text="Search:").pack(side=tk.LEFT, padx=2)
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(toolbar, textvariable=self.search_var, width=20)
        self.search_entry.pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Find", command=self.search_text).pack(side=tk.LEFT, padx=2)
        
        # Page rotation
        tk.Button(toolbar, text="Rotate Left", command=lambda: self.rotate_pdf('left')).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Rotate Right", command=lambda: self.rotate_pdf('right')).pack(side=tk.LEFT, padx=2)

    def create_navigation_frames(self):
        nav_frame = tk.Frame(self.root)
        nav_frame.pack(fill=tk.X)
        # Sync checkbox
        tk.Checkbutton(nav_frame, text="Sync Page Navigation", variable=self.sync_pages).pack(side=tk.TOP, anchor='center', padx=2)
        # Left navigation
        left_nav = tk.Frame(nav_frame)
        left_nav.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(left_nav, text="\u2190", command=lambda: self.navigate_page('left', -1)).pack(side=tk.LEFT, padx=2)
        self.left_page_label = tk.Label(left_nav, text="Page: 0/0")
        self.left_page_label.pack(side=tk.LEFT, padx=5)
        tk.Button(left_nav, text="\u2192", command=lambda: self.navigate_page('left', 1)).pack(side=tk.LEFT, padx=2)
        # Right navigation
        right_nav = tk.Frame(nav_frame)
        right_nav.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        tk.Button(right_nav, text="\u2190", command=lambda: self.navigate_page('right', -1)).pack(side=tk.LEFT, padx=2)
        self.right_page_label = tk.Label(right_nav, text="Page: 0/0")
        self.right_page_label.pack(side=tk.LEFT, padx=5)
        tk.Button(right_nav, text="\u2192", command=lambda: self.navigate_page('right', 1)).pack(side=tk.LEFT, padx=2)

    def bind_shortcuts(self):
        self.root.bind('<Control-plus>', lambda e: self.zoom(1.1))
        self.root.bind('<Control-minus>', lambda e: self.zoom(0.9))
        self.root.bind('<Control-f>', lambda e: self.search_entry.focus())
        self.root.bind('<Control-l>', lambda e: self.open_left_pdf())
        self.root.bind('<Control-r>', lambda e: self.open_right_pdf())
        self.root.bind('<Left>', lambda e: self.navigate_page('left', -1))
        self.root.bind('<Right>', lambda e: self.navigate_page('left', 1))
        self.root.bind('<Control-Left>', lambda e: self.navigate_page('right', -1))
        self.root.bind('<Control-Right>', lambda e: self.navigate_page('right', 1))

    def bind_mouse_events(self):
        # Bind mouse events for both canvases
        for canvas in [self.left_canvas, self.right_canvas]:
            canvas.bind("<ButtonPress-2>", self.start_pan)  # Middle mouse button
            canvas.bind("<B2-Motion>", self.pan)
            canvas.bind("<ButtonRelease-2>", self.stop_pan)
            canvas.bind("<ButtonPress-3>", self.start_pan)  # Right mouse button
            canvas.bind("<B3-Motion>", self.pan)
            canvas.bind("<ButtonRelease-3>", self.stop_pan)
            canvas.bind("<MouseWheel>", self.smooth_scroll)  # Windows
            canvas.bind("<Button-4>", self.smooth_scroll)    # Linux scroll up
            canvas.bind("<Button-5>", self.smooth_scroll)    # Linux scroll down

    def start_pan(self, event):
        canvas = event.widget
        canvas.scan_mark(event.x, event.y)
        self.panning = True
        self.last_x = event.x
        self.last_y = event.y

    def pan(self, event):
        if self.panning:
            canvas = event.widget
            canvas.scan_dragto(event.x, event.y, gain=1)
            self.last_x = event.x
            self.last_y = event.y

    def stop_pan(self, event):
        self.panning = False

    def smooth_scroll(self, event):
        # Determine which canvas triggered the event
        canvas = event.widget
        other_canvas = self.right_canvas if canvas == self.left_canvas else self.left_canvas
        
        # Calculate scroll amount
        if event.num == 5 or event.delta < 0:  # Scroll down
            delta = 1
        else:  # Scroll up
            delta = -1
            
        # Smooth scrolling
        for _ in range(10):  # Number of steps for smooth scrolling
            canvas.yview_scroll(delta, "units")
            other_canvas.yview_scroll(delta, "units")
            canvas.update_idletasks()
            other_canvas.update_idletasks()
            self.root.after(10)  # Small delay between steps

    def navigate_page(self, side, delta):
        if self.sync_pages.get():
            if hasattr(self, 'left_pages') and hasattr(self, 'right_pages') and self.left_images and self.right_images:
                new_page = (self.current_page_left if side == 'left' else self.current_page_right) + delta
                if 1 <= new_page <= min(len(self.left_pages), len(self.right_pages)):
                    self.current_page_left = new_page
                    self.current_page_right = new_page
                    self.load_pdf(self.left_filepath, self.left_canvas, self.left_images, side='left', page_num=new_page-1)
                    self.load_pdf(self.right_filepath, self.right_canvas, self.right_images, side='right', page_num=new_page-1)
            self.update_page_labels()
        else:
            if side == 'left' and hasattr(self, 'left_pages') and self.left_images:
                new_page = self.current_page_left + delta
                if 1 <= new_page <= len(self.left_pages):
                    self.current_page_left = new_page
                    self.load_pdf(self.left_filepath, self.left_canvas, self.left_images, side='left', page_num=new_page-1)
            elif side == 'right' and hasattr(self, 'right_pages') and self.right_images:
                new_page = self.current_page_right + delta
                if 1 <= new_page <= len(self.right_pages):
                    self.current_page_right = new_page
                    self.load_pdf(self.right_filepath, self.right_canvas, self.right_images, side='right', page_num=new_page-1)
            self.update_page_labels()

    def scroll_to_page(self, side, page):
        canvas = self.left_canvas if side == 'left' else self.right_canvas
        # Calculate the y position for the page
        y_pos = 0
        for i in range(page - 1):
            if side == 'left' and i < len(self.left_images):
                y_pos += self.left_images[i].height() + 10
            elif side == 'right' and i < len(self.right_images):
                y_pos += self.right_images[i].height() + 10
        canvas.yview_moveto(y_pos / canvas.winfo_height())

    def update_page_labels(self):
        self.left_page_label.config(text=f"Page: {self.current_page_left}/{self.left_page_count}")
        self.right_page_label.config(text=f"Page: {self.current_page_right}/{self.right_page_count}")

    def search_text(self):
        search_term = self.search_var.get().lower()
        if not search_term:
            return
        
        results = []
        # Search in both PDFs
        for side, filepath in [('left', self.left_filepath), ('right', self.right_filepath)]:
            if filepath:
                doc = fitz.open(filepath)
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    text = page.get_text().lower()
                    if search_term in text:
                        results.append(f"{side.title()} PDF - Page {page_num + 1}")
                doc.close()
        
        if results:
            messagebox.showinfo("Search Results", "\n".join(results))
        else:
            messagebox.showinfo("Search Results", "No matches found")

    def rotate_pdf(self, side):
        if side == 'left' and self.left_filepath:
            self.rotate_pdf_pages(self.left_filepath, self.left_canvas, self.left_images)
        elif side == 'right' and self.right_filepath:
            self.rotate_pdf_pages(self.right_filepath, self.right_canvas, self.right_images)

    def rotate_pdf_pages(self, filepath, canvas, image_list):
        doc = fitz.open(filepath)
        for page in doc:
            page.rotate(90)  # Rotate 90 degrees clockwise
        doc.save(filepath + ".rotated.pdf")
        doc.close()
        self.load_pdf(filepath + ".rotated.pdf", canvas, image_list)
        os.remove(filepath + ".rotated.pdf")  # Clean up temporary file

    def create_scrollable_canvas(self, parent, side='left'):
        frame = tk.Frame(parent, borderwidth=0, highlightthickness=0)
        frame.pack(side=side, fill='both', expand=True, padx=0, pady=0)
        canvas = tk.Canvas(frame, bg='white', borderwidth=0, highlightthickness=0)
        scrollbar = tk.Scrollbar(frame, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        h_scrollbar = tk.Scrollbar(frame, orient='horizontal', command=canvas.xview)
        canvas.configure(xscrollcommand=h_scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        h_scrollbar.pack(side='bottom', fill='x')
        canvas.pack(side='left', fill='both', expand=True)
        return canvas

    def zoom(self, factor):
        self.zoom_level *= factor
        self.zoom_label.config(text=f"Zoom: {int(self.zoom_level * 100)}%")
        
        if self.left_images:
            self.load_pdf(self.left_filepath, self.left_canvas, self.left_images)
        if self.right_images:
            self.load_pdf(self.right_filepath, self.right_canvas, self.right_images)

    def open_left_pdf(self):
        filepath = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if filepath:
            self.left_filepath = filepath
            doc = fitz.open(filepath)
            self.left_pages = list(range(len(doc)))  # logical page list
            self.left_pdf_page_count = len(doc)
            self.left_page_count = len(self.left_pages)
            self.load_pdf(filepath, self.left_canvas, self.left_images, side='left', page_num=0)

    def open_right_pdf(self):
        filepath = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if filepath:
            self.right_filepath = filepath
            doc = fitz.open(filepath)
            self.right_pages = list(range(len(doc)))  # logical page list
            self.right_pdf_page_count = len(doc)
            self.right_page_count = len(self.right_pages)
            self.load_pdf(filepath, self.right_canvas, self.right_images, side='right', page_num=0)

    def load_pdf(self, filepath, canvas, image_list, redraw_highlights=False, side=None, page_num=None):
        from PIL import Image
        import sys
        if not filepath:
            print(f"[DEBUG] No filepath provided for {side} side.")
            return
        if side == 'left':
            pages = getattr(self, 'left_pages', None)
        elif side == 'right':
            pages = getattr(self, 'right_pages', None)
        else:
            pages = None
        if pages is not None and page_num is not None:
            if page_num < 0 or page_num >= len(pages):
                print(f"[DEBUG] page_num {page_num} out of range for {side} logical pages (len={len(pages)})")
                return
            logical_page = pages[page_num]
        else:
            logical_page = page_num
        image_list.clear()
        canvas.delete("all")
        zoom_factor = 1.0 * self.zoom_level
        if logical_page == 'blank':
            # Render a white blank page
            w, h = 800, 1000
            if side and hasattr(self, 'original_images') and side in self.original_images and len(self.original_images[side]) > 0:
                idx = page_num-1 if page_num > 0 else 0
                w, h = self.original_images[side][idx].size
            blank = Image.new('RGB', (w, h), 'white')
            tk_img = ImageTk.PhotoImage(blank)
            image_list.append(tk_img)
            canvas.create_image(0, 0, image=tk_img, anchor='nw')
            if canvas == self.left_canvas:
                self.current_page_left = page_num + 1
            else:
                self.current_page_right = page_num + 1
            self.update_page_labels()
            self.update_status_bar()
            print(f"[DEBUG] Rendered blank page for {side} at page_num {page_num}")
            return
        # Otherwise, render the PDF page as before
        try:
            doc = fitz.open(filepath)
        except Exception as e:
            print(f"[DEBUG] Failed to open PDF {filepath}: {e}")
            return
        if logical_page is None or not isinstance(logical_page, int) or logical_page < 0 or logical_page >= len(doc):
            print(f"[DEBUG] logical_page {logical_page} out of range for PDF (len={len(doc)}) on {side}")
            return
        page = doc[logical_page]
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom_factor, zoom_factor))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        if side:
            if not hasattr(self, 'original_images'):
                self.original_images = {'left': [], 'right': []}
            # Ensure original_images[side] is long enough
            while len(self.original_images[side]) <= page_num:
                self.original_images[side].append(img.copy())
            self.original_images[side][page_num] = img.copy()
            if not hasattr(self, 'page_offsets'):
                self.page_offsets = {'left': [], 'right': []}
            while len(self.page_offsets[side]) <= page_num:
                self.page_offsets[side].append(0)
            self.page_offsets[side][page_num] = 0
        tk_img = ImageTk.PhotoImage(img)
        image_list.append(tk_img)
        canvas.create_image(0, 0, image=tk_img, anchor='nw')
        self.redraw_highlight_overlays(canvas, side, page_num)
        canvas.config(scrollregion=canvas.bbox("all"))
        if canvas == self.left_canvas:
            self.left_page_count = len(self.left_pages) if hasattr(self, 'left_pages') else len(doc)
            self.current_page_left = page_num + 1
        else:
            self.right_page_count = len(self.right_pages) if hasattr(self, 'right_pages') else len(doc)
            self.current_page_right = page_num + 1
        self.update_page_labels()
        self.update_status_bar()
        print(f"[DEBUG] Rendered PDF page {logical_page} for {side} at page_num {page_num}")

    def redraw_highlight_overlays(self, canvas, side, page_num):
        canvas.delete('highlight')
        zoom_factor = 1.0 * self.zoom_level
        # Draw user highlights
        if hasattr(self, 'highlights') and side:
            for (coords, color, pnum) in self.highlights.get(side, []):
                if pnum == page_num:
                    x0, y0, x1, y1 = [c * zoom_factor for c in coords]
                    y_offset = self.get_page_y_offset(canvas, page_num)
                    canvas.create_rectangle(x0, y0 + y_offset, x1, y1 + y_offset, outline='', fill=color, stipple='gray25', tags='highlight')
        # Draw compare highlights
        if hasattr(self, 'compare_highlights') and side:
            for (coords, color, pnum) in self.compare_highlights.get(side, []):
                if pnum == page_num:
                    x0, y0, x1, y1 = coords
                    canvas.create_rectangle(x0, y0, x1, y1, outline='', fill=color, stipple='gray25', tags='highlight')

    def get_rgba_color(self, color, alpha=80):
        # Convert color name to RGBA tuple
        color_map = {
            'yellow': (255, 255, 0, alpha),
            'green': (0, 255, 0, alpha),
            'pink': (255, 105, 180, alpha)
        }
        return color_map.get(color, (255, 255, 0, alpha))

    def update_status_bar(self):
        status_text = f"Left PDF: {self.left_page_count} pages | Right PDF: {self.right_page_count} pages"
        self.status_bar.config(text=status_text)

    def toggle_highlighter(self):
        if self.highlighter_on.get():
            self.highlighter_on.set(False)
            self.highlighter_btn.config(text="Highlighter OFF", bg="lightgray")
            self.left_canvas.unbind('<Button-1>')
            self.left_canvas.unbind('<B1-Motion>')
            self.left_canvas.unbind('<ButtonRelease-1>')
            self.right_canvas.unbind('<Button-1>')
            self.right_canvas.unbind('<B1-Motion>')
            self.right_canvas.unbind('<ButtonRelease-1>')
        else:
            self.highlighter_on.set(True)
            self.highlighter_btn.config(text="Highlighter ON", bg="yellow")
            self.left_canvas.bind('<Button-1>', lambda e: self.start_highlight(e, 'left'))
            self.left_canvas.bind('<B1-Motion>', lambda e: self.draw_highlight(e, 'left'))
            self.left_canvas.bind('<ButtonRelease-1>', lambda e: self.end_highlight(e, 'left'))
            self.right_canvas.bind('<Button-1>', lambda e: self.start_highlight(e, 'right'))
            self.right_canvas.bind('<B1-Motion>', lambda e: self.draw_highlight(e, 'right'))
            self.right_canvas.bind('<ButtonRelease-1>', lambda e: self.end_highlight(e, 'right'))

    def start_highlight(self, event, side):
        if not self.highlighter_on.get():
            return
        canvas = event.widget
        self.highlighting = True
        self.start_x = canvas.canvasx(event.x)
        self.start_y = canvas.canvasy(event.y)
        self.current_highlight = canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline='', fill='#ffff99', stipple='gray25', tags='highlight'
        )
        self.highlight_page = self.get_page_from_y(canvas, self.start_y)

    def draw_highlight(self, event, side):
        if not self.highlighter_on.get():
            return
        if self.highlighting and self.current_highlight:
            canvas = event.widget
            cur_x = canvas.canvasx(event.x)
            cur_y = canvas.canvasy(event.y)
            canvas.coords(self.current_highlight, self.start_x, self.start_y, cur_x, cur_y)

    def end_highlight(self, event, side):
        if not self.highlighter_on.get():
            return
        self.highlighting = False
        canvas = event.widget
        if self.current_highlight:
            coords = canvas.coords(self.current_highlight)
            color = '#ffff99'  # Use a visible yellow
            page_num = self.highlight_page
            if hasattr(self, 'highlights'):
                if side not in self.highlights:
                    self.highlights[side] = []
                y_offset = self.get_page_y_offset(canvas, page_num)
                rel_coords = [coords[0], coords[1] - y_offset, coords[2], coords[3] - y_offset]
                self.highlights[side].append((rel_coords, color, page_num))
            canvas.delete(self.current_highlight)
            self.current_highlight = None
            self.redraw_highlight_overlays(canvas, side, page_num)

    def get_page_from_y(self, canvas, y):
        # Estimate which page the y coordinate is on
        y_offset = 0
        for i, img in enumerate(self.left_images if canvas == self.left_canvas else self.right_images):
            if y < y_offset + img.height():
                return i
            y_offset += img.height() + 10
        return 0

    def get_page_y_offset(self, canvas, page_num):
        y_offset = 0
        for i, img in enumerate(self.left_images if canvas == self.left_canvas else self.right_images):
            if i == page_num:
                return y_offset
            y_offset += img.height() + 10
        return 0

    def on_zoom_combo_change(self, event=None):
        try:
            val = float(self.zoom_combo.get())
            if val <= 0:
                raise ValueError
            self.zoom_level = val / 100.0
            self.zoom_label.config(text=f"Zoom: {int(self.zoom_level * 100)}%")
            self.reload_visible_pages()
        except Exception:
            self.zoom_combo.set(str(int(self.zoom_level * 100)))

    def reload_visible_pages(self):
        # Reload only the current page for each side
        if hasattr(self, 'left_filepath') and self.left_filepath and self.left_images and hasattr(self, 'current_page_left') and self.current_page_left is not None:
            self.load_pdf(self.left_filepath, self.left_canvas, self.left_images, redraw_highlights=True, side='left', page_num=self.current_page_left-1)
        if hasattr(self, 'right_filepath') and self.right_filepath and self.right_images and hasattr(self, 'current_page_right') and self.current_page_right is not None:
            self.load_pdf(self.right_filepath, self.right_canvas, self.right_images, redraw_highlights=True, side='right', page_num=self.current_page_right-1)

    def export_jpeg(self):
        # Placeholder for export as JPEG logic
        messagebox.showinfo("Export JPEG", "Export as JPEG feature coming soon!")

    def export_pdf(self):
        # Placeholder for export as PDF logic
        messagebox.showinfo("Export PDF", "Export as PDF feature coming soon!")

    def compare_numbers(self):
        import collections
        import re
        if not hasattr(self, 'left_filepath') or not hasattr(self, 'right_filepath'):
            messagebox.showinfo("Compare Numbers", "Please load both PDFs first.")
            return
        try:
            left_page_num = self.current_page_left - 1
            right_page_num = self.current_page_right - 1
            # Skip blank pages
            if (hasattr(self, 'left_pages') and self.left_pages[left_page_num] == 'blank') or \
               (hasattr(self, 'right_pages') and self.right_pages[right_page_num] == 'blank'):
                messagebox.showinfo("Compare Numbers", "Cannot compare numbers on a blank page.")
                return
            left_doc = fitz.open(self.left_filepath)
            right_doc = fitz.open(self.right_filepath)
            left_pdf_page = self.left_pages[left_page_num] if hasattr(self, 'left_pages') else left_page_num
            right_pdf_page = self.right_pages[right_page_num] if hasattr(self, 'right_pages') else right_page_num
            left_words = left_doc[left_pdf_page].get_text("words")
            right_words = right_doc[right_pdf_page].get_text("words")

            def normalize_number(text):
                # Remove spaces, percent signs, and normalize decimal separator
                text = text.replace(' ', '').replace('%', '')
                text = text.strip('()')  # Remove parentheses
                # Remove thousands separators (either . or , if followed by 3 digits)
                text = re.sub(r'(?<=\d)[.,](?=\d{3}(\D|$))', '', text)
                # Replace remaining comma with dot for decimal
                text = text.replace(',', '.')
                return text

            # Updated regex: allow optional parentheses around the number
            number_regex = re.compile(r'^\(?-?\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d+)?%?\)?$')

            def extract_numbers_from_words(words):
                numbers = []
                for w in words:
                    text = w[4]
                    if number_regex.match(text):
                        x0, y0, x1, y1 = w[0], w[1], w[2], w[3]
                        numbers.append({
                            'num': text,
                            'rect': (x0, y0, x1, y1)
                        })
                return numbers

            left_numbers = extract_numbers_from_words(left_words)
            right_numbers = extract_numbers_from_words(right_words)
            left_nums_norm = [normalize_number(n['num']) for n in left_numbers]
            right_nums_norm = [normalize_number(n['num']) for n in right_numbers]
            left_counter = collections.Counter(left_nums_norm)
            right_counter = collections.Counter(right_nums_norm)
            left_highlighted = collections.Counter()
            right_highlighted = collections.Counter()
            # Only clear compare highlights for the current page, not all pages
            if not hasattr(self, 'compare_highlights'):
                self.compare_highlights = {'left': [], 'right': []}
            self.compare_highlights['left'] = [h for h in self.compare_highlights['left'] if h[2] != left_page_num]
            self.compare_highlights['right'] = [h for h in self.compare_highlights['right'] if h[2] != right_page_num]
            zoom = self.zoom_level
            for i, n in enumerate(left_numbers):
                norm = left_nums_norm[i]
                min_count = min(left_counter[norm], right_counter[norm])
                if left_highlighted[norm] < min_count and min_count > 0:
                    color = '#00ff00'  # Green
                else:
                    color = '#ff00ff'  # Magenta
                left_highlighted[norm] += 1
                x0, y0, x1, y1 = n['rect']
                x0, y0, x1, y1 = x0*zoom, y0*zoom, x1*zoom, y1*zoom
                self.compare_highlights['left'].append(((x0, y0, x1, y1), color, left_page_num))
            for i, n in enumerate(right_numbers):
                norm = right_nums_norm[i]
                min_count = min(left_counter[norm], right_counter[norm])
                if right_highlighted[norm] < min_count and min_count > 0:
                    color = '#00ff00'  # Green
                else:
                    color = '#ff00ff'  # Magenta
                right_highlighted[norm] += 1
                x0, y0, x1, y1 = n['rect']
                x0, y0, x1, y1 = x0*zoom, y0*zoom, x1*zoom, y1*zoom
                self.compare_highlights['right'].append(((x0, y0, x1, y1), color, right_page_num))
            self.redraw_highlight_overlays(self.left_canvas, 'left', left_page_num)
            self.redraw_highlight_overlays(self.right_canvas, 'right', right_page_num)
            summary = []
            if any(c == '#ff00ff' for (_, c, _) in self.compare_highlights['left'] + self.compare_highlights['right']):
                summary.append('Magenta: Not found on other side')
            if any(c == '#00ff00' for (_, c, _) in self.compare_highlights['left'] + self.compare_highlights['right']):
                summary.append('Green: Match (value exists on both sides)')
            messagebox.showinfo("Compare Numbers", "Number comparison complete.\n" + "\n".join(summary))
        except Exception as e:
            messagebox.showerror("Compare Numbers", f"Error: {e}")

    def clear_highlights(self):
        import tkinter.simpledialog
        choice = tkinter.simpledialog.askstring(
            "Clear Highlights", "Type 'current' to clear highlights for the current page, or 'all' to clear all pages:", parent=self.root)
        if not choice:
            return
        choice = choice.strip().lower()
        if choice == 'all':
            if hasattr(self, 'highlights'):
                self.highlights = { 'left': [], 'right': [] }
            if hasattr(self, 'compare_highlights'):
                self.compare_highlights = { 'left': [], 'right': [] }
            for canvas in [self.left_canvas, self.right_canvas]:
                canvas.delete('highlight')
        elif choice == 'current':
            page_left = self.current_page_left - 1
            page_right = self.current_page_right - 1
            if hasattr(self, 'highlights'):
                self.highlights['left'] = [h for h in self.highlights['left'] if h[2] != page_left]
                self.highlights['right'] = [h for h in self.highlights['right'] if h[2] != page_right]
            if hasattr(self, 'compare_highlights'):
                self.compare_highlights['left'] = [h for h in self.compare_highlights['left'] if h[2] != page_left]
                self.compare_highlights['right'] = [h for h in self.compare_highlights['right'] if h[2] != page_right]
            self.redraw_highlight_overlays(self.left_canvas, 'left', page_left)
            self.redraw_highlight_overlays(self.right_canvas, 'right', page_right)
        self.update_page_labels()
        self.update_status_bar()

    def insert_blank_page(self, side):
        from PIL import Image
        if side == 'left':
            page_num = self.current_page_left - 1
            if not hasattr(self, 'left_pages'):
                self.left_pages = []
            if not hasattr(self, 'original_images'):
                self.original_images = {'left': [], 'right': []}
            # Use the size of the current page if possible, else default
            w, h = 800, 1000
            if hasattr(self, 'original_images') and 'left' in self.original_images and len(self.original_images['left']) > 0:
                if page_num < len(self.original_images['left']):
                    w, h = self.original_images['left'][page_num].size
                else:
                    w, h = self.original_images['left'][-1].size
            # Insert 'blank' marker in logical page list
            self.left_pages.insert(page_num, 'blank')
            self.left_page_count = len(self.left_pages)
            self.load_pdf(self.left_filepath, self.left_canvas, self.left_images, side='left', page_num=page_num)
        elif side == 'right':
            page_num = self.current_page_right - 1
            if not hasattr(self, 'right_pages'):
                self.right_pages = []
            if not hasattr(self, 'original_images'):
                self.original_images = {'left': [], 'right': []}
            w, h = 800, 1000
            if hasattr(self, 'original_images') and 'right' in self.original_images and len(self.original_images['right']) > 0:
                if page_num < len(self.original_images['right']):
                    w, h = self.original_images['right'][page_num].size
                else:
                    w, h = self.original_images['right'][-1].size
            self.right_pages.insert(page_num, 'blank')
            self.right_page_count = len(self.right_pages)
            self.load_pdf(self.right_filepath, self.right_canvas, self.right_images, side='right', page_num=page_num)
        self.update_page_labels()

# Run the app
if __name__ == '__main__':
    root = tk.Tk()
    app = PDFViewer(root)
    root.mainloop()
