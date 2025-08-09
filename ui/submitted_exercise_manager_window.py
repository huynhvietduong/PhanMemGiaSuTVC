import os
import tkinter as tk
from tkinter import ttk, messagebox
# 🧾 GIAO DIỆN XEM BÀI ĐÃ NỘP
class SubmittedExerciseManagerWindow(tk.Toplevel):
    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self.title("📂 Danh sách bài đã nộp")
        self.geometry("900x550")
        self.grab_set()

        # --- Bộ lọc ---
        filter_frame = ttk.LabelFrame(self, text="Bộ lọc", padding=10)
        filter_frame.pack(fill="x", padx=10, pady=5)

        # Học sinh
        ttk.Label(filter_frame, text="Học sinh:").grid(row=0, column=0, sticky="w")
        students = db.execute_query("SELECT id, name FROM students ORDER BY name", fetch="all") or []
        self.student_map = {f"{name} (ID {sid})": sid for sid, name in students}
        self.student_var = tk.StringVar()
        student_cb = ttk.Combobox(filter_frame, textvariable=self.student_var, values=list(self.student_map.keys()),
                                  width=30, state="readonly")
        student_cb.grid(row=0, column=1, padx=5)

        # Chủ đề
        ttk.Label(filter_frame, text="Chủ đề:").grid(row=0, column=2, sticky="w")
        self.topic_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.topic_var, width=20).grid(row=0, column=3, padx=5)

        # Ngày
        ttk.Label(filter_frame, text="Từ ngày:").grid(row=0, column=4, sticky="w")
        self.from_date = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.from_date, width=12).grid(row=0, column=5, padx=2)
        ttk.Label(filter_frame, text="Đến:").grid(row=0, column=6)
        self.to_date = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.to_date, width=12).grid(row=0, column=7, padx=2)

        # Nút lọc
        ttk.Button(filter_frame, text="🔍 Lọc", command=self.load_data).grid(row=0, column=8, padx=5)

        # --- Bảng ---
        self.tree = ttk.Treeview(self, columns=("HS", "Chủ đề", "Tên bài", "Ngày nộp", "Điểm", "Nhận xét", "Xem"),
                                 show="headings")
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)

        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=100)

        self.tree.bind("<Double-1>", self.view_file)

        self.load_data()

    def load_data(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        query = """
            SELECT s.name, e.chu_de, e.ten_bai, sub.ngay_nop, sub.diem, sub.nhan_xet, sub.file_path
            FROM exercise_submissions sub
            JOIN assigned_exercises ae ON sub.assignment_id = ae.id
            JOIN exercises e ON ae.exercise_id = e.id
            JOIN students s ON sub.student_id = s.id
            WHERE 1=1
        """
        params = []

        if self.student_var.get():
            sid = self.student_map.get(self.student_var.get())
            query += " AND sub.student_id = ?"
            params.append(sid)

        if self.topic_var.get():
            query += " AND e.chu_de LIKE ?"
            params.append(f"%{self.topic_var.get()}%")

        if self.from_date.get():
            query += " AND sub.ngay_nop >= ?"
            params.append(self.from_date.get())

        if self.to_date.get():
            query += " AND sub.ngay_nop <= ?"
            params.append(self.to_date.get())

        rows = self.db.execute_query(query, tuple(params), fetch="all") or []
        for row in rows:
            self.tree.insert("", "end", values=row)

    def view_file(self, event):
        item = self.tree.selection()
        if not item:
            return
        file_path = self.tree.item(item[0])["values"][-1]
        if os.path.exists(file_path):
            os.startfile(file_path)
        else:
            messagebox.showerror("Lỗi", f"Không tìm thấy file:\n{file_path}", parent=self)