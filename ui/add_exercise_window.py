import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
class AddExerciseWindow(tk.Toplevel):
    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self.title("➕ Thêm bài tập mới")
        self.geometry("600x400")
        self.grab_set()

        self.file_path = ""

        frm = ttk.Frame(self, padding=15)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Chủ đề:").grid(row=0, column=0, sticky="w")
        self.chu_de_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.chu_de_var, width=40).grid(row=0, column=1, pady=5)

        ttk.Label(frm, text="Tên bài:").grid(row=1, column=0, sticky="w")
        self.ten_bai_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.ten_bai_var, width=40).grid(row=1, column=1, pady=5)

        ttk.Label(frm, text="Loại bài tập:").grid(row=2, column=0, sticky="w")
        self.loai_var = tk.StringVar()
        loai_combo = ttk.Combobox(frm, textvariable=self.loai_var, values=["text", "image", "pdf", "word", "link"],
                                  state="readonly", width=37)
        loai_combo.grid(row=2, column=1, pady=5)
        loai_combo.bind("<<ComboboxSelected>>", self.toggle_input_type)

        self.noi_dung_text = tk.Text(frm, height=6, width=50)
        self.noi_dung_text.grid(row=3, column=0, columnspan=2, pady=5)

        self.choose_btn = ttk.Button(frm, text="📁 Chọn file...", command=self.choose_file)
        # Ban đầu ẩn nút chọn file
        self.choose_btn.grid(row=4, column=0, columnspan=2)
        self.choose_btn.grid_remove()

        ttk.Label(frm, text="Ghi chú (nếu có):").grid(row=5, column=0, sticky="w")
        self.ghi_chu_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.ghi_chu_var, width=50).grid(row=5, column=1, pady=5)

        ttk.Button(frm, text="💾 Lưu bài tập", command=self.save).grid(row=6, column=0, columnspan=2, pady=15)

    def toggle_input_type(self, event=None):
        loai = self.loai_var.get()
        if loai == "text":
            self.noi_dung_text.config(state="normal")
            self.noi_dung_text.delete("1.0", tk.END)
            self.choose_btn.grid_remove()
        else:
            self.noi_dung_text.delete("1.0", tk.END)
            self.noi_dung_text.config(state="disabled")
            self.choose_btn.grid()

    def choose_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            # Lưu đường dẫn tương đối nếu nằm trong thư mục phần mềm
            rel_path = os.path.relpath(file_path, start=os.getcwd())
            self.file_path = rel_path
            self.noi_dung_text.config(state="normal")
            self.noi_dung_text.delete("1.0", tk.END)
            self.noi_dung_text.insert("1.0", self.file_path)
            self.noi_dung_text.config(state="disabled")

    def save(self):
        chu_de = self.chu_de_var.get().strip()
        ten_bai = self.ten_bai_var.get().strip()
        loai = self.loai_var.get().strip()
        noi_dung = self.noi_dung_text.get("1.0", tk.END).strip()
        ghi_chu = self.ghi_chu_var.get().strip()

        if not (chu_de and ten_bai and loai and noi_dung):
            messagebox.showwarning("Thiếu thông tin", "Vui lòng điền đầy đủ thông tin.")
            return

        self.db.execute_query("""
            INSERT INTO exercises (chu_de, ten_bai, loai_tap, noi_dung, ghi_chu)
            VALUES (?, ?, ?, ?, ?)
        """, (chu_de, ten_bai, loai, noi_dung, ghi_chu))

        messagebox.showinfo("Thành công", "Đã lưu bài tập.")
        self.destroy()
