import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta

from constants import DAYS_OF_WEEK_VN
from .schedule_makeup_window import ScheduleMakeUpWindow
class AttendanceReportWindow(tk.Toplevel):
    # Giao diện báo cáo chuyên cần & sắp xếp học bù
    def __init__(self, parent, db_manager):
        super().__init__(parent);
        self.db = db_manager;
        self.parent = parent
        self.title("Báo cáo Chuyên cần");
        self.geometry("900x600")
        ttk.Label(self, text="Báo cáo Chuyên cần", font=("Helvetica", 16, "bold")).pack(pady=10)
        filter_frame = ttk.Frame(self, padding="10");
        filter_frame.pack(fill="x")
        ttk.Label(filter_frame, text="Từ ngày:").pack(side="left", padx=5)
        self.start_date_var = tk.StringVar(value=(datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"))
        ttk.Entry(filter_frame, textvariable=self.start_date_var).pack(side="left", padx=5)
        ttk.Label(filter_frame, text="Đến ngày:").pack(side="left", padx=5)
        self.end_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ttk.Entry(filter_frame, textvariable=self.end_date_var).pack(side="left", padx=5)
        self.hide_completed_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(filter_frame, text="Ẩn các buổi đã dạy bù", variable=self.hide_completed_var,
                        command=self.load_report).pack(side="left", padx=10)
        ttk.Button(filter_frame, text="Xem báo cáo", command=self.load_report).pack(side="left", padx=5)
        self.tree = ttk.Treeview(self, columns=("Ngày", "Học sinh", "Nhóm", "Lý do", "Dạy bù"), show="headings",
                                 selectmode='extended')
        for col in ("Ngày", "Học sinh", "Nhóm", "Lý do", "Dạy bù"): self.tree.heading(col, text=col)
        self.tree.column("Dạy bù", width=250)
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="🗓️ Sắp xếp lịch bù...", command=self.open_schedule_makeup_window)
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.load_report()

    # Tải danh sách học sinh nghỉ và trạng thái học bù
    def load_report(self):
        self.attendance_data = {}
        for i in self.tree.get_children():
            self.tree.delete(i)

        start_date = self.start_date_var.get()
        end_date = self.end_date_var.get()
        hide_completed = self.hide_completed_var.get()

        report_items = self.db.get_attendance_report(start_date, end_date, hide_completed)

        for item in report_items:
            att_id = item['id']
            values = (
                item['session_date'],
                item['student_name'],
                item['group_name'],
                item['status'],
                item['detailed_status']
            )
            self.tree.insert("", "end", iid=att_id, values=values)
            self.attendance_data[att_id] = {
                'id': att_id,
                'session_date': item['session_date'],
                'student_name': item['student_name'],
                'student_id': item['student_id'],
                'group_grade': item['group_grade']
            }
    # Hiện menu chuột phải khi chọn học sinh nghỉ
    def show_context_menu(self, event):
        item_id = self.tree.identify_row(event.y)
        if item_id:
            if item_id not in self.tree.selection(): self.tree.selection_set(item_id)
            self.context_menu.post(event.x_root, event.y_root)

    # Mở cửa sổ sắp xếp lịch học bù cho học sinh đã chọn
    def open_schedule_makeup_window(self):
        selected_items = self.tree.selection()
        if not selected_items: messagebox.showwarning("Chưa chọn",
                                                      "Vui lòng chọn ít nhất một học sinh để sắp xếp lịch."); return
        attendance_info_list = [self.attendance_data[int(item_id)] for item_id in selected_items]
        first_grade = attendance_info_list[0]['group_grade']
        if not all(info['group_grade'] == first_grade for info in attendance_info_list):
            messagebox.showerror("Lỗi", "Vui lòng chỉ chọn các học sinh có cùng khối lớp để sắp xếp lịch chung.");
            return
        ScheduleMakeUpWindow(self, self.db, attendance_info_list)
