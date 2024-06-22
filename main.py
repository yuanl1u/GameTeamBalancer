import tkinter as tk
from tkinter import messagebox
from tkinter.ttk import Treeview, Scrollbar, Style
import json

# 55及以上为上等马
# 45以下为下等马
# 其余为中等马
kPowerThreshold = 55
kNormalThreshold = 50


def team_addition(team, team_weight, team_positions,
                  weight, lane, player_name, player_data):
    team.append((player_name, player_data, lane))
    team_weight = team_weight + weight
    team_positions[lane] += 1
    return team_weight


def he_can_be_added(player_name, team_players):
    if len(team_players) == 5:
        return False
    elif player_name == "杰尼龟":
        return "鸡" not in team_players
    elif player_name == "基拉祈":
        return "严酷训域" not in team_players
    elif player_name == "鸡":
        return "杰尼龟" not in team_players and "严酷训诫" not in team_players
    return True

def team_assignment(team1, team1_weight, team1_positions, team1_players,
                    team2, team2_weight, team2_positions, team2_players,
                    weight, lane, player_name, player_data):
    # Pre-check those who do not want in the same team
    if not he_can_be_added(player_name, team1_players) and \
            he_can_be_added(player_name, team2_players):
        team2_weight = team_addition(team2, team2_weight, team2_positions,
                                     weight, lane, player_name, player_data)
        team2_players.append(player_name)
        print(player_name, lane, weight, "team2-1")
        return team1_weight, team2_weight
    elif not he_can_be_added(player_name, team2_players) and \
            he_can_be_added(player_name, team1_players):
        team1_weight = team_addition(team1, team1_weight, team1_positions,
                                     weight, lane, player_name, player_data)
        team1_players.append(player_name)
        print(player_name, lane, weight, "team1-1")
        return team1_weight, team2_weight

    team1_avg = 0
    team2_avg = 0
    if len(team1) != 0:
        team1_avg = team1_weight / len(team1)
    if len(team2) != 0:
        team2_avg = team2_weight / len(team2)

    # team1 弱于 team2, 则优先将上等马分给 team1；
    # 连续三轮选秀没有上等马，则将第三只中等马分给team1; 除此之外的中/下等马分给 team2
    if team1_avg < team2_avg:
        print("team1:", team1_avg, "team2:", team2_avg)
        if weight >= kPowerThreshold or \
                (len(team2) - len(team1) > 1 and weight >= kNormalThreshold):
            team1_weight = team_addition(team1, team1_weight, team1_positions,
                                         weight, lane, player_name, player_data)
            team1_players.append(player_name)
            print(player_name, lane, weight, "team1-2")
        else:
            team2_weight = team_addition(team2, team2_weight, team2_positions,
                                         weight, lane, player_name, player_data)
            team2_players.append(player_name)
            print(player_name, lane, weight, "team2-2")
    else:
        print("team1:", team1_avg, "team2:", team2_avg)
        if weight >= kPowerThreshold or \
                (len(team1) - len(team2) > 1 and weight >= kNormalThreshold):
            team2_weight = team_addition(team2, team2_weight, team2_positions,
                                         weight, lane, player_name, player_data)
            team2_players.append(player_name)
            print(player_name, lane, weight, "team2-3")
        else:
            team1_weight = team_addition(team1, team1_weight, team1_positions,
                                         weight, lane, player_name, player_data)
            team1_players.append(player_name)
            print(player_name, lane, weight, "team1-3")
    return team1_weight, team2_weight


def weighted_win_rate(player):
    if player["games"] < 5:
        return 50.0  # 设置默认胜率为50%以避免极端情况
    return player["win_rate"]


def sort_team(players_list):
    single_pos_players = [x for x in players_list if len(x[1]["lane"]) == 1]
    multi_pos_players = [x for x in players_list if x not in single_pos_players]
    sorted_multi_pos_players_by_wr = sorted(multi_pos_players, key=lambda item: weighted_win_rate(item[1]),
                                            reverse=True)
    sorted_multi_pos_players = []
    mid_size = int(len(sorted_multi_pos_players_by_wr) / 2)
    for i in range(mid_size):
        sorted_multi_pos_players.append(sorted_multi_pos_players_by_wr[i])
        sorted_multi_pos_players.append(sorted_multi_pos_players_by_wr[len(sorted_multi_pos_players_by_wr) - i - 1])
    if len(sorted_multi_pos_players_by_wr) % 2 != 0:
        sorted_multi_pos_players.append(sorted_multi_pos_players_by_wr[mid_size])
    single_pos_players.extend(sorted_multi_pos_players)
    return single_pos_players


