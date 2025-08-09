import tkinter as tk
from tkinter import ttk
class StudentSkillReportWindow(tk.Toplevel):
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.db = db_manager
        self.title("Hồ sơ năng lực học sinh")
        self.geometry("900x600")
        self.grab_set()

        ttk.Label(self, text="Hồ sơ năng lực theo chủ đề", font=("Helvetica", 16, "bold")).pack(pady=10)

        filter_frame = ttk.Frame(self, padding=10)
        filter_frame.pack(fill="x")

        ttk.Label(filter_frame, text="Chọn học sinh:").pack(side="left")
        students = self.db.execute_query("SELECT id, name FROM students ORDER BY name", fetch='all') or []
        self.student_map = {f"{name} (ID {sid})": sid for sid, name in students}
        self.student_var = tk.StringVar()
        student_combo = ttk.Combobox(filter_frame, textvariable=self.student_var, values=list(self.student_map.keys()),
                                     state="readonly", width=40)
        student_combo.pack(side="left", padx=10)
        student_combo.bind("<<ComboboxSelected>>", self.load_report)

        self.tree = ttk.Treeview(self, columns=("Chủ đề", "Điểm TB", "Lần cuối đánh giá", "Xếp loại"), show="headings")
        for col in ("Chủ đề", "Điểm TB", "Lần cuối đánh giá", "Xếp loại"):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

    def load_report(self, event=None):
        for i in self.tree.get_children():
            self.tree.delete(i)

        selected_name = self.student_var.get()
        student_id = self.student_map.get(selected_name)
        if not student_id:
            return

        query = """
            SELECT chu_de, ROUND(AVG(diem),1), MAX(ngay_danh_gia)
            FROM student_skills
            WHERE student_id = ?
            GROUP BY chu_de
            ORDER BY chu_de
        """
        rows = self.db.execute_query(query, (student_id,), fetch='all') or []
        for chu_de, avg_score, last_date in rows:
            xep_loai = self.get_rating_label(avg_score)
            self.tree.insert("", "end", values=(chu_de, avg_score, last_date, xep_loai))

    def get_rating_label(self, score):
        if score >= 4.5:
            return "Giỏi"
        elif score >= 3.5:
            return "Khá"
        elif score >= 2.5:
            return "Trung bình"
        else:
            return "Yếu"
