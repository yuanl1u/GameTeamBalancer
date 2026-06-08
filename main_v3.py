import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import tkinter.font as tkfont
import json
import pathlib

LANES = ["上单", "打野", "中单", "射手", "辅助"]
RULES_FILENAME = "S2026_rules.json"
MAX_CANT_SAME_PAIRS = 3
DEFAULT_CANT_SAME_TEAM = [["基拉祈", "惠"], ["鸡", "杰尼龟"]]


def weighted_win_rate(player: dict, player_name: str = None, prev_season: dict = None) -> float:
    """
    分队用胜率（含低场次保护 + 上赛季回退）：

    新规则：
    - 若当前 games < 10：
        - 若上赛季存在该玩家：用上赛季 win_rate
        - 否则：沿用 41~59 保护规则（基于当前 win_rate）
    - 若当前 games >= 10：用当前 win_rate
    """
    games = int(player.get("games", 0))
    cur_wr = float(player.get("win_rate", 0.0))

    # >=10 直接用当前赛季数据
    if games >= 10:
        return cur_wr

    # <10：优先回退上赛季
    if prev_season and player_name and player_name in prev_season:
        try:
            return float(prev_season[player_name].get("win_rate", cur_wr))
        except Exception:
            # 上赛季数据异常则回退到当前规则
            pass

    # <10 且上赛季无此人：沿用原 41-59 保护
    if cur_wr > 65.0:
        return 65.0
    if cur_wr < 35.0:
        return 35.0
    return cur_wr



def clean_cant_same_team(pairs):
    cleaned = []
    seen = set()

    for pair in pairs or []:
        if len(pair) != 2:
            continue
        a = str(pair[0]).strip()
        b = str(pair[1]).strip()
        if not a or not b or a == b:
            continue

        key = tuple(sorted((a.lower(), b.lower())))
        if key in seen:
            continue
        seen.add(key)
        cleaned.append([a, b])

        if len(cleaned) >= MAX_CANT_SAME_PAIRS:
            break

    return cleaned


def load_team_rules(filename=RULES_FILENAME):
    rules = {"cant_same_team": clean_cant_same_team(DEFAULT_CANT_SAME_TEAM)}

    try:
        with open(filename, "r", encoding="utf-8") as file:
            saved_rules = json.load(file)
    except FileNotFoundError:
        return rules
    except Exception:
        return rules

    rules["cant_same_team"] = clean_cant_same_team(
        saved_rules.get("cant_same_team", rules["cant_same_team"])
    )
    return rules


def save_default_rules_to_py(cant_same_team):
    try:
        target = pathlib.Path(__file__)
        lines = target.read_text(encoding="utf-8").splitlines()
        new_line = "DEFAULT_CANT_SAME_TEAM = " + json.dumps(cant_same_team, ensure_ascii=False)

        for idx, line in enumerate(lines):
            if line.startswith("DEFAULT_CANT_SAME_TEAM = "):
                lines[idx] = new_line
                target.write_text("\n".join(lines) + "\n", encoding="utf-8")
                return True
    except Exception:
        return False

    return False


def save_team_rules(rules, filename=RULES_FILENAME):
    rules_to_save = {
        "cant_same_team": clean_cant_same_team(rules.get("cant_same_team", []))
    }

    with open(filename, "w", encoding="utf-8") as file:
        json.dump(rules_to_save, file, ensure_ascii=False, indent=4)

    return save_default_rules_to_py(rules_to_save["cant_same_team"])


