# Các thư viện chuẩnnnnnnn
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from PIL import Image, ImageTk
import os

import sys
from utils import ToolTip
# Import từ các file bạn vừa tạo
from database import DatabaseManager
from constants import DAYS_OF_WEEK_VN, FIXED_TIME_SLOTS
from utils import ToolTip, PlaceholderEntry # Nếu bạn có gọi trong App

# Import TẤT CẢ các cửa sổ từ thư mục UI
from ui.student_window import StudentWindow
from ui.group_window import GroupWindow
from ui.package_window import PackageWindow
from ui.session_detail_window import SessionDetailWindow
from ui.attendance_report_window import AttendanceReportWindow
from ui.progress_report_window import ProgressReportWindow
from ui.salary_window import SalaryWindow
from ui.skill_rating_window import SkillRatingWindow
from ui.question_bank_window import QuestionBankWindow
from ui.create_test_window import CreateTestWindow
from ui.exercise_manager_window import ExerciseManagerWindow
from ui.assign_exercise_window import AssignExerciseWindow
from ui.assigned_exercise_manager_window import AssignedExerciseManagerWindow
from ui.submit_exercise_window import SubmitExerciseWindow
from ui.submitted_exercise_manager_window import SubmittedExerciseManagerWindow
from ui.student_skill_report_window import StudentSkillReportWindow
from ui.group_suggestion_window import GroupSuggestionWindow
from ui.exercise_suggestion_window import ExerciseSuggestionWindow
from ui.add_exercise_window import AddExerciseWindow
from ui.create_exercise_tree_window import ExerciseTreeManager

