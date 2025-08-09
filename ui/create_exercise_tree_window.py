import os
import tkinter as tk
from tkinter import ttk, messagebox
from database import DatabaseManager

class ExerciseTreeManager(tk.Toplevel):
    LEVELS = ["Môn", "Lớp", "Chủ đề", "Dạng", "Mức độ"]
    DEFAULT_LEVELS = ["Nhận biết", "Thông hiểu", "Vận dụng", "Vận dụng cao", "Sáng tạo"]

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Quản lý cây thư mục bài tập")
        self.geometry("800x500")
        self.db = parent.db if hasattr(parent, "db") else DatabaseManager()
        self.tree_nodes = {}
        self.selected_node_id = None

        main = ttk.Frame(self, padding=10)
        main.pack(fill="both", expand=True)

        # Treeview bên trái
        left = ttk.Frame(main)
        left.pack(side="left", fill="both", expand=True)

        ttk.Label(left, text="Cây thư mục").pack(anchor="w")
        self.tree = ttk.Treeview(left)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select_node)

        # Bên phải: khung nhập
        right = ttk.Frame(main, padding=(10, 0))
        right.pack(side="right", fill="y")

        ttk.Label(right, text="Thêm mục con mới").grid(row=0, column=0, columnspan=2, pady=5)

        ttk.Label(right, text="Cấp thêm:").grid(row=1, column=0, sticky="w")
        self.level_var = tk.StringVar()
        self.level_cb = ttk.Combobox(right, textvariable=self.level_var, values=self.LEVELS, state="readonly")
        self.level_cb.grid(row=1, column=1, sticky="ew", pady=3)

        ttk.Label(right, text="Tên (cách nhau bởi dấu phẩy):").grid(row=2, column=0, columnspan=2, sticky="w")
        self.name_entry = ttk.Entry(right, width=30)
        self.name_entry.grid(row=3, column=0, columnspan=2, pady=5)

        ttk.Button(right, text="➕ Thêm vào cây", command=self.add_node).grid(row=4, column=0, columnspan=2, pady=10)
        ttk.Button(right, text="❌ Xoá mục đã chọn", command=self.delete_node).grid(row=5, column=0, columnspan=2, pady=5)

        self.refresh_tree()

    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        self.tree_nodes.clear()

        rows = self.db.execute_query(
            "SELECT id, parent_id, name, level FROM exercise_tree ORDER BY parent_id, level, name",
            fetch="all"
        )

        tree_dict = {}
        for row in rows:
            tree_dict.setdefault(row["parent_id"], []).append(row)

        def build(parent_id, parent_item):
            for node in tree_dict.get(parent_id, []):
                iid = str(node["id"])
                item = self.tree.insert(parent_item, "end", iid=iid, text=f"{node['name']} ({node['level']})")
                self.tree_nodes[iid] = node["id"]
                build(node["id"], item)

        build(None, "")

    def on_select_node(self, event=None):
        selected = self.tree.focus()
        self.selected_node_id = self.tree_nodes.get(selected)

    def add_node(self):
        level = self.level_var.get()
        names = self.name_entry.get().strip()
        if not level or not names:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng chọn cấp và nhập tên.", parent=self)
            return
        if not self.selected_node_id and level != "Môn":
            messagebox.showwarning("Thiếu mục cha", "Hãy chọn mục cha trên cây để thêm cấp con.", parent=self)
            return

        parent_id = self.selected_node_id if level != "Môn" else None

        added_count = 0
        for name in [n.strip() for n in names.split(",") if n.strip()]:
            # Thêm node
            self.db.execute_query(
                "INSERT OR IGNORE INTO exercise_tree (parent_id, name, level) VALUES (?, ?, ?)",
                (parent_id, name, level)
            )

            # Nếu là Dạng thì thêm mặc định 5 mức độ
            if level == "Dạng":
                child_id = self.db.execute_query(
                    "SELECT id FROM exercise_tree WHERE parent_id=? AND name=? AND level=?",
                    (parent_id, name, level), fetch="one"
                )[0]
                for muc in self.DEFAULT_LEVELS:
                    self.db.execute_query(
                        "INSERT OR IGNORE INTO exercise_tree (parent_id, name, level) VALUES (?, ?, ?)",
                        (child_id, muc, "Mức độ")
                    )
            added_count += 1

        self.name_entry.delete(0, "end")
        self.refresh_tree()
        messagebox.showinfo("Thành công", f"Đã thêm {added_count} mục.", parent=self)

    def delete_node(self):
        if not self.selected_node_id:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn mục trên cây để xoá.", parent=self)
            return

        # Kiểm tra có bài nào gắn vào không
        count = self.db.execute_query("SELECT COUNT(*) FROM question_bank WHERE tree_id=?", (self.selected_node_id,), fetch="one")[0]
        if count > 0:
            messagebox.showerror("Không thể xoá", f"Mục này đang chứa {count} câu hỏi. Hãy chuyển hoặc xoá trước.", parent=self)
            return

        if not messagebox.askyesno("Xác nhận", "Bạn có chắc chắn muốn xoá mục này và toàn bộ mục con?", parent=self):
            return

        self._delete_recursive(self.selected_node_id)
        self.refresh_tree()
        messagebox.showinfo("Đã xoá", "Đã xoá thành công mục đã chọn.", parent=self)

    def _delete_recursive(self, node_id):
        children = self.db.execute_query("SELECT id FROM exercise_tree WHERE parent_id=?", (node_id,), fetch="all") or []
        for c in children:
            self._delete_recursive(c["id"])
        self.db.execute_query("DELETE FROM exercise_tree WHERE id=?", (node_id,))
