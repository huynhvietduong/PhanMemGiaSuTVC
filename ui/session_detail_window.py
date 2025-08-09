import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import os
from tkinter import filedialog
from pathlib import Path
from tkinter import messagebox
from ui.drawing_board_window import DrawingBoardWindow
# Import cửa sổ Đánh giá năng lực vì nó được gọi từ đây
from .skill_rating_window import SkillRatingWindow
class SessionDetailWindow(tk.Toplevel):
    # Giao diện điểm danh và nhập nhật ký buổi học
    def __init__(self, parent, db_manager, session_date, group_id=None, group_name=None, makeup_info=None):
        super().__init__(parent)
        self.db = db_manager
        self.is_makeup_session = makeup_info is not None
        self.session_date = session_date.strftime("%Y-%m-%d")  # Sử dụng ngày được truyền vào
        self.session_id = None  # ✅ Khởi tạo luôn để tránh lỗi AttributeError

        if self.is_makeup_session:
            self.makeup_list = makeup_info
            self.title("Chi tiết Buổi học bù")
        else:
            self.group_id = group_id
            self.group_name = group_name
            self.title(f"Chi tiết Buổi học: Nhóm {self.group_name}")

        self.geometry("800x600");
        self.grab_set()
        main_frame = ttk.Frame(self, padding="10");
        main_frame.pack(fill="both", expand=True)
        info_frame = ttk.LabelFrame(main_frame, text="Thông tin chung ℹ️");
        info_frame.pack(fill="x", pady=5)

        if self.is_makeup_session:
            ttk.Label(info_frame, text=f"Buổi học bù cho {len(self.makeup_list)} học sinh").pack(anchor="w")
            ttk.Label(info_frame, text=f"Ngày: {self.session_date}").pack(anchor="w")
        else:
            last_session_topic = self.db.execute_query(
                "SELECT topic FROM session_logs WHERE group_id = ? AND session_date < ? ORDER BY session_date DESC LIMIT 1",
                (self.group_id, self.session_date), fetch='one')
            ttk.Label(info_frame, text=f"Nhóm: {self.group_name}").pack(anchor="w")
            ttk.Label(info_frame, text=f"Ngày: {self.session_date}").pack(anchor="w")
            ttk.Label(info_frame,
                      text=f"Buổi trước đã học: {last_session_topic[0] if last_session_topic else 'Chưa có'}",
                      foreground="blue").pack(anchor="w")

        attendance_frame = ttk.LabelFrame(main_frame, text="Điểm danh ✅");
        attendance_frame.pack(fill="both", expand=True, pady=5)
        self.student_vars = {}

        if self.is_makeup_session:
            for info in self.makeup_list:
                self.create_attendance_row(attendance_frame, info['student_id'], info['student_name'])
        else:
            self.makeup_joiners = self.get_makeup_joiners()
            students = self.db.execute_query("SELECT id, name FROM students WHERE group_id = ?", (self.group_id,),
                                             fetch='all') or []
            if not students and not self.makeup_joiners:
                ttk.Label(attendance_frame, text="Chưa có học sinh nào trong nhóm này.", foreground="gray").pack(
                    pady=20)
            else:
                for student_id, student_name in students: self.create_attendance_row(attendance_frame, student_id,
                                                                                     student_name)
                if self.makeup_joiners:
                    ttk.Separator(attendance_frame).pack(fill="x", pady=5)
                    for makeup in self.makeup_joiners: self.create_attendance_row(attendance_frame,
                                                                                  makeup['student_id'],
                                                                                  f"[Bù] {makeup['student_name']}")

        log_frame = ttk.LabelFrame(main_frame, text="Nhật ký buổi dạy hôm nay ✍️");
        log_frame.pack(fill="x", pady=5)
        ttk.Label(log_frame, text="Chủ đề đã dạy:").pack(anchor="w")
        self.topic_text = tk.Text(log_frame, height=3, width=80);
        self.topic_text.pack(fill="x", expand=True, padx=5, pady=2)
        ttk.Label(log_frame, text="Bài tập về nhà:").pack(anchor="w")
        self.homework_text = tk.Text(log_frame, height=2, width=80);
        self.homework_text.pack(fill="x", expand=True, padx=5, pady=2)
        self.load_today_log()

        btn_frame = ttk.Frame(main_frame);
        btn_frame.pack(pady=10)
        if not self.is_makeup_session:
            ttk.Button(btn_frame, text="Đánh giá năng lực", command=self.open_skill_rating).pack(side="left", padx=5)

        ttk.Button(btn_frame, text="🖍️ Bảng Vẽ Bài Giảng", command=self.open_board).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Lưu & Kết thúc buổi học",
                   command=self.save_session).pack(side="left", padx=5)

        ttk.Button(log_frame, text="📂 Thêm file bài giảng", command=self.chon_file_bai_giang).pack(pady=5)
        # 📁 Danh sách file bài giảng đã lưu
        self.lesson_files_frame = ttk.LabelFrame(log_frame, text="📎 File bài giảng đã gắn:")
        self.lesson_files_frame.pack(fill="x", pady=5)

        # 🔍 Tự lấy session_id từ DB nếu đã tồn tại
        self.session_id = None
        if not self.is_makeup_session:
            row = self.db.execute_query(
                "SELECT id FROM session_logs WHERE group_id = ? AND session_date = ?",
                (self.group_id, self.session_date), fetch="one"
            )
            if row:
                self.session_id = row["id"]

        self.render_lesson_files()

    # Lấy danh sách học sinh học bù vào buổi này
    def get_makeup_joiners(self):
        query = "SELECT m.attendance_id, m.student_id, s.name FROM makeup_sessions m JOIN students s ON m.student_id = s.id WHERE m.host_group_id = ? AND m.session_date = ?"
        return [{'attendance_id': r[0], 'student_id': r[1], 'student_name': r[2]} for r in
                self.db.execute_query(query, (self.group_id, self.session_date), fetch='all') or []]

    # Tạo dòng điểm danh cho 1 học sinh
    def create_attendance_row(self, parent, student_id, display_name):
        row = ttk.Frame(parent);
        row.pack(fill="x", padx=5, pady=2)
        ttk.Label(row, text=display_name, width=25).pack(side="left")
        status_var = tk.StringVar(master=self, value="Có mặt")
        self.student_vars[student_id] = status_var
        for val in ["Có mặt", "Nghỉ có phép", "Nghỉ không phép"]: ttk.Radiobutton(row, text=val, variable=status_var,
                                                                                  value=val).pack(side="left", padx=10)

    # Tải chủ đề & bài tập đã ghi trước đó nếu có

    def load_today_log(self):
        group_id_for_log = self.group_id if not self.is_makeup_session else None
        if not group_id_for_log: return
        result = self.db.execute_query(
            "SELECT topic, homework FROM session_logs WHERE group_id = ? AND session_date = ?",
            (group_id_for_log, self.session_date), fetch='one')
        if result: self.topic_text.insert("1.0", result[0] or ""); self.homework_text.insert("1.0", result[1] or "")

    # Lưu điểm danh + chủ đề + bài tập buổi học
    def save_session(self):
        try:
            makeup_list_to_process = self.makeup_list if self.is_makeup_session else self.makeup_joiners
            for makeup in makeup_list_to_process:
                student_id = makeup['student_id']
                original_att_id = makeup['att_id'] if 'att_id' in makeup else makeup['attendance_id']
                status = self.student_vars[student_id].get()
                new_makeup_status = 'Đã dạy bù' if status == "Có mặt" else 'Vắng buổi bù'
                self.db.execute_query("UPDATE attendance SET make_up_status = ? WHERE id = ?",
                                      (new_makeup_status, original_att_id))
                self.db.execute_query("DELETE FROM makeup_sessions WHERE attendance_id = ?", (original_att_id,))

            if not self.is_makeup_session:
                for student_id, status_var in self.student_vars.items():
                    if not any(s['student_id'] == student_id for s in self.makeup_joiners):
                        query = "INSERT INTO attendance (student_id, group_id, session_date, status, make_up_status) VALUES (?, ?, ?, ?, ?) ON CONFLICT(student_id, group_id, session_date) DO UPDATE SET status = excluded.status, make_up_status = excluded.make_up_status"
                        make_up_status = 'Chưa sắp xếp' if 'Nghỉ' in status_var.get() else ''
                        self.db.execute_query(query, (student_id, self.group_id, self.session_date, status_var.get(),
                                                      make_up_status))

                topic, homework = self.topic_text.get("1.0", tk.END).strip(), self.homework_text.get("1.0",
                                                                                                     tk.END).strip()
                log_query = "INSERT OR REPLACE INTO session_logs (group_id, session_date, topic, homework) VALUES (?, ?, ?, ?)"
                self.db.execute_query(log_query, (self.group_id, self.session_date, topic, homework))

            messagebox.showinfo("Thành công", "Đã lưu thông tin buổi học.", parent=self)
            self.master.update_all_schedules()
            for win in self.master.winfo_children():
                if hasattr(win, 'load_report'):
                    win.load_report()
                    break
            self.destroy()
        except Exception as e:
            messagebox.showerror("Lỗi Lưu Trữ", f"Đã có lỗi xảy ra khi lưu dữ liệu:\n{e}", parent=self)

    # Mở cửa sổ đánh giá năng lực
    def open_skill_rating(self):
        # Lấy danh sách học sinh trong buổi học
        if self.is_makeup_session:
            student_list = [(info['student_id'], info['student_name']) for info in self.makeup_list]
        else:
            student_list = self.db.execute_query(
                "SELECT id, name FROM students WHERE group_id = ?", (self.group_id,), fetch='all') or []

        # --- Lấy chủ đề từ ô nhập (Text widget) ---
        raw_text = self.topic_text.get("1.0", tk.END).strip()

        # Tách thành danh sách các chủ đề riêng biệt (phân tách bằng dấu phẩy hoặc chấm phẩy)
        topics = []
        for part in raw_text.replace(";", ",").split(","):
            topic = part.strip()
            if topic:
                topics.append(topic)

        # Gọi giao diện đánh giá năng lực, truyền danh sách chủ đề
        SkillRatingWindow(self, self.db, student_list, default_topics=topics)

    def create_lesson_directory(base_folder, group_name, session_date):
        date_str = datetime.strptime(session_date, "%Y-%m-%d").strftime("%Y-%m-%d")
        safe_group_name = group_name.replace(" ", "_")
        folder_path = os.path.join(base_folder, "lesson_files", "teacher_001", f"{date_str}_{safe_group_name}")
        os.makedirs(folder_path, exist_ok=True)
        return folder_path

    def chon_file_bai_giang(self):
        file_path = filedialog.askopenfilename(
            title="Chọn file bài giảng",
            filetypes=[("Tất cả các file", "*.*"),
                       ("PDF", "*.pdf"),
                       ("PowerPoint", "*.pptx"),
                       ("Word", "*.docx"),
                       ("EasiNote", "*.enb"),
                       ("OneNote", "*.one")]
        )
        if file_path:
            self.luu_file_bai_giang(file_path)

    def luu_file_bai_giang(self, file_path):
        try:
            if not self.session_id:
                messagebox.showerror("Chưa lưu buổi học", "Vui lòng lưu buổi học trước khi gắn file bài giảng.",
                                     parent=self)
                return

            file_type = Path(file_path).suffix
            title = Path(file_path).stem
            notes = ""

            self.db.add_lesson_file(self.session_id, file_path, file_type, title, notes)
            messagebox.showinfo("✅ Thành công", "Đã lưu file bài giảng vào CSDL.", parent=self)
            self.render_lesson_files()

        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể lưu file bài giảng: {e}", parent=self)

    def render_lesson_files(self):
        for widget in self.lesson_files_frame.winfo_children():
            widget.destroy()

        if not self.session_id:
            ttk.Label(self.lesson_files_frame, text="⛔ Chưa có file bài giảng.").pack(anchor="w", padx=10)
            return

        rows = self.db.execute_query(
            "SELECT id, file_path, title, file_type FROM lesson_files WHERE session_id = ? ORDER BY id DESC",
            (self.session_id,), fetch='all'
        )

        if not rows:
            ttk.Label(self.lesson_files_frame, text="⛔ Chưa có file bài giảng.").pack(anchor="w", padx=10)
            return

        for row in rows:
            file_path = row["file_path"]
            title = row["title"] or os.path.basename(file_path)
            file_type = (row["file_type"] or "").lower()

            frame = ttk.Frame(self.lesson_files_frame)
            frame.pack(fill="x", padx=5, pady=2)

            ttk.Label(frame, text=title).pack(side="left", anchor="w")

            if file_type == "board" or file_path.endswith(".board.json"):
                ttk.Button(frame, text="🖍️ Mở & Sửa", width=10,
                           command=lambda p=file_path: self.open_board(board_path=p)).pack(side="right")
            else:
                ttk.Button(frame, text="📂 Mở", width=6,
                           command=lambda p=file_path: self.open_file(p)).pack(side="right")

    def open_file(self, file_path):
        try:
            if os.path.exists(file_path):
                os.startfile(file_path)  # Windows only
            else:
                messagebox.showerror("Lỗi", f"File không tồn tại:\n{file_path}", parent=self)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể mở file:\n{e}", parent=self)

    def open_board(self, board_path=None):
        if not self.session_id:
            messagebox.showerror("Chưa có buổi học", "Vui lòng lưu buổi học trước khi mở Bảng vẽ.", parent=self)
            return

        lesson_dir = os.path.join(os.getcwd(), "data", "lessons", str(self.session_id))

        def _on_board_saved(path, title):
            # Lưu vào DB rồi refresh danh sách
            self.db.add_lesson_file(self.session_id, path, "board", title, "")
            self.render_lesson_files()

        win = DrawingBoardWindow(
            self,
            group_name=self.group_name,
            session_date=self.session_date,
            session_id=self.session_id,
            lesson_dir=lesson_dir,
            board_path=board_path,    # None = tạo mới; có path = mở để sửa
            on_saved=_on_board_saved
        )
        win.grab_set()

