import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from utils import PlaceholderEntry

class StudentWindow(tk.Toplevel):
    # Giao diện quản lý hồ sơ học sinh và học phí
    def __init__(self, parent, db_manager):
        super().__init__(parent);
        self.db = db_manager;
        self.title("Quản lý Học sinh");
        self.geometry("1000x700")
        main_frame = ttk.Frame(self, padding="10");
        main_frame.pack(fill="both", expand=True)
        list_frame = ttk.Frame(main_frame);
        list_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        ttk.Label(list_frame, text="Danh sách học sinh", font=("Helvetica", 14, "bold")).pack(pady=10)
        self.student_tree = ttk.Treeview(list_frame, columns=("ID", "Họ tên", "Lớp", "Nhóm"), show="headings")
        for col, txt in {"ID": "ID", "Họ tên": "Họ tên", "Lớp": "Lớp",
                         "Nhóm": "Nhóm"}.items(): self.student_tree.heading(col, text=txt)
        self.student_tree.column("ID", width=30);
        self.student_tree.pack(fill="both", expand=True);
        self.student_tree.bind("<<TreeviewSelect>>", self.on_student_select)

        form_frame = ttk.Frame(main_frame, width=400);
        form_frame.pack(side="right", fill="y");
        form_frame.pack_propagate(False)
        ttk.Label(form_frame, text="Hồ sơ học sinh", font=("Helvetica", 14, "bold")).pack(pady=10)

        info_frame = ttk.LabelFrame(form_frame, text="Thông tin cá nhân", padding=10);
        info_frame.pack(fill="x", pady=5)
        fields = ["Họ tên", "Khối lớp", "SĐT"];
        self.vars = {f: tk.StringVar() for f in fields}
        for i, f in enumerate(fields):
            ttk.Label(info_frame, text=f"{f}:").grid(row=i, column=0, sticky="w", padx=5, pady=2)
            ttk.Entry(info_frame, textvariable=self.vars[f], width=30).grid(row=i, column=1, sticky="ew", padx=5,
                                                                            pady=2)

        study_frame = ttk.LabelFrame(form_frame, text="Thông tin học tập", padding=10);
        study_frame.pack(fill="x", pady=5)
        ttk.Label(study_frame, text="Trạng thái học:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.status_var = tk.StringVar(value="Kèm riêng")
        status_frame = ttk.Frame(study_frame);
        status_frame.grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(status_frame, text="Kèm riêng", variable=self.status_var, value="Kèm riêng",
                        command=self.toggle_group_select).pack(side="left")
        ttk.Radiobutton(status_frame, text="Học nhóm", variable=self.status_var, value="Học nhóm",
                        command=self.toggle_group_select).pack(side="left")

        self.group_label = ttk.Label(study_frame, text="Chọn nhóm:");
        self.group_label.grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.group_var = tk.StringVar()
        group_names = [g[0] for g in self.db.execute_query("SELECT name FROM groups ORDER BY name", fetch='all') or []]
        self.group_combo = ttk.Combobox(study_frame, textvariable=self.group_var, values=group_names, state='readonly');
        self.group_combo.grid(row=1, column=1, sticky="ew", padx=5, pady=2)

        fee_frame = ttk.LabelFrame(form_frame, text="Thông tin học phí", padding=10);
        fee_frame.pack(fill="x", pady=5)
        ttk.Label(fee_frame, text="Gói học:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.package_var = tk.StringVar()
        packages = self.db.execute_query("SELECT id, name FROM packages ORDER BY name", fetch='all') or []
        self.package_map = {name: id for id, name in packages}
        self.package_combo = ttk.Combobox(fee_frame, textvariable=self.package_var,
                                          values=list(self.package_map.keys()), state='readonly');
        self.package_combo.grid(row=0, column=1, sticky="ew", padx=5, pady=2)

        ttk.Label(fee_frame, text="Ngày BĐ chu kỳ:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        # ---- Ngày BĐ chu kỳ với placeholder tự ẩn ----
        # tạo widget Entry
        self.cycle_date_entry = ttk.Entry(fee_frame, width=30)
        self.cycle_date_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        # gán placeholder ban đầu
        self.cycle_date_entry.insert(0, "DD-MM-YYYY")
        # khi click chuột vào ô, nếu đang là placeholder thì xóa
        self.cycle_date_entry.bind(
            "<Button-1>",
            lambda e: e.widget.delete(0, "end")
            if e.widget.get() == "DD-MM-YYYY" else None
        )
        # khi bỏ focus mà ô trống thì trả lại placeholder
        self.cycle_date_entry.bind(
            "<FocusOut>",
            lambda e: e.widget.insert(0, "DD-MM-YYYY")
            if not e.widget.get() else None
        )

        btn_frame = ttk.Frame(form_frame);
        btn_frame.pack(pady=20, fill="x", side="bottom")
        for txt, cmd in {"Thêm mới": self.add_student, "Cập nhật": self.update_student, "Xóa": self.delete_student,
                         "Làm mới": self.clear_form}.items():
            ttk.Button(btn_frame, text=txt, command=cmd).pack(side="right", padx=5)

        self.load_students();
        self.clear_form()

    # Bật/tắt chọn nhóm theo trạng thái kèm riêng hay học nhóm
    def toggle_group_select(self):
        is_group = self.status_var.get() == "Học nhóm"
        self.group_label.config(state="normal" if is_group else "disabled");
        self.group_combo.config(state="readonly" if is_group else "disabled")
        if not is_group: self.group_var.set("")

    # Tải danh sách học sinh và hiển thị vào bảng
    def load_students(self):
        for i in self.student_tree.get_children():
            self.student_tree.delete(i)

        students = self.db.get_all_students_for_display()
        for s in students:
            self.student_tree.insert("", "end", values=(s['id'], s['name'], s['grade'], s['group_name'] or "Kèm riêng"))

    # Hiển thị chi tiết học sinh được chọn lên form
    def on_student_select(self, event):
        if not self.student_tree.selection():
            return

        student_id = self.student_tree.item(self.student_tree.selection()[0])['values'][0]
        data = self.db.get_student_details_by_id(student_id)
        if not data:
            return

        self.vars["Họ tên"].set(data['name'])
        self.vars["Khối lớp"].set(data['grade'])
        self.vars["SĐT"].set(data['phone'] or "")
        self.status_var.set(data['status'])
        self.group_var.set(data['group_name'])
        self.package_var.set(data['package_name'])
        self.toggle_group_select()

        self.cycle_date_entry.delete(0, tk.END)
        if data.get('cycle_start_date'):
            try:
                display_date = datetime.strptime(data['cycle_start_date'], "%Y-%m-%d").strftime("%d-%m-%Y")
                self.cycle_date_entry.insert(0, display_date)
            except (ValueError, TypeError):
                self.cycle_date_entry.put_placeholder()
        else:
            self.cycle_date_entry.put_placeholder()

    # Đọc dữ liệu từ form nhập và chuẩn hóa lại để lưu
    def get_form_data(self):
        # Lấy dữ liệu từ các ô cơ bản
        data = {var: entry.get() for var, entry in self.vars.items()}
        data["status"] = self.status_var.get()

        # Xác định group_id nếu học nhóm
        data["group_id"] = None
        if data["status"] == "Học nhóm":
            if not self.group_var.get():
                messagebox.showerror("Lỗi", "Vui lòng chọn nhóm.")
                return None
            res = self.db.execute_query(
                "SELECT id FROM groups WHERE name = ?",
                (self.group_var.get(),),
                fetch='one'
            )
            if res:
                data["group_id"] = res[0]

        # Xác định package_id
        data["package_id"] = None
        if self.package_var.get():
            data["package_id"] = self.package_map.get(self.package_var.get())

        # Xử lý ngày BĐ chu kỳ
        cycle_date_input = self.cycle_date_entry.get()
        data["cycle_start_date"] = ""
        # Chỉ chuyển khi thực sự có ngày và khác placeholder
        if cycle_date_input and cycle_date_input != "DD-MM-YYYY":
            try:
                date_obj = datetime.strptime(cycle_date_input, "%d-%m-%Y")
                data["cycle_start_date"] = date_obj.strftime("%Y-%m-%d")
            except ValueError:
                messagebox.showerror(
                    "Lỗi Định Dạng",
                    "Ngày BĐ chu kỳ không hợp lệ. Vui lòng nhập theo định dạng DD-MM-YYYY.",
                    parent=self
                )
                return None

        return data

    # Thêm học sinh mới vào cơ sở dữ liệu
    def add_student(self):
        form_data = self.get_form_data()
        if not form_data:
            return
        name, grade = form_data["Họ tên"], form_data["Khối lớp"]
        if not name or not grade:
            messagebox.showerror("Lỗi", "Họ tên và Khối lớp là bắt buộc.")
            return

        form_data['start_date'] = datetime.now().strftime("%Y-%m-%d")
        self.db.add_student(form_data)
        messagebox.showinfo("Thành công", f"Đã thêm học sinh {name}.")
        self.load_students()
        self.clear_form()
    # Cập nhật thông tin học sinh đã chọn
    def update_student(self):
        if not self.student_tree.selection():
            messagebox.showerror("Lỗi", "Vui lòng chọn học sinh.")
            return

        student_id = self.student_tree.item(self.student_tree.selection()[0])['values'][0]
        form_data = self.get_form_data()
        if not form_data:
            return

        self.db.update_student(student_id, form_data)
        messagebox.showinfo("Thành công", f"Đã cập nhật thông tin học sinh {form_data['Họ tên']}.")
        self.load_students()
        self.clear_form()

    # Xóa học sinh đã chọn khỏi cơ sở dữ liệu
    def delete_student(self):
        if not self.student_tree.selection():
            messagebox.showerror("Lỗi", "Vui lòng chọn học sinh.")
            return
        if not messagebox.askyesno("Xác nhận", "Bạn có chắc chắn muốn xóa học sinh này?"):
            return

        student_id = self.student_tree.item(self.student_tree.selection()[0])['values'][0]
        self.db.delete_student_by_id(student_id)
        messagebox.showinfo("Thành công", "Đã xóa học sinh.")
        self.load_students()
        self.clear_form()
    # Xóa trắng form nhập và bỏ chọn học sinh
    def clear_form(self):
        for f in self.vars: self.vars[f].set("")
        self.status_var.set("Kèm riêng");
        self.group_var.set("");
        self.package_var.set("")
        # Xóa rồi chèn lại placeholder
        self.cycle_date_entry.delete(0, tk.END)
        self.cycle_date_entry.insert(0, "DD-MM-YYYY")
        if self.student_tree.selection(): self.student_tree.selection_remove(self.student_tree.selection())
        self.toggle_group_select()