def create_balanced_teams(selected_players, prev_season=None, cant_same_team=None):
    """
    - 两队各5人
    - 每队五个位置(上单/中单/打野/射手/辅助)各1人
    - 只有1个位置的选手必须打该位置
    - 在满足约束的所有方案里，使两队平均胜率差最小
    - 指定的互斥玩家不能同队
    - NEW: games<10 时优先使用上赛季(S4_stats.json)胜率
    """
    # 若未传入上赛季数据，则这里尝试加载一次（失败就当空）
    if prev_season is None:
        try:
            with open("S4_stats.json", "r", encoding="utf-8") as f:
                prev_season = json.load(f)
        except Exception:
            prev_season = {}

    def norm_name(s: str) -> str:
        return (s or "").strip().lower()

    rule_pairs = cant_same_team if cant_same_team is not None else DEFAULT_CANT_SAME_TEAM
    cant_pairs = [(norm_name(a), norm_name(b)) for a, b in clean_cant_same_team(rule_pairs)]

    # ---------- build players ----------
    players = []
    for name, data in selected_players.items():
        lanes = list(data.get("lane", []))
        if not lanes:
            lanes = LANES[:]
        eff_wr = weighted_win_rate(data, name, prev_season)  # <-- NEW
        players.append((name, data, eff_wr, lanes))

    if len(players) != 10:
        raise ValueError("selected_players 必须恰好 10 人")

    slots = [(1, lane) for lane in LANES] + [(2, lane) for lane in LANES]

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

    slots_sorted = sorted(slots, key=slot_key)

    used = [False] * 10
    assign = [None] * len(slots_sorted)

    slot_candidates = []
    for _, lane in slots_sorted:
        cands = []
        for i, (_, _, _, lanes) in enumerate(players):
            if lane in lanes:
                cands.append(i)
        slot_candidates.append(cands)

    idx_to_norm_name = {i: norm_name(players[i][0]) for i in range(10)}
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
            for k, (team_id, _) in enumerate(slots_sorted):
                pi = assign[k]
                _, _, wr, _ = players[pi]
                if team_id == 1:
                    t1_sum += wr
                else:
                    t2_sum += wr
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
            if violates_cant_same_team(team_id, nm):
                continue

            used[pi] = True
            assign[pos] = pi
            team_members[team_id].add(nm)

            # pruning
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
        raise ValueError("无法找到满足“两队各5人且五位置齐全 + 互斥规则 + 上赛季回退”的分配方案")

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

    print(
        "平均胜率:",
        "Team 1:", t1_sum / 5.0,
        ", Team 2:", t2_sum / 5.0,
        "| 差值:", abs(t1_sum / 5.0 - t2_sum / 5.0)
    )
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


def load_players_data(filename="S2026_stats.json"):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            players = json.load(file)
        return players
    except FileNotFoundError:
        print("File not found.")
        return None


def save_players_data(players, filename="S2026_stats.json"):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(players, file, ensure_ascii=False, indent=4)


