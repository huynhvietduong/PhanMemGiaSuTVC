import os
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
class SubmitExerciseWindow(tk.Toplevel):
    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self.title("📤 Học sinh nộp bài tập")
        self.geometry("700x400")
        self.grab_set()

        self.file_path = None

        frame = ttk.Frame(self, padding=15)
        frame.pack(fill="both", expand=True)

        # Học sinh
        ttk.Label(frame, text="Chọn học sinh:").grid(row=0, column=0, sticky="w")
        students = self.db.execute_query("SELECT id, name FROM students ORDER BY name", fetch='all') or []
        self.student_map = {f"{name} (ID {sid})": sid for sid, name in students}
        self.student_var = tk.StringVar()
        student_cb = ttk.Combobox(frame, textvariable=self.student_var, values=list(self.student_map.keys()), width=40,
                                  state="readonly")
        student_cb.grid(row=0, column=1, columnspan=2, sticky="w")
        student_cb.bind("<<ComboboxSelected>>", self.update_assignments_for_student)

        # Bài tập đã giao
        ttk.Label(frame, text="Chọn bài tập đã giao:").grid(row=1, column=0, sticky="w")
        self.assignment_map = {}

        self.assignment_var = tk.StringVar()
        self.assignment_combo = ttk.Combobox(frame, textvariable=self.assignment_var, values=[], width=50,
                                             state="readonly")
        self.assignment_combo.grid(row=1, column=1, columnspan=2, sticky="w")

        # File
        ttk.Label(frame, text="File bài làm:").grid(row=2, column=0, sticky="w")
        self.file_label = ttk.Label(frame, text="Chưa chọn file", foreground="gray")
        self.file_label.grid(row=2, column=1, sticky="w")
        ttk.Button(frame, text="📂 Chọn file", command=self.select_file).grid(row=2, column=2, sticky="w")

        # Ngày nộp
        ttk.Label(frame, text="Ngày nộp:").grid(row=3, column=0, sticky="w")
        self.date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ttk.Entry(frame, textvariable=self.date_var, width=15).grid(row=3, column=1, sticky="w")

        # Điểm & Nhận xét
        ttk.Label(frame, text="Điểm:").grid(row=4, column=0, sticky="w")
        self.score_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.score_var, width=5).grid(row=4, column=1, sticky="w")

        ttk.Label(frame, text="Nhận xét:").grid(row=5, column=0, sticky="nw")
        self.comment_text = tk.Text(frame, height=3, width=50)
        self.comment_text.grid(row=5, column=1, columnspan=2, sticky="w")

        # Nút nộp
        ttk.Button(frame, text="✅ Xác nhận nộp bài", command=self.submit).grid(row=6, column=0, columnspan=3, pady=10)

    def select_file(self):
        filepath = filedialog.askopenfilename(title="Chọn file bài làm")
        if filepath:
            self.file_path = filepath
            self.file_label.config(text=os.path.basename(filepath), foreground="black")

    def submit(self):
        student_id = self.student_map.get(self.student_var.get())
        assignment_id = self.assignment_map.get(self.assignment_var.get())
        if not student_id or not assignment_id or not self.file_path:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng chọn học sinh, bài tập và file.", parent=self)
            return

        diem = self.score_var.get()
        nhan_xet = self.comment_text.get("1.0", tk.END).strip()
        ngay = self.date_var.get()

        # Tạo thư mục lưu bài
        os.makedirs("submissions", exist_ok=True)
        ext = os.path.splitext(self.file_path)[1]
        file_name = f"{student_id}_{assignment_id}_{int(datetime.now().timestamp())}{ext}"
        save_path = os.path.join("submissions", file_name)
        shutil.copy2(self.file_path, save_path)

        # Lưu vào database
        try:
            self.db.execute_query("""
                INSERT INTO exercise_submissions (student_id, assignment_id, file_path, ngay_nop, diem, nhan_xet)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (student_id, assignment_id, save_path, ngay, diem, nhan_xet))

            messagebox.showinfo("Thành công", "Đã lưu bài nộp.", parent=self)
            self.destroy()
        except Exception as e:
            messagebox.showerror("Lỗi CSDL", f"Có lỗi xảy ra khi lưu vào cơ sở dữ liệu:\n{e}", parent=self)

    def update_assignments_for_student(self, event=None):
        selected = self.student_var.get()
        student_id = self.student_map.get(selected)
        if not student_id:
            return
        rows = self.db.execute_query("""
            SELECT ae.id, e.ten_bai, e.chu_de
            FROM assigned_exercises ae
            JOIN exercises e ON ae.exercise_id = e.id
            WHERE ae.student_id = ?
            ORDER BY ae.ngay_giao DESC
        """, (student_id,), fetch='all') or []

        self.assignment_map.clear()
        combo_values = []
        for aid, ten_bai, chu_de in rows:
            label = f"[{chu_de}] {ten_bai}"
            self.assignment_map[label] = aid
            combo_values.append(label)

        self.assignment_combo['values'] = combo_values
        self.assignment_var.set(combo_values[0] if combo_values else "")

