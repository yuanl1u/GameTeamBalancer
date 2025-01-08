import tkinter as tk
from tkinter import messagebox
from tkinter.ttk import Treeview, Scrollbar, Style
import json

# 54及以上为上等马
# 45以下为下等马
# 其余为中等马
kPowerThreshold = 52
kNormalThreshold = 45


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
        return "鸡" not in team_players and "c罗" not in team_players
    elif player_name == "c罗":
        return "杰尼龟" not in team_players
    elif player_name == "基拉祈":
        return "严酷训域" not in team_players
    elif player_name == "木守宫":
        return "基拉祈" in team_players
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
    if player["games"] < 5 and player["win_rate"] > 60.0:
        return 60.0
    elif player["games"] < 5 and player["win_rate"] < 40.0:
        return 40.0
    elif player["games"] < 5:
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


def check_positions_covered(team_positions):
    for pos in ["上单", "中单", "打野", "射手", "辅助"]:
        if team_positions[pos] < 1:
            return False
    return True


def swap_players_if_better(team1, team2, team1_weight, team2_weight):
    best_team1, best_team2 = team1[:], team2[:]
    best_diff = abs(team1_weight - team2_weight)
    improved = False
    final_team1_weight = team1_weight
    final_team2_weight = team2_weight

    for i, (p1_name, p1_data, p1_lane) in enumerate(team1):
        for j, (p2_name, p2_data, p2_lane) in enumerate(team2):
            if p1_lane == p2_lane or (p1_lane in p2_data["lane"] and p2_lane in p1_data["lane"]):
                new_team1 = team1[:]
                new_team2 = team2[:]
                new_team1[i], new_team2[j] = (p2_name, p2_data, p2_lane), (p1_name, p1_data, p1_lane)
                new_team1_weight = sum(weighted_win_rate(data) for _, data, _ in new_team1)
                new_team2_weight = sum(weighted_win_rate(data) for _, data, _ in new_team2)
                new_diff = abs(new_team1_weight - new_team2_weight)
                if new_diff < best_diff:
                    best_team1, best_team2 = new_team1[:], new_team2[:]
                    best_diff = new_diff
                    improved = True
                    final_team1_weight = new_team1_weight
                    final_team2_weight = new_team2_weight
                    print("同位置互换成功！交易前胜率差：", abs(team1_weight - team2_weight), "交易后胜率差：", best_diff)
    pos_player_weight_1 = dict()
    i_1 = 0
    for item in best_team1:
        pos_player_weight_1[item[2]] = (item[0], item[1], i_1)
        i_1 += 1
    pos_player_weight_2 = dict()
    i_2 = 0
    for item in best_team2:
        pos_player_weight_2[item[2]] = (item[0], item[1], i_2)
        i_2 += 1
    team1_sum = sum(weighted_win_rate(data) for _, data, _ in best_team1)
    team2_sum = sum(weighted_win_rate(data) for _, data, _ in best_team2)
    mid_id_1 = pos_player_weight_1["中单"][2]
    mid_id_2 = pos_player_weight_2["中单"][2]
    if ('打野' in pos_player_weight_1 and '打野' not in pos_player_weight_2 and
            pos_player_weight_1["中单"][0] == "c罗" and pos_player_weight_1["打野"][0] == "杰尼龟"):
        best_team1[mid_id_1], best_team2[mid_id_2] = (
            (pos_player_weight_2["中单"][0], pos_player_weight_2["中单"][1], "中单"),
            ("c罗", pos_player_weight_1["中单"][1], "中单"))
        return best_team1, best_team2, improved, final_team1_weight, final_team2_weight
    elif ('打野' in pos_player_weight_2 and '打野' not in pos_player_weight_1 and
          pos_player_weight_2["中单"][0] == "c罗" and pos_player_weight_2["打野"][0] == "杰尼龟"):
        best_team2[mid_id_2], best_team1[mid_id_1] = (
            (pos_player_weight_1["中单"][0], pos_player_weight_1["中单"][1], "中单"),
            ("c罗", pos_player_weight_2["中单"][1], "中单"))
        return best_team1, best_team2, improved, final_team1_weight, final_team2_weight
    elif ('打野' not in pos_player_weight_1 or '打野' not in pos_player_weight_2 or
            '中单' not in pos_player_weight_1 or '中单' not in pos_player_weight_2):
        return best_team1, best_team2, improved, final_team1_weight, final_team2_weight
    jg_id_1 = pos_player_weight_1["打野"][2]
    jg_id_2 = pos_player_weight_2["打野"][2]
    if pos_player_weight_1["中单"][0] == "c罗" and pos_player_weight_1["打野"][0] == "杰尼龟":
        jg_change_diff = abs(team1_sum - pos_player_weight_1['打野'][1]['win_rate'] + pos_player_weight_2["打野"][1][
            'win_rate'] - team2_sum)
        mid_change_diff = abs(team1_sum - pos_player_weight_1['中单'][1]['win_rate'] + pos_player_weight_2["中单"][1][
            'win_rate'] - team2_sum)
        if jg_change_diff < mid_change_diff:
            best_team1[jg_id_1], best_team2[jg_id_2] = (
            (pos_player_weight_2["打野"][0], pos_player_weight_2["打野"][1], "打野"),
            ("杰尼龟", pos_player_weight_1["打野"][1], "打野"))
        else:
            best_team1[mid_id_1], best_team2[mid_id_2] = (
            (pos_player_weight_2["中单"][0], pos_player_weight_2["中单"][1], "中单"),
            ("c罗", pos_player_weight_1["中单"][1], "中单"))
    elif pos_player_weight_2["中单"][0] == "c罗" and pos_player_weight_2["打野"][0] == "杰尼龟":
        jg_change_diff = abs(team2_sum - pos_player_weight_2['打野'][1]['win_rate'] + pos_player_weight_1["打野"][1][
            'win_rate'] - team1_sum)
        mid_change_diff = abs(team2_sum - pos_player_weight_2['中单'][1]['win_rate'] + pos_player_weight_1["中单"][1][
            'win_rate'] - team1_sum)
        if jg_change_diff < mid_change_diff:
            best_team2[jg_id_2], best_team1[jg_id_1] = (
            (pos_player_weight_1["打野"][0], pos_player_weight_1["打野"][1], "打野"),
            ("杰尼龟", pos_player_weight_2["打野"][1], "打野"))
        else:
            best_team2[mid_id_2], best_team1[mid_id_1] = (
            (pos_player_weight_1["中单"][0], pos_player_weight_1["中单"][1], "中单"),
            ("c罗", pos_player_weight_2["中单"][1], "中单"))

    pos_player_weight_1 = dict()
    i_1 = 0
    for item in best_team1:
        pos_player_weight_1[item[2]] = (item[0], item[1], i_1)
        i_1 += 1
    pos_player_weight_2 = dict()
    i_2 = 0
    for item in best_team2:
        pos_player_weight_2[item[2]] = (item[0], item[1], i_2)
        i_2 += 1
    if ('打野' not in pos_player_weight_1 or '打野' not in pos_player_weight_2 or
            '辅助' not in pos_player_weight_1 or '辅助' not in pos_player_weight_2):
        return best_team1, best_team2, improved, final_team1_weight, final_team2_weight
    sup_id_1 = pos_player_weight_1["辅助"][2]
    sup_id_2 = pos_player_weight_2["辅助"][2]
    if (pos_player_weight_1["打野"][0] == "杰尼龟" and pos_player_weight_1["射手"][0] == "右蛋" and
            pos_player_weight_1["辅助"][0] == "左蛋"):
        best_team1[sup_id_1], best_team2[sup_id_2] = (
            (pos_player_weight_2["辅助"][0], pos_player_weight_2["辅助"][1], "辅助"),
            ("左蛋", pos_player_weight_1["辅助"][1], "辅助"))
    elif (pos_player_weight_2["打野"][0] == "杰尼龟" and pos_player_weight_2["射手"][0] == "右蛋" and
          pos_player_weight_2["辅助"][0] == "左蛋"):
        best_team2[sup_id_2], best_team1[sup_id_1] = (
            (pos_player_weight_1["辅助"][0], pos_player_weight_1["辅助"][1], "辅助"),
            ("左蛋", pos_player_weight_2["辅助"][1], "辅助"))
    return best_team1, best_team2, improved, final_team1_weight, final_team2_weight


