import tkinter as tk
from tkinter import ttk, messagebox
class PackageWindow(tk.Toplevel):
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.db = db_manager
        self.title("Quản lý Gói học")
        self.geometry("600x400")
        self.grab_set()

        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)

        list_frame = ttk.LabelFrame(main_frame, text="Danh sách Gói học", padding="10")
        list_frame.pack(fill="both", expand=True, pady=5)

        self.tree = ttk.Treeview(list_frame, columns=("ID", "Tên gói", "Số buổi", "Học phí"), show="headings")
        self.tree.heading("ID", text="ID"); self.tree.column("ID", width=30)
        self.tree.heading("Tên gói", text="Tên gói")
        self.tree.heading("Số buổi", text="Số buổi / 4 tuần"); self.tree.column("Số buổi", anchor="center")
        self.tree.heading("Học phí", text="Học phí (VND)"); self.tree.column("Học phí", anchor="e")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_package_select)

        form_frame = ttk.LabelFrame(main_frame, text="Chi tiết Gói học", padding="10")
        form_frame.pack(fill="x", pady=5)

        ttk.Label(form_frame, text="Tên gói:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.name_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.name_var, width=30).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(form_frame, text="Số buổi (trong 4 tuần):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.sessions_var = tk.IntVar(value=8)
        ttk.Entry(form_frame, textvariable=self.sessions_var, width=10).grid(row=1, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(form_frame, text="Học phí (VND):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.price_var = tk.DoubleVar(value=0)
        ttk.Entry(form_frame, textvariable=self.price_var, width=20).grid(row=2, column=1, padx=5, pady=5, sticky="w")

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Thêm mới", command=self.add_package).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cập nhật", command=self.update_package).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Xóa", command=self.delete_package).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Làm mới", command=self.clear_form).pack(side="left", padx=5)

        self.load_packages()

    def load_packages(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for row in self.db.execute_query("SELECT id, name, sessions, price FROM packages ORDER BY name", fetch='all') or []:
            self.tree.insert("", "end", values=tuple(row))

    def on_package_select(self, event):
        if not self.tree.selection(): return
        item = self.tree.item(self.tree.selection()[0])['values']
        self.name_var.set(item[1]); self.sessions_var.set(item[2]); self.price_var.set(item[3])

    def add_package(self):
        name, sessions, price = self.name_var.get(), self.sessions_var.get(), self.price_var.get()
        if not name or sessions <= 0 or price <= 0:
            messagebox.showerror("Lỗi", "Vui lòng nhập đầy đủ và hợp lệ.", parent=self); return
        self.db.execute_query("INSERT INTO packages (name, sessions, price) VALUES (?, ?, ?)", (name, sessions, price))
        self.load_packages(); self.clear_form()

    def update_package(self):
        if not self.tree.selection(): return
        package_id = self.tree.item(self.tree.selection()[0])['values'][0]
        name, sessions, price = self.name_var.get(), self.sessions_var.get(), self.price_var.get()
        self.db.execute_query("UPDATE packages SET name=?, sessions=?, price=? WHERE id=?", (name, sessions, price, package_id))
        self.load_packages(); self.clear_form()

    def delete_package(self):
        if not self.tree.selection(): return
        if not messagebox.askyesno("Xác nhận", "Xóa gói học này sẽ gỡ gói học khỏi các học sinh đang được gán. Bạn có chắc không?", parent=self): return
        package_id = self.tree.item(self.tree.selection()[0])['values'][0]
        self.db.execute_query("DELETE FROM packages WHERE id=?", (package_id,))
        self.load_packages(); self.clear_form()

    def clear_form(self):
        self.name_var.set(""); self.sessions_var.set(8); self.price_var.set(0)
        if self.tree.selection(): self.tree.selection_remove(self.tree.selection())
