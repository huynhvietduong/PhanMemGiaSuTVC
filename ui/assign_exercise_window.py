import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
class AssignExerciseWindow(tk.Toplevel):
    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self.title("📩 Giao bài tập cho học sinh / nhóm")
        self.geometry("880x600")
        self.grab_set()

        self.student_checks = {}
        self.group_map = {}
        self.exercise_map = {}

        main = ttk.Frame(self, padding=10)
        main.pack(fill="both", expand=True)

        # Chọn nhóm học
        ttk.Label(main, text="Nhóm học:").grid(row=0, column=0, sticky="w")
        groups = self.db.execute_query("SELECT id, name FROM groups ORDER BY name", fetch='all') or []
        self.group_map = {name: gid for gid, name in groups}
        self.group_var = tk.StringVar()
        group_cb = ttk.Combobox(main, textvariable=self.group_var, values=list(self.group_map.keys()), state="readonly",
                                width=30)
        group_cb.grid(row=0, column=1, padx=5, sticky="w")
        group_cb.bind("<<ComboboxSelected>>", self.load_students)

        # Ngày giao bài
        ttk.Label(main, text="Ngày giao:").grid(row=0, column=2, sticky="e")
        self.date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ttk.Entry(main, textvariable=self.date_var, width=15).grid(row=0, column=3, padx=5, sticky="w")

        # Danh sách học sinh (checkbox)
        self.student_frame = ttk.LabelFrame(main, text="Chọn học sinh nhận bài")
        self.student_frame.grid(row=1, column=0, columnspan=4, sticky="nsew", pady=10)
        self.student_frame.columnconfigure(0, weight=1)

        # Bài tập
        ttk.Label(main, text="Chọn bài tập:").grid(row=2, column=0, sticky="w")
        self.exercise_var = tk.StringVar()
        exercises = self.db.execute_query("SELECT id, chu_de, ten_bai FROM exercises ORDER BY chu_de",
                                          fetch='all') or []
        ex_labels = []
        for eid, chu_de, ten_bai in exercises:
            label = f"[{chu_de}] {ten_bai}"
            self.exercise_map[label] = eid
            ex_labels.append(label)
        ttk.Combobox(main, textvariable=self.exercise_var, values=ex_labels, state="readonly", width=50).grid(row=2,
                                                                                                              column=1,
                                                                                                              columnspan=3,
                                                                                                              sticky="w")

        # Ghi chú
        ttk.Label(main, text="Ghi chú:").grid(row=3, column=0, sticky="nw")
        self.note_text = tk.Text(main, height=2, width=70)
        self.note_text.grid(row=3, column=1, columnspan=3, sticky="w")

        # Nút giao bài
        ttk.Button(main, text="📤 Giao bài tập", command=self.assign_exercise).grid(row=4, column=0, columnspan=4,
                                                                                   pady=10)

    def load_students(self, event=None):
        for widget in self.student_frame.winfo_children():
            widget.destroy()
        self.student_checks.clear()

        gid = self.group_map.get(self.group_var.get())
        if not gid: return

        students = self.db.execute_query("SELECT id, name FROM students WHERE group_id = ?", (gid,), fetch='all') or []
        for sid, name in students:
            var = tk.BooleanVar(value=True)  # mặc định tick hết
            cb = ttk.Checkbutton(self.student_frame, text=name, variable=var)
            cb.pack(anchor="w")
            self.student_checks[sid] = var

    def assign_exercise(self):
        selected_ids = [sid for sid, var in self.student_checks.items() if var.get()]
        if not selected_ids:
            messagebox.showwarning("Thiếu thông tin", "Bạn chưa chọn học sinh nào.", parent=self)
            return
        label = self.exercise_var.get()
        eid = self.exercise_map.get(label)
        if not eid:
            messagebox.showwarning("Thiếu bài tập", "Vui lòng chọn bài tập.", parent=self)
            return
        ngay = self.date_var.get()
        ghi_chu = self.note_text.get("1.0", "end").strip()
        count = 0
        for sid in selected_ids:
            self.db.execute_query("""
                INSERT INTO assigned_exercises (student_id, exercise_id, ngay_giao, trang_thai, ghi_chu)
                VALUES (?, ?, ?, 'Chưa làm', ?)
            """, (sid, eid, ngay, ghi_chu))
            count += 1
        messagebox.showinfo("Thành công", f"Đã giao bài cho {count} học sinh.", parent=self)
        self.destroy()
