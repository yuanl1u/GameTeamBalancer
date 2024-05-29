import tkinter as tk
from tkinter import messagebox
from tkinter.ttk import Treeview, Scrollbar, Style
import json
import math
import random

def create_balanced_teams(selected_players):
    # 计算加权胜率，并减少游戏数的影响
    def weighted_win_rate(player):
        return player["win_rate"] * math.log(player["games"] + 1)  # 使用对数减少游戏数的影响

    # 按加权胜率对玩家进行排序
    players_list = list(selected_players.items())
    random.shuffle(players_list)  # 每次随机排列顺序
    sorted_players_by_pos = sorted(players_list, key = lambda item: len(item[1]["lane"]), reverse=False)

    # 初始化队伍和权重
    team1 = []
    team2 = []
    team1_weight = 0
    team2_weight = 0

    # 初始化每个队伍的位置计数器
    team1_positions = {"上单": 0, "中单": 0, "打野": 0, "射手": 0, "辅助": 0}
    team2_positions = {"上单": 0, "中单": 0, "打野": 0, "射手": 0, "辅助": 0}

    team1_players = set()
    team2_players = set()
    team1_wr = dict()
    team2_wr = dict()
    # 将玩家分配到队伍中，同时考虑其首选位置并平衡位置
    for player_name, player_data in sorted_players_by_pos:
        weight = weighted_win_rate(player_data)
        preferred_lanes = player_data["lane"]
        assigned = False
        for lane in preferred_lanes:
            # 检查两支队伍中是否已经有该位置
            if team1_positions[lane] < 1 and team2_positions[lane] < 1:
                if team1_weight <= team2_weight:
                    if weight > 55:
                        team1.append((player_name, player_data))
                        team1_weight += weight
                        team1_positions[lane] += 1
                        team1_players.add(player_name)
                        team1_wr[player_name] = player_data["win_rate"]
                    else:
                        team2.append((player_name, player_data))
                        team2_weight += weight
                        team2_positions[lane] += 1
                        team2_players.add(player_name)
                        team2_wr[player_name] = player_data["win_rate"]
                else:
                    if weight > 55:
                        team2.append((player_name, player_data))
                        team2_weight += weight
                        team2_positions[lane] += 1
                        team2_players.add(player_name)
                        team2_wr[player_name] = player_data["win_rate"]
                    else:
                        team1.append((player_name, player_data))
                        team1_weight += weight
                        team1_positions[lane] += 1
                        team1_players.add(player_name)
                        team1_wr[player_name] = player_data["win_rate"]
                assigned = True
                break
        # 如果无法按照首选位置分配，则根据先前的逻辑进行分配
        if not assigned:
            if team1_weight <= team2_weight:
                if weight > 55:
                    team1.append((player_name, player_data))
                    team1_weight += weight
                    team1_positions[lane] += 1
                    team1_players.add(player_name)
                    team1_wr[player_name] = player_data["win_rate"]
                else:
                    team2.append((player_name, player_data))
                    team2_weight += weight
                    team2_positions[lane] += 1
                    team2_players.add(player_name)
                    team2_wr[player_name] = player_data["win_rate"]
            else:
                if weight > 55:
                    team2.append((player_name, player_data))
                    team2_weight += weight
                    team2_positions[lane] += 1
                    team2_players.add(player_name)
                    team2_wr[player_name] = player_data["win_rate"]
                else:
                    team1.append((player_name, player_data))
                    team1_weight += weight
                    team1_positions[lane] += 1
                    team1_players.add(player_name)
                    team1_wr[player_name] = player_data["win_rate"]
    return team1, team2

def update_player_stats(players, player_name, is_winner):
    player_data = players[player_name]
    total_games = player_data["games"]
    win_rate = player_data["win_rate"]
    wins = round(win_rate * total_games / 100)

    total_games += 1
    if is_winner:
        wins += 1

    new_win_rate = (wins / total_games) * 100
    player_data["games"] = total_games
    player_data["win_rate"] = round(new_win_rate, 2)

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
        style.configure("Treeview", rowheight=30)  # Adjust row height
        style.configure("Treeview.Heading", font=('Arial', 12, 'bold'))
        style.configure("Treeview", font=('Arial', 11))

        self.title_label = tk.Label(root, text="请选择本次参与游戏的10人")
        self.title_label.pack()

        self.player_tree = Treeview(root, columns=("Name", "WinRate", "Games"), show='headings', height = 15)
        self.player_tree.heading("Name", text="名字", anchor='center')
        self.player_tree.heading("WinRate", text="胜率", anchor='center')
        self.player_tree.heading("Games", text="总游戏数", anchor='center')
        self.player_tree.column("Name", width=100, anchor='center')  # Set the width of the Name column
        self.player_tree.column("WinRate", width=100, anchor='center')  # Set the width of the WinRate column
        self.player_tree.column("Games", width=100, anchor='center')  # Set the width of the Games column
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
        self.team1_listbox = tk.Listbox(root, width=27, height=8)  # Set the width and height of the Listbox
        self.team2_listbox = tk.Listbox(root, width=27, height=8) 
        self.balance_button = tk.Button(root, text="平衡分队", command=self.balance_teams)
        self.balance_button.pack()

        self.team1_label.pack()
        self.team1_listbox.pack()
        self.team2_label.pack()
        self.team2_listbox.pack()

    def populate_player_tree(self):
        for player_name, player_data in sorted(self.players.items(), key=lambda item: -item[1]['win_rate']):
            self.player_tree.insert("", tk.END, values=(player_name, f"{player_data['win_rate']}%", player_data["games"]))

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

        selected_players = {self.player_tree.item(i, 'values')[0]: self.players[self.player_tree.item(i, 'values')[0]] for i in selected_items}
        team1, team2 = create_balanced_teams(selected_players)

        self.team1_listbox.delete(0, tk.END)
        self.team2_listbox.delete(0, tk.END)

        for player_name, player_data in team1:
            self.team1_listbox.insert(tk.END, f"{player_name}: {player_data['win_rate']}% ({player_data['games']} games)")

        for player_name, player_data in team2:
            self.team2_listbox.insert(tk.END, f"{player_name}: {player_data['win_rate']}% ({player_data['games']} games)")

if __name__ == "__main__":
    players = load_players_data() or {}
    root = tk.Tk()
    root.title("Team Balancer")
    app = TeamBalancerApp(root, players)
    root.mainloop()