# --- Cửa sổ chính của ứng dụng ---
class App(tk.Tk):
    # Cửa sổ chính: hiển thị lịch tuần và truy cập các chức năng
    def __init__(self, db_manager):
        super().__init__();
        self.db = db_manager;
        self.title("Phần mềm Quản lý Gia sư - v3.8");
        self.geometry("1200x800")
        self.style = ttk.Style(self);
        self.style.theme_use("clam")
        self.current_week_start = datetime.now() - timedelta(days=datetime.now().weekday())
        self.last_upcoming_check = None
        self.create_menu()
        main_frame = ttk.Frame(self, padding="5");
        main_frame.pack(fill="both", expand=True)
        left_panel = ttk.Frame(main_frame, width=300, relief="solid", borderwidth=1);
        left_panel.pack(side="left", fill="y", padx=(0, 5));
        left_panel.pack_propagate(False)
        right_panel = ttk.Frame(main_frame, relief="solid", borderwidth=1);
        right_panel.pack(side="right", fill="both", expand=True)
        self.create_right_panel(right_panel)
        self.create_left_panel(left_panel)
        self.update_day_headers()
        self.update_all_schedules()

    # Tạo thanh menu trên cùng: quản lý và báo cáo
    def create_menu(self):

        menu_bar = tk.Menu(self)
        self.config(menu=menu_bar)
        manage_menu = tk.Menu(menu_bar, tearoff=0)
        manage_menu.add_command(label="🌐 Mở bảng điều khiển", command=self.open_dashboard)
        menu_bar.add_cascade(label="Quản lý", menu=manage_menu)

        manage_menu.add_command(label="Ngân hàng câu hỏi", command=lambda: QuestionBankWindow(self, self.db))
        manage_menu.add_command(label="Gợi ý nhóm học phù hợp", command=self.open_group_suggestion)
        manage_menu.add_command(label="Học sinh...", command=self.open_student_window)
        manage_menu.add_command(label="Nhóm học...", command=self.open_group_window)
        manage_menu.add_command(label="Gói học...", command=self.open_package_window)
        manage_menu.add_separator();
        manage_menu.add_command(label="Thoát", command=self.quit)


        report_menu = tk.Menu(menu_bar, tearoff=0);
        menu_bar.add_cascade(label="Báo cáo", menu=report_menu)
        report_menu.add_command(label="Tính lương...", command=self.open_salary_window)  # Mới
        report_menu.add_command(label="Chuyên cần...", command=self.open_attendance_report)
        report_menu.add_command(label="Tiến độ...", command=self.open_progress_report)
        report_menu.add_command(label="Năng lực học sinh...", command=self.open_student_skill_report)

        # Menu Bài tập
        exercise_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Bài tập", menu=exercise_menu)
        exercise_menu.add_command(label="Gợi ý theo điểm yếu", command=self.open_exercise_suggestion)
        exercise_menu.add_command(label="Thêm bài tập", command=self.open_add_exercise)
        exercise_menu.add_command(label="Quản lý bài tập", command=self.open_exercise_manager)
        exercise_menu.add_command(label="📩 Giao bài tập", command=self.open_assign_exercise)
        exercise_menu.add_command(label="📋 Bài đã giao", command=self.open_assigned_exercises)
        exercise_menu.add_command(label="📤 Nộp bài tập...", command=self.open_submit_window)
        exercise_menu.add_command(label="📂 Bài đã nộp...", command=self.open_submitted_manager)
        manage_menu.add_command(label="⚙️ Tạo bảng exercises", command=self.fix_missing_exercises_table)
        exercise_menu.add_command(label="✍️ Tạo đề thi PDF", command=lambda: CreateTestWindow(self, self.db))
        exercise_menu.add_command(label="🌲 Cây thư mục bài tập", command=self.open_exercise_tree_manager)

    # Tạo bảng điều khiển bên trái: thời gian, lịch hôm nay, lớp sắp tới
    def create_left_panel(self, parent):
        ttk.Label(parent, text="Bảng điều khiển", font=("Helvetica", 16, "bold")).pack(pady=10)
        self.clock_label = ttk.Label(parent, font=("Helvetica", 14));
        self.clock_label.pack(pady=10)

        ttk.Separator(parent, orient='horizontal').pack(fill='x', padx=5, pady=10)

        ttk.Label(parent, text="Lịch dạy hôm nay", font=("Helvetica", 12, "bold")).pack(pady=5)
        self.today_schedule_frame = ttk.Frame(parent);
        self.today_schedule_frame.pack(fill="x", padx=10)

        # KHUNG MỚI CHO LỚP SẮP TỚI
        self.upcoming_class_frame = ttk.LabelFrame(parent, text="Lớp học sắp tới", padding="10")

        self.upcoming_class_frame.pack(fill="x", padx=10, pady=10)
        ttk.Label(self.upcoming_class_frame, text="Chưa có lớp nào sắp diễn ra.", foreground="gray").pack()

        ttk.Separator(parent, orient='horizontal').pack(fill='x', padx=5, pady=10)
        ttk.Label(parent, text="Thông báo", font=("Helvetica", 12, "bold")).pack(pady=5)
        self.notification_label = ttk.Label(parent, text="Sẵn sàng...", justify="left");
        self.notification_label.pack(padx=10, anchor="w")
        self.update_clock()

    # Tạo bảng lịch tuần ở bên phải
    def create_right_panel(self, parent):
        # Frame chứa tiêu đề và các nút điều khiển
        header_frame = ttk.Frame(parent)
        header_frame.pack(pady=5)

        ttk.Button(header_frame, text="< Tuần trước", command=lambda: self.change_week(-7)).pack(side="left", padx=10)

        self.week_title_label = ttk.Label(header_frame, text="Lịch biểu Tuần", font=("Helvetica", 16, "bold"))
        self.week_title_label.pack(side="left", padx=10)

        ttk.Button(header_frame, text="Tuần sau >", command=lambda: self.change_week(7)).pack(side="left", padx=10)
        ttk.Button(header_frame, text="Hôm nay", command=self.go_to_today).pack(side="left", padx=10)

        self.schedule_grid_frame = ttk.Frame(parent);
        self.schedule_grid_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.day_header_context_menu = tk.Menu(self, tearoff=0)
        self.day_header_context_menu.add_command(label="Hủy tất cả buổi học trong ngày",
                                                 command=self.cancel_day_sessions)
        self.clicked_day_info = {}

        self.day_header_labels = []
        for i, day in enumerate(DAYS_OF_WEEK_VN):
            day_lbl = ttk.Label(self.schedule_grid_frame, text=day, font=("Helvetica", 10, "bold"), relief="groove",
                                anchor="center")
            day_lbl.grid(row=0, column=i + 1, sticky="nsew")
            day_lbl.bind("<Button-3>", lambda e, day_idx=i: self.show_day_header_context_menu(e, day_idx))
            self.day_header_labels.append(day_lbl)

        for i, slot in enumerate(FIXED_TIME_SLOTS):
            end_time = (datetime.strptime(slot, "%H:%M") + timedelta(minutes=90)).strftime("%H:%M")
            ttk.Label(self.schedule_grid_frame, text=f"{slot}\n-\n{end_time}", font=("Helvetica", 10, "bold"),
                      relief="groove", anchor="center").grid(row=i + 1, column=0, sticky="nsew")

        self.schedule_grid_frame.grid_columnconfigure(list(range(8)), weight=1)
        self.schedule_grid_frame.grid_rowconfigure(list(range(len(FIXED_TIME_SLOTS) + 1)), weight=1)

        self.session_context_menu = tk.Menu(self, tearoff=0)

    # Cập nhật thời gian đồng hồ và lớp sắp tới theo thời gian thực
    def update_clock(self):
        now = datetime.now()

        if not hasattr(self, 'last_updated_date') or self.last_updated_date != now.date():
            self.update_day_headers()
            self.last_updated_date = now.date()

        # Cập nhật lớp học sắp tới mỗi 30 giây
        if self.last_upcoming_check is None or (now - self.last_upcoming_check).total_seconds() > 30:
            self.update_upcoming_class()
            self.last_upcoming_check = now

        day_of_week_vn = DAYS_OF_WEEK_VN[now.weekday()]
        formatted_string = f"{now.strftime('%H:%M:%S')}\n{day_of_week_vn}, {now.strftime('%d-%m-%Y')}"
        self.clock_label.config(text=formatted_string)
        self.clock_job = self.after(1000, self.update_clock)

    def destroy(self):
        try:
            if hasattr(self, "clock_job"):
                self.after_cancel(self.clock_job)
            if hasattr(self, "schedule_job"):
                self.after_cancel(self.schedule_job)  # hủy vòng lặp
        except:
            pass
        super().destroy()

    # Cập nhật tiêu đề ngày trên lịch theo tuần hiện tại
    def update_day_headers(self):
        start_of_week = self.current_week_start
        end_of_week = start_of_week + timedelta(days=6)

        # Cập nhật tiêu đề tuần
        self.week_title_label.config(
            text=f"Lịch biểu Tuần ({start_of_week.strftime('%d/%m')} - {end_of_week.strftime('%d/%m')})")

        today = datetime.now().date()
        style = ttk.Style()
        default_bg = style.lookup('TLabel', 'background')

        for i, lbl in enumerate(self.day_header_labels):
            current_day = start_of_week + timedelta(days=i)
            lbl.config(text=f"{DAYS_OF_WEEK_VN[i]}\n({current_day.strftime('%d/%m')})")

            if current_day.date() == today:
                lbl.config(background="#cce5ff")
            else:
                lbl.config(background=default_bg)

    # Làm mới lịch tuần + lịch hôm nay định kỳ mỗi 5 giây
    def update_all_schedules(self):
        self.update_schedule_grid()
        self.update_today_schedule()
        self.schedule_job = self.after(5000, self.update_all_schedules)  # lưu ID

    # Vẽ toàn bộ lịch tuần dạng lưới (các ô thời gian)
    def update_upcoming_class(self):
        for widget in self.upcoming_class_frame.winfo_children():
            widget.destroy()

        now = datetime.now()
        today_vn = DAYS_OF_WEEK_VN[now.weekday()]
        today_str = now.strftime("%Y-%m-%d")

        # Lấy lịch học hôm nay
        query = "SELECT g.name, g.id, s.time_slot FROM schedule s JOIN groups g ON s.group_id = g.id WHERE s.day_of_week = ? ORDER BY s.time_slot"
        today_classes = self.db.execute_query(query, (today_vn,), fetch='all') or []

        next_class_info = None
        # Tìm lớp học tiếp theo trong ngày
        for group_name, group_id, time_slot in today_classes:
            class_time = datetime.strptime(f"{today_str} {time_slot}", "%Y-%m-%d %H:%M")
            if class_time > now:
                next_class_info = {'name': group_name, 'id': group_id, 'time': class_time}
                break

        # Nếu tìm thấy lớp và thời gian phù hợp (trong vòng 30 phút tới)
        if next_class_info and (next_class_info['time'] - now).total_seconds() <= 1800:  # 30 phút = 1800 giây
            self.upcoming_class_frame.config(text=f"Lớp sắp tới: {next_class_info['name']}")

            # Lấy danh sách HS chính thức
            students = self.db.execute_query("SELECT name FROM students WHERE group_id = ?", (next_class_info['id'],),
                                             fetch='all') or []
            for (student_name,) in students:
                ttk.Label(self.upcoming_class_frame, text=f"- {student_name}").pack(anchor="w")

            # Lấy danh sách HS học bù
            joiners_query = "SELECT s.name FROM makeup_sessions m JOIN students s ON m.student_id = s.id WHERE m.is_private = 0 AND m.host_group_id = ? AND m.session_date = ?"
            joiners = self.db.execute_query(joiners_query, (next_class_info['id'], today_str), fetch='all') or []
            if joiners:
                ttk.Separator(self.upcoming_class_frame).pack(fill='x', pady=2)
                for (student_name,) in joiners:
                    ttk.Label(self.upcoming_class_frame, text=f"- [Bù] {student_name}").pack(anchor="w")
        else:
            # Nếu không có lớp nào sắp diễn ra
            self.upcoming_class_frame.config(text="Lớp học sắp tới")
            ttk.Label(self.upcoming_class_frame, text="Chưa có lớp nào sắp diễn ra.", foreground="gray").pack()

    # Vẽ 1 ô buổi học lên lịch tuần (gồm tooltip, màu, sự kiện)
    def update_schedule_grid(self):
        for widget in self.schedule_grid_frame.winfo_children():
            if widget.grid_info().get('row', 0) > 0 and widget.grid_info().get('column', 0) > 0: widget.destroy()

        start_of_week = self.current_week_start
        end_of_week = start_of_week + timedelta(days=6)

        # 1. Lấy dữ liệu cho tuần hiện tại
        cancelled_set = {(g_id, date) for g_id, date in self.db.execute_query(
            "SELECT group_id, cancelled_date FROM cancelled_sessions WHERE cancelled_date BETWEEN ? AND ?",
            (start_of_week.strftime('%Y-%m-%d'), end_of_week.strftime('%Y-%m-%d')), fetch='all') or []}

        # 2. Lặp qua các ngày và vẽ lịch
        for i, day_vn in enumerate(DAYS_OF_WEEK_VN):
            current_day = start_of_week + timedelta(days=i)
            current_day_str = current_day.strftime('%Y-%m-%d')

            # Vẽ các buổi học chính thức
            main_sessions_in_day = self.db.execute_query(
                "SELECT g.name, g.id, s.time_slot FROM schedule s JOIN groups g ON s.group_id=g.id WHERE s.day_of_week = ?",
                (day_vn,), fetch='all') or []
            for group_name, group_id, time_slot in main_sessions_in_day:
                is_cancelled = (group_id, current_day_str) in cancelled_set
                self.add_session_to_grid(day_vn, time_slot, group_name, group_id, current_day, is_cancelled)

            # Vẽ các buổi bù riêng
            private_makeups_in_day = self.db.execute_query(
                "SELECT s.name, m.time_slot FROM makeup_sessions m JOIN students s ON m.student_id = s.id WHERE m.is_private = 1 AND m.session_date = ?",
                (current_day_str,), fetch='all') or []
            for student_name, time_slot in private_makeups_in_day:
                text = f"[Bù] {student_name}"
                self.add_session_to_grid(day_vn, time_slot, text, None, current_day, False)

    # Hiển thị danh sách lớp diễn ra hôm nay bên trái
    def add_session_to_grid(self, day_vn, time_slot, text, group_id, session_date, is_cancelled, command=None, tooltip_text=""):
        try:
            row, col = FIXED_TIME_SLOTS.index(time_slot) + 1, DAYS_OF_WEEK_VN.index(day_vn) + 1
            frame = ttk.Frame(self.schedule_grid_frame, relief="solid", borderwidth=1)
            frame.grid(row=row, column=col, sticky="nsew", padx=1, pady=1)

            # 🟦 Màu nền
            color = "#d9d9d9" if is_cancelled else ("#fff0e0" if "[Bù]" in text else "#e0e8f0")
            font_style = ("Helvetica", 9, "italic overstrike") if is_cancelled else ("Helvetica", 9)

            label_text = text  # ví dụ: '9.1'

            extra_text = ""
            tooltip = ""

            # Nếu là buổi học chính thức
            if group_id and not is_cancelled and "[Bù]" not in text:
                # Lấy tên nhóm
                group_name_res = self.db.execute_query("SELECT name FROM groups WHERE id = ?", (group_id,), fetch='one')
                group_name = group_name_res[0] if group_name_res else text

                # 🔢 Lấy số buổi đã học trong chu kỳ hiện tại
                student_sample = self.db.execute_query("SELECT id FROM students WHERE group_id = ? LIMIT 1",
                                                       (group_id,), fetch='one')
                total = self.db.execute_query(
                    "SELECT sessions FROM packages p JOIN students s ON s.package_id = p.id WHERE s.group_id = ? LIMIT 1",
                    (group_id,), fetch='one')
                if student_sample:
                    sid = student_sample[0]
                    start_date = self.db.execute_query("SELECT cycle_start_date FROM students WHERE id = ?", (sid,),
                                                       fetch='one')
                    if start_date and start_date[0]:
                        buoi_hoc = self.db.execute_query("""
                            SELECT COUNT(*) FROM attendance 
                            WHERE group_id = ? AND session_date >= ? AND status = 'Có mặt'
                        """, (group_id, start_date[0]), fetch='one')[0]
                        total_sessions = total[0] if total else 8
                        extra_text = f"Buổi {buoi_hoc}/{total_sessions}"

                # 👨‍🏫 Lấy danh sách học sinh
                hs_list = self.db.execute_query("SELECT name FROM students WHERE group_id = ?", (group_id,),
                                                fetch='all') or []
                tooltip = "Học sinh:\n" + "\n".join(f"- {h[0]}" for h in hs_list)

                label_text = f"Nhóm {group_name}"

            elif "[Bù]" in text:
                # Không can thiệp ô học bù
                label_text = text

            # Nội dung hiển thị
            lbl = ttk.Label(frame, text=label_text + ("\n" + extra_text if extra_text else ""),
                            anchor="center", background=color, font=font_style, wraplength=120, justify="center")
            lbl.pack(fill="both", expand=True)

            # Tạo biến lưu thông tin buổi học
            session_info = {'group_id': group_id, 'group_name': text.split(' ')[0], 'date': session_date,
                            'is_cancelled': is_cancelled}

            # Gắn sự kiện chuột phải để hiện menu context
            lbl.bind("<Button-3>", lambda e, info=session_info: self.show_session_context_menu(e, info))
            frame.bind("<Button-3>", lambda e, info=session_info: self.show_session_context_menu(e, info))

            # Gắn click trái mở chi tiết
            if not is_cancelled and group_id:
                lbl.bind("<Button-1>",
                         lambda e, d=session_date, gid=group_id, gname=label_text: self.open_session_detail(d, gid,
                                                                                                            gname))
                frame.bind("<Button-1>",
                           lambda e, d=session_date, gid=group_id, gname=label_text: self.open_session_detail(d, gid,
                                                                                                              gname))

            # Tooltip
            if tooltip:
                from utils import ToolTip
                ToolTip(lbl, tooltip)
                ToolTip(frame, tooltip)

        except (ValueError, IndexError):
            pass

    # Hiển thị lớp sắp diễn ra trong 30 phút tới (nếu có)
    def update_today_schedule(self):
        for widget in self.today_schedule_frame.winfo_children(): widget.destroy()
        today_vn, today_date_str = DAYS_OF_WEEK_VN[datetime.now().weekday()], datetime.now().strftime("%Y-%m-%d")

        all_today = []
        # Lấy lịch nhóm
        for name, slot in self.db.execute_query(
                "SELECT g.name, s.time_slot FROM schedule s JOIN groups g ON s.group_id = g.id WHERE s.day_of_week = ? ORDER BY s.time_slot",
                (today_vn,), fetch='all') or []:
            all_today.append({'time': slot, 'text': f"Nhóm {name}"})

        # Lấy lịch bù riêng
        for name, slot in self.db.execute_query(
                "SELECT s.name, m.time_slot FROM makeup_sessions m JOIN students s ON m.student_id=s.id WHERE m.session_date = ? AND m.is_private = 1 ORDER BY m.time_slot",
                (today_date_str,), fetch='all') or []:
            all_today.append({'time': slot, 'text': f"[Bù] {name}"})

        all_today.sort(key=lambda x: x['time'])

        if not all_today:
            ttk.Label(self.today_schedule_frame, text="Hôm nay không có lớp.").pack(anchor="w")
            return

        for session in all_today:
            ttk.Label(self.today_schedule_frame, text=f"- {session['time']}: {session['text']}").pack(anchor="w")

    # Hiện menu chuột phải trên buổi học (hủy/phục hồi)
    def show_session_context_menu(self, event, session_info):
        self.clicked_session_info = session_info

        context_menu = tk.Menu(self, tearoff=0)
        if session_info['is_cancelled']:
            context_menu.add_command(label="Phục hồi buổi học này", command=self.restore_single_session)
        else:
            context_menu.add_command(label="Hủy buổi học này", command=self.cancel_single_session)

        context_menu.post(event.x_root, event.y_root)

    # Hủy 1 buổi học cụ thể (thêm vào bảng cancelled_sessions)
    def show_day_header_context_menu(self, event, day_index):
        self.clicked_day_info = {'day_index': day_index}
        self.day_header_context_menu.post(event.x_root, event.y_root)

    # Phục hồi buổi học đã bị hủy
    def cancel_single_session(self):
        info = self.clicked_session_info
        group_id, group_name, date = info['group_id'], info['group_name'], info['date']
        date_str = date.strftime('%Y-%m-%d')
        msg = f"Bạn có chắc chắn muốn hủy buổi học của Nhóm {group_name} vào ngày {date_str} không?\nTất cả học sinh trong nhóm sẽ được ghi nhận nghỉ."
        if not messagebox.askyesno("Xác nhận Hủy lịch", msg): return
        self._perform_cancellation(group_id, date_str)
        self.update_all_schedules()

    # Hiện menu chuột phải trên tiêu đề ngày
    def restore_single_session(self):
        info = self.clicked_session_info
        group_id, group_name, date = info['group_id'], info['group_name'], info['date']
        date_str = date.strftime('%Y-%m-%d')

        msg = f"Bạn có chắc chắn muốn phục hồi buổi học của Nhóm {group_name} vào ngày {date_str} không?\n\nCác ghi nhận 'Nghỉ do GV bận' của học sinh sẽ bị xóa."
        if not messagebox.askyesno("Xác nhận Phục hồi", msg):
            return

        # 1. Xóa khỏi bảng đã hủy
        self.db.execute_query("DELETE FROM cancelled_sessions WHERE group_id = ? AND cancelled_date = ?",
                              (group_id, date_str))

        # 2. Xóa các lượt điểm danh "Nghỉ do GV bận" tương ứng
        self.db.execute_query(
            "DELETE FROM attendance WHERE group_id = ? AND session_date = ? AND status = 'Nghỉ do GV bận'",
            (group_id, date_str))

        self.update_all_schedules()

    # Hủy tất cả buổi học trong một ngày
    def cancel_day_sessions(self):
        day_index = self.clicked_day_info['day_index']
        day_vn = DAYS_OF_WEEK_VN[day_index]
        today = datetime.now();
        start_of_week = today - timedelta(days=today.weekday())
        target_date = start_of_week + timedelta(days=day_index);
        date_str = target_date.strftime('%Y-%m-%d')
        groups_to_cancel = self.db.execute_query(
            "SELECT g.id, g.name FROM schedule s JOIN groups g ON s.group_id = g.id WHERE s.day_of_week=?", (day_vn,),
            fetch='all') or []
        if not groups_to_cancel: messagebox.showinfo("Thông báo",
                                                     f"Không có lớp nào được lên lịch vào {day_vn} ngày {date_str}."); return
        group_names = ", ".join([g[1] for g in groups_to_cancel])
        msg = f"Bạn có chắc chắn muốn hủy TẤT CẢ các buổi học trong {day_vn} ({date_str}) không?\nCác nhóm bị ảnh hưởng: {group_names}."
        if not messagebox.askyesno("Xác nhận Hủy lịch Cả Ngày", msg): return
        for group_id, _ in groups_to_cancel: self._perform_cancellation(group_id, date_str)
        self.update_all_schedules()

    # Ghi nhận học sinh nghỉ do GV bận cho buổi bị hủy
    def _perform_cancellation(self, group_id, date_str):
        self.db.execute_query("INSERT OR IGNORE INTO cancelled_sessions (group_id, cancelled_date) VALUES (?, ?)",
                              (group_id, date_str))
        for (student_id,) in self.db.execute_query("SELECT id FROM students WHERE group_id = ?", (group_id,),
                                                   fetch='all') or []:
            query = "INSERT INTO attendance (student_id, group_id, session_date, status, make_up_status) VALUES (?, ?, ?, 'Nghỉ do GV bận', 'Chưa sắp xếp') ON CONFLICT(student_id, group_id, session_date) DO UPDATE SET status = excluded.status, make_up_status = excluded.make_up_status"
            self.db.execute_query(query, (student_id, group_id, date_str))

    def open_exercise_tree_manager(self):
        from ui.create_exercise_tree_window import ExerciseTreeManager
        ExerciseTreeManager(self)

    # Mở giao diện điểm danh và nhập chủ đề buổi học
    def open_session_detail(self, session_date, group_id=None, group_name=None, makeup_info=None):
        SessionDetailWindow(self, self.db, session_date, group_id=group_id, group_name=group_name,
                            makeup_info=makeup_info)

    # Mở cửa sổ quản lý học sinh
    def open_student_window(self):
        win = StudentWindow(self, self.db);
        win.grab_set()

    # Mở cửa sổ quản lý nhóm học
    def open_group_window(self):
        win = GroupWindow(self, self, self.db);
        win.grab_set()

    # Mở báo cáo chuyên cần
    def open_attendance_report(self):
        win = AttendanceReportWindow(self, self.db);
        win.grab_set()

    # Mở quản lý gói học
    def open_progress_report(self):
        win = ProgressReportWindow(self, self.db);
        win.grab_set()

    # Mở quản lý gói học
    def open_package_window(self):
        win = PackageWindow(self, self.db);
        win.grab_set()

    # Mở cửa sổ tính học phí chu kỳ
    def open_salary_window(self):
        win = SalaryWindow(self, self.db);
        win.grab_set()

    # MỞ CỬA SỔ: Hồ sơ năng lực học sinh
    def open_student_skill_report(self):
        win = StudentSkillReportWindow(self, self.db)
        win.grab_set()

    # Mở của sổ Gợi ý nhóm học
    def open_group_suggestion(self):
        win = GroupSuggestionWindow(self, self.db)
        win.grab_set()

    # Chuyển tuần hiển thị lịch theo hướng trước/sau
    def change_week(self, days):
        self.current_week_start += timedelta(days=days)
        self.update_day_headers()
        self.update_schedule_grid()

    # mở gợi ý bài tập
    def open_exercise_suggestion(self):
        ExerciseSuggestionWindow(self, self.db)

    # Mở Thêm bài tập
    def open_add_exercise(self):
        AddExerciseWindow(self, self.db)

    # Mở Quản lí bài tập
    def open_exercise_manager(self):
        try:
            # 🧱 Kiểm tra & tạo bảng exercises nếu thiếu
            self.db.execute_query("""
                CREATE TABLE IF NOT EXISTS exercises (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chu_de TEXT,
                    ten_bai TEXT,
                    loai_tap TEXT,
                    noi_dung TEXT,
                    ghi_chu TEXT
                );
            """)
            ExerciseManagerWindow(self, self.db)
        except Exception as e:
            messagebox.showerror("Lỗi CSDL", f"Không thể mở quản lý bài tập:\n{e}")

    # Giao Bài Tập
    def open_assign_exercise(self):
        AssignExerciseWindow(self, self.db)

    # Bài tập đã giao
    def open_assigned_exercises(self):
        AssignedExerciseManagerWindow(self, self.db)

    # Nộp bài tập
    def open_submit_window(self):
        SubmitExerciseWindow(self, self.db)

    # Bài đã nộp
    def open_submitted_manager(self):
        SubmittedExerciseManagerWindow(self, self.db)

    def fix_missing_exercises_table(self):
        self.db.create_exercises_table_if_missing()
        messagebox.showinfo("Xong", "Đã kiểm tra và tạo bảng exercises nếu còn thiếu.")

    def open_dashboard(self):
        from main import DashboardWindow  # Lưu ý: dùng DashboardWindow, không dùng Tk nữa
        DashboardWindow(self, self.db)

    # Quay về tuần hiện tại (có ngày hôm nay)
    def go_to_today(self):
        self.current_week_start = datetime.now() - timedelta(days=datetime.now().weekday())
        self.update_day_headers()
        self.update_schedule_grid()