def create_balanced_teams(selected_players):
    players_list = list(selected_players.items())
    team1 = []
    team2 = []
    team1_weight = 0
    team2_weight = 0
    team1_positions = {"上单": 0, "中单": 0, "打野": 0, "射手": 0, "辅助": 0}
    team2_positions = {"上单": 0, "中单": 0, "打野": 0, "射手": 0, "辅助": 0}
    team1_players = []
    team2_players = []

    # 提取特殊玩家并优先分配
    special_players = {"基拉祈", "鸡", "严酷训诫", "小超梦", "香克斯"}
    special_team1 = []
    special_team2 = []

    for player_name, player_data in players_list:
        if player_name in special_players:
            if player_name in {"严酷训诫", "香克斯"}:
                special_team1.append((player_name, player_data, None))
            else:
                special_team2.append((player_name, player_data, None))

    if len(special_team1) == 2 and len(special_team2) == 3:
        # 优先分配特殊玩家到各自队伍并设定默认位置
        team1.append(("严酷训诫", next(data for name, data, _ in special_team1 if name == "严酷训诫"), "上单"))
        team1.append(("香克斯", next(data for name, data, _ in special_team1 if name == "香克斯"), "射手"))
        team2.append(("基拉祈", next(data for name, data, _ in special_team2 if name == "基拉祈"), "射手"))
        team2.append(("鸡", next(data for name, data, _ in special_team2 if name == "鸡"), "辅助"))
        team2.append(("小超梦", next(data for name, data, _ in special_team2 if name == "小超梦"), "上单"))

        # 更新队伍权重
        team1_weight = sum(weighted_win_rate(player_data) for _, player_data, _ in team1)
        team2_weight = sum(weighted_win_rate(player_data) for _, player_data, _ in team2)

        # 更新位置计数器
        team1_positions = {"上单": 1, "中单": 0, "打野": 0, "射手": 1, "辅助": 0}
        team2_positions = {"上单": 1, "中单": 0, "打野": 0, "射手": 1, "辅助": 1}

        team1_players = [player_name for player_name, _, _ in team1]
        team2_players = [player_name for player_name, _, _ in team2]

        # 将剩余玩家分配到队伍中，同时考虑其首选位置并平衡位置
        for player_name, player_data in players_list:
            if player_name in special_players:
                continue
            weight = weighted_win_rate(player_data)
            if player_name == "杰尼龟":
                weight *= 1.1
            preferred_lanes = player_data["lane"]
            assigned = False
            for lane in preferred_lanes:
                # 双方队伍都缺少该位置的情况
                if team1_positions[lane] < 1 and team2_positions[lane] < 1:
                    if he_can_be_added(player_name, team1_players):
                        team1_weight, team2_weight = team_assignment(team1, team1_weight, team1_positions,
                                                                     team1_players,
                                                                     team2, team2_weight, team2_positions,
                                                                     team2_players,
                                                                     weight, lane, player_name, player_data)
                        assigned = True
                        break
                    elif he_can_be_added(player_name, team2_players):
                        team1_weight, team2_weight = team_assignment(team1, team1_weight, team1_positions,
                                                                     team1_players,
                                                                     team2, team2_weight, team2_positions,
                                                                     team2_players,
                                                                     weight, lane, player_name, player_data)
                        assigned = True
                        break
                elif team1_positions[lane] < 1 and he_can_be_added(player_name, team1_players):
                    team1_weight = team_addition(team1, team1_weight, team1_positions, weight, lane, player_name,
                                                 player_data)
                    team1_players.append(player_name)
                    print(player_name, lane, weight, "team1-4")
                    assigned = True
                    break
                elif team2_positions[lane] < 1 and he_can_be_added(player_name, team2_players):
                    team2_weight = team_addition(team2, team2_weight, team2_positions, weight, lane, player_name,
                                                 player_data)
                    team2_players.append(player_name)
                    print(player_name, lane, weight, "team2-4")
                    assigned = True
                    break
            if not assigned:
                team1_weight, team2_weight = team_assignment(team1, team1_weight, team1_positions, team1_players,
                                                             team2, team2_weight, team2_positions, team2_players,
                                                             weight, lane, player_name, player_data)
    else:
        # 将玩家按照其位置多样性升序，保证只玩一个位置的玩家可以优先被考虑；
        # 在位置数量一样的情况下，按胜率降序，保证强的选手可以优先被考虑
        sorted_players_by_pos = sort_team(players_list)
        # 将玩家分配到队伍中，同时考虑其首选位置并平衡位置
        for player_name, player_data in sorted_players_by_pos:
            weight = weighted_win_rate(player_data)
            if player_name == "杰尼龟":
                weight *= 1.1
            preferred_lanes = player_data["lane"]
            assigned = False
            for lane in preferred_lanes:
                # 双方队伍都缺少该位置的情况
                if team1_positions[lane] < 1 and team2_positions[lane] < 1:
                    team1_weight, team2_weight = team_assignment(team1, team1_weight, team1_positions, team1_players,
                                                                 team2, team2_weight, team2_positions, team2_players,
                                                                 weight, lane, player_name, player_data)
                    assigned = True
                    break
                elif team1_positions[lane] < 1 and he_can_be_added(player_name, team1_players):
                    team1_weight = team_addition(team1, team1_weight, team1_positions, weight, lane, player_name,
                                                 player_data)
                    team1_players.append(player_name)
                    print(player_name, lane, weight, "team1-4")
                    assigned = True
                    break
                elif team2_positions[lane] < 1 and he_can_be_added(player_name, team2_players):
                    team2_weight = team_addition(team2, team2_weight, team2_positions, weight, lane, player_name,
                                                 player_data)
                    team2_players.append(player_name)
                    print(player_name, lane, weight, "team2-4")
                    assigned = True
                    break
            if not assigned:
                team1_weight, team2_weight = team_assignment(team1, team1_weight, team1_positions, team1_players,
                                                             team2, team2_weight, team2_positions, team2_players,
                                                             weight, lane, player_name, player_data)

    print("平均胜率:", "Team 1: ", team1_weight / len(team1), ", Team 2: ", team2_weight / len(team2))
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


