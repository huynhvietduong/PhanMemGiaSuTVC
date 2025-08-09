
import tkinter as tk
from tkinter import ttk, messagebox

# Class này dùng để sửa bài tập đã có
class EditExerciseWindow(tk.Toplevel):
    def __init__(self, parent, db, ex_id, values, on_saved=None):
        super().__init__(parent)
        self.db = db
        self.ex_id = ex_id
        self.on_saved = on_saved
        self.title("✏️ Sửa bài tập")
        self.geometry("600x400")
        self.grab_set()

        chu_de, ten_bai, loai_tap, noi_dung, ghi_chu = values

        frm = ttk.Frame(self, padding=15)
        frm.pack(fill="both", expand=True)

        self.vars = {}
        for i, label in enumerate(["Chủ đề", "Tên bài", "Loại", "Nội dung", "Ghi chú"]):
            ttk.Label(frm, text=label + ":").grid(row=i, column=0, sticky="w")
            var = tk.StringVar(value=values[i])
            entry = ttk.Entry(frm, textvariable=var, width=50)
            entry.grid(row=i, column=1, pady=5)
            self.vars[label] = var

        ttk.Button(frm, text="💾 Lưu thay đổi", command=self.save).grid(row=5, column=0, columnspan=2, pady=15)

    def save(self):
        values = (
            self.vars["Chủ đề"].get().strip(),
            self.vars["Tên bài"].get().strip(),
            self.vars["Loại"].get().strip(),
            self.vars["Nội dung"].get().strip(),
            self.vars["Ghi chú"].get().strip()
        )
        if not all(values):
            messagebox.showwarning("Thiếu thông tin", "Vui lòng điền đầy đủ.", parent=self)
            return

        self.db.execute_query("""
            UPDATE exercises SET chu_de = ?, ten_bai = ?, loai_tap = ?, noi_dung = ?, ghi_chu = ?
            WHERE id = ?
        """, (*values, self.ex_id))

        messagebox.showinfo("Thành công", "Đã cập nhật bài tập.")
        if self.on_saved:
            self.on_saved()
        self.destroy()