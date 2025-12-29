import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import tkinter.font as tkfont
import json

LANES = ["上单", "中单", "打野", "射手", "辅助"]


def weighted_win_rate(player):
    # 低场次保护
    if player["games"] < 10 and player["win_rate"] > 59.0:
        return 59.0
    elif player["games"] < 10 and player["win_rate"] < 41.0:
        return 41.0
    return float(player["win_rate"])


def create_balanced_teams(selected_players):
    """
    - 两队各5人
    - 每队五个位置(上单/中单/打野/射手/辅助)各1人
    - 只有1个位置的选手必须打该位置
    - 在满足约束的所有方案里，使两队平均胜率差最小
    - NEW: c罗 和 杰尼龟 不能同队
    """
    # ---------- config: constraints ----------
    CANT_SAME_TEAM = [("c罗", "杰尼龟")]

    def norm_name(s: str) -> str:
        # 轻量规范化：避免前后空格/大小写影响
        return (s or "").strip().lower()

    cant_pairs = [(norm_name(a), norm_name(b)) for a, b in CANT_SAME_TEAM]

    # ---------- build players ----------
    players = []
    for name, data in selected_players.items():
        lanes = list(data.get("lane", []))
        if not lanes:
            lanes = LANES[:]
        players.append((name, data, weighted_win_rate(data), lanes))

    if len(players) != 10:
        raise ValueError("selected_players 必须恰好 10 人")

    # 10 slots: (team_id, lane)
    slots = [(1, lane) for lane in LANES] + [(2, lane) for lane in LANES]

    # lane -> candidate player indices
    lane_to_candidates = {lane: [] for lane in LANES}
    for i, (_, _, _, lanes) in enumerate(players):
        for lane in lanes:
            if lane in lane_to_candidates:
                lane_to_candidates[lane].append(i)

    for lane in LANES:
        if len(lane_to_candidates[lane]) < 2:
            raise ValueError(f"无法分队：位置[{lane}]的可选人数不足 2（当前={len(lane_to_candidates[lane])}）")

    def slot_key(s):
        _, lane = s
        return len(lane_to_candidates[lane])

    # fill the most constrained lane first
    slots_sorted = sorted(slots, key=slot_key)

    used = [False] * 10              # player index used or not
    assign = [None] * len(slots_sorted)  # slot idx -> player idx

    # slot -> candidate indices (by lane)
    slot_candidates = []
    for _, lane in slots_sorted:
        cands = []
        for i, (_, _, _, lanes) in enumerate(players):
            if lane in lanes:
                cands.append(i)
        slot_candidates.append(cands)

    # quick index->normalized name
    idx_to_norm_name = {i: norm_name(players[i][0]) for i in range(10)}

    # per team current members (normalized names)
    team_members = {1: set(), 2: set()}

    def violates_cant_same_team(team_id: int, nm: str) -> bool:
        s = team_members[team_id]
        for a, b in cant_pairs:
            if nm == a and b in s:
                return True
            if nm == b and a in s:
                return True
        return False

    best_assign = None
    best_diff = float("inf")

    def backtrack(pos: int):
        nonlocal best_assign, best_diff

        if pos == len(slots_sorted):
            t1_sum = 0.0
            t2_sum = 0.0
            t1_cnt = 0
            t2_cnt = 0
            for k, (team_id, _) in enumerate(slots_sorted):
                pi = assign[k]
                _, _, wr, _ = players[pi]
                if team_id == 1:
                    t1_sum += wr
                    t1_cnt += 1
                else:
                    t2_sum += wr
                    t2_cnt += 1
            diff = abs(t1_sum / 5.0 - t2_sum / 5.0)
            if diff < best_diff:
                best_diff = diff
                best_assign = assign[:]
            return

        team_id, lane = slots_sorted[pos]

        for pi in slot_candidates[pos]:
            if used[pi]:
                continue

            nm = idx_to_norm_name[pi]

            # NEW: mutual exclusion rule
            if violates_cant_same_team(team_id, nm):
                continue

            used[pi] = True
            assign[pos] = pi
            team_members[team_id].add(nm)

            # pruning: ensure remaining lanes still have at least one unused candidate
            ok = True
            filled = {(slots_sorted[k][0], slots_sorted[k][1]) for k in range(pos + 1)}
            for (t, l) in slots_sorted[pos + 1:]:
                if (t, l) in filled:
                    continue
                exists = any((not used[cand]) for cand in lane_to_candidates[l])
                if not exists:
                    ok = False
                    break

            if ok:
                backtrack(pos + 1)

            team_members[team_id].remove(nm)
            used[pi] = False
            assign[pos] = None

    backtrack(0)

    if best_assign is None:
        raise ValueError("无法找到满足“两队各5人且五位置齐全 + 互斥规则”的分配方案")

    team1, team2 = [], []
    t1_sum, t2_sum = 0.0, 0.0

    for k, (team_id, lane) in enumerate(slots_sorted):
        pi = best_assign[k]
        name, data, wr, _ = players[pi]
        if team_id == 1:
            team1.append((name, data, lane))
            t1_sum += wr
        else:
            team2.append((name, data, lane))
            t2_sum += wr

    print("平均胜率:", "Team 1: ", t1_sum / 5.0, ", Team 2: ", t2_sum / 5.0, " | 差值:", abs(t1_sum/5.0 - t2_sum/5.0))
    return team1, team2