def load_players_data(filename="players_data.json"):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            players = json.load(file)
        return players
    except FileNotFoundError:
        print("File not found.")
        return None


def save_players_data(players, filename="players_data.json"):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(players, file, ensure_ascii=False, indent=4)


class TeamBalancerApp:
    def __init__(self, root, players):
        self.root = root
        self.players = players

        # Set style for Treeview
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
        region = self.player_tree.identify("region", event.x, event.y)
        if region == "cell":
            item = self.player_tree.identify_row(event.y)
            if self.player_tree.selection_includes(item):
                self.player_tree.selection_remove(item)
            else:
                self.player_tree.selection_add(item)

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

        selected_players = {self.player_tree.item(i, 'values')[0]: self.players[self.player_tree.item(i, 'values')[0]]
                            for i in selected_items}
        team1, team2 = create_balanced_teams(selected_players)

        self.team1_listbox.delete(0, tk.END)
        self.team2_listbox.delete(0, tk.END)

        # 按位置排序
        positions_order = ["上单", "打野", "中单", "射手", "辅助"]
        sorted_team1 = sorted(team1, key=lambda x: positions_order.index(x[2]))
        sorted_team2 = sorted(team2, key=lambda x: positions_order.index(x[2]))

        for player_name, player_data, lane in sorted_team1:
            self.team1_listbox.insert(tk.END,
                                      f"{lane}: {player_name}- {player_data['win_rate']}% ({player_data['games']} 场)")

        for player_name, player_data, lane in sorted_team2:
            self.team2_listbox.insert(tk.END,
                                      f"{lane}: {player_name}- {player_data['win_rate']}% ({player_data['games']} 场)")


if __name__ == "__main__":
    players = load_players_data() or {}
    root = tk.Tk()
    root.title("Team Balancer")
    app = TeamBalancerApp(root, players)
    root.mainloop()
