import tkinter as tk
from tkinter import ttk, messagebox
from constants import DAYS_OF_WEEK_VN, FIXED_TIME_SLOTS

class GroupWindow(tk.Toplevel):
    # Giao diện quản lý nhóm học (tên, khối, lịch, sĩ số)
    def __init__(self, parent, app, db_manager):
        super().__init__(parent)
        self.db = db_manager
        self.parent_app = app
        self.title("Quản lý Nhóm học")
        self.geometry("800x600")

        left_frame = ttk.Frame(self, padding="10")
        left_frame.pack(side="left", fill="both", expand=True)
        ttk.Label(left_frame, text="Danh sách các nhóm học", font=("Helvetica", 14, "bold")).pack(pady=10)
        # THAY ĐỔI: Thêm cột "Sĩ số"
        self.tree = ttk.Treeview(left_frame, columns=("ID", "Tên nhóm", "Khối lớp", "Sĩ số", "Lịch học"),
                                 show="headings")
        self.tree.heading("ID", text="ID");
        self.tree.column("ID", width=30)
        self.tree.heading("Tên nhóm", text="Tên nhóm")
        self.tree.heading("Khối lớp", text="Khối lớp");
        self.tree.column("Khối lớp", width=60, anchor="center")
        self.tree.heading("Sĩ số", text="Sĩ số");
        self.tree.column("Sĩ số", width=50, anchor="center")
        self.tree.heading("Lịch học", text="Lịch học")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_group_select)
        for col, txt in {"ID": "ID", "Tên nhóm": "Tên nhóm", "Khối lớp": "Khối lớp",
                         "Lịch học": "Lịch học"}.items(): self.tree.heading(col, text=txt)
        self.tree.column("ID", width=30);
        self.tree.pack(fill="both", expand=True);
        self.tree.bind("<<TreeviewSelect>>", self.on_group_select)

        right_frame = ttk.Frame(self, padding="10");
        right_frame.pack(side="right", fill="y")
        ttk.Label(right_frame, text="Thông tin nhóm", font=("Helvetica", 14, "bold")).pack(pady=10)
        ttk.Label(right_frame, text="Tên nhóm (ví dụ: 9.1, 10.2):").pack(anchor="w");
        self.name_var = tk.StringVar();
        ttk.Entry(right_frame, textvariable=self.name_var, width=30).pack(pady=5, anchor="w")
        ttk.Label(right_frame, text="Khối lớp:").pack(anchor="w");
        self.grade_var = tk.StringVar();
        ttk.Entry(right_frame, textvariable=self.grade_var, width=30).pack(pady=5, anchor="w")
        ttk.Label(right_frame, text="Lịch học:", font=("Helvetica", 12, "bold")).pack(pady=10, anchor="w");
        self.schedule_vars = {}
        schedule_frame = ttk.Frame(right_frame);
        schedule_frame.pack(anchor="w")
        for day in DAYS_OF_WEEK_VN:
            frame = ttk.LabelFrame(schedule_frame, text=day);
            frame.pack(fill="x", pady=2);
            self.schedule_vars[day] = {}
            for slot in FIXED_TIME_SLOTS: var = tk.BooleanVar(); ttk.Checkbutton(frame, text=slot, variable=var).pack(
                side="left", padx=5); self.schedule_vars[day][slot] = var
        btn_frame = ttk.Frame(right_frame);
        btn_frame.pack(pady=20)
        for txt, cmd in {"Thêm mới": self.add_group, "Cập nhật": self.update_group, "Xóa": self.delete_group,
                         "Làm mới form": self.clear_form}.items():
            ttk.Button(btn_frame, text=txt, command=cmd).pack(side="left", padx=5)
        self.load_groups()

    # Tải danh sách nhóm học và hiển thị lên bảng
    def load_groups(self):
        # Xóa dữ liệu cũ trên cây
        for i in self.tree.get_children():
            self.tree.delete(i)

        # Chỉ cần gọi một hàm duy nhất từ DatabaseManager
        all_groups = self.db.get_groups_with_details()

        # Hiển thị dữ liệu đã được xử lý sẵn
        for group in all_groups:
            self.tree.insert("", "end", values=(
                group["id"],
                group["name"],
                group["grade"],
                group["student_count"],
                group["schedule_str"]
            ))
    # Hiển thị thông tin nhóm đã chọn lên form
    def on_group_select(self, event):
        if not self.tree.selection(): return
        g_id, name, grade, _ = self.tree.item(self.tree.selection()[0])['values']
        self.name_var.set(name);
        self.grade_var.set(grade)
        for slots in self.schedule_vars.values():
            for var in slots.values(): var.set(False)
        for day, slot in self.db.execute_query("SELECT day_of_week, time_slot FROM schedule WHERE group_id = ?",
                                               (g_id,), fetch='all') or []:
            if day in self.schedule_vars and slot in self.schedule_vars[day]: self.schedule_vars[day][slot].set(True)

    # Thêm nhóm học mới và lưu lịch học
    def add_group(self):
        name, grade = self.name_var.get(), self.grade_var.get()
        if not name or not grade: messagebox.showerror("Lỗi", "Tên nhóm và Khối lớp không được để trống."); return
        g_id = self.db.execute_query("INSERT INTO groups (name, grade) VALUES (?, ?)", (name, grade))
        if g_id:
            self._save_schedule(g_id);
            messagebox.showinfo("Thành công", "Đã thêm nhóm mới.")
            self.load_groups();
            self.clear_form();
            self.parent_app.update_all_schedules()
        else:
            messagebox.showerror("Lỗi", "Tên nhóm có thể đã tồn tại.")

    # Cập nhật tên, khối và lịch học của nhóm
    def update_group(self):
        if not self.tree.selection(): messagebox.showerror("Lỗi", "Vui lòng chọn nhóm."); return
        g_id = self.tree.item(self.tree.selection()[0])['values'][0];
        name, grade = self.name_var.get(), self.grade_var.get()
        self.db.execute_query("UPDATE groups SET name = ?, grade = ? WHERE id = ?", (name, grade, g_id))
        self.db.execute_query("DELETE FROM schedule WHERE group_id = ?", (g_id,))
        self._save_schedule(g_id);
        messagebox.showinfo("Thành công", "Đã cập nhật thông tin nhóm.")
        self.load_groups();
        self.clear_form();
        self.parent_app.update_all_schedules()

    # Xóa nhóm học (nếu không còn học sinh)
    def delete_group(self):
        if not self.tree.selection(): messagebox.showerror("Lỗi", "Vui lòng chọn nhóm."); return
        if not messagebox.askyesno("Xác nhận", "Bạn có chắc chắn muốn xóa nhóm này?"): return
        g_id = self.tree.item(self.tree.selection()[0])['values'][0]
        if self.db.execute_query("SELECT id FROM students WHERE group_id = ?", (g_id,),
                                 fetch='all'): messagebox.showerror("Lỗi",
                                                                    "Không thể xóa nhóm vì vẫn còn học sinh."); return
        self.db.execute_query("DELETE FROM groups WHERE id = ?", (g_id,))
        messagebox.showinfo("Thành công", "Đã xóa nhóm.");
        self.load_groups();
        self.clear_form();
        self.parent_app.update_all_schedules()

    # Lưu lịch học cố định của nhóm vào CSDL
    def _save_schedule(self, group_id):
        for day, slots in self.schedule_vars.items():
            for slot, var in slots.items():
                if var.get(): self.db.execute_query(
                    "INSERT INTO schedule (group_id, day_of_week, time_slot) VALUES (?, ?, ?)", (group_id, day, slot))

    # Xóa trắng form nhập và bỏ chọn bảng nhóm
    def clear_form(self):
        self.name_var.set("");
        self.grade_var.set("")
        for slots in self.schedule_vars.values():
            for var in slots.values(): var.set(False)
        if self.tree.selection(): self.tree.selection_remove(self.tree.selection())
