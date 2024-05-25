import tkinter as tk
from tkinter import messagebox, Menu, Toplevel
from tkinter.ttk import Treeview, Scrollbar
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
    sorted_players = sorted(players_list, key=lambda item: weighted_win_rate(item[1]), reverse=True)

    # 初始化队伍和权重
    team1 = []
    team2 = []
    team1_weight = 0
    team2_weight = 0

    # 初始化每个队伍的位置计数器
    team1_positions = {"上单": 0, "中单": 0, "打野": 0, "射手": 0, "辅助": 0}
    team2_positions = {"上单": 0, "中单": 0, "打野": 0, "射手": 0, "辅助": 0}

    # 将玩家分配到队伍中，同时考虑其首选位置并平衡位置
    for player_name, player_data in sorted_players:
        weight = weighted_win_rate(player_data)
        preferred_lanes = player_data["lane"]
        assigned = False
        for lane in preferred_lanes:
            # 检查两支队伍中是否已经有该位置
            if team1_positions[lane] < 1 and team2_positions[lane] < 1:
                if team1_weight <= team2_weight:
                    team1.append((player_name, player_data))
                    team1_weight += weight
                    team1_positions[lane] += 1
                    assigned = True
                else:
                    team2.append((player_name, player_data))
                    team2_weight += weight
                    team2_positions[lane] += 1
                    assigned = True
                break
        # 如果无法按照首选位置分配，则根据先前的逻辑进行分配
        if not assigned:
            if team1_weight <= team2_weight:
                team1.append((player_name, player_data))
                team1_weight += weight
            else:
                team2.append((player_name, player_data))
                team2_weight += weight

    return team1, team2


def update_player_stats(players, team, is_winner):
    for player_name, player_data in team:
        total_games = players[player_name]["games"]
        win_rate = players[player_name]["win_rate"]
        wins = round(win_rate * total_games / 100)

        total_games += 1
        if is_winner:
            wins += 1

        new_win_rate = (wins / total_games) * 100
        players[player_name]["games"] = total_games
        players[player_name]["win_rate"] = new_win_rate


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
        self.selected_players = []
        self.team1 = []
        self.team2 = []

        self.title_label = tk.Label(root, text="请选择本次参与游戏的10人")
        self.title_label.pack()

        self.players_listbox = tk.Listbox(root, selectmode=tk.MULTIPLE)
        for player in players:
            self.players_listbox.insert(tk.END, player)
        self.players_listbox.pack()

        self.team1_label = tk.Label(root, text="Team 1")
        self.team2_label = tk.Label(root, text="Team 2")
        self.team1_listbox = tk.Listbox(root)
        self.team2_listbox = tk.Listbox(root)
        self.balance_button = tk.Button(root, text="Balance Teams", command=self.balance_teams)
        self.winner_button = tk.Button(root, text="选择获胜队伍", command=self.select_winner)

        self.team1_label.pack()
        self.team1_listbox.pack()
        self.team2_label.pack()
        self.team2_listbox.pack()
        self.balance_button.pack()
        self.winner_button.pack()

        self.create_menu()

    def create_menu(self):
        menubar = Menu(self.root)
        self.root.config(menu=menubar)

        # 创建文件菜单
        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="菜单", menu=file_menu)
        file_menu.add_command(label="查看胜率天梯", command=self.show_ladder)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)

    def show_ladder(self):
        ladder_window = Toplevel(self.root)
        ladder_window.title("胜率天梯")

        tree = Treeview(ladder_window, columns=("name", "win_rate", "games", "lane"), show='headings')
        tree.heading("name", text="名字")
        tree.heading("win_rate", text="胜率")
        tree.heading("games", text="总游戏数")
        tree.heading("lane", text="位置")

        scrollbar = Scrollbar(ladder_window, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 插入JSON数据到表格
        for player_name, player_data in self.players.items():
            lanes = ', '.join(player_data["lane"])
            tree.insert("", tk.END, values=(player_name, player_data["win_rate"], player_data["games"], lanes))

    def balance_teams(self):
        selected_indices = self.players_listbox.curselection()
        if len(selected_indices) != 10:
            messagebox.showerror("错误", "请选择10名玩家进行游戏")
            return

        self.selected_players = []
        incomplete_players = []
        for i in selected_indices:
            player_name = self.players_listbox.get(i)
            if player_name in self.players and "lane" in self.players[player_name]:
                self.selected_players.append(player_name)
            else:
                incomplete_players.append(player_name)

        if incomplete_players:
            messagebox.showerror("错误", f"以下玩家数据不完整: {', '.join(incomplete_players)}")
            return

        selected_players_data = {player: self.players[player] for player in self.selected_players}
        self.team1, self.team2 = create_balanced_teams(selected_players_data)

        self.team1_listbox.delete(0, tk.END)
        self.team2_listbox.delete(0, tk.END)

        for player_name, player_data in self.team1:
            self.team1_listbox.insert(tk.END,
                                      f"{player_name}: {player_data['win_rate']}% ({player_data['games']} games)")

        for player_name, player_data in self.team2:
            self.team2_listbox.insert(tk.END,
                                      f"{player_name}: {player_data['win_rate']}% ({player_data['games']} games)")
        # 强制刷新Tkinter窗口
        self.root.update()

    def select_winner(self):
        if not self.team1 or not self.team2:
            messagebox.showerror("错误", "请先生成队伍")
            return

        winner = messagebox.askquestion("选择获胜队伍", "Team 1 获胜吗？ (是/否)")
        if winner == 'yes':
            update_player_stats(self.players, self.team1, True)
            update_player_stats(self.players, self.team2, False)
        else:
            update_player_stats(self.players, self.team1, False)
            update_player_stats(self.players, self.team2, True)

        messagebox.showinfo("更新成功", "玩家数据已更新")
        self.save_players_data()

    def save_players_data(self):
        save_players_data(self.players)


if __name__ == "__main__":
    # Load player data from file if it exists
    loaded_players = load_players_data()
    if loaded_players:
        players = loaded_players

    root = tk.Tk()
    root.title("Team Balancer")
    app = TeamBalancerApp(root, players)
    root.mainloop()
