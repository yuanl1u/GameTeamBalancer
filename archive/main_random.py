import tkinter as tk
from tkinter import messagebox
from tkinter.ttk import Treeview, Scrollbar, Style
import json, random

# ---------- 基础工具 ----------
def weighted_win_rate(p):
    if p["games"] < 5 and p["win_rate"] > 60: return 60.0
    if p["games"] < 5 and p["win_rate"] < 40: return 40.0
    if p["games"] < 5:                         return 50.0
    return p["win_rate"]

# ---------- *新的* 随机分配 5‑lane（避开首选） ----------
LANES = ["上单", "打野", "中单", "射手", "辅助"]

def random_lanes_avoid_primary(team):
    """
    team: [(name, data)] 5 人
    返回 [(name, data, lane)]，优先做到：
      1) lane 不在 data["lane"] （完全避开所有偏好）
      2) 若 1) 不可行，则保证 lane != data["lane"][0]（避开首选即可）
      3) 若再不行，接受冲突
    """
    lanes = LANES[:]                      # ["上单", "打野", "中单", "射手", "辅助"]

    # --- 尝试完全避开所有偏好 ---
    for _ in range(200):
        random.shuffle(lanes)
        if all(lanes[i] not in t[1]["lane"] for i, t in enumerate(team)):
            return [(n, d, lanes[i]) for i, (n, d) in enumerate(team)]

    # --- 尝试至少避开首选 ---
    for _ in range(200):
        random.shuffle(lanes)
        if all(lanes[i] != t[1]["lane"][0] for i, t in enumerate(team)):
            return [(n, d, lanes[i]) for i, (n, d) in enumerate(team)]

    # --- 仍无法满足，接受冲突 ---
    random.shuffle(lanes)
    return [(n, d, lanes[i]) for i, (n, d) in enumerate(team)]


# ---------- 分队（只看平均胜率） ----------
def create_balanced_teams(selected):
    players = sorted(selected.items(), key=lambda x: -weighted_win_rate(x[1]))
    team1, team2 = [], []
    w1 = w2 = 0
    for n, d in players:
        wr = weighted_win_rate(d)
        if len(team1) < 5 and (w1 <= w2 or len(team2) == 5):
            team1.append((n, d)); w1 += wr
        else:
            team2.append((n, d)); w2 += wr
        if len(team1) == len(team2) == 5: break
    team1 = random_lanes_avoid_primary(team1)
    team2 = random_lanes_avoid_primary(team2)
    print("平均胜率: Team1", round(w1/5,2), "| Team2", round(w2/5,2))
    return team1, team2

# ---------- 数据 IO ----------
def load_players_data(file="S3_stats.json"):
    try:
        with open(file, "r", encoding="utf-8") as f: return json.load(f)
    except FileNotFoundError: return {}

def save_players_data(players, file="S3_stats.json"):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(players, f, ensure_ascii=False, indent=4)

def update_player_stats(players, name, win):
    d = players[name]; d["games"] += 1
    if win: d["win"] += 1
    else:   d["loss"] += 1
    d["win_rate"] = round(d["win"]/d["games"]*100, 2)

# ---------- GUI ----------
class TeamBalancerApp:
    def __init__(self, root, players):
        self.root, self.players = root, players
        Style().configure("Treeview", rowheight=28, font=("Arial",11))
        Style().configure("Treeview.Heading", font=("Arial",12,"bold"))
        tk.Label(root,text="请选择 10 名玩家").pack()

        self.tree = Treeview(root, columns=("Name","WR","Games"), show="headings", height=18)
        for c,w in zip(("Name","WR","Games"),(100,90,80)):
            self.tree.heading(c,text=c,anchor="center")
            self.tree.column(c,width=w,anchor="center")
        self.tree["selectmode"]="extended"
        self.populate_tree()

        Scrollbar(root,command=self.tree.yview).pack(side=tk.RIGHT,fill=tk.Y)
        self.tree.configure(yscrollcommand=lambda f,s: None)
        self.tree.pack(side=tk.LEFT,fill=tk.BOTH,expand=True)
        self.tree.bind("<Button-1>", self.toggle_sel)

        frame = tk.Frame(root); frame.pack(pady=8)
        tk.Button(frame,text="Win",command=lambda:self.update_wl(True)).pack(side=tk.LEFT,padx=5)
        tk.Button(frame,text="Loss",command=lambda:self.update_wl(False)).pack(side=tk.LEFT,padx=5)
        tk.Button(frame,text="平衡分队",command=self.balance).pack(side=tk.LEFT,padx=5)

        self.lb1, self.lb2 = tk.Listbox(root,width=27,height=8), tk.Listbox(root,width=27,height=8)
        tk.Label(root,text="Team 1").pack(); self.lb1.pack()
        tk.Label(root,text="Team 2").pack(); self.lb2.pack()

    def populate_tree(self):
        for n,d in sorted(self.players.items(), key=lambda x:-x[1]['win_rate']):
            self.tree.insert("",tk.END, values=(n,f'{d["win_rate"]}%',d["games"]))

    def toggle_sel(self,event):
        if self.tree.identify("region",event.x,event.y)=="cell":
            iid=self.tree.identify_row(event.y)
            if self.tree.selection_includes(iid): self.tree.selection_remove(iid)
            else: self.tree.selection_add(iid)

    def update_wl(self,win):
        for iid in self.tree.selection():
            n=self.tree.item(iid,"values")[0]; update_player_stats(self.players,n,win)
        save_players_data(self.players); self.refresh_tree()

    def refresh_tree(self):
        for iid in self.tree.get_children():
            n=self.tree.item(iid,"values")[0]; d=self.players[n]
            self.tree.item(iid, values=(n,f'{d["win_rate"]}%',d["games"]))

    def balance(self):
        sel=self.tree.selection()
        if len(sel)!=10:
            messagebox.showerror("错误","必须选 10 名玩家")
            return
        selected={self.tree.item(i,"values")[0]:self.players[self.tree.item(i,"values")[0]] for i in sel}
        t1,t2=create_balanced_teams(selected)
        self.show_teams(t1,t2)

    def show_teams(self,t1,t2):
        self.lb1.delete(0,tk.END); self.lb2.delete(0,tk.END)
        order=dict(zip(LANES,range(5)))
        for n,d,l in sorted(t1,key=lambda x:order[x[2]]):
            self.lb1.insert(tk.END,f"{l}: {n} - {d['win_rate']}% ({d['games']} 场)")
        for n,d,l in sorted(t2,key=lambda x:order[x[2]]):
            self.lb2.insert(tk.END,f"{l}: {n} - {d['win_rate']}% ({d['games']} 场)")

# ---------- main ----------
if __name__ == "__main__":
    players = load_players_data()
    root = tk.Tk(); root.title("Team Balancer")
    TeamBalancerApp(root, players); root.mainloop()