def adjust_positions(team1, team1_positions, team2, team2_positions):
    all_positions = {"上单", "中单", "打野", "射手", "辅助"}

    def find_player_for_position(team, position):
        for i, (player_name, player_data, lane) in enumerate(team):
            if position in player_data["lane"] and lane != position:
                return i, (player_name, player_data, position)
        return None, None

    for pos in all_positions:
        if team1_positions[pos] == 0:
            index, player = find_player_for_position(team1, pos)
            if player:
                team1[index] = player
                team1_positions[player[2]] += 1
                team1_positions[pos] -= 1

        if team2_positions[pos] == 0:
            index, player = find_player_for_position(team2, pos)
            if player:
                team2[index] = player
                team2_positions[player[2]] += 1
                team2_positions[pos] -= 1

    return team1, team1_positions, team2, team2_positions


def adjust_positions_within_team(team, team_positions):
    all_positions = ["上单", "中单", "打野", "射手", "辅助"]

    def find_player_for_position(team, position):
        for i, (player_name, player_data, lane) in enumerate(team):
            if position in player_data["lane"] and lane != position:
                return i, (player_name, player_data, position)
        return None, None

    for pos in all_positions:
        if team_positions[pos] == 0:
            index, player = find_player_for_position(team, pos)
            if player:
                current_position = player[2]
                team[index] = player
                team_positions[current_position] -= 1
                team_positions[pos] += 1

    return team, team_positions


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

    # 将玩家按照其位置多样性升序，保证只玩一个位置的玩家可以优先被考虑
    sorted_players_by_pos = sort_team(players_list)

    single_pos_players = [player for player in sorted_players_by_pos if len(player[1]["lane"]) == 1]
    multi_pos_players = [player for player in sorted_players_by_pos if len(player[1]["lane"]) > 1]

    for player_name, player_data in single_pos_players:
        lane = player_data["lane"][0]
        weight = weighted_win_rate(player_data)
        if team1_positions[lane] < 1:
            team1_weight = team_addition(team1, team1_weight, team1_positions, weight, lane, player_name, player_data)
            team1_players.append(player_name)
            print(player_name, lane, weight, "team1-单位置")
        elif team2_positions[lane] < 1:
            team2_weight = team_addition(team2, team2_weight, team2_positions, weight, lane, player_name, player_data)
            team2_players.append(player_name)
            print(player_name, lane, weight, "team2-单位置")

    # 争取有5个位置的选手
    def assign_unique_position_players():
        nonlocal team1_weight, team2_weight
        assigned = False
        for lane in ["上单", "中单", "打野", "射手", "辅助"]:
            if team1_positions[lane] == 0 or team2_positions[lane] == 0:
                for player_name, player_data in multi_pos_players:
                    if lane in player_data["lane"]:
                        weight = weighted_win_rate(player_data)
                        if team1_positions[lane] == 0:
                            team1_weight = team_addition(team1, team1_weight, team1_positions, weight, lane,
                                                         player_name, player_data)
                            team1_players.append(player_name)
                            print(player_name, lane, weight, "team1-唯二位置")
                            multi_pos_players.remove((player_name, player_data))
                            assigned = True
                            break
                        elif team2_positions[lane] == 0:
                            team2_weight = team_addition(team2, team2_weight, team2_positions, weight, lane,
                                                         player_name, player_data)
                            team2_players.append(player_name)
                            print(player_name, lane, weight, "team2-唯二位置")
                            multi_pos_players.remove((player_name, player_data))
                            assigned = True
                            break
            if assigned:
                break
        return assigned

    while assign_unique_position_players():
        pass

    for player_name, player_data in multi_pos_players:
        weight = weighted_win_rate(player_data)
        preferred_lanes = player_data["lane"]
        assigned = False
        for lane in preferred_lanes:
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

    team1, team1_positions, team2, team2_positions = adjust_positions(team1, team1_positions, team2, team2_positions)

    # 队伍内部位置调整
    team1, team1_positions = adjust_positions_within_team(team1, team1_positions)
    team2, team2_positions = adjust_positions_within_team(team2, team2_positions)

    # 检查交换同位置玩家是否会有更合适的胜率
    for _ in range(20):  # Try up to 10 times to improve balance
        team1, team2, improved, team1_weight, team2_weight = swap_players_if_better(team1, team2, team1_weight,
                                                                                    team2_weight)
        if not improved:
            break

    # 队伍内部位置调整
    team1, team1_positions = adjust_positions_within_team(team1, team1_positions)
    team2, team2_positions = adjust_positions_within_team(team2, team2_positions)

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


def load_players_data(filename="october.json"):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            players = json.load(file)
        return players
    except FileNotFoundError:
        print("File not found.")
        return None


def save_players_data(players, filename="october.json"):
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