class TeamBalancerApp:
    def __init__(self, root, players):
        self.root = root
        self.players = players
        self.rules = load_team_rules()
        self.rules_window = None
        self.current_team1 = []
        self.current_team2 = []
        self.current_prev_season = {}

        # ---- state ----
        self._sel_anchor = None
        self._hover_item = None
        self._base_tags = {}  # item_id -> "even"/"odd"

        # ---- window ----
        root.title("Team Balancer")
        root.geometry("860x780")
        root.minsize(820, 760)
        root.configure(bg="#F6F7FB")
        try:
            root.tk.call('tk', 'scaling', 1.2)
        except Exception:
            pass
        root.protocol("WM_DELETE_WINDOW", self.on_app_close)

        # ---- styles ----
        style = ttk.Style()
        try:
            style.theme_use("vista")
        except Exception:
            style.theme_use(style.theme_names()[0])

        UI_FONT = ("Microsoft YaHei UI", 11)
        UI_FONT_BOLD = ("Microsoft YaHei UI", 11, "bold")
        TREE_FONT = ("Microsoft YaHei UI", 12)
        TREE_FONT_BOLD = ("Microsoft YaHei UI", 12, "bold")
        TITLE_FONT = ("Microsoft YaHei UI", 16, "bold")
        RULE_FONT = ("Microsoft YaHei UI", 13)
        RULE_FONT_BOLD = ("Microsoft YaHei UI", 13, "bold")
        TEAM_RESULT_FONT = ("Microsoft YaHei UI", 10)

        style.configure("App.TFrame", background="#F6F7FB")
        style.configure("Card.TFrame", background="#FFFFFF", relief="solid", borderwidth=1)
        style.configure("CardInner.TFrame", background="#FFFFFF")

        style.configure("Title.TLabel", background="#F6F7FB", font=TITLE_FONT)
        style.configure("SubTitle.TLabel", background="#FFFFFF", font=UI_FONT_BOLD)
        style.configure("Hint.TLabel", background="#F6F7FB", foreground="#666666", font=("Microsoft YaHei UI", 10))
        style.configure("Info.TLabel", background="#F6F7FB", foreground="#333333", font=("Microsoft YaHei UI", 11, "bold"))
        style.configure("RuleHeader.TLabel", background="#FFFFFF", font=RULE_FONT_BOLD)
        style.configure("RuleName.TLabel", background="#FFFFFF", font=RULE_FONT)
        style.configure("RuleCardHint.TLabel", background="#FFFFFF", foreground="#555555", font=RULE_FONT)
        style.configure("RuleFooterHint.TLabel", background="#F6F7FB", foreground="#555555", font=RULE_FONT)
        style.configure("Rule.TCheckbutton", background="#FFFFFF", font=RULE_FONT, padding=(2, 2))

        style.configure("Treeview",
                        font=TREE_FONT,
                        rowheight=32,
                        background="#FFFFFF",
                        fieldbackground="#FFFFFF",
                        borderwidth=0)
        style.configure("Treeview.Heading", font=TREE_FONT_BOLD)
        style.map("Treeview",
                background=[("selected", "#6B9BF5")],
                foreground=[("selected", "#0F1E3A")])



        style.configure("Primary.TButton", font=UI_FONT, padding=(12, 8))
        style.configure("Secondary.TButton", font=UI_FONT, padding=(12, 8))
        style.configure("TeamResult.TButton", font=TEAM_RESULT_FONT, padding=(6, 5))

        # ---- layout root ----
        outer = ttk.Frame(root, style="App.TFrame", padding=8)
        outer.grid(row=0, column=0, sticky="nsew")
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)

        RIGHT_W = 280

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
            height=17,
            selectmode="extended"
        )
        self.player_tree.heading("Name", text="玩家ID", anchor="center")
        self.player_tree.heading("WinRate", text="胜率", anchor="center")
        self.player_tree.heading("Games", text="总场次", anchor="center")
        self.player_tree.column("Name", width=50, minwidth=50, anchor="center", stretch=True)
        self.player_tree.column("WinRate", width=50, minwidth=50, anchor="center", stretch=True)
        self.player_tree.column("Games", width=50, minwidth=50, anchor="center", stretch=True)


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

        btn_row = ttk.Frame(ctrl_card, style="CardInner.TFrame")
        btn_row.grid(row=1, column=0, sticky="ew")
        btn_row.grid_columnconfigure(0, weight=1)
        btn_row.grid_columnconfigure(1, weight=1)

        self.win_button = ttk.Button(btn_row, text="手动 Win", style="Secondary.TButton",
                                     command=lambda: self.update_win_loss(True))
        self.loss_button = ttk.Button(btn_row, text="手动 Loss", style="Secondary.TButton",
                                      command=lambda: self.update_win_loss(False))
        self.win_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.loss_button.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        self.balance_button = ttk.Button(ctrl_card, text="平衡分队", style="Primary.TButton",
                                         command=self.balance_teams)
        self.balance_button.grid(row=2, column=0, sticky="ew", pady=(10, 0))

        self.rules_button = ttk.Button(ctrl_card, text="更改规则", style="Secondary.TButton",
                                       command=self.open_rule_editor)
        self.rules_button.grid(row=3, column=0, sticky="ew", pady=(8, 0))

        # result card
        result_card = ttk.Frame(right_col, style="Card.TFrame", padding=8)
        result_card.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        result_card.grid_columnconfigure(0, weight=1)

        # team1
        team1_title = ttk.Label(result_card, text="Team 1", style="SubTitle.TLabel")
        team1_title.grid(row=0, column=0, sticky="w", pady=(0, 6))

        self.team1_listbox = tk.Listbox(
            result_card, width=22, height=6,
            font=("Microsoft YaHei UI", 11),
            bg="#FFFFFF", relief="solid", bd=1,
            highlightthickness=0, selectbackground="#DCEBFF",
            activestyle="none"
        )
        self.team1_listbox.grid(row=1, column=0, sticky="ew")

        self.team1_avg_label = ttk.Label(result_card, text="平均胜率: -", style="Hint.TLabel")
        self.team1_avg_label.grid(row=2, column=0, sticky="w", pady=(4, 8))

        result_btn_row = ttk.Frame(result_card, style="CardInner.TFrame")
        result_btn_row.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        result_btn_row.grid_columnconfigure(0, weight=1)
        result_btn_row.grid_columnconfigure(1, weight=1)

        self.team1_win_button = ttk.Button(
            result_btn_row,
            text="Team 1 Win",
            style="TeamResult.TButton",
            command=lambda: self.record_team_result(1)
        )
        self.team2_win_button = ttk.Button(
            result_btn_row,
            text="Team 2 Win",
            style="TeamResult.TButton",
            command=lambda: self.record_team_result(2)
        )
        self.team1_win_button.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.team2_win_button.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        self.team1_win_button.state(["disabled"])
        self.team2_win_button.state(["disabled"])

        # team2
        team2_title = ttk.Label(result_card, text="Team 2", style="SubTitle.TLabel")
        team2_title.grid(row=4, column=0, sticky="w", pady=(6, 6))

        self.team2_listbox = tk.Listbox(
            result_card, width=22, height=6,
            font=("Microsoft YaHei UI", 11),
            bg="#FFFFFF", relief="solid", bd=1,
            highlightthickness=0, selectbackground="#DCEBFF",
            activestyle="none"
        )
        self.team2_listbox.grid(row=5, column=0, sticky="ew")

        self.team2_avg_label = ttk.Label(result_card, text="平均胜率: -", style="Hint.TLabel")
        self.team2_avg_label.grid(row=6, column=0, sticky="w", pady=(4, 0))

        self.diff_label = ttk.Label(result_card, text="差值: -", style="Hint.TLabel")
        self.diff_label.grid(row=7, column=0, sticky="w", pady=(2, 0))

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

    def autosize_treeview_columns(self, pad_px=16, max_px=220):
        # 根据内容自动调整列宽
        tv = self.player_tree
        font = tkfont.Font(font=ttk.Style().lookup("Treeview", "font"))
        max_widths = {"Name": 100, "WinRate": 100, "Games": 100}
        min_widths = {"Name": 50, "WinRate": 50, "Games": 50}

        for col in ("Name", "WinRate", "Games"):
            heading = tv.heading(col, "text") or ""
            w = font.measure(heading) + pad_px

            for iid in tv.get_children(""):
                val = str(tv.set(iid, col))
                w = max(w, font.measure(val) + pad_px)

            w = max(min_widths[col], min(w, max_widths.get(col, max_px), max_px))
            tv.column(col, width=w, minwidth=min_widths[col], stretch=True)

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

    # ---------------- rule editor ----------------

    def on_app_close(self):
        if self.rules_window and self.rules_window.winfo_exists():
            if not self.save_rule_editor(self.rules_window, destroy_window=False):
                return

        try:
            save_players_data(self.players)
            save_team_rules(self.rules)
        except Exception as e:
            messagebox.showerror("保存失败", str(e), parent=self.root)
            return

        self.root.destroy()

    def open_rule_editor(self):
        if self.rules_window and self.rules_window.winfo_exists():
            self.rules_window.lift()
            self.rules_window.focus_force()
            return

        window = tk.Toplevel(self.root)
        self.rules_window = window
        window.title("更改规则")
        window.geometry("460x820")
        window.minsize(430, 760)
        window.configure(bg="#F6F7FB")
        window.transient(self.root)
        window.option_add("*TCombobox*Listbox.font", "{Microsoft YaHei UI} 13")

        outer = ttk.Frame(window, style="App.TFrame", padding=10)
        outer.grid(row=0, column=0, sticky="nsew")
        window.grid_rowconfigure(0, weight=1)
        window.grid_columnconfigure(0, weight=1)
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_rowconfigure(1, weight=1)

        title = ttk.Label(outer, text="规则设置", style="Title.TLabel")
        title.grid(row=0, column=0, sticky="w", pady=(0, 8))

        player_card = ttk.Frame(outer, style="Card.TFrame", padding=8)
        player_card.grid(row=1, column=0, sticky="nsew")
        player_card.grid_columnconfigure(0, weight=1)
        player_card.grid_rowconfigure(1, weight=1)

        player_title = ttk.Label(player_card, text="玩家候补位置", style="RuleHeader.TLabel")
        player_title.grid(row=0, column=0, sticky="w", pady=(0, 6))

        canvas = tk.Canvas(player_card, bg="#FFFFFF", highlightthickness=0, height=560)
        yscroll = ttk.Scrollbar(player_card, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=yscroll.set)
        canvas.grid(row=1, column=0, sticky="nsew")
        yscroll.grid(row=1, column=1, sticky="ns")

        rows_frame = ttk.Frame(canvas, style="CardInner.TFrame", padding=(8, 0, 6, 0))
        rows_window = canvas.create_window((0, 0), window=rows_frame, anchor="nw")

        def update_scroll_region(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def fit_rows_width(event):
            canvas.itemconfigure(rows_window, width=event.width)

        rows_frame.bind("<Configure>", update_scroll_region)
        canvas.bind("<Configure>", fit_rows_width)

        header_frame = tk.Frame(rows_frame, bg="#FFFFFF")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        header_frame.grid_columnconfigure(0, minsize=112)
        for col in range(1, len(LANES) + 1):
            header_frame.grid_columnconfigure(col, minsize=46)

        tk.Label(
            header_frame,
            text="玩家",
            bg="#FFFFFF",
            font=("Microsoft YaHei UI", 13, "bold"),
            anchor="w"
        ).grid(row=0, column=0, sticky="ew", padx=(4, 14), pady=(0, 4))

        for col, lane in enumerate(LANES, start=1):
            tk.Label(
                header_frame,
                text=lane,
                bg="#FFFFFF",
                font=("Microsoft YaHei UI", 13, "bold"),
                anchor="center"
            ).grid(row=0, column=col, sticky="ew", padx=2, pady=(0, 4))

        self.rule_lane_vars = {}
        for row, (player_name, player_data) in enumerate(self.players.items(), start=1):
            row_bg = "#FFFFFF" if row % 2 == 1 else "#F3F3F3"
            row_frame = tk.Frame(rows_frame, bg=row_bg)
            row_frame.grid(row=row, column=0, sticky="ew")
            row_frame.grid_columnconfigure(0, minsize=112)
            for col in range(1, len(LANES) + 1):
                row_frame.grid_columnconfigure(col, minsize=46)

            tk.Label(
                row_frame,
                text=player_name,
                bg=row_bg,
                font=("Microsoft YaHei UI", 13),
                anchor="w"
            ).grid(
                row=0, column=0, sticky="ew", padx=(4, 14), pady=3
            )
            selected_lanes = set(player_data.get("lane") or LANES)
            lane_vars = {}
            for col, lane in enumerate(LANES, start=1):
                var = tk.BooleanVar(value=lane in selected_lanes)
                lane_vars[lane] = var
                tk.Checkbutton(
                    row_frame,
                    variable=var,
                    bg=row_bg,
                    activebackground=row_bg,
                    selectcolor=row_bg,
                    highlightthickness=0,
                    bd=0
                ).grid(row=0, column=col, padx=4, pady=3)
            self.rule_lane_vars[player_name] = lane_vars

        rows_frame.grid_columnconfigure(0, weight=1)

        pair_card = ttk.Frame(outer, style="Card.TFrame", padding=8)
        pair_card.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        pair_card.grid_columnconfigure(1, weight=0)
        pair_card.grid_columnconfigure(3, weight=0)

        pair_title = ttk.Label(pair_card, text="不能同队的玩家", style="RuleHeader.TLabel")
        pair_title.grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 6))

        player_choices = [""] + list(self.players.keys())
        existing_pairs = clean_cant_same_team(self.rules.get("cant_same_team", []))
        self.rule_pair_vars = []

        for row in range(MAX_CANT_SAME_PAIRS):
            pair = existing_pairs[row] if row < len(existing_pairs) else ["", ""]
            left_var = tk.StringVar(value=pair[0])
            right_var = tk.StringVar(value=pair[1])
            self.rule_pair_vars.append((left_var, right_var))

            ttk.Label(pair_card, text=f"第 {row + 1} 组", style="RuleCardHint.TLabel").grid(
                row=row + 1, column=0, sticky="w", padx=(0, 8), pady=3
            )
            ttk.Combobox(pair_card, textvariable=left_var, values=player_choices, state="readonly", width=8, font=("Microsoft YaHei UI", 13)).grid(
                row=row + 1, column=1, sticky="w", padx=(0, 8), pady=3
            )
            ttk.Label(pair_card, text="不可同队", style="RuleCardHint.TLabel").grid(
                row=row + 1, column=2, padx=(0, 8), pady=3
            )
            ttk.Combobox(pair_card, textvariable=right_var, values=player_choices, state="readonly", width=8, font=("Microsoft YaHei UI", 13)).grid(
                row=row + 1, column=3, sticky="w", pady=3
            )

        footer = ttk.Frame(outer, style="App.TFrame")
        footer.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        footer.grid_columnconfigure(0, weight=1)

        self.rules_status_label = ttk.Label(footer, text="关闭窗口时会自动保存", style="RuleFooterHint.TLabel")
        self.rules_status_label.grid(row=0, column=0, sticky="w")

        save_button = ttk.Button(
            footer,
            text="保存并关闭",
            style="Primary.TButton",
            command=lambda: self.save_rule_editor(window)
        )
        save_button.grid(row=0, column=1, sticky="e")

        window.protocol("WM_DELETE_WINDOW", lambda: self.save_rule_editor(window))

    def save_rule_editor(self, window, destroy_window=True):
        for player_name, lane_vars in self.rule_lane_vars.items():
            lanes = [lane for lane in LANES if lane_vars[lane].get()]
            if not lanes:
                messagebox.showerror("规则错误", f"{player_name} 至少需要选择一个位置", parent=window)
                return False

        pairs = []
        seen = set()
        for left_var, right_var in self.rule_pair_vars:
            left = left_var.get().strip()
            right = right_var.get().strip()

            if not left and not right:
                continue
            if not left or not right:
                messagebox.showerror("规则错误", "互斥组需要同时选择两个玩家，或两边都留空", parent=window)
                return False
            if left == right:
                messagebox.showerror("规则错误", "同一组里不能选择同一个玩家", parent=window)
                return False

            key = tuple(sorted((left.lower(), right.lower())))
            if key in seen:
                messagebox.showerror("规则错误", "不能重复设置同一组互斥玩家", parent=window)
                return False
            seen.add(key)
            pairs.append([left, right])

        for player_name, lane_vars in self.rule_lane_vars.items():
            self.players[player_name]["lane"] = [lane for lane in LANES if lane_vars[lane].get()]

        self.rules["cant_same_team"] = clean_cant_same_team(pairs)

        try:
            save_players_data(self.players)
            saved_to_py = save_team_rules(self.rules)
        except Exception as e:
            messagebox.showerror("保存失败", str(e), parent=window)
            return False

        self.populate_player_tree()
        if not saved_to_py:
            messagebox.showwarning("保存提醒", "规则已保存到 JSON，但没有成功同步写入 main_v3.py", parent=window)

        if destroy_window and window.winfo_exists():
            window.destroy()
            self.rules_window = None

        return True

    # ---------------- actions ----------------

    def restore_player_selection(self, selected_names):
        tv = self.player_tree
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

    def render_team_results(self, team1=None, team2=None, prev_season=None):
        team1 = team1 if team1 is not None else self.current_team1
        team2 = team2 if team2 is not None else self.current_team2
        prev_season = prev_season if prev_season is not None else self.current_prev_season

        self.team1_listbox.delete(0, tk.END)
        self.team2_listbox.delete(0, tk.END)

        if not team1 or not team2:
            self.team1_avg_label.config(text="平均胜率: -")
            self.team2_avg_label.config(text="平均胜率: -")
            self.diff_label.config(text="差值: -")
            self.team1_win_button.state(["disabled"])
            self.team2_win_button.state(["disabled"])
            return

        sorted_team1 = sorted(team1, key=lambda x: LANES.index(x[2]))
        sorted_team2 = sorted(team2, key=lambda x: LANES.index(x[2]))

        def fmt_player_line(lane, name, data):
            cur_wr = float(data.get("win_rate", 0.0))
            games = int(data.get("games", 0))

            tag = ""
            if games < 10:
                if name in prev_season:
                    tag = "*"
                else:
                    tag = "[NEW]"

            return f"{lane}: {name}- {cur_wr:.2f}% ({games}场{tag})"

        for name, data, lane in sorted_team1:
            self.team1_listbox.insert(tk.END, fmt_player_line(lane, name, data))

        for name, data, lane in sorted_team2:
            self.team2_listbox.insert(tk.END, fmt_player_line(lane, name, data))

        t1_avg = sum(weighted_win_rate(d, n, prev_season) for n, d, _ in team1) / 5.0
        t2_avg = sum(weighted_win_rate(d, n, prev_season) for n, d, _ in team2) / 5.0
        diff = abs(t1_avg - t2_avg)

        self.team1_avg_label.config(text=f"平均胜率: {t1_avg:.2f}%")
        self.team2_avg_label.config(text=f"平均胜率: {t2_avg:.2f}%")
        self.diff_label.config(text=f"胜率差值: {diff:.2f}%")
        self.team1_win_button.state(["!disabled"])
        self.team2_win_button.state(["!disabled"])

    def record_team_result(self, winning_team_id: int):
        if not self.current_team1 or not self.current_team2:
            messagebox.showerror("错误", "请先平衡分队，再记录队伍胜负")
            return

        if winning_team_id == 1:
            winners = self.current_team1
            losers = self.current_team2
        else:
            winners = self.current_team2
            losers = self.current_team1

        for name, _, _ in winners:
            update_player_stats(self.players, name, True)
        for name, _, _ in losers:
            update_player_stats(self.players, name, False)

        save_players_data(self.players)
        participant_names = [name for name, _, _ in self.current_team1 + self.current_team2]

        self.populate_player_tree()
        self.restore_player_selection(participant_names)
        self.render_team_results()

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
        self.render_team_results()


    def balance_teams(self):
        selected_items = self.player_tree.selection()
        if len(selected_items) != 10:
            messagebox.showerror("错误", "请选择10名玩家进行游戏")
            return

        selected_players = {
            self.player_tree.item(i, "values")[0]: self.players[self.player_tree.item(i, "values")[0]]
            for i in selected_items
        }

        # 读取上赛季数据（失败就当空）
        try:
            with open("S4_stats.json", "r", encoding="utf-8") as f:
                prev_season = json.load(f)
        except Exception:
            prev_season = {}

        try:
            team1, team2 = create_balanced_teams(
                selected_players,
                prev_season=prev_season,
                cant_same_team=self.rules.get("cant_same_team", [])
            )
        except Exception as e:
            messagebox.showerror("分队失败", str(e))
            return

        self.current_team1 = team1
        self.current_team2 = team2
        self.current_prev_season = prev_season
        self.render_team_results()

        self.update_selected_count()




if __name__ == "__main__":
    players = load_players_data() or {}
    root = tk.Tk()
    app = TeamBalancerApp(root, players)
    root.mainloop()
