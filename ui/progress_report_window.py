import tkinter as tk
from tkinter import ttk
class ProgressReportWindow(tk.Toplevel):
    # Giao diện báo cáo tiến độ dạy học theo từng khối
    def __init__(self, parent, db_manager):
        super().__init__(parent);
        self.db = db_manager;
        self.title("Báo cáo Tiến độ");
        self.geometry("900x600")
        ttk.Label(self, text="Báo cáo Tiến độ Giảng dạy", font=("Helvetica", 16, "bold")).pack(pady=10)
        filter_frame = ttk.Frame(self, padding="10");
        filter_frame.pack(fill="x")
        ttk.Label(filter_frame, text="Chọn khối lớp:").pack(side="left", padx=5)
        grade_list = [g[0] for g in
                      self.db.execute_query("SELECT DISTINCT grade FROM groups ORDER BY grade", fetch='all') or []]
        self.grade_var = tk.StringVar();
        self.grade_combo = ttk.Combobox(filter_frame, textvariable=self.grade_var, values=grade_list, state='readonly')
        self.grade_combo.pack(side="left", padx=5)
        if grade_list: self.grade_combo.set(grade_list[0])
        self.grade_combo.bind("<<ComboboxSelected>>", self.load_report)
        self.report_frame = ttk.Frame(self, padding="10");
        self.report_frame.pack(fill="both", expand=True)
        self.load_report()

    # Tải và hiển thị bảng tiến độ học các chủ đề theo nhóm
    def load_report(self, event=None):
        for widget in self.report_frame.winfo_children(): widget.destroy()
        grade = self.grade_var.get()
        if not grade: return
        groups = self.db.execute_query("SELECT id, name FROM groups WHERE grade = ? ORDER BY name", (grade,),
                                       fetch='all')
        topics = self.db.execute_query(
            "SELECT DISTINCT topic FROM session_logs sl JOIN groups g ON sl.group_id = g.id WHERE g.grade = ? AND sl.topic IS NOT NULL AND sl.topic != '' ORDER BY sl.session_date",
            (grade,), fetch='all')
        if not groups or not topics: ttk.Label(self.report_frame,
                                               text="Không có dữ liệu tiến độ cho khối lớp này.").pack(); return
        g_ids, g_names, topic_list = [g[0] for g in groups], [g[1] for g in groups], [t[0] for t in topics]
        tree = ttk.Treeview(self.report_frame, columns=["Chủ đề"] + g_names, show="headings")
        for col in ["Chủ đề"] + g_names: tree.heading(col, text=col); tree.column(col,
                                                                                  width=150 if col != "Chủ đề" else 250,
                                                                                  anchor="center")
        tree.pack(fill="both", expand=True)
        learned_data = {}
        res = self.db.execute_query(
            "SELECT group_id, topic FROM session_logs WHERE topic IN ({})".format(','.join('?' * len(topic_list))),
            topic_list, fetch='all')
        if res:
            for g_id, topic in res: learned_data[(g_id, topic)] = True
        for topic in topic_list:
            tree.insert("", "end",
                        values=tuple([topic] + ["✅" if learned_data.get((gid, topic)) else "" for gid in g_ids]))
