import tkinter as tk
from tkinter import messagebox
from tkinter.ttk import Treeview, Scrollbar, Style
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
    """
    players = []
    for name, data in selected_players.items():
        lanes = list(data.get("lane", []))
        if not lanes:
            # 没有lane数据就当全能
            lanes = LANES[:]
        players.append((name, data, weighted_win_rate(data), lanes))

    if len(players) != 10:
        raise ValueError("selected_players 必须恰好 10 人")

    # 10 个槽位：Team1 5个位置 + Team2 5个位置
    slots = [(1, lane) for lane in LANES] + [(2, lane) for lane in LANES]

    # 预检查：每个 lane 至少要有 2 个候选（否则一定无法让两队都覆盖）
    lane_to_candidates = {lane: [] for lane in LANES}
    for i, (_, _, _, lanes) in enumerate(players):
        for lane in lanes:
            if lane in lane_to_candidates:
                lane_to_candidates[lane].append(i)
    for lane in LANES:
        if len(lane_to_candidates[lane]) < 2:
            # 错误信息
            raise ValueError(f"无法分队：位置[{lane}]的可选人数不足 2（当前={len(lane_to_candidates[lane])}）")

    # 优先填“候选更少”的槽位
    def slot_key(s):
        _, lane = s
        return len(lane_to_candidates[lane])

    slots_sorted = sorted(slots, key=slot_key)

    # 单位置玩家：必须被放进该lane的某一个队
    single_pos_idx = set(i for i, (_, _, _, lanes) in enumerate(players) if len(lanes) == 1)

    best_assign = None
    best_diff = float("inf")

    used = [False] * 10
    assign = [None] * 10  # 对 slots_sorted 的每个槽位，存放 player index

    # 预计算：每个槽位可用玩家（按候选位置过滤）
    slot_candidates = []
    for team_id, lane in slots_sorted:
        cands = []
        for i, (_, _, _, lanes) in enumerate(players):
            if lane in lanes:
                cands.append(i)
        slot_candidates.append(cands)

    # 剩余未用玩家的winrate上下界对diff的影响

    def backtrack(pos):
        nonlocal best_assign, best_diff

        if pos == len(slots_sorted):
            # 计算两队平均胜率差
            t1 = []
            t2 = []
            for k, (team_id, lane) in enumerate(slots_sorted):
                pi = assign[k]
                name, data, wr, _ = players[pi]
                if team_id == 1:
                    t1.append(wr)
                else:
                    t2.append(wr)
            diff = abs(sum(t1) / 5.0 - sum(t2) / 5.0)
            if diff < best_diff:
                best_diff = diff
                best_assign = assign[:]
            return

        team_id, lane = slots_sorted[pos]

        for pi in slot_candidates[pos]:
            if used[pi]:
                continue

            # 单位置玩家如果只能打一个 lane，那么它必须被放进那个 lane 的槽位
            # 单位置玩家不会被迫“挤掉”导致另一个队该 lane 无人可用
            used[pi] = True
            assign[pos] = pi

            # 对于每个 lane，如果某队的该 lane 尚未填，那么剩余未用玩家里是否还存在能填这个槽的候选
            ok = True
            filled = {(slots_sorted[k][0], slots_sorted[k][1]) for k in range(pos + 1)}
            for (t, l) in slots_sorted[pos + 1:]:
                if (t, l) in filled:
                    continue
                # 还未填的槽位 (t,l)
                exists = False
                for cand in lane_to_candidates[l]:
                    if not used[cand]:
                        exists = True
                        break
                if not exists:
                    ok = False
                    break

            if ok:
                backtrack(pos + 1)

            used[pi] = False
            assign[pos] = None

    backtrack(0)

    if best_assign is None:
        raise ValueError("无法找到满足“两队各5人且五位置齐全”的分配方案（可能是位置选择集合导致不可行）")

    # 还原为 team1/team2 列表 (name, data, lane)
    team1 = []
    team2 = []
    t1_sum = 0.0
    t2_sum = 0.0

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

        style = Style()
        style.configure("Treeview", rowheight=30)
        style.configure("Treeview.Heading", font=('Arial', 12, 'bold'))
        style.configure("Treeview", font=('Arial', 11))

        self.title_label = tk.Label(root, text="请选择本次参与游戏的10人")
        self.title_label.pack()

        self.player_tree = Treeview(root, columns=("Name", "WinRate", "Games"), show='headings', height=20)
        self.player_tree.heading("Name", text="名字", anchor='center')
        self.player_tree.heading("WinRate", text="胜率", anchor='center')
        self.player_tree.heading("Games", text="总游戏数", anchor='center')
        self.player_tree.column("Name", width=100, anchor='center')
        self.player_tree.column("WinRate", width=100, anchor='center')
        self.player_tree.column("Games", width=100, anchor='center')
        self.player_tree['selectmode'] = 'extended'
        self.populate_player_tree()

        scrollbar = Scrollbar(root, command=self.player_tree.yview)
        self.player_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.player_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.player_tree.bind('<Button-1>', self.toggle_selection)
        self._anchor_item = None

        self.win_button = tk.Button(root, text="Win", command=lambda: self.update_win_loss(True))
        self.loss_button = tk.Button(root, text="Loss", command=lambda: self.update_win_loss(False))
        self.win_button.pack(side=tk.TOP, padx=10, pady=10)
        self.loss_button.pack(side=tk.TOP, padx=10, pady=10)

        self.team1_label = tk.Label(root, text="Team 1")
        self.team2_label = tk.Label(root, text="Team 2")
        self.team1_listbox = tk.Listbox(root, width=27, height=8)
        self.team2_listbox = tk.Listbox(root, width=27, height=8)
        self.balance_button = tk.Button(root, text="平衡分队", command=self.balance_teams)
        self.balance_button.pack()

        self.team1_label.pack()
        self.team1_listbox.pack()
        self.team2_label.pack()
        self.team2_listbox.pack()

    def populate_player_tree(self):
        for player_name, player_data in sorted(self.players.items(), key=lambda item: -item[1]['win_rate']):
            self.player_tree.insert("", tk.END,
                                    values=(player_name, f"{player_data['win_rate']}%", player_data["games"]))

    def toggle_selection(self, event):
        tv = self.player_tree

        # 只处理点击在单元格/行区域的情况
        region = tv.identify("region", event.x, event.y)
        if region not in ("cell", "tree"):
            return

        item = tv.identify_row(event.y)
        if not item:
            return

        # Windows 上常见：Shift=0x0001, Ctrl=0x0004（不同平台可能有差异，但这俩在 Win 基本稳）
        shift = (event.state & 0x0001) != 0
        ctrl  = (event.state & 0x0004) != 0

        selected = set(tv.selection())

        # 初始化锚点：上一次“非 shift 点击”的那一行
        if not hasattr(self, "_sel_anchor"):
            self._sel_anchor = None

        if shift:
            # Shift：连续选择（不管当前是否已选，都按范围选择）
            # 如果没有锚点，则用当前 focus 或任一已选项作为锚点
            anchor = self._sel_anchor or tv.focus() or (next(iter(selected)) if selected else item)
            items = list(tv.get_children(""))
            try:
                a = items.index(anchor)
            except ValueError:
                a = items.index(item)
            b = items.index(item)
            lo, hi = (a, b) if a <= b else (b, a)

            # 这里的语义按你说的“shift 覆盖中间所有”——通常不保留其它离散选择
            tv.selection_set(items[lo:hi + 1])
            tv.focus(item)
            return "break"

        if ctrl:
            # Ctrl：toggle 单行，不影响其它
            if item in selected:
                tv.selection_remove(item)
            else:
                tv.selection_add(item)
            tv.focus(item)
            # ctrl 点击不改变锚点（也可以改成 item，看你习惯）
            return "break"

        # 普通单击：清空之前选择，只选当前；如果点到已选中，则取消（toggle）
        if item in selected and len(selected) == 1:
            tv.selection_remove(item)
            tv.focus("")
            self._sel_anchor = None
        else:
            tv.selection_set(item)
            tv.focus(item)
            self._sel_anchor = item

        return "break"



    def update_win_loss(self, is_winner):
        selected_items = self.player_tree.selection()
        for item in selected_items:
            player_name = self.player_tree.item(item, 'values')[0]
            update_player_stats(self.players, player_name, is_winner)
        save_players_data(self.players)
        self.refresh_player_tree()

    def refresh_player_tree(self):
        for i in self.player_tree.get_children():
            player_name = self.player_tree.item(i, 'values')[0]
            player_data = self.players[player_name]
            self.player_tree.item(i, values=(player_name, f"{player_data['win_rate']}%", player_data["games"]))

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


if __name__ == "__main__":
    players = load_players_data() or {}
    root = tk.Tk()
    root.title("Team Balancer")
    app = TeamBalancerApp(root, players)
    root.mainloop()
