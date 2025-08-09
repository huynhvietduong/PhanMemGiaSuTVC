import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
class SkillRatingWindow(tk.Toplevel):
    def __init__(self, parent, db, student_list, default_topics=[]):
        super().__init__(parent)
        self.db = db
        self.student_list = student_list
        self.default_topics = default_topics
        self.title("Đánh giá năng lực học sinh")
        self.geometry("950x600")
        self.grab_set()

        self.frames = {}  # Lưu frame từng học sinh
        self.skill_vars = {}  # Dạng {(student_id, chu_de): (diem_var, nhan_xet_var)}

        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scroll_frame = ttk.Frame(canvas)

        self.scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for student_id, name in self.student_list:
            self.add_student_section(student_id, name)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Lưu đánh giá", command=self.save_skills).pack()

    # ⏬ Tạo khung đánh giá cho mỗi học sinh
    def add_student_section(self, student_id, student_name):
        box = ttk.LabelFrame(self.scroll_frame, text=f"{student_name} (ID {student_id})", padding=10)
        box.pack(fill="x", padx=10, pady=5)

        add_btn = ttk.Button(box, text="➕ Thêm chủ đề", command=lambda: self.add_topic_row(box, student_id))
        add_btn.pack(anchor="w")

        self.frames[student_id] = box

        # Nếu có chủ đề mặc định, thêm sẵn
        for chu_de in self.default_topics:
            self.add_topic_row(box, student_id, prefill_topic=chu_de)

    # ⏬ Thêm dòng nhập: chủ đề, điểm, nhận xét
    def add_topic_row(self, parent_frame, student_id, prefill_topic=""):
        row = ttk.Frame(parent_frame)
        row.pack(fill="x", pady=2)

        chu_de_var = tk.StringVar(value=prefill_topic)
        diem_var = tk.IntVar(value=3)
        nhan_xet_var = tk.StringVar()

        ttk.Entry(row, textvariable=chu_de_var, width=30).pack(side="left", padx=5)
        ttk.Label(row, text="Điểm:").pack(side="left")
        ttk.Spinbox(row, from_=1, to=5, textvariable=diem_var, width=5).pack(side="left", padx=5)
        ttk.Entry(row, textvariable=nhan_xet_var, width=50).pack(side="left", padx=5)

        # ✅ Dùng id(chu_de_var) làm key, vì StringVar không hash được
        self.skill_vars[(student_id, id(chu_de_var))] = (chu_de_var, diem_var, nhan_xet_var)

    # ⏬ Lưu đánh giá vào bảng student_skills
    def save_skills(self):
        count = 0
        ngay_danh_gia = datetime.now().strftime("%Y-%m-%d")
        for (student_id, _), (chu_de_var, diem_var, nhan_xet_var) in self.skill_vars.items():
            chu_de = chu_de_var.get().strip()
            if not chu_de:
                continue
            diem = diem_var.get()
            nhan_xet = nhan_xet_var.get()
            self.db.add_student_skill(student_id, chu_de, ngay_danh_gia, diem, nhan_xet)
            count += 1
        messagebox.showinfo("Thành công", f"Đã lưu {count} đánh giá.")
        self.destroy()
