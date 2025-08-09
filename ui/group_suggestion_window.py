import tkinter as tk
from tkinter import ttk, messagebox
class GroupSuggestionWindow(tk.Toplevel):
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.db = db_manager
        self.title("Gợi ý nhóm học phù hợp")
        self.geometry("850x600")
        self.grab_set()

        ttk.Label(self, text="🔍 Phân tích nhóm phù hợp theo chủ đề kỹ năng", font=("Helvetica", 14, "bold")).pack(
            pady=10)

        frame = ttk.Frame(self, padding=10)
        frame.pack(fill="x")

        ttk.Label(frame, text="Chọn học sinh:").grid(row=0, column=0, sticky="w")
        students = self.db.execute_query("SELECT id, name FROM students ORDER BY name", fetch='all') or []
        self.student_map = {f"{name} (ID {sid})": sid for sid, name in students}
        self.student_var = tk.StringVar()
        ttk.Combobox(frame, textvariable=self.student_var, values=list(self.student_map.keys()), width=40,
                     state="readonly").grid(row=0, column=1, padx=10)

        ttk.Label(frame, text="Chủ đề trọng tâm (ngăn cách bằng dấu phẩy):").grid(row=1, column=0, sticky="w", pady=10)
        self.topic_entry = ttk.Entry(frame, width=60)
        self.topic_entry.grid(row=1, column=1, pady=10, sticky="w")

        ttk.Button(frame, text="Phân tích nhóm phù hợp", command=self.analyze).grid(row=2, column=0, columnspan=2,
                                                                                    pady=10)

        self.result_tree = ttk.Treeview(self, columns=("Nhóm", "Lệch điểm trung bình"), show="headings")
        self.result_tree.heading("Nhóm", text="Nhóm")
        self.result_tree.heading("Lệch điểm trung bình", text="Lệch điểm trung bình")
        self.result_tree.pack(fill="both", expand=True, padx=10, pady=10)

    # Hàm xử lý phân tích
    def analyze(self):
        for i in self.result_tree.get_children():
            self.result_tree.delete(i)

        student_name = self.student_var.get()
        student_id = self.student_map.get(student_name)
        if not student_id:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng chọn học sinh.", parent=self)
            return

        topics = [t.strip() for t in self.topic_entry.get().split(",") if t.strip()]
        if not topics:
            messagebox.showwarning("Thiếu chủ đề", "Vui lòng nhập ít nhất 1 chủ đề.", parent=self)
            return

        # Lấy điểm trung bình của học sinh
        student_scores = {}
        for topic in topics:
            score = self.db.execute_query(
                "SELECT ROUND(AVG(diem), 1) FROM student_skills WHERE student_id = ? AND chu_de = ?",
                (student_id, topic), fetch='one')
            if score and score[0] is not None:
                student_scores[topic] = score[0]

        if not student_scores:
            messagebox.showinfo("Không có dữ liệu", "Học sinh này chưa được đánh giá các chủ đề đã chọn.", parent=self)
            return

        # Lấy danh sách nhóm
        groups = self.db.execute_query("SELECT id, name FROM groups ORDER BY name", fetch='all') or []

        results = []
        for gid, gname in groups:
            total_diff = 0
            count = 0
            for topic in student_scores:
                group_score = self.db.execute_query("""
                    SELECT ROUND(AVG(diem), 1)
                    FROM student_skills
                    WHERE student_id IN (SELECT id FROM students WHERE group_id = ?)
                    AND chu_de = ?
                """, (gid, topic), fetch='one')
                if group_score and group_score[0] is not None:
                    diff = abs(student_scores[topic] - group_score[0])
                    total_diff += diff
                    count += 1
            if count > 0:
                avg_diff = round(total_diff / count, 2)
                results.append((gname, avg_diff))

        results.sort(key=lambda x: x[1])
        for name, diff in results:
            self.result_tree.insert("", "end", values=(name, diff))
