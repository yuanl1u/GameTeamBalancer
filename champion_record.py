import sys
import os

champion_set = {"黑暗之女", "狂战士", "正义巨像", "卡牌大师", "德邦总管", "无畏战车", "诡术妖姬", "猩红收割者", "远古恐惧", "正义天使", "无极剑圣", "牛头酋长", "符文法师",
                "亡灵战神", "战争女神", "众星之子", "迅捷斥候", "麦林炮手", "祖安怒兽", "雪原双子", "赏金猎人", "寒冰射手", "蛮族之王", "武器大师", "堕落天使", "时光守护者",
                "炼金术士", "痛苦之拥", "瘟疫之源", "死亡颂唱者", "虚空恐惧", "殇之木乃伊", "披甲龙龟", "冰晶凤凰", "恶魔小丑", "祖安狂人", "琴瑟仙女", "虚空行者", "刀锋舞者",
                "风暴之怒", "海洋之灾", "英勇投弹手", "天启者", "瓦罗兰之盾", "邪恶小法师", "巨魔之王", "诺克萨斯统领", "皮城女警", "蒸汽机器人", "熔岩巨兽", "不祥之刃", "永恒梦魇",
                "扭曲树精", "荒漠屠夫", "德玛西亚皇子", "蜘蛛女皇", "发条魔灵", "齐天大圣", "复仇焰魂", "盲僧", "暗夜猎手", "机械公敌", "魔蛇之拥", "上古领主", "大发明家",
                "沙漠死神", "狂野女猎手", "兽灵行者", "圣锤之毅", "酒桶", "不屈之枪", "探险家", "铁铠冥魂", "牧魂人", "离群之刺", "狂暴之心", "德玛西亚之力", "曙光女神",
                "虚空先知", "刀锋之影", "放逐之刃", "深渊巨口", "暮光之眼", "光辉女郎", "远古巫灵", "龙血武姬", "九尾妖狐", "法外狂徒", "潮汐海灵", "不灭狂雷", "傲之追猎者",
                "惩戒之箭", "深海泰坦", "机械先驱", "北地之怒", "无双剑姬", "爆破鬼才", "仙灵女巫", "荣耀行刑官", "战争之影", "虚空掠夺者", "诺克萨斯之手", "未来守护者", "冰霜女巫",
                "皎月女神", "德玛西亚之翼", "暗黑元首", "铸星龙王", "影流之镰", "暮光星灵", "荆棘之兴", "虚空之女", "星籁歌姬", "迷失之牙", "生化魔人", "疾风剑豪", "虚空之眼",
                "岩雀", "青钢影", "影哨", "虚空女皇", "弗雷尔卓德之心", "戏命师", "永猎双子", "祖安花火", "暴走萝莉", "河流之王", "狂厄蔷薇", "破败之王", "涤魂圣枪",
                "圣枪游侠", "影流之主", "暴怒骑士", "时间刺客", "元素女皇", "皮城执法官", "暗裔剑魔", "唤潮鲛姬", "沙漠皇帝", "魔法猫咪", "沙漠玫瑰", "魂锁典狱长", "海兽祭司",
                "虚空遁地兽", "翠神", "复仇之矛", "星界游神", "幻翎", "逆羽", "山隐之焰", "解脱者", "万花通灵", "残月之肃", "熔铁少女", "血港鬼影", "愁云使者",
                "封魔剑魂", "腕豪", "含羞蓓蕾", "灵罗娃娃", "炼金男爵", "双界灵兔", "不羁之悦", "纳祖芒荣耀", "炽焰雏龙", "明烛", "异画师", "百裂冥犬"}

today_champs_path = "today_champs.txt"
used_champions_path = "used_champions.txt"
usable_champs_path = "usable_champs.txt"

champion_used = set()
champ_last = set()

# 录入本周已用英雄并计算本周可用英雄
with (open(used_champions_path, 'r', encoding='utf-8') as f1):
    lines = f1.readlines()
    for line in lines:
        line_list = line.split()
        for champ in line_list:
            champion_used.add(champ)
    champ_last = champion_set - champion_used

print("选择功能：1 or 2")
print("1. 赛前查看可用英雄")
print("2. 赛后录入本日使用的英雄")
choice = input("你的选择：")

if choice == "1":
    with open(usable_champs_path, 'w', encoding='utf-8') as f2:
        count = 0
        for item in champ_last:
            f2.write(str(item) + ' ')
            count += 1
            if count >= 10:
                f2.write("\n")
                count = 0

elif choice == "2":
    if os.path.exists(usable_champs_path):
        os.remove(usable_champs_path)
    today_champs = set()
    valid_to_record = True
    with (open(today_champs_path, 'r', encoding='utf-8') as f3):
        lines = f3.readlines()
        for line in lines:
            champ_list = line.replace(",", "").replace(":", "").split()[1:]
            for champ in champ_list:
                if champ not in champion_set:
                    print(champ, " not in database.")
                    valid_to_record = False
                    break
                elif champ in champion_used:
                    print(champ, " is used this week.")
                    valid_to_record = False
                    break
                else:
                    today_champs.add(champ)
            if not valid_to_record:
                break
    if not valid_to_record:
        sys.exit()
    with (open(used_champions_path, 'a', encoding='utf-8') as f4):
        for champ in today_champs:
            f4.write(champ + ' ')
        f4.write('\n')
else:
    print("？奶b 重选")