class DashboardWindow(tk.Tk):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.title("📚 Bảng điều khiển - Phần mềm Gia sư")
        self.geometry("1100x750")
        self.configure(bg="#f5f5f5")

        # 📂 Chia nhóm các chức năng
        self.sections = {
            "📂 Quản lý học tập": [
                {"label": "Học sinh", "icon": "assets/icons/students.png", "command": lambda: StudentWindow(self, self.db)},
                {"label": "Nhóm học", "icon": "assets/icons/groups.png", "command": lambda: GroupWindow(self, self, self.db)},
                {"label": "Chuyên cần", "icon": "assets/icons/attendance.png", "command": lambda: AttendanceReportWindow(self, self.db)},
                {"label": "Lịch dạy", "icon": "assets/icons/calendar.png", "command": lambda: App(self.db)},
            ],
            "📝 Bài tập & Câu hỏi": [
                {"label": "Giao bài", "icon": "assets/icons/assignment.png", "command": lambda: AssignExerciseWindow(self, self.db)},
                {"label": "Nộp bài", "icon": "assets/icons/submit.png", "command": lambda: SubmitExerciseWindow(self, self.db)},
                {"label": "Đã nộp", "icon": "assets/icons/submitted.png", "command": lambda: SubmittedExerciseManagerWindow(self, self.db)},
                {"label": "Ngân hàng câu hỏi", "icon": "assets/icons/question_bank.png", "command": lambda: QuestionBankWindow(self, self.db)},
                {"label": "Gợi ý bài", "icon": "assets/icons/suggest.png", "command": lambda: ExerciseSuggestionWindow(self, self.db)},
                {"label": "Tạo đề", "icon": "assets/icons/test.png", "command": lambda: CreateTestWindow(self, self.db)},
                {"label": "Cây thư mục", "icon": "assets/icons/folder.png",
                 "command": lambda: ExerciseTreeManager(self)},
            ],
            "📊 Báo cáo & Đánh giá": [
                {"label": "Tiến độ", "icon": "assets/icons/progress.png", "command": lambda: ProgressReportWindow(self, self.db)},
                {"label": "Năng lực", "icon": "assets/icons/skill.png", "command": lambda: StudentSkillReportWindow(self, self.db)},
                {"label": "Đánh giá", "icon": "assets/icons/rating.png", "command": lambda: SkillRatingWindow(self, self.db, self.db.get_all_students())},
                {"label": "Gợi ý nhóm", "icon": "assets/icons/group_suggest.png", "command": lambda: GroupSuggestionWindow(self, self.db)},
                {"label": "Học phí", "icon": "assets/icons/salary.png", "command": lambda: SalaryWindow(self, self.db)},
            ]
        }

        self.build_dashboard()

    def build_dashboard(self):
        # Scrollable dashboard
        canvas = tk.Canvas(self, bg="#f5f5f5")
        scrollbar = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg="#f5f5f5")

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for section, items in self.sections.items():
            label = tk.Label(scroll_frame, text=section, font=("Helvetica", 14, "bold"), bg="#f5f5f5", anchor="w")
            label.pack(padx=20, pady=(20, 10), anchor="w")

            group_frame = tk.Frame(scroll_frame, bg="#f5f5f5")
            group_frame.pack(padx=20, pady=10, anchor="w")

            for idx, feat in enumerate(items):
                box = tk.Frame(group_frame, bg="#ffffff", bd=1, relief="raised", padx=10, pady=10)
                box.grid(row=idx // 5, column=idx % 5, padx=10, pady=10)

                try:
                    if os.path.exists(feat["icon"]):
                        img = Image.open(feat["icon"]).resize((64, 64))
                        photo = ImageTk.PhotoImage(img)
                        if not hasattr(self, "photos"):
                            self.photos = []
                        self.photos.append(photo)
                    else:
                        print("❌ Không tìm thấy ảnh:", feat["icon"])
                        photo = None
                except Exception as e:
                    print("🔥 Lỗi ảnh:", e)
                    photo = None

                btn = tk.Button(box,
                                text=feat["label"],
                                image=photo,
                                compound="top",
                                font=("Helvetica", 10, "bold"),
                                width=100,
                                height=100,
                                command=feat["command"],
                                bg="#ffffff")
                btn.pack()

# 🔰 Khởi chạy phần mềm
if __name__ == "__main__":
    db = DatabaseManager()
    app = DashboardWindow(db)
    app.mainloop()
