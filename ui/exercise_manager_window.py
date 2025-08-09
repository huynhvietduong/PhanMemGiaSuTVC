import os
import tkinter as tk
import webbrowser
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

# Import cửa sổ sửa bài tập đã tách ở trên
from .edit_exercise_window import EditExerciseWindow
class ExerciseManagerWindow(tk.Toplevel):
    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self.title("🗂️ Quản lý bài tập")
        self.geometry("900x600")
        self.grab_set()

        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="Lọc theo chủ đề:").pack(side="left")
        self.filter_var = tk.StringVar()
        entry = ttk.Entry(top, textvariable=self.filter_var, width=30)
        entry.pack(side="left", padx=5)
        ttk.Button(top, text="Lọc", command=self.load_data).pack(side="left")

        self.tree = ttk.Treeview(self, columns=("Chủ đề", "Tên bài", "Loại", "Nội dung", "Ghi chú"), show="headings")
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=150)
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        # Popup menu chuột phải
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="✏️ Sửa bài tập", command=self.edit_selected)
        self.context_menu.add_command(label="🗑️ Xoá bài tập", command=self.delete_selected)
        self.context_menu.add_command(label="👁️ Xem bài tập", command=self.view_selected)
        self.load_data()

    def load_data(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        keyword = self.filter_var.get().strip()
        if keyword:
            query = "SELECT id, chu_de, ten_bai, loai_tap, noi_dung, ghi_chu FROM exercises WHERE chu_de LIKE ? ORDER BY chu_de"
            rows = self.db.execute_query(query, ('%' + keyword + '%',), fetch='all') or []
        else:
            rows = self.db.execute_query(
                "SELECT id, chu_de, ten_bai, loai_tap, noi_dung, ghi_chu FROM exercises ORDER BY chu_de",
                fetch='all') or []

        self.row_map = {}
        for row in rows:
            ex_id, *vals = row
            self.row_map[self.tree.insert("", "end", values=vals)] = ex_id

    def show_context_menu(self, event):
        try:
            row_id = self.tree.identify_row(event.y)
            if row_id:
                self.tree.selection_set(row_id)
                self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def edit_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        tree_id = sel[0]
        ex_id = self.row_map[tree_id]
        values = self.tree.item(tree_id, "values")
        EditExerciseWindow(self, self.db, ex_id, values, on_saved=self.load_data)

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        tree_id = sel[0]
        ex_id = self.row_map[tree_id]
        confirm = messagebox.askyesno("Xác nhận xoá", "Bạn có chắc chắn muốn xoá bài tập này?", parent=self)
        if confirm:
            self.db.execute_query("DELETE FROM exercises WHERE id = ?", (ex_id,))
            self.load_data()

    # Xem lại bài tập trong Quản lí bài tập
    def view_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        tree_id = sel[0]
        values = self.tree.item(tree_id, "values")
        chu_de, ten_bai, loai_tap, noi_dung, _ = values

        if loai_tap == "text":
            messagebox.showinfo(f"Bài: {ten_bai}", noi_dung, parent=self)

        elif loai_tap == "image":
            try:
                from PIL import Image, ImageTk
                img_win = tk.Toplevel(self)
                img_win.title(f"Bài tập: {ten_bai}")
                img = Image.open(noi_dung)
                img = img.resize((600, 400))
                photo = ImageTk.PhotoImage(img)
                label = ttk.Label(img_win, image=photo)
                label.image = photo
                label.pack()
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không mở được ảnh:\n{e}", parent=self)

        elif loai_tap in ["pdf", "word"]:
            try:
                os.startfile(noi_dung)
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể mở file:\n{e}", parent=self)

        elif loai_tap == "link":
            try:
                import webbrowser
                webbrowser.open(noi_dung)
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không mở được link:\n{e}", parent=self)
        else:
            messagebox.showinfo("Không hỗ trợ", f"Không hỗ trợ xem bài loại: {loai_tap}", parent=self)
