import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
class SalaryWindow(tk.Toplevel):
    """Cửa sổ để tính lương theo chu kỳ 4 tuần."""

    # Giao diện tính học phí học sinh theo chu kỳ 4 tuần
    def __init__(self, parent, db_manager):
        super().__init__(parent);
        self.db = db_manager;
        self.title("Tính lương Gia sư");
        self.geometry("800x600")
        main_frame = ttk.Frame(self, padding="10");
        main_frame.pack(fill="both", expand=True)

        # Phần thiết lập và chọn chu kỳ
        filter_frame = ttk.LabelFrame(main_frame, text="Chọn chu kỳ tính lương", padding=10);
        filter_frame.pack(fill="x")
        ttk.Label(filter_frame, text="Ngày BĐ chu kỳ đầu tiên:").grid(row=0, column=0, padx=5, pady=5)

        start_date_db = self.db.execute_query("SELECT value FROM settings WHERE key='salary_start_date'", fetch='one')
        self.start_date_var = tk.StringVar(value=start_date_db[0] if start_date_db else "2025-06-30")

        ttk.Entry(filter_frame, textvariable=self.start_date_var).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(filter_frame, text="Lưu", command=self.save_start_date).grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(filter_frame, text="Chọn chu kỳ để tính lương:").grid(row=1, column=0, padx=5, pady=5)
        self.cycle_var = tk.StringVar()
        self.cycle_combo = ttk.Combobox(filter_frame, textvariable=self.cycle_var, state='readonly', width=40)
        self.cycle_combo.grid(row=1, column=1, columnspan=2, padx=5, pady=5)
        ttk.Button(filter_frame, text="Tính lương", command=self.calculate_salary).grid(row=2, column=1, pady=10)

        self.generate_cycles()

        # Phần kết quả
        result_frame = ttk.LabelFrame(main_frame, text="Bảng kê chi tiết", padding=10);
        result_frame.pack(fill="both", expand=True, pady=10)

        # THAY ĐỔI: Thêm cột STT và Lớp
        self.tree = ttk.Treeview(result_frame, columns=("STT", "Họ và tên", "Lớp", "Gói học", "Học phí"),
                                 show="headings")
        self.tree.heading("STT", text="STT");
        self.tree.column("STT", width=40, anchor="center")
        self.tree.heading("Họ và tên", text="Họ và tên")
        self.tree.heading("Lớp", text="Lớp");
        self.tree.column("Lớp", width=50, anchor="center")
        self.tree.heading("Gói học", text="Gói học")
        self.tree.heading("Học phí", text="Học phí");
        self.tree.column("Học phí", anchor="e")
        self.tree.pack(fill="both", expand=True)

        self.total_label = ttk.Label(result_frame, text="TỔNG CỘNG: 0 VND", font=("Helvetica", 14, "bold"))
        self.total_label.pack(pady=10, anchor="e")

    # Lưu ngày bắt đầu chu kỳ đầu tiên vào CSDL
    def save_start_date(self):
        start_date = self.start_date_var.get()
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
            self.db.execute_query("INSERT OR REPLACE INTO settings (key, value) VALUES ('salary_start_date', ?)",
                                  (start_date,))
            messagebox.showinfo("Thành công", "Đã lưu ngày bắt đầu chu kỳ.")
            self.generate_cycles()
        except ValueError:
            messagebox.showerror("Lỗi", "Định dạng ngày không hợp lệ. Vui lòng dùng YYYY-MM-DD.")

    # Tạo danh sách 12 chu kỳ liên tiếp (mỗi chu kỳ 4 tuần)
    def generate_cycles(self):
        try:
            start_date = datetime.strptime(self.start_date_var.get(), "%Y-%m-%d")
        except ValueError:
            return

        cycles = []
        for i in range(12):  # Tạo sẵn 12 chu kỳ (gần 1 năm)
            end_date = start_date + timedelta(days=27)  # 4 tuần = 28 ngày
            cycles.append(f"Chu kỳ {i + 1}: {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}")
            start_date += timedelta(days=28)

        self.cycle_combo['values'] = cycles
        if cycles: self.cycle_combo.set(cycles[0])

    # Tính tổng học phí theo chu kỳ đã chọn
    # Thay thế hàm này trong file ui/salary_window.py

    def calculate_salary(self):
        # Xóa dữ liệu cũ trên cây
        for i in self.tree.get_children():
            self.tree.delete(i)

        # Lấy dữ liệu đã được xử lý và sắp xếp sẵn từ database
        students_data = self.db.get_students_for_salary_report()

        total_salary = 0
        stt = 1  # Bắt đầu số thứ tự

        for student in students_data:
            # Chèn dữ liệu vào bảng
            price_formatted = f"{student['price']:,.0f}"
            self.tree.insert("", "end",
                             values=(stt, student['name'], student['grade'], student['package_name'], price_formatted))
            total_salary += student['price']
            stt += 1  # Tăng số thứ tự

        # Cập nhật tổng tiền
        self.total_label.config(text=f"TỔNG CỘNG: {total_salary:,.0f} VND")