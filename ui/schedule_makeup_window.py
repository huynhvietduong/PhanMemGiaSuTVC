import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from constants import DAYS_OF_WEEK_VN, FIXED_TIME_SLOTS
class ScheduleMakeUpWindow(tk.Toplevel):
    # Tạo cửa sổ sắp xếp lịch dạy bù cho học sinh
    def __init__(self, parent, db_manager, attendance_info_list):
        super().__init__(parent)
        self.db, self.parent, self.attendance_list = db_manager, parent, attendance_info_list
        self.title("Sắp xếp Dạy bù")
        self.geometry("600x450")
        self.grab_set()

        student_info = self.attendance_list[0]
        self.student_grade = student_info['group_grade']

        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill="both", expand=True)
        ttk.Label(main_frame, text="Sắp xếp Lịch Dạy bù", font=("Helvetica", 16, "bold")).pack(pady=10)
        # Gợi ý năng lực yếu
        suggestion = self.suggest_weak_skills()
        ttk.Label(main_frame, text=suggestion, foreground="red").pack(pady=5)

        if len(self.attendance_list) == 1:
            ttk.Label(main_frame, text=f"Học sinh: {student_info['student_name']}", font=("Helvetica", 12)).pack()
            ttk.Label(main_frame, text=f"Buổi nghỉ ngày: {student_info['session_date']}").pack(pady=5)
        else:
            ttk.Label(main_frame, text=f"Cho {len(self.attendance_list)} học sinh đã chọn",
                      font=("Helvetica", 12)).pack(pady=5)

        notebook = ttk.Notebook(main_frame)
        notebook.pack(pady=15, fill="both", expand=True)

        group_tab = ttk.Frame(notebook, padding="10")
        notebook.add(group_tab, text="Học bù với nhóm khác")
        private_tab = ttk.Frame(notebook, padding="10")

        if len(self.attendance_list) > 1:
            notebook.add(private_tab, text="Tạo buổi bù mới cho các em đã chọn")
        else:
            notebook.add(private_tab, text="Dạy bù riêng (1-1)")

        # === TAB 1: Học bù với nhóm khác ===
        self.show_all_grades_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(group_tab, text="Hiển thị cả các nhóm khác khối", variable=self.show_all_grades_var,
                        command=self.populate_group_combo).pack(anchor="w")
        ttk.Label(group_tab, text="Bước 1: Chọn nhóm để học bù:").pack(anchor="w", pady=5)
        self.group_var = tk.StringVar()
        self.group_combo = ttk.Combobox(group_tab, textvariable=self.group_var, state='readonly')
        self.group_combo.pack(fill="x")
        self.group_combo.bind("<<ComboboxSelected>>", self.on_group_selected)

        ttk.Label(group_tab, text="Bước 2: Chọn ngày học của nhóm:").pack(anchor="w", pady=5)
        self.session_date_var = tk.StringVar()
        self.session_combo = ttk.Combobox(group_tab, textvariable=self.session_date_var, state='disabled', height=10)
        self.session_combo.pack(fill="x")

        ttk.Button(group_tab, text="Xác nhận học bù với nhóm", command=self.schedule_group_session).pack(pady=15)

        # Chỉ sau khi đã khai báo session_combo thì mới được gọi
        self.populate_group_combo()

        # === TAB 2: Dạy bù riêng ===
        ttk.Label(private_tab, text="Khung giờ trống sẵn có (14 ngày tới):").grid(row=0, column=0, padx=5, pady=5,
                                                                                  sticky="w")
        self.free_slot_var = tk.StringVar()
        self.free_slot_combo = ttk.Combobox(private_tab, textvariable=self.free_slot_var, state='readonly', height=10)
        self.free_slot_combo.grid(row=0, column=1, padx=5, pady=5)

        ttk.Button(private_tab, text="Lên lịch buổi bù mới", command=self.schedule_private_session).grid(
            row=1, column=0, columnspan=2, pady=10
        )

        self.find_and_display_free_slots()

    # Hiển thị danh sách nhóm phù hợp để học bù
    def populate_group_combo(self):
        if self.show_all_grades_var.get():
            groups = self.db.execute_query("SELECT id, name FROM groups ORDER BY name", fetch='all') or []
        else:
            groups = self.db.execute_query("SELECT id, name FROM groups WHERE grade = ? ORDER BY name",
                                           (self.student_grade,), fetch='all') or []
        self.group_map = {name: id for id, name in groups}
        self.group_combo['values'] = list(self.group_map.keys())
        self.group_var.set("")
        self.session_combo.config(values=[], state='disabled')
        self.session_date_var.set("")

    # Hiển thị các ngày có thể học bù với nhóm đã chọn
    def on_group_selected(self, event):
        group_id = self.group_map.get(self.group_var.get())
        if not group_id:
            return
        schedule = self.db.execute_query("SELECT day_of_week, time_slot FROM schedule WHERE group_id = ?", (group_id,),
                                         fetch='all') or []
        if not schedule:
            self.session_combo.config(values=[], state='disabled')
            self.session_date_var.set("")
            return

        possible_dates = []
        today = datetime.now()
        for i in range(1, 31):
            future_date = today + timedelta(days=i)
            day_of_week_vn = DAYS_OF_WEEK_VN[future_date.weekday()]
            for day, time in schedule:
                if day == day_of_week_vn:
                    possible_dates.append(
                        f"Nhóm {self.group_var.get()} - {day_of_week_vn}, {future_date.strftime('%Y-%m-%d')} ({time})")
        self.session_combo.config(values=possible_dates, state='readonly')
        if possible_dates:
            self.session_combo.set(possible_dates[0])

    # Tìm khung giờ trống 14 ngày tới để dạy bù riêng
    def find_and_display_free_slots(self):
        today = datetime.now()
        start_date = today + timedelta(days=1)
        end_date = today + timedelta(days=14)

        busy_slots = set()
        for i in range(14):
            current_date = today + timedelta(days=i)
            day_vn = DAYS_OF_WEEK_VN[current_date.weekday()]
            scheduled_times = self.db.execute_query("SELECT time_slot FROM schedule WHERE day_of_week = ?", (day_vn,),
                                                    fetch='all') or []
            for (time_slot,) in scheduled_times:
                busy_slots.add((current_date.strftime("%Y-%m-%d"), time_slot))

        private_makeups = self.db.execute_query(
            "SELECT session_date, time_slot FROM makeup_sessions WHERE is_private = 1 AND session_date BETWEEN ? AND ?",
            (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')), fetch='all') or []
        for date, time in private_makeups:
            busy_slots.add((date, time))

        free_slots = []
        for i in range(1, 15):
            current_date = today + timedelta(days=i)
            date_str = current_date.strftime('%Y-%m-%d')
            day_vn = DAYS_OF_WEEK_VN[current_date.weekday()]
            for time_slot in FIXED_TIME_SLOTS:
                if (date_str, time_slot) not in busy_slots:
                    free_slots.append(
                        {'date': date_str, 'time': time_slot, 'display': f"{day_vn}, {date_str} ({time_slot})"}
                    )

        self.free_slot_map = {item['display']: item for item in free_slots}
        self.free_slot_combo['values'] = list(self.free_slot_map.keys())
        if free_slots:
            self.free_slot_combo.set(free_slots[0]['display'])

    # Ghi nhận học bù với nhóm đã chọn
    def schedule_group_session(self):
        selected_display = self.session_date_var.get()
        if not selected_display:
            messagebox.showerror("Lỗi", "Vui lòng chọn một buổi học.", parent=self)
            return

        group_id = self.group_map.get(self.group_var.get())
        if not group_id:
            messagebox.showerror("Lỗi", "Nhóm không hợp lệ.")
            return

        # Lấy ngày
        parts = selected_display.split(", ")
        date_str = parts[1].split(" ")[0]

        for att_info in self.attendance_list:
            self.db.execute_query("DELETE FROM makeup_sessions WHERE attendance_id = ?", (att_info['id'],))
            self.db.execute_query(
                "INSERT INTO makeup_sessions (attendance_id, student_id, session_date, host_group_id, is_private) VALUES (?, ?, ?, ?, 0)",
                (att_info['id'], att_info['student_id'], date_str, group_id))

        self.update_status_and_close("Đã lên lịch")

    # Ghi nhận buổi dạy bù riêng (1-1 hoặc nhóm nhỏ)
    def schedule_private_session(self):
        selected_slot = self.free_slot_var.get()
        if not selected_slot:
            messagebox.showerror("Lỗi", "Vui lòng chọn một khung giờ trống.", parent=self)
            return

        slot_info = self.free_slot_map[selected_slot]
        date, time = slot_info['date'], slot_info['time']

        for att_info in self.attendance_list:
            self.db.execute_query("DELETE FROM makeup_sessions WHERE attendance_id = ?", (att_info['id'],))
            self.db.execute_query(
                "INSERT INTO makeup_sessions (attendance_id, student_id, session_date, time_slot, is_private) VALUES (?, ?, ?, ?, 1)",
                (att_info['id'], att_info['student_id'], date, time))

        self.update_status_and_close("Đã lên lịch")

    # Phân tích điểm yếu của học sinh để gợi ý học lại
    def suggest_weak_skills(self):
        weak_skills = {}

        for info in self.attendance_list:
            student_id = info['student_id']
            rows = self.db.execute_query("""
                SELECT chu_de, ROUND(AVG(diem),1)
                FROM student_skills
                WHERE student_id = ?
                GROUP BY chu_de
                HAVING AVG(diem) < 3.0
                ORDER BY AVG(diem) ASC
            """, (student_id,), fetch='all') or []

            for chu_de, avg in rows:
                if chu_de not in weak_skills:
                    weak_skills[chu_de] = []
                weak_skills[chu_de].append(avg)

        # Tổng hợp trung bình nhiều học sinh (nếu chọn nhiều em cùng lúc)
        merged = [(k, round(sum(v) / len(v), 1)) for k, v in weak_skills.items()]
        merged.sort(key=lambda x: x[1])

        if not merged:
            return "Không có chủ đề yếu nổi bật."
        else:
            return "Gợi ý học lại: " + ", ".join([f"{chu_de} ({diem})" for chu_de, diem in merged])

    # Cập nhật trạng thái học bù và đóng cửa sổ
    def update_status_and_close(self, status):
        for att_info in self.attendance_list:
            self.db.execute_query("UPDATE attendance SET make_up_status = ? WHERE id = ?", (status, att_info['id']))
        messagebox.showinfo("Thành công", f"Đã cập nhật trạng thái cho {len(self.attendance_list)} học sinh.",
                            parent=self)
        self.parent.load_report()
        if hasattr(self.parent, 'master') and hasattr(self.parent.master, 'update_all_schedules'):
            self.parent.master.update_all_schedules()
        self.destroy()
