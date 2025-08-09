import tkinter as tk
from tkinter import ttk
class AssignedExerciseManagerWindow(tk.Toplevel):
    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self.title("📖 Bài tập đã giao")
        self.geometry("950x600")
        self.grab_set()

        self.group_map = {}
        self.student_map = {}

        filter_frame = ttk.LabelFrame(self, text="Bộ lọc")
        filter_frame.pack(fill="x", padx=10, pady=5)

        # Nhóm học
        ttk.Label(filter_frame, text="Nhóm học:").grid(row=0, column=0, padx=5, pady=2, sticky="e")
        self.group_var = tk.StringVar()
        group_list = self.db.execute_query("SELECT id, name FROM groups ORDER BY name", fetch='all') or []
        self.group_map = {name: gid for gid, name in group_list}
        group_cb = ttk.Combobox(filter_frame, textvariable=self.group_var, values=list(self.group_map.keys()), width=20,
                                state="readonly")
        group_cb.grid(row=0, column=1, padx=5)
        group_cb.bind("<<ComboboxSelected>>", self.on_group_selected)

        # Học sinh
        ttk.Label(filter_frame, text="Học sinh:").grid(row=0, column=2, padx=5, pady=2, sticky="e")
        self.student_var = tk.StringVar()
        self.student_cb = ttk.Combobox(filter_frame, textvariable=self.student_var, values=[], width=25,
                                       state="readonly")
        self.student_cb.grid(row=0, column=3, padx=5)

        # Chủ đề
        ttk.Label(filter_frame, text="Chủ đề:").grid(row=0, column=4, padx=5, pady=2, sticky="e")
        self.topic_var = tk.StringVar()
        topics = self.db.execute_query("SELECT DISTINCT chu_de FROM exercises ORDER BY chu_de", fetch='all') or []
        topic_list = [row[0] for row in topics if row[0]]
        topic_cb = ttk.Combobox(filter_frame, textvariable=self.topic_var, values=topic_list, width=15,
                                state="readonly")
        topic_cb.grid(row=0, column=5, padx=5)

        # Trạng thái
        ttk.Label(filter_frame, text="Trạng thái:").grid(row=0, column=6, padx=5, pady=2, sticky="e")
        self.status_var = tk.StringVar()
        status_cb = ttk.Combobox(filter_frame, textvariable=self.status_var, values=["Chưa làm", "Đã làm", "Đã chấm"],
                                 width=10, state="readonly")
        status_cb.grid(row=0, column=7, padx=5)

        # Từ ngày - đến ngày
        ttk.Label(filter_frame, text="Từ ngày:").grid(row=1, column=0, padx=5, pady=2, sticky="e")
        self.from_date = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.from_date, width=12).grid(row=1, column=1, padx=5)

        ttk.Label(filter_frame, text="Đến ngày:").grid(row=1, column=2, padx=5, pady=2, sticky="e")
        self.to_date = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.to_date, width=12).grid(row=1, column=3, padx=5)

        # Nút lọc
        ttk.Button(filter_frame, text="🔍 Lọc", command=self.load_data).grid(row=1, column=7, padx=5)
        ttk.Button(filter_frame, text="❌ Xóa lọc", command=self.clear_filters).grid(row=1, column=8, padx=5)

        # Bảng dữ liệu
        columns = ("Ngày giao", "Học sinh", "Tên bài", "Chủ đề", "Trạng thái", "Ghi chú")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=120)
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)

        self.tree.bind("<<TreeviewSelect>>", self.view_exercise_content)

        # Khung xem nội dung bài tập
        self.content_box = tk.Text(self, height=5, font=("Consolas", 11))
        self.content_box.pack(fill="x", padx=10, pady=5)

        self.load_data()

    def on_group_selected(self, event=None):
        gid = self.group_map.get(self.group_var.get())
        if not gid:
            self.student_cb.config(values=[])
            self.student_var.set("")
            return
        students = self.db.execute_query("SELECT id, name FROM students WHERE group_id = ?", (gid,), fetch='all') or []
        student_list = [f"{name} (ID {sid})" for sid, name in students]
        self.student_map = {text: sid for text, sid in zip(student_list, [s[0] for s in students])}
        self.student_cb.config(values=student_list)
        self.student_var.set("")

    def load_data(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        query = """
            SELECT ae.id, ae.ngay_giao, s.name, e.ten_bai, e.chu_de, ae.trang_thai, ae.ghi_chu, e.noi_dung, e.loai_tap
            FROM assigned_exercises ae
            JOIN exercises e ON ae.exercise_id = e.id
            JOIN students s ON ae.student_id = s.id
            WHERE 1=1
        """
        params = []

        if self.group_var.get():
            gid = self.group_map.get(self.group_var.get())
            query += " AND s.group_id = ?"
            params.append(gid)

        if self.student_var.get():
            sid = self.student_map.get(self.student_var.get())
            query += " AND ae.student_id = ?"
            params.append(sid)

        if self.topic_var.get():
            query += " AND e.chu_de = ?"
            params.append(self.topic_var.get())

        if self.status_var.get():
            query += " AND ae.trang_thai = ?"
            params.append(self.status_var.get())

        if self.from_date.get():
            query += " AND ae.ngay_giao >= ?"
            params.append(self.from_date.get())

        if self.to_date.get():
            query += " AND ae.ngay_giao <= ?"
            params.append(self.to_date.get())

        rows = self.db.execute_query(query, params, fetch='all') or []
        self.data_map = {}
        for row in rows:
            rid, ngay, hs_name, ten_bai, chu_de, trang_thai, ghi_chu, nd, loai = row
            self.tree.insert("", "end", iid=str(rid), values=(ngay, hs_name, ten_bai, chu_de, trang_thai, ghi_chu))
            self.data_map[str(rid)] = {'content': nd, 'loai': loai}

    def view_exercise_content(self, event=None):
        selected = self.tree.selection()
        if not selected:
            return
        rid = selected[0]
        info = self.data_map.get(rid)
        if not info:
            return
        self.content_box.delete("1.0", tk.END)
        content = info['content']
        loai = info['loai']
        if loai in ('text', 'link'):
            self.content_box.insert("1.0", content)
        else:
            self.content_box.insert("1.0", f"[{loai.upper()}] {content}")

    def clear_filters(self):
        self.group_var.set("")
        self.student_var.set("")
        self.student_cb['values'] = []
        self.topic_var.set("")
        self.status_var.set("")
        self.from_date.set("")
        self.to_date.set("")
        self.load_data()
