import os
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from database import DatabaseManager
from .create_exercise_tree_window import ExerciseTreeManager

class QuestionBankWindow(tk.Toplevel):
    def __init__(self, parent, db):
        super().__init__(parent)
        self.title("Ngân hàng câu hỏi")
        self.geometry("1200x600")
        self.resizable(True, True)
        self.attributes("-toolwindow", False)

        self.db = db if isinstance(db, DatabaseManager) else DatabaseManager(db)

        self.db.execute_query(
            """
            CREATE TABLE IF NOT EXISTS exercise_tree (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id INTEGER,
                name TEXT NOT NULL,
                level TEXT NOT NULL,
                UNIQUE(parent_id,name,level)
            )
            """
        )

        self.db.execute_query(
            """
            CREATE TABLE IF NOT EXISTS question_bank (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_text TEXT,
                options TEXT,
                correct TEXT,
                tree_id INTEGER
            )
            """
        )

        self.tree_nodes = {}
        self._build_ui()
        self.refresh_tree()

    def _build_ui(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True)

        # ===================== KHỐI NHẬP THÔNG TIN ======================
        config_frame = ttk.Frame(main_frame)
        config_frame.pack(fill="x", pady=5)

        self.tree_shown = True  # Mặc định hiển thị cây thư mục
        ttk.Button(config_frame, text="🪟 Ẩn/Hiện cây", command=self.toggle_tree_panel).grid(
            row=0, column=0, padx=5, pady=2, sticky="w"
        )

        self.level_vars = {}
        level_names = ["Môn", "Lớp", "Chủ đề", "Dạng", "Mức độ"]
        level_refs = ["subject_cb", "grade_cb", "topic_cb", "type_cb", "level_cb"]
        level_widths = [15, 7, 20, 15, 12]

        for i, (lv, ref, width) in enumerate(zip(level_names, level_refs, level_widths)):
            ttk.Label(config_frame, text=f"{lv}:").grid(row=0, column=i * 2 + 1, padx=2)
            cb = ttk.Combobox(config_frame, width=width, state="readonly")
            cb.grid(row=0, column=i * 2 + 2, padx=2)
            self.level_vars[lv] = cb
            setattr(self, ref, cb)
            cb.bind("<<ComboboxSelected>>", self.filter_by_combobox)

        # Gán sự kiện click để nạp dữ liệu động
        self.subject_cb.bind("<Button-1>", lambda e: self.load_available_subjects())
        self.grade_cb.bind("<Button-1>", lambda e: self.load_available_grades())
        self.topic_cb.bind("<Button-1>", lambda e: self.load_available_topics())
        self.type_cb.bind("<Button-1>", lambda e: self.load_available_types())
        self.level_cb['values'] = ["Nhận biết", "Thông hiểu", "Vận dụng", "Vận dụng cao", "Sáng tạo"]

        # Các nút phụ trợ
        ttk.Button(config_frame, text="🌲 Quản lý cây", command=self.open_tree_manager).grid(row=1, column=1, padx=2)
        ttk.Label(config_frame, text="🔍 Từ khoá:").grid(row=1, column=2, padx=2)
        self.search_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.search_var, width=20).grid(row=1, column=3, padx=2)
        ttk.Button(config_frame, text="Tìm", command=self.search_questions).grid(row=1, column=4, padx=2)
        ttk.Button(config_frame, text="📥 Nhập từ Word", command=self.import_from_word).grid(row=1, column=5, padx=2)

        # ===================== KHUNG CHÍNH CHIA 3 ======================
        self.pw = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        self.pw.pack(fill="both", expand=True)

        # ------ KHUNG TRÁI: CÂY THƯ MỤC ------
        self.left_frame = ttk.Frame(self.pw, width=200)
        self.pw.add(self.left_frame, weight=1)

        ttk.Label(self.left_frame, text="Cây thư mục").pack(anchor="w", padx=5, pady=5)
        self.tree = ttk.Treeview(self.left_frame)
        self.tree.pack(fill="both", expand=True, padx=5)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # ------ KHUNG GIỮA: DANH SÁCH CÂU HỎI ------
        mid = ttk.Frame(self.pw)
        self.pw.add(mid, weight=2)

        ttk.Label(mid, text="Danh sách câu hỏi").pack(anchor="w", padx=5, pady=5)
        cols = ("id", "noidung", "so_dapan", "dap_an", "dang", "muc_do")
        headers = ["ID", "Nội dung", "Số đáp án", "Đáp án đúng", "Dạng", "Mức độ"]
        widths = [50, 300, 80, 100, 120, 120]

        self.q_list = ttk.Treeview(mid, columns=cols, show="headings", selectmode="browse")
        for c, h, w in zip(cols, headers, widths):
            self.q_list.heading(c, text=h)
            self.q_list.column(c, width=w)
        self.q_list.pack(fill="both", expand=True, padx=5)
        self.q_list.bind("<<TreeviewSelect>>", self.on_question_select)

        # ------ KHUNG PHẢI: CHI TIẾT CÂU HỎI ------
        right = ttk.Frame(self.pw, width=300)
        self.pw.add(right, weight=3)

        ttk.Label(right, text="Chi tiết câu hỏi").pack(anchor="w", padx=5, pady=5)
        self.content_text = tk.Text(right, height=6, wrap="word")
        self.content_text.pack(fill="x", padx=5)

        self.correct_var = tk.StringVar()
        self.option_vars = []
        self.current_question_id = None

        for label in ["A", "B", "C", "D", "E"]:
            row = ttk.Frame(right)
            row.pack(fill="x", padx=5, pady=2)
            ttk.Radiobutton(row, text=label, variable=self.correct_var, value=label).pack(side="left")
            ent = ttk.Entry(row)
            ent.pack(fill="x", expand=True, side="left", padx=5)
            self.option_vars.append((label, ent))

        btn_frame = ttk.Frame(right)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="Lưu/Cập nhật", command=self.save_question).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="❌ Xoá", command=self.delete_question).pack(side="left", padx=5)

    def open_tree_manager(self):
        ExerciseTreeManager(self)

    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        self.tree_nodes.clear()
        rows = self.db.execute_query(
            "SELECT id,parent_id,name,level FROM exercise_tree ORDER BY parent_id,level,name",
            fetch='all'
        )
        tree_dict = {}
        for r in rows:
            pid = r['parent_id']
            tree_dict.setdefault(pid, []).append(r)
        def build(parent_db_id, parent_item):
            for node in tree_dict.get(parent_db_id, []):
                iid = str(node['id'])
                item = self.tree.insert(parent_item, 'end', iid=iid, text=node['name'], values=(node['id'],))
                self.tree_nodes[iid] = node['id']
                build(node['id'], iid)
        build(None, '')

    def on_tree_select(self, event):
        selected = self.tree.focus()
        if not selected:
            return

        tree_id = self.tree_nodes.get(selected)
        if not tree_id:
            return

        rows = self.db.execute_query(
            "SELECT * FROM question_bank WHERE tree_id=?", (tree_id,), fetch="all"
        ) or []

        self.q_list.delete(*self.q_list.get_children())
        for r in rows:
            # Rút gọn nội dung để hiển thị
            content_preview = (r["content_text"] or "")[:50].replace("\n", " ").strip()

            # Tách số lượng đáp án
            opts = json.loads(r["options"]) if "options" in r.keys() else []
            so_dapan = len(opts)
            dap_an = r["correct"] if "correct" in r.keys() else "-"

            # Lấy thông tin Dạng, Mức độ từ cây
            path = self.get_tree_path(r["tree_id"])
            path_dict = {p["level"]: p["name"] for p in path}
            dang = path_dict.get("Dạng", "-")
            muc_do = path_dict.get("Mức độ", "-")

            # Thêm vào bảng
            self.q_list.insert(
                "", "end",
                values=(r["id"], content_preview, so_dapan, dap_an, dang, muc_do)
            )

    def on_question_select(self, event):
        sel = self.q_list.focus()
        if not sel:
            return
        qid = self.q_list.item(sel)['values'][0]
        self.current_question_id = qid
        q = self.db.execute_query("SELECT * FROM question_bank WHERE id=?", (qid,), fetch="one")

        # Gán nội dung câu hỏi
        self.content_text.delete('1.0', 'end')
        self.content_text.insert('end', q["content_text"] or "")

        # Gán đáp án đúng
        self.correct_var.set(q["correct"])

        # Gán nội dung từng phương án
        for label, entry in self.option_vars:
            entry.delete(0, 'end')  # xoá cũ

        opts = json.loads(q["options"]) if "options" in q.keys() else []
        for opt in opts:
            text = opt["text"]
            if "." not in text:
                continue
            label, content = text.split(".", 1)
            label = label.strip().upper()
            for opt_label, entry in self.option_vars:
                if opt_label == label:
                    entry.insert(0, content.strip())

    def save_question(self):
        sel = self.tree.focus()
        if not sel:
            messagebox.showwarning("Chưa chọn thư mục", "Vui lòng chọn 1 thư mục để lưu câu hỏi", parent=self)
            return
        tree_id = self.tree_nodes.get(sel)
        if not tree_id:
            return
        content = self.content_text.get("1.0", "end").strip()
        correct = self.correct_var.get()
        opts = []
        for label, ent in self.option_vars:
            t = ent.get().strip()
            if t:
                opts.append({"text": f"{label}. {t}", "is_correct": label == correct})
        if not content or not correct or not opts:
            messagebox.showwarning("Thiếu dữ liệu", "Cần nhập đầy đủ nội dung và đáp án.", parent=self)
            return

        if self.current_question_id:
            # Cập nhật
            self.db.execute_query(
                "UPDATE question_bank SET content_text=?, options=?, correct=?, tree_id=? WHERE id=?",
                (content, json.dumps(opts, ensure_ascii=False), correct, tree_id, self.current_question_id)
            )
            messagebox.showinfo("Cập nhật", "Đã cập nhật câu hỏi.", parent=self)
        else:
            # Thêm mới
            self.db.execute_query(
                "INSERT INTO question_bank(content_text, options, correct, tree_id) VALUES (?, ?, ?, ?)",
                (content, json.dumps(opts, ensure_ascii=False), correct, tree_id)
            )
            messagebox.showinfo("Thêm mới", "Đã lưu câu hỏi mới.", parent=self)

        self.on_tree_select(None)
        self.clear_question_form()

    def clear_question_form(self):
        self.current_question_id = None
        self.content_text.delete('1.0', 'end')
        self.correct_var.set('')
        for _, ent in self.option_vars:
            ent.delete(0, 'end')

    def delete_question(self):
        if not self.current_question_id:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn câu hỏi để xoá.", parent=self)
            return
        if not messagebox.askyesno("Xác nhận", "Bạn có chắc chắn muốn xoá câu hỏi này?", parent=self):
            return
        self.db.execute_query("DELETE FROM question_bank WHERE id=?", (self.current_question_id,))
        self.clear_question_form()
        self.on_tree_select(None)
        messagebox.showinfo("Đã xoá", "Câu hỏi đã được xoá.", parent=self)

    def get_tree_path(self, tree_id):
        path = []
        while tree_id:
            row = self.db.execute_query(
                "SELECT id, parent_id, name, level FROM exercise_tree WHERE id=?",
                (tree_id,), fetch="one"
            )
            if row:
                path.insert(0, row)
                tree_id = row["parent_id"]
            else:
                break
        return path

    def search_questions(self):
        keyword = self.search_var.get().strip().lower()
        if not keyword:
            self.on_tree_select(None)
            return

        sel = self.tree.focus()
        if not sel:
            messagebox.showwarning("Chưa chọn", "Hãy chọn thư mục để tìm trong đó.", parent=self)
            return

        tree_id = self.tree_nodes.get(sel)
        if not tree_id:
            return

        # Lấy toàn bộ các tree_id con của node đang chọn
        all_ids = self.get_all_subtree_ids(tree_id)

        query = f"""
            SELECT * FROM question_bank
            WHERE tree_id IN ({','.join('?' for _ in all_ids)})
        """
        rows = self.db.execute_query(query, tuple(all_ids), fetch="all")

        self.q_list.delete(*self.q_list.get_children())
        for r in rows:
            if keyword not in (r["content_text"] or "").lower():
                continue

            content_preview = (r["content_text"] or "")[:50].replace("\n", " ").strip()
            opts = json.loads(r["options"]) if "options" in r.keys() else []
            so_dapan = len(opts)
            dap_an = r["correct"] or "-"
            co_anh = "✅" if "content_image" in r.keys() and r["content_image"] else "❌"

            path = self.get_tree_path(r["tree_id"])
            path_dict = {p["level"]: p["name"] for p in path}
            dang = path_dict.get("Dạng", "-")
            muc_do = path_dict.get("Mức độ", "-")

            self.q_list.insert("", "end", values=(
                r["id"], content_preview, so_dapan, dap_an, dang, muc_do, co_anh
            ))

    def get_all_subtree_ids(self, root_id):
        ids = [root_id]
        children = self.db.execute_query("SELECT id FROM exercise_tree WHERE parent_id=?", (root_id,), fetch="all")
        for c in children:
            ids.extend(self.get_all_subtree_ids(c["id"]))
        return ids

    def load_available_grades(self):
        rows = self.db.execute_query(
            "SELECT DISTINCT name FROM exercise_tree WHERE level = 'Lớp' ORDER BY name ASC",
            fetch="all"
        )
        grade_names = [r["name"] for r in rows]
        self.grade_cb['values'] = grade_names

    def load_available_grades(self):
        rows = self.db.execute_query(
            "SELECT DISTINCT name FROM exercise_tree WHERE level = 'Lớp' ORDER BY name ASC",
            fetch="all"
        )
        grade_names = [r["name"] for r in rows]
        self.grade_cb['values'] = grade_names

    def load_available_subjects(self):
        rows = self.db.execute_query(
            "SELECT DISTINCT name FROM exercise_tree WHERE level = 'Môn' ORDER BY name ASC",
            fetch="all"
        )
        self.subject_cb['values'] = [r["name"] for r in rows]

    def load_available_topics(self):
        subject = self.subject_cb.get()
        grade = self.grade_cb.get()
        if not subject or not grade:
            self.topic_cb['values'] = []
            return

        rows = self.db.execute_query("""
            SELECT name FROM exercise_tree 
            WHERE level = 'Chủ đề' AND parent_id IN (
                SELECT id FROM exercise_tree 
                WHERE name = ? AND level = 'Lớp' AND parent_id IN (
                    SELECT id FROM exercise_tree 
                    WHERE name = ? AND level = 'Môn'
                )
            )
        """, (grade, subject), fetch="all")

        self.topic_cb['values'] = [r["name"] for r in rows]

    def load_available_types(self):
        topic = self.topic_cb.get()
        if not topic:
            self.type_cb['values'] = []
            return

        rows = self.db.execute_query("""
            SELECT name FROM exercise_tree 
            WHERE level = 'Dạng' AND parent_id IN (
                SELECT id FROM exercise_tree 
                WHERE name = ? AND level = 'Chủ đề'
            )
        """, (topic,), fetch="all")

        self.type_cb['values'] = [r["name"] for r in rows]

    def import_from_word(self):
        from docx import Document
        import json

        file_path = filedialog.askopenfilename(
            filetypes=[("Word files", "*.docx")],
            title="Chọn file Word chứa câu hỏi"
        )
        if not file_path:
            return

        sel = self.tree.focus()
        tree_id = self.tree_nodes.get(sel)
        if not tree_id:
            messagebox.showwarning("Thiếu thư mục", "Vui lòng chọn nơi lưu câu hỏi (trong cây bên trái)", parent=self)
            return

        try:
            doc = Document(file_path)
            questions = []
            current_question = None

            for para in doc.paragraphs:
                line = para.text.strip()
                if not line:
                    continue

                if line.lower().startswith("câu hỏi:"):
                    if current_question:
                        questions.append(current_question)
                    current_question = {"content": line[8:].strip(), "options": [], "answer": ""}
                elif any(line.startswith(f"{opt}.") for opt in "ABCDE"):
                    if current_question:
                        current_question["options"].append(line.strip())
                elif line.lower().startswith("đáp án:"):
                    if current_question:
                        current_question["answer"] = line.split(":")[-1].strip().upper()

            if current_question:
                questions.append(current_question)

            inserted = 0
            for q in questions:
                content = q["content"]
                answer = q["answer"]
                raw_options = q["options"]

                if not content or not answer or not raw_options:
                    continue

                opts_data = []
                for opt in raw_options:
                    if "." not in opt:
                        continue
                    label, text = opt.split(".", 1)
                    label = label.strip().upper()
                    if label not in "ABCDE":
                        continue
                    is_correct = (label == answer)
                    opts_data.append({
                        "text": f"{label}. {text.strip()}",
                        "is_correct": is_correct
                    })

                if not opts_data:
                    continue

                self.db.execute_query(
                    "INSERT INTO question_bank(content_text, options, correct, tree_id) VALUES (?, ?, ?, ?)",
                    (content, json.dumps(opts_data, ensure_ascii=False), answer, tree_id)
                )
                inserted += 1

            self.on_tree_select(None)
            messagebox.showinfo("Thành công", f"Đã thêm {inserted} câu hỏi từ file Word.", parent=self)

        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể xử lý file: {e}", parent=self)

    def filter_by_combobox(self, event=None):
        subject = self.subject_cb.get()
        grade = self.grade_cb.get()
        topic = self.topic_cb.get()
        q_type = self.type_cb.get()
        level = self.level_cb.get()

        conditions = []
        params = []

        if subject:
            conditions.append(
                "EXISTS (SELECT 1 FROM exercise_tree s WHERE s.id = q.tree_id AND s.level = 'Mức độ' AND s.parent_id IN (SELECT id FROM exercise_tree WHERE level = 'Dạng' AND parent_id IN (SELECT id FROM exercise_tree WHERE level = 'Chủ đề' AND parent_id IN (SELECT id FROM exercise_tree WHERE level = 'Lớp' AND name=? AND parent_id IN (SELECT id FROM exercise_tree WHERE level = 'Môn' AND name=?)))))")
            params.extend([grade, subject] if grade else [None, subject])
        if grade and not subject:
            conditions.append(
                "EXISTS (SELECT 1 FROM exercise_tree s WHERE s.id = q.tree_id AND s.level = 'Mức độ' AND s.parent_id IN (SELECT id FROM exercise_tree WHERE level = 'Dạng' AND parent_id IN (SELECT id FROM exercise_tree WHERE level = 'Chủ đề' AND parent_id IN (SELECT id FROM exercise_tree WHERE level = 'Lớp' AND name=?))))")
            params.append(grade)

        if topic:
            conditions.append(
                "EXISTS (SELECT 1 FROM exercise_tree s WHERE s.id = q.tree_id AND s.level = 'Mức độ' AND s.parent_id IN (SELECT id FROM exercise_tree WHERE level = 'Dạng' AND parent_id IN (SELECT id FROM exercise_tree WHERE level = 'Chủ đề' AND name=?)))")
            params.append(topic)

        if q_type:
            conditions.append(
                "EXISTS (SELECT 1 FROM exercise_tree s WHERE s.id = q.tree_id AND s.level = 'Mức độ' AND s.parent_id IN (SELECT id FROM exercise_tree WHERE level = 'Dạng' AND name=?))")
            params.append(q_type)

        if level:
            conditions.append(
                "EXISTS (SELECT 1 FROM exercise_tree s WHERE s.id = q.tree_id AND s.name=? AND s.level = 'Mức độ')")
            params.append(level)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT q.* FROM question_bank q WHERE {where_clause}"

        rows = self.db.execute_query(query, tuple(params), fetch="all")

        self.q_list.delete(*self.q_list.get_children())
        for r in rows:
            content_preview = (r["content_text"] or "")[:50].replace("\n", " ").strip()
            opts = json.loads(r["options"]) if "options" in r.keys() else []
            so_dapan = len(opts)
            dap_an = r["correct"] or "-"
            path = self.get_tree_path(r["tree_id"])
            path_dict = {p["level"]: p["name"] for p in path}
            dang = path_dict.get("Dạng", "-")
            muc_do = path_dict.get("Mức độ", "-")
            self.q_list.insert("", "end", values=(r["id"], content_preview, so_dapan, dap_an, dang, muc_do))

    def toggle_tree_panel(self):
        if self.tree_shown:
            # Ẩn cây thư mục
            self.pw.forget(self.left_frame)
            self.tree_shown = False
        else:
            # Tránh lỗi nếu đã được add trước đó
            if str(self.left_frame) not in self.pw.panes():
                self.pw.insert(0, self.left_frame, weight=1)
            self.tree_shown = True