def update_player_stats(players, player_name, is_winner):
    player_data = players[player_name]
    total_games = player_data["games"]
    wins = player_data["win"]
    loses = player_data["loss"]
    total_games += 1
    if is_winner:
        wins += 1
    else:
        loses += 1
    new_win_rate = (wins / total_games) * 100
    player_data["games"] = total_games
    player_data["win_rate"] = round(new_win_rate, 2)
    player_data["win"] = wins
    player_data["loss"] = loses


def load_players_data(filename="S4_stats.json"):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            players = json.load(file)
        return players
    except FileNotFoundError:
        print("File not found.")
        return None


def save_players_data(players, filename="S4_stats.json"):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(players, file, ensure_ascii=False, indent=4)


class TeamBalancerApp:
    def __init__(self, root, players):
        self.root = root
        self.players = players

        # ---- state ----
        self._sel_anchor = None
        self._hover_item = None
        self._base_tags = {}  # item_id -> "even"/"odd"

        # ---- window ----
        root.title("Team Balancer")
        root.minsize(660, 700)
        root.configure(bg="#F6F7FB")
        try:
            root.tk.call('tk', 'scaling', 1.2)
        except Exception:
            pass

        # ---- styles ----
        style = ttk.Style()
        try:
            style.theme_use("vista")
        except Exception:
            style.theme_use(style.theme_names()[0])

        UI_FONT = ("Microsoft YaHei UI", 11)
        UI_FONT_BOLD = ("Microsoft YaHei UI", 11, "bold")
        TITLE_FONT = ("Microsoft YaHei UI", 16, "bold")

        style.configure("App.TFrame", background="#F6F7FB")
        style.configure("Card.TFrame", background="#FFFFFF", relief="solid", borderwidth=1)

        style.configure("Title.TLabel", background="#F6F7FB", font=TITLE_FONT)
        style.configure("SubTitle.TLabel", background="#FFFFFF", font=UI_FONT_BOLD)
        style.configure("Hint.TLabel", background="#F6F7FB", foreground="#666666", font=("Microsoft YaHei UI", 10))
        style.configure("Info.TLabel", background="#F6F7FB", foreground="#333333", font=("Microsoft YaHei UI", 11, "bold"))

        style.configure("Treeview",
                        font=UI_FONT,
                        rowheight=30,
                        background="#FFFFFF",
                        fieldbackground="#FFFFFF",
                        borderwidth=0)
        style.configure("Treeview.Heading", font=UI_FONT_BOLD)
        style.map("Treeview",
                background=[("selected", "#6B9BF5")],
                foreground=[("selected", "#0F1E3A")])



        style.configure("Primary.TButton", font=UI_FONT, padding=(12, 8))
        style.configure("Secondary.TButton", font=UI_FONT, padding=(12, 8))

        # ---- layout root ----
        outer = ttk.Frame(root, style="App.TFrame", padding=8)
        outer.grid(row=0, column=0, sticky="nsew")
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)

        RIGHT_W = 220

        outer.grid_columnconfigure(0, weight=1)
        outer.grid_columnconfigure(1, weight=0, minsize=RIGHT_W)
        outer.grid_rowconfigure(1, weight=1)

        # ---- top: title + hint + selected count ----
        header = ttk.Frame(outer, style="App.TFrame")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=0)

        title = ttk.Label(header, text="请选择本次参与游戏的 10 人", style="Title.TLabel")
        title.grid(row=0, column=0, sticky="w")

        hint = ttk.Label(header, text="单击：仅选中该行；Ctrl：多选；Shift：范围选择", style="Hint.TLabel")
        hint.grid(row=1, column=0, sticky="w", pady=(2, 0))

        # 右上角计数
        self.selected_count_label = ttk.Label(header, text="已选 0 / 10", style="Hint.TLabel")
        self.selected_count_label.grid(row=0, column=1, sticky="e")

        # ---- left card: player list ----
        left_card = ttk.Frame(outer, style="Card.TFrame", padding=8)
        left_card.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        left_card.grid_rowconfigure(1, weight=1)
        left_card.grid_columnconfigure(0, weight=1)

        left_title = ttk.Label(left_card, text="玩家列表", style="SubTitle.TLabel")
        left_title.grid(row=0, column=0, sticky="w", pady=(0, 8))

        self.player_tree = ttk.Treeview(
            left_card,
            columns=("Name", "WinRate", "Games"),
            show="headings",
            height=16,
            selectmode="extended"
        )
        self.player_tree.heading("Name", text="玩家ID", anchor="center")
        self.player_tree.heading("WinRate", text="胜率", anchor="center")
        self.player_tree.heading("Games", text="总场次", anchor="center")
        self.player_tree.column("Name", width=100, anchor="center")
        self.player_tree.column("WinRate", width=100, anchor="center")
        self.player_tree.column("Games", width=100, anchor="center")


        self.player_tree.tag_configure("even", background="#FFFFFF")
        self.player_tree.tag_configure("odd", background="#F3F3F3")    
        self.player_tree.tag_configure("hover", background="#EAEAEA")  


        yscroll = ttk.Scrollbar(left_card, command=self.player_tree.yview)
        self.player_tree.configure(yscrollcommand=yscroll.set)
        self.player_tree.grid(row=1, column=0, sticky="nsew")
        yscroll.grid(row=1, column=1, sticky="ns")

        # bindings
        self.player_tree.bind("<Button-1>", self.toggle_selection)
        self.player_tree.bind("<<TreeviewSelect>>", lambda e: self.update_selected_count())
        self.player_tree.bind("<Motion>", self.on_tree_motion)
        self.player_tree.bind("<Leave>", self.on_tree_leave)

        self.populate_player_tree()

        # ---- right column ----
        right_col = ttk.Frame(outer, style="App.TFrame", width=RIGHT_W)
        right_col.grid(row=1, column=1, sticky="nsew")
        right_col.grid_propagate(False) 
        right_col.grid_columnconfigure(0, weight=1)
        right_col.grid_rowconfigure(1, weight=1)  


        # controls card
        ctrl_card = ttk.Frame(right_col, style="Card.TFrame", padding=8)
        ctrl_card.grid(row=0, column=0, sticky="ew")
        ctrl_card.grid_columnconfigure(0, weight=1)

        ctrl_title = ttk.Label(ctrl_card, text="操作", style="SubTitle.TLabel")
        ctrl_title.grid(row=0, column=0, sticky="w", pady=(0, 8))

        btn_row = ttk.Frame(ctrl_card, style="App.TFrame")
        btn_row.grid(row=1, column=0, sticky="ew")
        btn_row.grid_columnconfigure(0, weight=1)
        btn_row.grid_columnconfigure(1, weight=1)

        self.win_button = ttk.Button(btn_row, text="Win", style="Secondary.TButton",
                                     command=lambda: self.update_win_loss(True))
        self.loss_button = ttk.Button(btn_row, text="Loss", style="Secondary.TButton",
                                      command=lambda: self.update_win_loss(False))
        self.win_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.loss_button.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        self.balance_button = ttk.Button(ctrl_card, text="平衡分队", style="Primary.TButton",
                                         command=self.balance_teams)
        self.balance_button.grid(row=2, column=0, sticky="ew", pady=(10, 0))

        # result card
        result_card = ttk.Frame(right_col, style="Card.TFrame", padding=8)
        result_card.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        result_card.grid_columnconfigure(0, weight=1)

        # team1
        team1_title = ttk.Label(result_card, text="Team 1", style="SubTitle.TLabel")
        team1_title.grid(row=0, column=0, sticky="w", pady=(0, 6))

        self.team1_listbox = tk.Listbox(
            result_card, width=22, height=7,
            font=("Microsoft YaHei UI", 11),
            bg="#FFFFFF", relief="solid", bd=1,
            highlightthickness=0, selectbackground="#DCEBFF",
            activestyle="none"
        )
        self.team1_listbox.grid(row=1, column=0, sticky="ew")

        self.team1_avg_label = ttk.Label(result_card, text="平均胜率: -", style="Hint.TLabel")
        self.team1_avg_label.grid(row=2, column=0, sticky="w", pady=(4, 8))

        # team2
        team2_title = ttk.Label(result_card, text="Team 2", style="SubTitle.TLabel")
        team2_title.grid(row=3, column=0, sticky="w", pady=(6, 6))

        self.team2_listbox = tk.Listbox(
            result_card, width=22, height=7,
            font=("Microsoft YaHei UI", 11),
            bg="#FFFFFF", relief="solid", bd=1,
            highlightthickness=0, selectbackground="#DCEBFF",
            activestyle="none"
        )
        self.team2_listbox.grid(row=4, column=0, sticky="ew")

        self.team2_avg_label = ttk.Label(result_card, text="平均胜率: -", style="Hint.TLabel")
        self.team2_avg_label.grid(row=5, column=0, sticky="w", pady=(4, 0))

        self.diff_label = ttk.Label(result_card, text="差值: -", style="Hint.TLabel")
        self.diff_label.grid(row=6, column=0, sticky="w", pady=(2, 0))

        self.update_selected_count()

    # ---------------- UI helpers ----------------

    def update_selected_count(self):
        cnt = len(self.player_tree.selection())
        self.selected_count_label.config(text=f"已选 {cnt} / 10")

    def populate_player_tree(self):
        # rebuild list with zebra tags
        for item in self.player_tree.get_children():
            self.player_tree.delete(item)
        self._base_tags.clear()

        rows = sorted(self.players.items(), key=lambda item: -float(item[1]['win_rate']))
        for idx, (player_name, player_data) in enumerate(rows):
            tag = "even" if idx % 2 == 0 else "odd"
            iid = self.player_tree.insert(
                "",
                tk.END,
                values=(player_name, f"{player_data['win_rate']}%", player_data["games"]),
                tags=(tag,)
            )
            self._base_tags[iid] = tag

        self.autosize_treeview_columns()

    def autosize_treeview_columns(self, pad_px=20, max_px=360):
        # 根据内容自动调整列宽
        tv = self.player_tree
        font = tkfont.Font(font=ttk.Style().lookup("Treeview", "font"))

        for col in ("Name", "WinRate", "Games"):
            heading = tv.heading(col, "text") or ""
            w = font.measure(heading) + pad_px

            for iid in tv.get_children(""):
                val = str(tv.set(iid, col))
                w = max(w, font.measure(val) + pad_px)

            w = min(w, max_px)
            tv.column(col, width=w)

    def on_tree_motion(self, event):
        tv = self.player_tree
        item = tv.identify_row(event.y)
        if item == self._hover_item:
            return

        # restore previous hover item tag
        if self._hover_item and self._hover_item in self._base_tags:
            base = self._base_tags[self._hover_item]
            # 保留选中高亮由style控制，不在tags里干预
            tv.item(self._hover_item, tags=(base,))
        self._hover_item = item

        # apply hover tag
        if item and item in self._base_tags:
            base = self._base_tags[item]
            tv.item(item, tags=(base, "hover"))

    def on_tree_leave(self, event):
        tv = self.player_tree
        if self._hover_item and self._hover_item in self._base_tags:
            base = self._base_tags[self._hover_item]
            tv.item(self._hover_item, tags=(base,))
        self._hover_item = None

    # ---------------- selection behavior ----------------

    def toggle_selection(self, event):
        tv = self.player_tree

        region = tv.identify("region", event.x, event.y)
        if region not in ("cell", "tree"):
            return

        item = tv.identify_row(event.y)
        if not item:
            return

        shift = (event.state & 0x0001) != 0
        ctrl = (event.state & 0x0004) != 0

        selected = list(tv.selection())

        if shift:
            anchor = self._sel_anchor or tv.focus() or (selected[0] if selected else item)
            items = list(tv.get_children(""))
            try:
                a = items.index(anchor)
            except ValueError:
                a = items.index(item)
            b = items.index(item)
            lo, hi = (a, b) if a <= b else (b, a)

            tv.selection_set(items[lo:hi + 1])
            tv.focus(item)
            self.update_selected_count()
            return "break"

        if ctrl:
            if item in tv.selection():
                tv.selection_remove(item)
            else:
                tv.selection_add(item)
            tv.focus(item)
            self.update_selected_count()
            return "break"

        # normal click: single selection; click again to clear if it is the only one selected
        if len(selected) == 1 and selected[0] == item:
            tv.selection_remove(item)
            tv.focus("")
            self._sel_anchor = None
        else:
            tv.selection_set(item)
            tv.focus(item)
            self._sel_anchor = item

        self.update_selected_count()
        return "break"

    # ---------------- actions ----------------

    def update_win_loss(self, is_winner: bool):
        selected_items = self.player_tree.selection()
        if not selected_items:
            return

        tv = self.player_tree

        # 1) 记住当前选中的玩家名字
        selected_names = [tv.item(i, "values")[0] for i in selected_items]

        # 2) 更新数据（一次按钮点击 = 1 场）
        for name in selected_names:
            update_player_stats(self.players, name, is_winner)

        save_players_data(self.players)

        # 3) 重建列表（会导致 iid 变化）
        self.populate_player_tree()

        # 4) name -> iid 映射，恢复选择
        name_to_iid = {}
        for iid in tv.get_children(""):
            nm = tv.item(iid, "values")[0]
            name_to_iid[nm] = iid

        restore_iids = [name_to_iid[n] for n in selected_names if n in name_to_iid]
        if restore_iids:
            tv.selection_set(restore_iids)
            tv.focus(restore_iids[-1])
            self._sel_anchor = restore_iids[-1]
        else:
            tv.selection_remove(tv.selection())
            tv.focus("")
            self._sel_anchor = None

        self.update_selected_count()


    def balance_teams(self):
        selected_items = self.player_tree.selection()
        if len(selected_items) != 10:
            messagebox.showerror("错误", "请选择10名玩家进行游戏")
            return

        selected_players = {
            self.player_tree.item(i, 'values')[0]: self.players[self.player_tree.item(i, 'values')[0]]
            for i in selected_items
        }

        try:
            team1, team2 = create_balanced_teams(selected_players)
        except Exception as e:
            messagebox.showerror("分队失败", str(e))
            return

        # fill listboxes
        self.team1_listbox.delete(0, tk.END)
        self.team2_listbox.delete(0, tk.END)

        positions_order = ["上单", "打野", "中单", "射手", "辅助"]
        sorted_team1 = sorted(team1, key=lambda x: positions_order.index(x[2]))
        sorted_team2 = sorted(team2, key=lambda x: positions_order.index(x[2]))

        for player_name, player_data, lane in sorted_team1:
            self.team1_listbox.insert(
                tk.END, f"{lane}: {player_name}- {player_data['win_rate']}% ({player_data['games']} 场)"
            )
        for player_name, player_data, lane in sorted_team2:
            self.team2_listbox.insert(
                tk.END, f"{lane}: {player_name}- {player_data['win_rate']}% ({player_data['games']} 场)"
            )

        # avg winrate labels (use weighted winrate to match balancing logic)
        t1_avg = sum(weighted_win_rate(d) for _, d, _ in team1) / 5.0
        t2_avg = sum(weighted_win_rate(d) for _, d, _ in team2) / 5.0
        diff = abs(t1_avg - t2_avg)

        self.team1_avg_label.config(text=f"平均胜率: {t1_avg:.2f}%")
        self.team2_avg_label.config(text=f"平均胜率: {t2_avg:.2f}%")
        self.diff_label.config(text=f"胜率差值: {diff:.2f}%")

        self.update_selected_count()


if __name__ == "__main__":
    players = load_players_data() or {}
    root = tk.Tk()
    app = TeamBalancerApp(root, players)
    root.mainloop()