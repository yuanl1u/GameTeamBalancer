import json
import sys

# 打开json文件
with open('players_data.json', 'r') as file:
    # 读取json数据
    data = json.load(file)  

winner_team = input("Please input winners (split by whitespace): ").split()
for winner in winner_team:
    if winner not in data:
        print("Unknown player: ", winner)
        sys.exit()
    data[winner]["win"] += 1
    data[winner]["games"] += 1
    data[winner]["win_rate"] = round(data[winner]["win"] * 100 / data[winner]["games"], 2)
lost_team = input("Please input losers (split by whitespace): ").split()
for loser in lost_team:
    if loser not in data:
        print("Unknown player: ", loser)
        sys.exit()
    data[loser]["games"] += 1
    data[loser]["win_rate"] = round(data[loser]["win"] * 100 / data[loser]["games"], 2)

with open('new_players_data.json', 'w') as out:
    json.dump(data, out, ensure_ascii=False, indent=4)