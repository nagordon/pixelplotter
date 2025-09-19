

# Notes and quick tips:

# Use mouse wheel to zoom (pointer-centric zoom keeps cursor over same image coordinate).

# Pan with middle mouse button drag; if you don’t have a middle button, hold Shift and drag with left mouse.

# Click 4 axis points in order X0, X1, Y0, Y1, then type their numeric values into the input boxes.

# After that, click data points; use Plot to preview and Export CSV to save.

# Reset clears everything; Quit exits the app.

# The status bar at the bottom now shows "Pixel: x, y" (image pixel coordinates) and "Calib: X, Y" (calibrated chart coordinates) updated live as the mouse moves.

# Calibrated coordinates appear only when 4 axis points are selected and valid numeric axis values are entered.

# Zoom is pointer-centric (mouse cursor stays over the same image point while zooming). Pan works with middle mouse drag or Shift+Left-drag.

# Each data point selected after calibration is appended to the table with pixel coordinates and calibrated coordinates (if calibration is available).

# Use "Delete Selected" to remove rows, "Clear Table" to remove all, and "Export Table CSV" to save table content (prefers calibrated values if present).

# Table double-click deletes a row and prompts you to reselect the point on the image.

# Zoom/pan refresh the table so calibrated values remain consistent with current calibration entries.


__version__ = '0.1'
__author__ = 'Neal Gordon'

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import cv2
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
import csv

HELP_TEXT = (
    "Workflow Instructions\n\n"
    "1) Open Image\n"
    "2) Click 4 axis points in order: X0, X1, Y0, Y1\n"
    "3) Enter numeric axis values in the toolbar boxes\n"
    "4) Click data points (after 4 axis points are set)\n"
    "   - Each selected data point is appended to the table on the right\n"
    "5) Use mouse wheel to zoom (pointer-centric)\n"
    "6) Pan with middle-mouse drag or Shift+Left-drag\n"
    "7) Status bar shows image pixel coords and calibrated coords (when available)\n"
    "8) Use table buttons to delete or clear points; Export CSV to save (now exports PixelX,PixelY,CalibX,CalibY)\n"
    "9) Reset clears selections; Quit exits the app\n"
)

