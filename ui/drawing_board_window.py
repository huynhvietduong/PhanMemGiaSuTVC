import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from PIL import Image, ImageTk, ImageDraw, ImageGrab
import io
import os
import uuid
import json, base64, time
from io import BytesIO
from PIL import ImageChops
from PIL import ImageFilter
class DrawingBoardWindow(tk.Toplevel):
    """
    ✨ Bảng Vẽ Bài Giảng (Phiên bản đã sửa lỗi)
    - Công cụ: pen, eraser, line, rect, oval, select
    - Ảnh: dán từ clipboard (Ctrl+V), chọn/kéo/xoá
    - Lưu lịch sử nét vẽ trong self.drawn_items để redraw khi mở lại
    - Dùng INK_SCALE để vẽ mượt trên lớp mực (PIL)
    """

    # 1) CLASS & LIFECYCLE / WINDOW MANAGEMENT/Nhóm 1 – Quản lý cửa sổ & vòng đời
    # Khởi tạo cửa sổ bảng vẽ, thiết lập UI, sự kiện, biến trạng thái
    def __init__(self, master=None, group_name=None, session_date=None,session_id=None, on_saved=None, board_path=None, lesson_dir=None):
        super().__init__(master)
        # Quản lý các after-callback để hủy an toàn khi đóng cửa sổ
        self._afters = {}
        # Đảm bảo đóng cửa sổ sẽ gọi destroy() của lớp
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        # Cho phép đầy đủ nút Thu nhỏ / Phóng to và resize cửa sổ
        self.resizable(True, True)
        try:
            # Không dùng toolwindow để không ẩn nút Min/Max (Windows)
            self.attributes("-toolwindow", False)
        except Exception:
            pass

        self.title("✨ Bảng Vẽ Bài Giảng")

        # Mặc định phóng to khi mở (maximize)
        def _maximize_on_open():
            try:
                self.state("zoomed")  # Windows
            except Exception:
                # Fallback nếu WM không hỗ trợ 'zoomed'
                sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
                self.geometry(f"{sw}x{sh}+0+0")

        # Đợi Tk dựng xong rồi mới maximize để tránh giật layout
        self.after(0, _maximize_on_open)

        self.group_name = group_name or ""
        self.session_date = session_date or ""
        self.session_id = session_id
        self.on_saved = on_saved
        self._lesson_dir = lesson_dir or os.path.join(os.getcwd(), "data", "lessons", str(self.session_id or "unknown"))
        self._current_board_path = None

        self.current_tool = "pen"
        self.draw_color = "#000000"
        self.bg_color = "#ffffff"
        self.pen_width = 3
        self.eraser_width = 25

        self.drawn_items = []
        self.undo_stack = []

        self.INK_SCALE = 3
        self._ink_img = None
        self._ink_draw = None
        self._ink_tk = None
        self._ink_item_id = None

        self.canvas_line_opts = dict(
            smooth=True, splinesteps=12,  # Giảm splinesteps cho preview mượt hơn
            capstyle=tk.ROUND, joinstyle=tk.ROUND
        )

        self._force_straight_line = False

        self._build_toolbar()
        self._build_canvas()

        self.selected_image_id = None
        self.dragging_image = None
        self.drag_offset = (0, 0)

        self._img_items = {}
        self._cid_to_key = {}
        self._img_handles = []
        self._img_selected = None
        self._img_drag = {"mode": None, "start": (0, 0), "orig_bbox": None, "handle": None}

        self.start_x = None
        self.start_y = None
        self._pen_points = []

        self.canvas.bind("<Button-1>", self._pointer_press)
        self.canvas.bind("<B1-Motion>", self._pointer_drag)
        self.canvas.bind("<ButtonRelease-1>", self._pointer_release)

        self.bind("<Control-v>", self.paste_from_clipboard)
        self.bind_all("<Delete>", self.delete_selected_image)
        # Phím tắt hiển thị cửa sổ
        self.bind('<F11>', lambda e: self.toggle_fullscreen())  # Toàn màn hình
        self.bind('<Escape>', lambda e: self.attributes('-fullscreen', False))  # Thoát fullscreen
        self.bind('<Alt-Return>', lambda e: self.toggle_max_restore())  # Phóng to / Khôi phục

        # Khi cửa sổ thay đổi vị trí/kích thước (kéo sang màn hình khác) → tự maximize lại nếu cần
        self.bind('<Configure>', self._ensure_maximized_after_move)
        self.bind_all("<Control-m>", lambda e: self._choose_custom_color())

        self.canvas.bind("<Configure>", self._on_canvas_resize)

        self._ensure_ink_layer()
        self.after(0, self._refresh_ink_layer)
        # === Quản lý đa trang ===
        self.pages = []  # Mỗi phần tử: {"drawn_items": [...], "images": {...}}
        self.current_page = 0

        # Tạo trang đầu tiên và chuyển các state hiện tại vào đó
        self._init_pages_model()
        self._init_pages_toolbar()  # nút Trang trước / Trang sau / Thêm / Xoá
        self._update_page_indicator()
        # thư mục chứa file board của buổi học
        if board_path:
            try:
                self.load_from_file(board_path)
                self._current_board_path = board_path
            except Exception as e:
                messagebox.showerror("Bảng vẽ", f"Không thể mở file bảng vẽ:\n{e}")
    # Đóng cửa sổ, huỷ tất cả tác vụ after
    def destroy(self):
        """Đóng cửa sổ bảng vẽ an toàn."""
        try:
            self._cancel_all_afters()
        except Exception:
            pass
        try:
            # Nếu bạn có tài nguyên khác cần giải phóng thì xử lý tại đây
            # ví dụ: self._ink_img = None, etc.
            pass
        except Exception:
            pass
        super().destroy()

    # Bật/tắt chế độ toàn màn hình
    def toggle_fullscreen(self):
        """Bật/tắt toàn màn hình (ẩn viền, không còn nút min/max)."""
        try:
            is_full = bool(self.attributes('-fullscreen'))
            self.attributes('-fullscreen', not is_full)
        except Exception:
            pass

    # Chuyển giữa chế độ phóng to và kích thước trước đó
    def toggle_max_restore(self):
        """Chuyển nhanh giữa maximize và normal (không phải fullscreen)."""
        try:
            if self.state() == 'zoomed':
                self.state('normal')
            else:
                self.state('zoomed')
        except Exception:
            # Nếu WM không hỗ trợ 'zoomed' thì dùng fullscreen như phương án B
            self.toggle_fullscreen()

    # Đảm bảo cửa sổ giữ trạng thái phóng to sau khi di chuyển
    def _ensure_maximized_after_move(self, event=None):
        """
        Khi cửa sổ vừa được kéo sang màn hình khác, nếu nó không còn ở trạng thái
        'zoomed' và kích thước < 90% màn hình hiện tại → tự maximize lại.
        """
        try:
            if bool(self.attributes('-fullscreen')):
                return  # đang fullscreen thì bỏ qua
        except Exception:
            pass

        try:
            if self.state() != 'zoomed':
                sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
                w, h = self.winfo_width(), self.winfo_height()
                if w < int(sw * 0.9) or h < int(sh * 0.9):
                    self.state('zoomed')
        except Exception:
            pass

    # 2) UI CONSTRUCTION/Xây dựng UI
    # 2.1 Toolbar & Pages toolbar
    # Tạo thanh công cụ chính với nút, màu, chọn công cụ
    def _build_toolbar(self):
        """
        Toolbar có thể CUỘN NGANG:
        - Dùng Canvas + Scrollbar để chứa 1 frame bên trong (self._toolbar_inner)
        - Khi không đủ chỗ, hiện thanh cuộn ngang để xem hết các nút.
        - Lưu tham chiếu self._toolbar_inner để các hàm khác (như _init_pages_toolbar) thêm nút vào đúng chỗ.
        """
        # Khung chứa toolbar ở trên cùng
        container = ttk.Frame(self)
        container.pack(side=tk.TOP, fill=tk.X)

        # Canvas để cuộn ngang
        self._toolbar_canvas = tk.Canvas(container, height=40, highlightthickness=0)
        self._toolbar_canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Thanh cuộn ngang
        hbar = ttk.Scrollbar(container, orient="horizontal", command=self._toolbar_canvas.xview)
        hbar.pack(side=tk.BOTTOM, fill=tk.X)
        self._toolbar_canvas.configure(xscrollcommand=hbar.set)

        # Frame thật để đặt các nút
        self._toolbar_inner = ttk.Frame(self._toolbar_canvas)
        self._toolbar_window_id = self._toolbar_canvas.create_window(
            (0, 0), window=self._toolbar_inner, anchor="nw"
        )

        # Cập nhật scrollregion theo kích thước nội dung
        def _sync_scrollregion(event=None):
            self._toolbar_canvas.configure(scrollregion=self._toolbar_canvas.bbox("all"))

        # Giữ cho width của cửa sổ con = width canvas (để không bị cắt)
        def _sync_inner_width(event):
            # luôn bám theo chiều rộng canvas; nếu nút quá dài sẽ bật scrollbar
            canvas_w = event.width
            self._toolbar_canvas.itemconfigure(self._toolbar_window_id, width=canvas_w)
            _sync_scrollregion()

        self._toolbar_inner.bind("<Configure>", _sync_scrollregion)
        self._toolbar_canvas.bind("<Configure>", _sync_inner_width)

        # ====== Tạo các nút giống phiên bản cũ, nhưng gắn vào self._toolbar_inner ======
        bar = self._toolbar_inner  # dùng biến 'bar' như trước để tái sử dụng code cũ

        def add_btn(text, cmd):
            b = ttk.Button(bar, text=text, command=cmd)
            b.pack(side=tk.LEFT, padx=4)
            return b

        # --- Pen (Menubutton) ---
        self.pen_btn = tk.Menubutton(bar, text="✏️ Pen ▾", relief="raised", borderwidth=1)
        self.pen_btn.pack(side=tk.LEFT, padx=4)
        self.pen_menu = tk.Menu(self.pen_btn, tearoff=0)
        self.pen_btn.configure(menu=self.pen_menu)
        self.pen_btn.bind("<Button-1>", lambda e: self._set_tool("pen"))

        colors_sub = tk.Menu(self.pen_menu, tearoff=0)
        for name, col in [("Đen", "#000000"), ("Đỏ", "#e53935"), ("Xanh", "#1e88e5"),
                          ("Lục", "#43a047"), ("Cam", "#fb8c00"), ("Tím", "#8e24aa")]:
            colors_sub.add_command(label=name, command=lambda c=col: self._set_pen_color(c))
        colors_sub.add_separator()
        colors_sub.add_command(label="Chọn màu…", command=self._choose_custom_color)

        self.pen_menu.add_cascade(label="🎨 Màu", menu=colors_sub)
        # Biến trạng thái kích thước tẩy (slider sẽ dùng biến này)
        self.eraser_width_var = tk.IntVar(value=self.eraser_width)

        # Nút chọn công cụ tẩy (không có menu)
        self.eraser_btn = ttk.Button(bar, text="🧽 Eraser", command=lambda: self._set_tool("eraser"))
        self.eraser_btn.pack(side=tk.LEFT, padx=4)

        # Thanh trượt chỉnh kích thước tẩy
        ttk.Label(bar, text="Độ dày").pack(side=tk.LEFT, padx=(6, 2))
        self._eraser_scale = ttk.Scale(
            bar, from_=1, to=100, orient="horizontal",
            command=lambda v: self._set_eraser_from_scale(v), length=160
        )
        self._eraser_scale.set(self.eraser_width_var.get())
        self._eraser_scale.pack(side=tk.LEFT, padx=(2, 6))

        # Phím tắt: '-' giảm, '=' tăng
        self.bind_all("<KeyPress-minus>", lambda e: self._adjust_eraser_width(-3))
        self.bind_all("<KeyPress-equal>", lambda e: self._adjust_eraser_width(+3))
        # --- Shapes ---
        self.shape_btn = tk.Menubutton(bar, text="🧩 HÌNH VẼ ▾", relief="raised", borderwidth=1)
        self.shape_btn.pack(side=tk.LEFT, padx=4)
        self.shape_menu = tk.Menu(self.shape_btn, tearoff=0)
        self.shape_menu.add_radiobutton(label="📏 Line", value="line", command=lambda: self._set_tool("line"))
        self.shape_menu.add_radiobutton(label="▭ Rect", value="rect", command=lambda: self._set_tool("rect"))
        self.shape_menu.add_radiobutton(label="◯ Oval", value="oval", command=lambda: self._set_tool("oval"))
        self.shape_btn.configure(menu=self.shape_menu)

        add_btn("🖱️ Select", lambda: self._set_tool("select"))
        add_btn("🗑️ Xoá Ảnh", self.delete_selected_image)

        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        # Chọn màu & preview
        ttk.Button(bar, text="🎨 Màu bút...", command=self._choose_custom_color).pack(side=tk.LEFT, padx=4)
        self._color_preview = tk.Canvas(bar, width=24, height=16, bg=self.draw_color,
                                        highlightthickness=1, highlightbackground="#888")
        self._color_preview.pack(side=tk.LEFT, padx=(0, 6))
        self._color_preview.bind("<Button-1>", lambda e: self._choose_custom_color())

        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        # Lưu/Chèn ảnh
        add_btn("💾 Lưu vào Bài giảng", self.save_to_lesson)
        add_btn("📂 Chèn Ảnh.", self.insert_image_from_file)

        self._set_tool("pen")

    # Khởi tạo dữ liệu các trang trắng ban đầu.
    def _init_pages_model(self):
        """Khởi tạo dữ liệu trang đầu tiên, gắn state hiện tại vào page[0]."""
        # Nếu trước đó bạn đã khởi tạo _img_items/_cid_to_key ở __init__, vẫn OK.
        # Ta gắn chúng vào model của page để mỗi trang có kho ảnh riêng.
        self._img_items = getattr(self, "_img_items", {})
        self._cid_to_key = getattr(self, "_cid_to_key", {})

        first_page = {
            "drawn_items": self.drawn_items,  # đang dùng list này rồi -> dùng trực tiếp
            "images": self._img_items,  # dict ảnh hiện tại
        }
        self.pages.append(first_page)
        self.current_page = 0
    # 2.2 Canvas
    # Khởi tạo vùng vẽ (canvas), gán sự kiện chuột/phím
    def _build_canvas(self):
        self.canvas = tk.Canvas(self, bg=self.bg_color, highlightthickness=0)
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.canvas._image_refs = {}
    # 2.3 Schedulers / after
    # Đặt một tác vụ chạy sau một khoảng thời gian
    def _schedule_after(self, key, ms, fn):
        old_id = self._afters.get(key)
        if old_id:
            self.after_cancel(old_id)
        self._afters[key] = self.after(ms, fn)

    # Huỷ tất cả tác vụ after đang chờ
    def _cancel_all_afters(self):
        """Hủy tất cả after callbacks nếu có."""
        try:
            if not hasattr(self, "_afters") or not self._afters:
                return
            for aid in list(self._afters.values()):
                try:
                    self.after_cancel(aid)
                except Exception:
                    pass
            self._afters.clear()
        except Exception:
            pass

    # 3) STATE & PAGE MANAGEMENT– Quản lý trang (Pages)
    # Tạo thanh điều hướng trang (trước, sau, thêm, xóa)
    def _init_pages_toolbar(self):
        """Thêm cụm nút điều hướng TRANG vào đúng thanh công cụ cuộn."""
        # Thanh công cụ thật đã được lưu ở self._toolbar_inner trong _build_toolbar
        bar = getattr(self, "_toolbar_inner", None)
        if bar is None or not bar.winfo_exists():
            return  # phòng hờ trường hợp toolbar chưa khởi tạo

        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        ttk.Button(bar, text="◀ Trang trước", command=self.prev_page).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="Trang sau ▶", command=self.next_page).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="➕ Thêm trang", command=self.add_page).pack(side=tk.LEFT, padx=6)
        ttk.Button(bar, text="🗑 Xoá trang", command=self.delete_page).pack(side=tk.LEFT, padx=2)

        # Nhãn hiển thị số trang
        self._page_label_var = tk.StringVar(value="Trang 1/1")
        ttk.Label(bar, textvariable=self._page_label_var).pack(side=tk.LEFT, padx=10)

    # Lưu trạng thái hiện tại của trang (nét vẽ + ảnh)
    def _snapshot_current_page(self):
        """Ghi lại state hiện tại vào self.pages[self.current_page]."""
        from copy import deepcopy
        p = self.pages[self.current_page]

        # Sao chép 'vector' nét vẽ (list tuple dict)
        p["drawn_items"] = deepcopy(self.drawn_items)

        # Sao chép metadata ảnh (PIL + tọa độ). Không cần giữ cid canvas.
        images_copy = {}
        for k, meta in self._img_items.items():
            images_copy[k] = {
                "pil": meta["pil"].copy(),
                "w": meta["w"], "h": meta["h"],
                "x": meta["x"], "y": meta["y"],
                "cid": None,  # sẽ tạo lại khi load
            }
        p["images"] = images_copy

    # Tải dữ liệu một trang vào giao diện để hiển thị
    def _load_page(self, index):
        """Nạp trang index -> thay state và redraw lên canvas."""
        if index < 0 or index >= len(self.pages):
            return
        self.current_page = index

        # Gắn state của trang
        p = self.pages[index]
        self.drawn_items = p["drawn_items"]
        self._img_items = p["images"]
        self._cid_to_key = {}

        # Xoá hết items rồi dựng lại
        self.canvas.delete("all")
        self._ink_item_id = None

        self._ensure_ink_layer()
        # Xoá sạch mực cũ
        self._ink_img.paste((0, 0, 0, 0), (0, 0, *self._ink_img.size))

        # Vẽ lại các nét
        for item_type, data in self.drawn_items:
            if item_type == "line":
                if "rgba" in data:
                    self._draw_line_points_rgba(data["points"], tuple(data["rgba"]), data.get("width", 3))
                else:
                    self._draw_line_points(data["points"], color=data.get("color"), width=data.get("width", 3))
            elif item_type == "rect":
                self._draw_rect(data, commit=True)
            elif item_type == "oval":
                self._draw_oval(data, commit=True)

        # Vẽ lại ảnh -> tạo tk image + cid, rồi HẠ ẢNH XUỐNG & NÂNG INK LÊN
        from PIL import ImageTk
        for key, meta in self._img_items.items():
            try:
                tk_img = ImageTk.PhotoImage(meta["pil"], master=self.canvas)
                cid = self.canvas.create_image(meta["x"], meta["y"], anchor="nw", image=tk_img)
                # lưu tham chiếu & map
                if not hasattr(self.canvas, "_image_refs"):
                    self.canvas._image_refs = {}
                self.canvas._image_refs[cid] = tk_img
                meta["cid"] = cid
                self._cid_to_key[cid] = key

                # 🔽 đảm bảo ảnh nằm dưới lớp mực
                self._ensure_image_below_ink(cid)
            except Exception:
                pass

        self._refresh_ink_layer()
        self._update_page_indicator()
        self.selected_image_id = None

    # Thêm một trang mới trắng
    def add_page(self):
        """Thêm trang mới (trống) và chuyển tới."""
        self._snapshot_current_page()
        new_page = {"drawn_items": [], "images": {}}
        self.pages.append(new_page)
        self._load_page(len(self.pages) - 1)

    # Xóa trang hiện tại
    def delete_page(self):
        """Xoá trang hiện tại. Luôn giữ lại ≥ 1 trang."""
        if len(self.pages) == 1:
            messagebox.showinfo("Trang", "Phải còn ít nhất 1 trang.")
            return
        # Xoá trang hiện tại
        del self.pages[self.current_page]
        # Chuyển tới trang trước (nếu xoá trang cuối thì cũng OK)
        self._load_page(max(0, self.current_page - 1))

    # Chuyển sang trang tiếp theo
    def next_page(self):
        self._snapshot_current_page()
        idx = self.current_page + 1
        if idx >= len(self.pages):
            return
        self._load_page(idx)

    # Quay lại trang trước đó
    def prev_page(self):
        self._snapshot_current_page()
        idx = self.current_page - 1
        if idx < 0:
            return
        self._load_page(idx)

    # Cập nhật số thứ tự trang đang xem
    def _update_page_indicator(self):
        self._page_label_var.set(f"Trang {self.current_page + 1}/{max(1, len(self.pages))}")

    # 4) INK LAYER (CORE RENDER)– Lớp mực (Ink Layer)
    # Đảm bảo có lớp mực RGBA, tạo mới nếu chưa có
    def _ensure_ink_layer(self):
        """Tạo/làm mới layer mực (RGBA) và đảm bảo nó luôn nằm trên cùng."""
        import PIL.Image as PILImage
        from PIL import ImageTk

        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())

        # Tạo ảnh RGBA trong suốt để chứa nét vẽ
        recreate_draw = False
        if self._ink_img is None or self._ink_img.size != (cw * self.INK_SCALE, ch * self.INK_SCALE):
            # Khi kích thước canvas thay đổi, tạo lại ảnh mực
            self._ink_img = PILImage.new(
                "RGBA", (cw * self.INK_SCALE, ch * self.INK_SCALE), (0, 0, 0, 0)
            )
            recreate_draw = True

            # Luôn đảm bảo _ink_draw tham chiếu đúng tới _ink_img hiện tại
        if (
                recreate_draw
                or self._ink_draw is None
                or getattr(getattr(self._ink_draw, "im", None), "mode", None) is None
                or getattr(self._ink_draw, "im", None) is not getattr(self._ink_img, "im", None)
        ):
            from PIL import ImageDraw
            self._ink_draw = ImageDraw.Draw(self._ink_img, "RGBA")

        # Render xuống ảnh Tk và gắn lên canvas
        downsample = self._ink_img.resize((cw, ch), resample=0)  # NEAREST để giữ alpha mịn đã tính sẵn
        self._ink_tk = ImageTk.PhotoImage(downsample, master=self.canvas)

        if self._ink_item_id is None or not self.canvas.type(self._ink_item_id):
            # Tạo item ảnh cho layer mực và đặt tag 'ink'
            self._ink_item_id = self.canvas.create_image(0, 0, anchor="nw", image=self._ink_tk, tags=("ink",))
        else:
            self.canvas.itemconfigure(self._ink_item_id, image=self._ink_tk)

        # 🔼 Quan trọng: đảm bảo layer mực luôn ở trên cùng
        try:
            self.canvas.tag_raise(self._ink_item_id)
            self.canvas.tag_raise("ink")
        except Exception:
            pass
    # Cập nhật hiển thị lớp mực trên canvas
    def _refresh_ink_layer(self):
        if not self.winfo_exists():
            return
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w <= 1 or h <= 1:
            self.after(16, self._refresh_ink_layer)
            return

        # Thu nhỏ theo premultiplied-alpha để nét mịn
        view = self._resize_rgba_premultiplied(self._ink_img, (w, h))

        from PIL import ImageTk
        self._ink_tk = ImageTk.PhotoImage(view, master=self.canvas)
        if self._ink_item_id is None:
            self._ink_item_id = self.canvas.create_image(
                0, 0, anchor="nw", image=self._ink_tk, tags=("ink",)
            )
        else:
            self.canvas.itemconfig(self._ink_item_id, image=self._ink_tk)

        # 🔼 ĐẢM BẢO LAYER MỰC Ở TRÊN CÙNG
        try:
            self.canvas.tag_raise(self._ink_item_id)
            self.canvas.tag_raise("ink")
        except Exception:
            pass

    # Thu nhỏ ảnh RGBA với premultiplied alpha cho mượt
    def _resize_rgba_premultiplied(self, img_rgba, size):
        """
        Thu nhỏ RGBA theo kiểu premultiplied alpha để tránh viền mờ ở rìa nét.
        """
        if img_rgba.mode != "RGBA":
            img_rgba = img_rgba.convert("RGBA")
        r, g, b, a = img_rgba.split()
        # Tiền nhân alpha
        r = ImageChops.multiply(r, a)
        g = ImageChops.multiply(g, a)
        b = ImageChops.multiply(b, a)
        # Thu nhỏ các kênh
        new_r = r.resize(size, Image.LANCZOS)
        new_g = g.resize(size, Image.LANCZOS)
        new_b = b.resize(size, Image.LANCZOS)
        new_a = a.resize(size, Image.LANCZOS)

        # Khôi phục từ premultiplied
        # Tránh chia 0 bằng cách cộng 1 vào alpha khi tính lại RGB
        def unpremul(c, alpha):
            # c' = round(255 * c / max(alpha,1))
            import numpy as np
            ca = np.array(c, dtype=np.uint16)
            aa = np.array(alpha, dtype=np.uint16)
            aa = np.maximum(aa, 1)
            out = (ca * 255 + (aa // 2)) // aa
            return Image.fromarray(out.astype('uint8'), mode="L")

        try:
            import numpy as np  # sẽ có sẵn trong môi trường runtime của bạn
            new_r = unpremul(new_r, new_a)
            new_g = unpremul(new_g, new_a)
            new_b = unpremul(new_b, new_a)
        except Exception:
            # Trường hợp không có numpy: vẫn ghép lại trực tiếp (có thể kém mượt hơn chút)
            pass

        return Image.merge("RGBA", (new_r, new_g, new_b, new_a))

    # Đảm bảo ảnh nằm dưới lớp mực
    def _ensure_image_below_ink(self, cid: int):
        """Hạ ảnh canvas item `cid` xuống dưới lớp mực, rồi nâng lớp mực lên."""
        try:
            self.canvas.tag_lower(cid)  # ảnh nằm dưới
            if self._ink_item_id:
                self.canvas.tag_raise(self._ink_item_id)
            self.canvas.tag_raise("ink")
        except Exception:
            pass

    # Vẽ lại toàn bộ nét + ảnh từ dữ liệu trang
    def _rebuild_and_redraw(self):
        self.canvas.delete("all")
        self._ink_item_id = None
        self._ensure_ink_layer()
        # xóa sạch ink
        self._ink_img.paste((0, 0, 0, 0), (0, 0, *self._ink_img.size))

        for item_type, data in self.drawn_items:
            if item_type == "line":
                rgba = tuple(data.get("rgba", (0, 0, 0, 255)))
                if data.get("mode") == "eraser" or (len(rgba) >= 4 and int(rgba[3]) == 0):
                    self._erase_line_points(data["points"], data.get("width", 3))
                else:
                    self._draw_line_points_rgba(data["points"], rgba, data.get("width", 3))
            elif item_type == "rect":
                self._draw_rect(data, commit=True)
            elif item_type == "oval":
                self._draw_oval(data, commit=True)

        self._refresh_ink_layer()
        self._redraw_images_layer()

    # Sự kiện khi canvas thay đổi kích thước (gọi redraw)
    def _on_canvas_resize(self, event):
        self._schedule_after("__resize__", 16, self._rebuild_and_redraw)

    # 5) INPUT HANDLERS (POINTER/KEYS)– Xử lý sự kiện chuột & phím
    # Xử lý nhấn chuột xuống
    def _pointer_press(self, event):
        self.on_press(event)

    # Xử lý kéo chuột
    def _pointer_drag(self, event):
        self.on_drag(event)

    # Xử lý thả chuột
    def _pointer_release(self, event):
        self.on_release(event)

    # Hành động khi bắt đầu vẽ/chọn
    def on_press(self, event):
        self.start_x, self.start_y = event.x, event.y
        self.canvas.delete("preview")

        if self.current_tool == "select":
            if self._try_select_image(event.x, event.y):
                self.dragging_image = self.selected_image_id
                bbox = self.canvas.bbox(self.dragging_image)
                self.drag_offset = (event.x - bbox[0], event.y - bbox[1])
        elif self.current_tool in ("pen", "eraser"):
            self._pen_points = [(event.x, event.y)]

    # Hành động khi đang vẽ/kéo ảnh
    def on_drag(self, event):
        if self.start_x is None or self.start_y is None:
            return

        if self.current_tool == "select" and self.dragging_image:
            x, y = event.x - self.drag_offset[0], event.y - self.drag_offset[1]
            self.canvas.coords(self.dragging_image, x, y)
            return

        is_pen = self.current_tool == "pen"
        is_eraser = self.current_tool == "eraser"
        cur_w = (self._get_pen_width() if is_pen else self._get_eraser_width())
        color = self.draw_color if is_pen else self.bg_color

        self.canvas.delete("preview")

        if is_pen or is_eraser:
            # ✨ FIX: Vẽ toàn bộ nét bút để có preview mượt mà, liền mạch
            self._pen_points.append((event.x, event.y))
            if len(self._pen_points) > 1:
                self.canvas.create_line(
                    self._pen_points,
                    fill=color,
                    width=cur_w,
                    tags=("preview",),
                    **self.canvas_line_opts
                )
        elif self.current_tool == "line":
            self.canvas.create_line(self.start_x, self.start_y, event.x, event.y,
                                    fill=self.draw_color, tags=("preview",))
        elif self.current_tool == "rect":
            self.canvas.create_rectangle(self.start_x, self.start_y, event.x, event.y,
                                         outline=self.draw_color, tags=("preview",))
        elif self.current_tool == "oval":
            self.canvas.create_oval(self.start_x, self.start_y, event.x, event.y,
                                    outline=self.draw_color, tags=("preview",))

        self.canvas.tag_raise("preview")

    # Hành động khi kết thúc vẽ/kéo
    def on_release(self, event):
        self.canvas.delete("preview")
        if self.start_x is None: return

        if self.current_tool == "select":
            if self.dragging_image:
                key = self._cid_to_key.get(self.dragging_image)
                if key and key in self._img_items:
                    x, y = self.canvas.coords(self.dragging_image)
                    self._img_items[key]['x'] = int(x)
                    self._img_items[key]['y'] = int(y)
            self.dragging_image = None
            return

        if self.current_tool in ("pen", "eraser"):
            self.on_pen_up(event)
        else:  # Shapes
            cur_w = 3
            data = {"color": self.draw_color, "width": cur_w}
            if self.current_tool == "line":
                pts = [(self.start_x, self.start_y), (event.x, event.y)]
                self._draw_line_points(pts, **data)
                self.drawn_items.append(("line", {"points": pts, **data}))
            else:
                shape_data = {"x1": self.start_x, "y1": self.start_y, "x2": event.x, "y2": event.y, **data}
                if self.current_tool == "rect":
                    self._draw_rect(shape_data, commit=True)
                    self.drawn_items.append(("rect", shape_data))
                elif self.current_tool == "oval":
                    self._draw_oval(shape_data, commit=True)
                    self.drawn_items.append(("oval", shape_data))
            self._refresh_ink_layer()

        self.start_x = self.start_y = None

    # 6) PEN / ERASER (STROKES)– Bút & Tẩy
    # Chuyển mã màu hex thành tuple RGBA
    def _hex_to_rgba(self, color_hex: str, alpha: int = 255):
        try:
            r, g, b = self.winfo_rgb(color_hex)
            return (r // 256, g // 256, b // 256, alpha)
        except tk.TclError:
            # fallback: đen đục
            return (0, 0, 0, alpha)

    # Chọn công cụ hiện tại (bút, tẩy, hình học)
    def _set_tool(self, tool):
        self.current_tool = tool
        # Cập nhật giao diện (ví dụ: làm nổi nút đang chọn) có thể thêm ở đây

    # Đặt màu cho bút vẽ
    def _set_pen_color(self, color_hex: str):
        """Đặt màu bút và cập nhật ô xem trước nếu có."""
        self.draw_color = color_hex
        try:
            if hasattr(self, "_color_preview") and self._color_preview.winfo_exists():
                self._color_preview.configure(bg=self.draw_color)
        except tk.TclError:
            pass
        self._set_tool("pen")

    # Mở hộp thoại chọn màu tùy chỉnh
    def _choose_custom_color(self):
        """
        Mở hộp thoại chọn màu làm *con* của Bảng vẽ để không làm cửa sổ khác bật lên.
        Sau khi chọn xong, đưa Bảng vẽ trở lại phía trước.
        """
        # Tạm thời đưa Bảng vẽ lên trên để hộp thoại xuất hiện đúng chỗ
        try:
            self.attributes("-topmost", True)
        except Exception:
            pass

        try:
            # Gắn parent=self để hộp thoại modal theo Bảng vẽ
            color = colorchooser.askcolor(
                initialcolor=self.draw_color,
                title="Chọn màu bút",
                parent=self
            )
        finally:
            # Trả lại trạng thái topmost
            try:
                self.attributes("-topmost", False)
            except Exception:
                pass

        # Cập nhật màu nếu người dùng bấm OK
        if color and color[1]:
            self._set_pen_color(color[1])

        # Đảm bảo Bảng vẽ được focus và nằm lên trên
        try:
            self.lift()
            self.focus_force()
        except Exception:
            pass

    # Cập nhật độ rộng tẩy khi người dùng chỉnh
    def _on_eraser_width_change(self):
        """Cập nhật khi đổi kích thước tẩy từ menu."""
        try:
            w = int(self.eraser_width_var.get())
        except (tk.TclError, ValueError):
            w = 25
        self.eraser_width = w
        self.pen_width = w

    # Thay đổi độ rộng tẩy từ thanh trượt
    def _set_eraser_from_scale(self, v):
        self.eraser_width_var.set(int(float(v)))
        self._on_eraser_width_change()

    # Tăng/giảm độ rộng tẩy bằng phím tắt
    def _adjust_eraser_width(self, delta):
        new_w = max(2, min(120, self._get_eraser_width() + int(delta)))
        self.eraser_width_var.set(new_w)
        self._on_eraser_width_change()

    # Lấy độ rộng tẩy hiện tại
    def _get_eraser_width(self):
        """Lấy kích thước tẩy hiện hành từ biến trạng thái, fallback về self.eraser_width."""
        try:
            return int(self.eraser_width_var.get())
        except Exception:
            return int(getattr(self, "eraser_width", 25))
    # Lấy độ rộng pen hiện tại
    def _get_pen_width(self):
        """Độ dày nét bút (dùng chung thanh trượt với eraser)."""
        try:
            return int(self.eraser_width_var.get())
        except Exception:
            return int(getattr(self, "pen_width", 3))

    # Kết thúc một stroke bút, lưu vào dữ liệu trang
    def on_pen_up(self, event):
        if not self._pen_points:
            return

        # đảm bảo điểm cuối
        if self._pen_points[-1] != (event.x, event.y):
            self._pen_points.append((event.x, event.y))

        if len(self._pen_points) > 1:
            if self.current_tool == "eraser":
                width = self.eraser_width
                self._erase_line_points(self._pen_points, width)
                self._refresh_ink_layer()
                # Đảm bảo tất cả ảnh xuống dưới mực
                for meta in self._img_items.values():
                    if meta.get("cid"):
                        self._ensure_image_below_ink(meta["cid"])

                self._commit_stroke(self._pen_points, (0, 0, 0, 0), width, mode="eraser")
            else:
                # pen / highlighter
                # luôn là bút thường (không còn highlighter)
                alpha = 255
                rgba = self._hex_to_rgba(self.draw_color, alpha=alpha)
                width = self._get_pen_width()
                self._draw_line_points_rgba(self._pen_points, rgba, width)
                self._refresh_ink_layer()
                self._commit_stroke(self._pen_points, rgba, width, mode="pen")

        self._pen_points = []
        self.canvas.delete("preview")

    # Ghi nét bút vào layer mực
    def _commit_stroke(self, points, rgba, width, mode):
        # Lưu đúng dữ liệu để redraw bền vững
        self.drawn_items.append((
            "line",
            {
                "points": [(float(x), float(y)) for (x, y) in points],
                "rgba": tuple(int(v) for v in rgba),  # (r,g,b,a)
                "width": int(width),
                "mode": mode  # "pen" | "eraser"
            }
        ))

    # Vẽ đường (RGBA) trực tiếp vào ảnh mực
    def _draw_line_points_rgba(self, points, rgba, width):
        """
        Vẽ line trực tiếp lên ink layer bằng RGBA đã biết.
        Nếu alpha == 0 => coi là tẩy (xóa thật sự bằng mask), không vẽ màu trong suốt.
        """
        if not points or len(points) < 2:
            return

        # Nếu là "tẩy": alpha = 0
        if rgba is not None and len(rgba) >= 4 and int(rgba[3]) == 0:
            self._erase_line_points(points, width)
            return

        self._ensure_ink_layer()
        s = self.INK_SCALE
        scaled = [(int(x * s), int(y * s)) for (x, y) in points]
        self._ink_draw.line(
            scaled,
            fill=tuple(int(v) for v in rgba),
            width=max(1, int(width * s))
        )

    # Xóa mực theo đường đi của tẩy
    def _erase_line_points(self, points, width):
        """
        Xoá sạch (clear alpha) dọc theo polyline `points` với độ dày `width`.
        - Vẽ line mask dày hơn một chút so với nét gốc (expand)
        - Quét cọ tròn tại từng điểm để không bị hở khi rê nhanh
        - Dãn (dilate) mask 1 bước để ăn trọn viền anti‑alias
        """
        if not points or len(points) < 2:
            return

        self._ensure_ink_layer()
        s = self.INK_SCALE

        # 1) Tạo mask đơn kênh: 0 = giữ, 255 = xóa
        mask = Image.new("L", self._ink_img.size, 0)
        mdraw = ImageDraw.Draw(mask)

        # 2) Nới rộng một chút so với bề rộng tẩy gốc
        expand = int(2 * s)  # thêm ~2px ở không gian gốc
        brush_w = max(1, int(width * s) + expand)  # bề rộng nét trên mask
        radius = brush_w // 2 + 1

        scaled = [(int(x * s), int(y * s)) for (x, y) in points]

        # 3) Vẽ polyline mask
        mdraw.line(scaled, fill=255, width=brush_w)

        # 4) Quét cọ tròn tại mọi điểm để bịt khe hở giữa các mẫu di chuyển
        for x, y in scaled:
            mdraw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=255)

        # 5) Dãn mask thêm 1 bước để phủ hết phần anti‑alias ở rìa
        try:
            from PIL import ImageFilter
            # Kích thước nhân lọc phải là số lẻ
            k = max(3, (int(0.75 * s) // 2) * 2 + 1)
            mask = mask.filter(ImageFilter.MaxFilter(size=k))
        except Exception:
            pass  # Nếu thiếu ImageFilter vẫn xài được

        # 6) Thực hiện xoá: dán vùng trong suốt với mask
        self._ink_img.paste((0, 0, 0, 0), (0, 0), mask)
    # Vẽ đường xem trước trên canvas
    def _draw_line_points(self, points, color=None, width=3, rgba=None, mode=None):
        """
        Wrapper tương thích ngược:
        - Nếu có 'rgba' (dữ liệu mới) thì dùng trực tiếp.
        - Nếu không có 'rgba' thì chuyển 'color' hex -> RGBA (alpha=255).
        - 'mode' chỉ là metadata (pen/highlighter/eraser) -> không ảnh hưởng khi vẽ lại.
        """
        if rgba is not None:
            fill_rgba = tuple(rgba)
        else:
            fill_rgba = self._hex_to_rgba(color or "#000000", alpha=255)

        self._draw_line_points_rgba(points, fill_rgba, width)

    # 7) SHAPES (LINE / RECT / OVAL COMMIT) – Hình học
    # Vẽ hình chữ nhật trên preview
    def _draw_rect(self, data, commit=False):
        x1, y1, x2, y2 = data["x1"], data["y1"], data["x2"], data["y2"]
        color, w = data["color"], data["width"]
        if commit:
            self._ensure_ink_layer()
            s = self.INK_SCALE
            self._ink_draw.rectangle(
                [int(x1 * s), int(y1 * s), int(x2 * s), int(y2 * s)],
                outline=color, width=max(1, int(w * s))
            )

    # Vẽ hình oval (ellipse) trên preview
    def _draw_oval(self, data, commit=False):
        x1, y1, x2, y2 = data["x1"], data["y1"], data["x2"], data["y2"]
        color, w = data["color"], data["width"]
        if commit:
            self._ensure_ink_layer()
            s = self.INK_SCALE
            self._ink_draw.ellipse(
                [int(x1 * s), int(y1 * s), int(x2 * s), int(y2 * s)],
                outline=color, width=max(1, int(w * s))
            )

    # 8) IMAGES LAYER (BMP)– Quản lý ảnh
    # Dán ảnh từ clipboard vào canvas
    def paste_from_clipboard(self, event=None):
        from PIL import ImageGrab, ImageTk
        try:
            grabbed = ImageGrab.grabclipboard()
        except Exception:
            grabbed = None

        if grabbed is None:
            from tkinter import messagebox
            messagebox.showinfo("Dán ảnh", "Clipboard không có ảnh.")
            return

        # Nếu clipboard trả về đường dẫn, mở ảnh; nếu là Image thì dùng trực tiếp
        if isinstance(grabbed, list) and grabbed and isinstance(grabbed[0], str):
            from PIL import Image
            pil = Image.open(grabbed[0]).convert("RGBA")
        else:
            pil = grabbed.convert("RGBA")

        x, y = 80, 80
        tk_img = ImageTk.PhotoImage(pil, master=self.canvas)
        cid = self.canvas.create_image(x, y, anchor="nw", image=tk_img)

        key = str(uuid.uuid4())
        self._img_items[key] = {"pil": pil, "w": pil.width, "h": pil.height, "x": x, "y": y, "cid": cid}
        self._cid_to_key[cid] = key
        if not hasattr(self.canvas, "_image_refs"):
            self.canvas._image_refs = {}
        self.canvas._image_refs[cid] = tk_img

        # 🔽 Ảnh xuống dưới, ink lên trên
        self._ensure_image_below_ink(cid)

    # Chèn ảnh từ file vào canvas
    def insert_image_from_file(self):
        from tkinter import filedialog, messagebox
        from PIL import Image, ImageTk

        path = filedialog.askopenfilename(
            title="Chọn ảnh",
            filetypes=[("Ảnh", "*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.gif"), ("Tất cả", "*.*")]
        )
        if not path:
            return

        try:
            pil = Image.open(path).convert("RGBA")
        except Exception as e:
            messagebox.showerror("Lỗi ảnh", f"Không mở được ảnh:\n{e}", parent=self)
            return

        # Vị trí mặc định
        x, y = 50, 50

        tk_img = ImageTk.PhotoImage(pil, master=self.canvas)
        cid = self.canvas.create_image(x, y, anchor="nw", image=tk_img)

        # Lưu meta
        key = str(uuid.uuid4())
        self._img_items[key] = {"pil": pil, "w": pil.width, "h": pil.height, "x": x, "y": y, "cid": cid}
        self._cid_to_key[cid] = key
        if not hasattr(self.canvas, "_image_refs"):
            self.canvas._image_refs = {}
        self.canvas._image_refs[cid] = tk_img

        # 🔽 Ảnh xuống dưới, ink lên trên
        self._ensure_image_below_ink(cid)

    # Thêm ảnh PIL vào trang, tạo object canvas
    def _insert_pil_image(self, pil_image: Image.Image, x=0, y=0):
        tk_img = ImageTk.PhotoImage(pil_image, master=self.canvas)
        cid = self.canvas.create_image(x, y, anchor="nw", image=tk_img)
        self.canvas._image_refs[cid] = tk_img

        image_key = str(uuid.uuid4())
        self._img_items[image_key] = {
            "pil": pil_image.copy(), "w": pil_image.width, "h": pil_image.height,
            "x": int(x), "y": int(y), "cid": cid
        }
        self._cid_to_key[cid] = image_key

        self.clear_selection()
        self.selected_image_id = cid

    # Kiểm tra xem click chuột có chọn ảnh nào không
    def _try_select_image(self, x, y):
        items = self.canvas.find_overlapping(x, y, x, y)
        target = None
        for it in reversed(items):
            if it in self._cid_to_key:
                target = it
                break
        self.clear_selection()
        self.selected_image_id = target
        return target

    # Bỏ chọn ảnh đang chọn
    def clear_selection(self):
        # Add visual deselection feedback if needed (e.g., remove outline)
        self.selected_image_id = None

    # Xóa ảnh đang chọn
    def delete_selected_image(self, event=None):
        if not self.selected_image_id: return
        key = self._cid_to_key.pop(self.selected_image_id, None)
        self.canvas.delete(self.selected_image_id)
        self.canvas._image_refs.pop(self.selected_image_id, None)
        if key: self._img_items.pop(key, None)
        self.clear_selection()

    # Vẽ lại tất cả ảnh của trang lên canvas
    def _redraw_images_layer(self):
        for key, meta in list(self._img_items.items()):
            pil, x, y, cid = meta["pil"], meta["x"], meta["y"], meta["cid"]
            try:
                self.canvas.coords(cid)  # check if item exists
                self.canvas.coords(cid, x, y)
            except tk.TclError:  # item deleted, recreate
                self.canvas._image_refs.pop(cid, None)
                tk_img = ImageTk.PhotoImage(pil, master=self.canvas)
                new_cid = self.canvas.create_image(x, y, anchor="nw", image=tk_img)
                self.canvas._image_refs[new_cid] = tk_img
                meta["cid"] = new_cid
                self._cid_to_key[new_cid] = key
                if self.selected_image_id == cid: self.selected_image_id = new_cid
                self._ensure_image_below_ink(new_cid)

    # 9) SERIALIZATION / SAVE– Lưu & Phục hồi
    # Chuyển toàn bộ dữ liệu bảng vẽ thành dict (để lưu JSON)
    def to_dict(self):
        self._snapshot_current_page()
        data = {"version": 1, "meta": {
            "group_name": self.group_name,
            "session_date": self.session_date,
            "saved_at": int(time.time()),
        },
                "pages": []}
        for p in self.pages:
            strokes = []
            for item_type, payload in p["drawn_items"]:
                if item_type == "line":
                    if "rgba" in payload:
                        strokes.append({"type": "line", "points": payload["points"],
                                        "rgba": tuple(payload["rgba"]), "width": payload.get("width", 3)})
                    else:
                        rgba = self._hex_to_rgba(payload.get("color", "#000000"), 255)
                        strokes.append({"type": "line", "points": payload["points"],
                                        "rgba": rgba, "width": payload.get("width", 3)})
                elif item_type in ("rect", "oval"):
                    d = dict(payload);
                    d["type"] = item_type
                    strokes.append(d)

            images = {}
            for key, meta in p["images"].items():
                buf = BytesIO()
                meta["pil"].save(buf, format="PNG")
                b64 = base64.b64encode(buf.getvalue()).decode("ascii")
                images[key] = {"png_b64": b64, "w": meta["w"], "h": meta["h"],
                               "x": meta["x"], "y": meta["y"]}
            data["pages"].append({"strokes": strokes, "images": images})
        return data

    # Nạp dữ liệu từ dict vào bảng vẽ
    def load_from_dict(self, data: dict):
        from copy import deepcopy
        self.pages = []
        for p in data.get("pages", []):
            drawn_items = []
            for s in p.get("strokes", []):
                t = s.get("type")
                if t == "line":
                    drawn_items.append(("line", {"points": s["points"], "rgba": tuple(s["rgba"]),
                                                 "width": s.get("width", 3)}))
                elif t in ("rect", "oval"):
                    d = deepcopy(s);
                    d.pop("type", None)
                    drawn_items.append((t, d))
            images = {}
            for key, meta in p.get("images", {}).items():
                img = Image.open(BytesIO(base64.b64decode(meta["png_b64"]))).convert("RGBA")
                images[key] = {"pil": img, "w": meta["w"], "h": meta["h"],
                               "x": meta["x"], "y": meta["y"], "cid": None}
            self.pages.append({"drawn_items": drawn_items, "images": images})
        self._load_page(0)

    # Nạp dữ liệu từ file JSON .board.json
    def load_from_file(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.load_from_dict(data)

    # Xuất trang hiện tại thành ảnh PNG
    def save_as_image(self):
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
        if not path: return

        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        out = Image.new("RGB", (w, h), self.bg_color)

        # Dán ảnh trước
        for meta in self._img_items.values():
            pil = meta["pil"].convert("RGBA")
            out.paste(pil, (meta['x'], meta['y']), pil)

        # Dán lớp mực lên trên
        if self._ink_img:
            ink_view = self._ink_img.resize((w, h), Image.LANCZOS)
            out.paste(ink_view, (0, 0), ink_view)

        try:
            out.save(path, "PNG")
            messagebox.showinfo("Lưu", f"Đã lưu bảng vẽ: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể lưu ảnh:\n{e}")

    # Lưu file bảng vẽ vào thư mục bài giảng
    def save_to_lesson(self):
        if not self.session_id:
            messagebox.showerror("Bảng vẽ", "Chưa có session_id. Hãy lưu buổi học trước.", parent=self)
            return
        os.makedirs(self._lesson_dir, exist_ok=True)
        payload = self.to_dict()
        if self._current_board_path:
            path = self._current_board_path
        else:
            # Lấy chủ đề từ ô nhập ở cửa sổ cha (SessionDetailWindow)
            topic = ""
            if hasattr(self.master, "topic_text"):
                topic = self.master.topic_text.get("1.0", "end").strip()
            topic_safe = topic.replace(" ", "_").replace("/", "-")[:50] or "no_topic"

            date_str = ""
            if self.session_date:
                try:
                    from datetime import datetime
                    date_obj = datetime.strptime(self.session_date, "%Y-%m-%d")
                    date_str = date_obj.strftime("%d-%m-%Y")
                except Exception:
                    date_str = self.session_date

            group_safe = (self.group_name or "no_group").replace(" ", "_")
            filename = f"{group_safe}_{date_str}_{topic_safe}.board.json"
            path = os.path.join(self._lesson_dir, filename)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)

        title = os.path.basename(path)
        try:
            if callable(getattr(self, "on_saved", None)):
                self.on_saved(path, title)
            messagebox.showinfo("Lưu bảng vẽ", f"Đã lưu vào Bài giảng:\n{title}", parent=self)
            self._current_board_path = path
        except Exception as e:
            messagebox.showwarning("Lưu bảng vẽ", f"Lưu file xong nhưng chưa gắn vào DB:\n{e}", parent=self)