class ChartDigitizer:
    def __init__(self, root):
        self.root = root
        self.root.title(f"pixelplotter v{__version__}")

        # Menu
        menubar = tk.Menu(root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open Image", command=self.load_image)
        file_menu.add_command(label="Export CSV", command=self.export_csv)
        file_menu.add_command(label="Plot", command=self.plot_data)
        file_menu.add_separator()
        file_menu.add_command(label="Reset", command=self.reset_all)
        file_menu.add_command(label="Quit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Workflow Instructions", command=self.show_help)
        menubar.add_cascade(label="Help", menu=help_menu)

        root.config(menu=menubar)

        # --- Top control frame (axis entries + quick buttons) ---
        ctl = tk.Frame(root)
        ctl.pack(side=tk.TOP, fill=tk.X, padx=6, pady=6)

        tk.Button(ctl, text="Open Image", command=self.load_image).pack(side=tk.LEFT, padx=4)
        tk.Button(ctl, text="Export CSV", command=self.export_csv).pack(side=tk.LEFT, padx=4)
        tk.Button(ctl, text="Plot", command=self.plot_data).pack(side=tk.LEFT, padx=4)
        tk.Button(ctl, text="Reset", command=self.reset_all).pack(side=tk.LEFT, padx=4)
        tk.Button(ctl, text="Quit", command=self.root.quit).pack(side=tk.LEFT, padx=4)

        # Axis entries inline
        tk.Label(ctl, text="  X0:").pack(side=tk.LEFT)
        self.x0_entry = tk.Entry(ctl, width=8); self.x0_entry.pack(side=tk.LEFT)
        tk.Label(ctl, text="X1:").pack(side=tk.LEFT)
        self.x1_entry = tk.Entry(ctl, width=8); self.x1_entry.pack(side=tk.LEFT)
        tk.Label(ctl, text="Y0:").pack(side=tk.LEFT)
        self.y0_entry = tk.Entry(ctl, width=8); self.y0_entry.pack(side=tk.LEFT)
        tk.Label(ctl, text="Y1:").pack(side=tk.LEFT)
        self.y1_entry = tk.Entry(ctl, width=8); self.y1_entry.pack(side=tk.LEFT)

        # --- Main area: left canvas, right table & controls ---
        main = tk.Frame(root)
        main.pack(fill=tk.BOTH, expand=True)

        # Canvas for image
        self.canvas = tk.Canvas(main, cursor="cross", bg="black")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Right frame: table + table buttons + help
        right = tk.Frame(main, width=360)
        right.pack(side=tk.RIGHT, fill=tk.Y)

        # Table label
        tk.Label(right, text="Selected Points (pixel → calibrated)").pack(anchor=tk.NW, padx=6, pady=(6,0))

        # Treeview as spreadsheet-like widget
        cols = ("index", "px", "py", "x", "y")
        self.tree = ttk.Treeview(right, columns=cols, show="headings", height=20)
        self.tree.heading("index", text="#")
        self.tree.heading("px", text="Pixel X")
        self.tree.heading("py", text="Pixel Y")
        self.tree.heading("x", text="Calib X")
        self.tree.heading("y", text="Calib Y")
        self.tree.column("index", width=30, anchor=tk.CENTER)
        self.tree.column("px", width=70, anchor=tk.CENTER)
        self.tree.column("py", width=70, anchor=tk.CENTER)
        self.tree.column("x", width=90, anchor=tk.CENTER)
        self.tree.column("y", width=90, anchor=tk.CENTER)
        self.tree.pack(fill=tk.Y, padx=6, pady=4)

        # Table buttons
        tb = tk.Frame(right)
        tb.pack(fill=tk.X, padx=6, pady=4)
        tk.Button(tb, text="Delete Selected", command=self.delete_selected).pack(side=tk.LEFT, padx=2)
        tk.Button(tb, text="Clear Table", command=self.clear_table).pack(side=tk.LEFT, padx=2)
        tk.Button(tb, text="Export Table CSV", command=self.export_csv).pack(side=tk.LEFT, padx=2)

        # Help shortcut
        tk.Button(right, text="Help", command=self.show_help).pack(side=tk.BOTTOM, pady=6)

        # --- Status bar (cursor coordinates) ---
        status = tk.Frame(root, relief=tk.SUNKEN, bd=1)
        status.pack(side=tk.BOTTOM, fill=tk.X)
        self.pixel_label = tk.Label(status, text="Pixel: -, -", anchor=tk.W)
        self.pixel_label.pack(side=tk.LEFT, padx=6)
        self.calib_label = tk.Label(status, text="Calib: -, -", anchor=tk.W)
        self.calib_label.pack(side=tk.LEFT, padx=10)

        # --- Internal state ---
        self.image = None          # original OpenCV image (BGR)
        self.tk_image = None       # PhotoImage used by canvas
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.drag_start = None
        self.axis_points = []      # [(x,y),...] in image (pixel) coordinates
        self.data_points = []      # [(x,y),...] in image (pixel) coordinates (pixel coords stored here)
        self.panning_by_shift = False

        # --- Bindings ---
        # Selection: left-click
        self.canvas.bind("<Button-1>", self.on_left_click)
        # Zoom: platform-safe bindings
        self.canvas.bind("<MouseWheel>", self.on_zoom)        # Windows / Mac
        self.canvas.bind("<Button-4>", lambda e: self.on_zoom(e, delta=1))   # Linux scroll up
        self.canvas.bind("<Button-5>", lambda e: self.on_zoom(e, delta=-1))  # Linux scroll down
        # Pan: middle button
        self.canvas.bind("<ButtonPress-2>", self.start_pan)   # middle press
        self.canvas.bind("<B2-Motion>", self.do_pan)          # middle drag
        self.canvas.bind("<ButtonRelease-2>", self.end_pan)
        # Pan: Shift+Left (explicit bindings)
        self.canvas.bind("<Shift-ButtonPress-1>", self.start_pan_shift)
        self.canvas.bind("<Shift-B1-Motion>", self.do_pan)
        self.canvas.bind("<Shift-ButtonRelease-1>", self.end_pan)
        # Track mouse motion to display coordinates
        self.canvas.bind("<Motion>", self.on_mouse_move)
        # Allow double-click on table to remove row
        self.tree.bind("<Delete>", lambda e: self.delete_selected())
        self.tree.bind("<Double-1>", lambda e: self.edit_entry())

        # Helpful defaults (optional)
        self.x0_entry.insert(0, "")
        self.x1_entry.insert(0, "")
        self.y0_entry.insert(0, "")
        self.y1_entry.insert(0, "")

    def show_help(self):
        win = tk.Toplevel(self.root)
        win.title("Workflow Instructions")
        txt = tk.Text(win, width=70, height=20, wrap=tk.WORD)
        txt.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        txt.insert(tk.END, HELP_TEXT)
        txt.config(state=tk.DISABLED)
        tk.Button(win, text="Close", command=win.destroy).pack(pady=4)

    # ---------- Image loading / display ----------
    def load_image(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.bmp;*.tif;*.tiff")])
        if not path:
            return
        img = cv2.imread(path)
        if img is None:
            messagebox.showerror("Load error", "Could not read selected image.")
            return
        self.image = img
        self.reset_view(keep_table=False)
        self.draw_image()

    def reset_view(self, keep_table=True):
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.drag_start = None
        self.axis_points.clear()
        self.data_points.clear()
        self.canvas.delete("all")
        self.update_status(None, None)
        if not keep_table:
            self.clear_table()

    def draw_image(self):
        if self.image is None:
            return
        h, w = self.image.shape[:2]
        new_w, new_h = int(w * self.scale), int(h * self.scale)
        if new_w < 1 or new_h < 1:
            return
        resized = cv2.resize(self.image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(rgb)
        self.tk_image = ImageTk.PhotoImage(pil)
        self.canvas.delete("all")
        self.canvas.config(scrollregion=(0, 0, new_w, new_h))
        self.canvas.create_image(self.offset_x, self.offset_y, anchor=tk.NW, image=self.tk_image)
        # redraw markers
        for i, (px, py) in enumerate(self.axis_points):
            sx = int(px * self.scale + self.offset_x)
            sy = int(py * self.scale + self.offset_y)
            label = ['X0', 'X1', 'Y0', 'Y1'][i] if i < 4 else str(i)
            self.canvas.create_text(sx + 6, sy - 6, text=label, fill="cyan", font=("Arial", 10, "bold"))
            self.canvas.create_oval(sx-4, sy-4, sx+4, sy+4, outline="cyan")
        for px, py in self.data_points:
            sx = int(px * self.scale + self.offset_x)
            sy = int(py * self.scale + self.offset_y)
            self.canvas.create_oval(sx-3, sy-3, sx+3, sy+3, fill="red", outline="red")

    # ---------- Click handling ----------
    def on_left_click(self, event):
        # If currently panning via Shift+Left, ignore selection
        if self.panning_by_shift:
            return
        if self.image is None:
            return
        img_x = int((event.x - self.offset_x) / self.scale)
        img_y = int((event.y - self.offset_y) / self.scale)
        h, w = self.image.shape[:2]
        img_x = max(0, min(w - 1, img_x))
        img_y = max(0, min(h - 1, img_y))
        if len(self.axis_points) < 4:
            self.axis_points.append((img_x, img_y))
            self.draw_image()
        else:
            # data point: store pixel coords and add to table with calibrated if possible
            self.data_points.append((img_x, img_y))
            calib = self.compute_calibrated_point(img_x, img_y)
            idx = len(self.data_points)
            if calib is None:
                x_val_str = ""
                y_val_str = ""
            else:
                x_val_str = f"{calib[0]:.6g}"
                y_val_str = f"{calib[1]:.6g}"
            self.tree.insert("", "end", values=(idx, img_x, img_y, x_val_str, y_val_str))
            self.draw_image()

    # ---------- Table operations ----------
    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        for iid in sel:
            vals = self.tree.item(iid, "values")
            try:
                idx = int(vals[0]) - 1
            except Exception:
                idx = None
            if idx is not None and 0 <= idx < len(self.data_points):
                self.data_points[idx] = None
            self.tree.delete(iid)
        # rebuild data_points from table rows
        new_points = []
        for row in self.tree.get_children():
            vals = self.tree.item(row, "values")
            try:
                px = int(vals[1]); py = int(vals[2])
                new_points.append((px, py))
            except Exception:
                pass
        self.data_points = new_points
        self.refresh_table()

    def clear_table(self):
        self.tree.delete(*self.tree.get_children())
        self.data_points.clear()

    def refresh_table(self):
        self.tree.delete(*self.tree.get_children())
        for i, (px, py) in enumerate(self.data_points, start=1):
            calib = self.compute_calibrated_point(px, py)
            if calib is None:
                x_val_str = ""
                y_val_str = ""
            else:
                x_val_str = f"{calib[0]:.6g}"
                y_val_str = f"{calib[1]:.6g}"
            self.tree.insert("", "end", values=(i, px, py, x_val_str, y_val_str))

    def edit_entry(self):
        sel = self.tree.selection()
        if not sel:
            return
        iid = sel[0]
        vals = self.tree.item(iid, "values")
        px, py = int(vals[1]), int(vals[2])
        try:
            self.data_points.remove((px, py))
        except ValueError:
            pass
        self.tree.delete(iid)
        self.refresh_table()
        messagebox.showinfo("Edit", "Deleted selected row. Click on the image to add a new point.")

    # ---------- Mouse motion: update status ----------
    def on_mouse_move(self, event):
        if self.image is None:
            self.update_status(None, None)
            return
        img_x = (event.x - self.offset_x) / self.scale
        img_y = (event.y - self.offset_y) / self.scale
        h, w = self.image.shape[:2]
        px = int(max(0, min(w - 1, round(img_x))))
        py = int(max(0, min(h - 1, round(img_y))))
        calib = self.compute_calibrated_point(img_x, img_y)
        self.update_status((px, py), calib)

    def update_status(self, pixel_tuple, calib_tuple):
        if pixel_tuple is None:
            self.pixel_label.config(text="Pixel: -, -")
        else:
            self.pixel_label.config(text=f"Pixel: {pixel_tuple[0]}, {pixel_tuple[1]}")
        if calib_tuple is None:
            self.calib_label.config(text="Calib: -, -")
        else:
            x_val, y_val = calib_tuple
            self.calib_label.config(text=f"Calib: {x_val:.6g}, {y_val:.6g}")

    def compute_calibrated_point(self, img_x, img_y):
        # accepts float img_x,img_y (image pixel coordinates)
        if self.image is None or len(self.axis_points) != 4:
            return None
        try:
            x0_val = float(self.x0_entry.get())
            x1_val = float(self.x1_entry.get())
            y0_val = float(self.y0_entry.get())
            y1_val = float(self.y1_entry.get())
        except Exception:
            return None
        x0_px, x1_px = self.axis_points[0][0], self.axis_points[1][0]
        y0_py, y1_py = self.axis_points[2][1], self.axis_points[3][1]
        if x1_px == x0_px or y0_py == y1_py:
            return None
        x_scale = (x1_val - x0_val) / (x1_px - x0_px)
        y_scale = (y1_val - y0_val) / (y0_py - y1_py)  # image y increases downward
        x_val = x0_val + (img_x - x0_px) * x_scale
        y_val = y0_val + (y0_py - img_y) * y_scale
        return (x_val, y_val)

    # ---------- Zoom / Pan ----------
    def on_zoom(self, event, delta=None):
        if self.image is None:
            return
        if delta is None:
            delta = 1 if event.delta > 0 else -1
        factor = 1.1 if delta > 0 else 0.9
        mx, my = event.x, event.y
        ix_before = (mx - self.offset_x) / self.scale
        iy_before = (my - self.offset_y) / self.scale
        self.scale *= factor
        self.offset_x = mx - ix_before * self.scale
        self.offset_y = my - iy_before * self.scale
        self.draw_image()
        self.refresh_table()

    def start_pan(self, event):
        self.drag_start = (event.x, event.y)
        self.panning_by_shift = False

    def start_pan_shift(self, event):
        self.drag_start = (event.x, event.y)
        self.panning_by_shift = True

    def do_pan(self, event):
        if self.drag_start is None:
            return
        dx = event.x - self.drag_start[0]
        dy = event.y - self.drag_start[1]
        self.offset_x += dx
        self.offset_y += dy
        self.drag_start = (event.x, event.y)
        self.draw_image()
        self.refresh_table()

    def end_pan(self, event):
        self.drag_start = None
        self.panning_by_shift = False

    # ---------- Conversion, CSV, Plot ----------
    def convert_points(self):
        if len(self.axis_points) != 4:
            messagebox.showerror("Error", "Please select exactly 4 axis points (X0, X1, Y0, Y1).")
            return None
        try:
            x0_val = float(self.x0_entry.get())
            x1_val = float(self.x1_entry.get())
            y0_val = float(self.y0_entry.get())
            y1_val = float(self.y1_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter numeric axis values in X0,X1,Y0,Y1.")
            return None

        x0_px, x1_px = self.axis_points[0][0], self.axis_points[1][0]
        y0_py, y1_py = self.axis_points[2][1], self.axis_points[3][1]
        if x1_px == x0_px or y0_py == y1_py:
            messagebox.showerror("Error", "Axis points produce zero division (choose distinct axis points).")
            return None

        x_scale = (x1_val - x0_val) / (x1_px - x0_px)
        y_scale = (y1_val - y0_val) / (y0_py - y1_py)

        converted = []
        for px, py in self.data_points:
            x_val = x0_val + (px - x0_px) * x_scale
            y_val = y0_val + (y0_py - py) * y_scale
            converted.append((px, py, x_val, y_val))
        return converted

    def export_csv(self):
        # Export table rows with PixelX, PixelY, CalibX, CalibY
        rows = []
        # prefer using the table contents (keeps user edits), else fallback to internal data_points
        for row in self.tree.get_children():
            vals = self.tree.item(row, "values")
            try:
                px = int(vals[1]); py = int(vals[2])
            except Exception:
                continue
            try:
                cx = float(vals[3]) if vals[3] != "" else None
                cy = float(vals[4]) if vals[4] != "" else None
            except Exception:
                cx = cy = None
            rows.append((px, py, cx, cy))

        if not rows and self.data_points:
            converted = self.convert_points()
            if converted is None:
                return
            # converted contains (px,py,x_val,y_val)
            for px, py, x_val, y_val in converted:
                rows.append((int(px), int(py), x_val, y_val))

        if not rows:
            messagebox.showinfo("Export", "No points to export.")
            return

        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        try:
            with open(path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["PixelX", "PixelY", "CalibX", "CalibY"])
                for px, py, cx, cy in rows:
                    writer.writerow([px, py, "" if cx is None else cx, "" if cy is None else cy])
            messagebox.showinfo("Export", f"Saved {len(rows)} points to:\n{path}")
        except Exception as e:
            messagebox.showerror("Save error", str(e))

    def plot_data(self):
        # plot using calibrated values if available in table, else use pixel coords
        rows = []
        for row in self.tree.get_children():
            vals = self.tree.item(row, "values")
            try:
                cx = float(vals[3]) if vals[3] != "" else None
                cy = float(vals[4]) if vals[4] != "" else None
                if cx is not None and cy is not None:
                    rows.append((cx, cy))
                else:
                    px = int(vals[1]); py = int(vals[2])
                    rows.append((px, py))
            except Exception:
                pass
        if not rows and self.data_points:
            converted = self.convert_points()
            if converted is None:
                return
            for px, py, x_val, y_val in converted:
                rows.append((x_val, y_val))
        if not rows:
            messagebox.showinfo("Plot", "No data points to plot.")
            return
        x_vals, y_vals = zip(*rows)
        plt.figure(figsize=(6,4))
        plt.plot(x_vals, y_vals, 'ro-')
        plt.title("Digitized Chart Data")
        plt.xlabel("X")
        plt.ylabel("Y")
        plt.grid(True)
        plt.show()

    # ---------- Reset ----------
    def reset_all(self):
        self.axis_points.clear()
        self.data_points.clear()
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.drag_start = None
        self.panning_by_shift = False
        self.x0_entry.delete(0, tk.END)
        self.x1_entry.delete(0, tk.END)
        self.y0_entry.delete(0, tk.END)
        self.y1_entry.delete(0, tk.END)
        self.canvas.delete("all")
        self.update_status(None, None)
        self.clear_table()
        if self.image is not None:
            self.draw_image()

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1200x700")
    app = ChartDigitizer(root)
    root.mainloop()
