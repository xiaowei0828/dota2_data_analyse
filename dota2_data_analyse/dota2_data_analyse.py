#coding=gbk

import dota2api
import threading
import pathlib
import pickle
import queue
import os

heroes_info_file_name = "heroes_info"

leagues_info_file_name = "leagues_info"

api = dota2api.Initialise(api_key = "4F2D3BB4373BAF59B8317005373E4954", language = "zh-cn")

def GetHeroesInfo():
    path = pathlib.Path(heroes_info_file_name)
    if path.exists():
        heroes_info = pickle.load(path.open(mode='rb'))
        return heroes_info
    else:
        global api
        heroes_info = api.get_heroes()
        pickle.dump(heroes_info, path.open(mode='wb'))
        return heroes_info

def GetHeroNameFromId(id):
    heroes_info = GetHeroesInfo()
    for heroinfo in heroes_info['heroes']:
        if heroinfo['id'] == id:
            return heroinfo['name']
    return None

def GetLocalizedNameFromId(id):
    heroes_info = GetHeroesInfo()
    for heroinfo in heroes_info['heroes']:
        if heroinfo['id'] == id:
            return heroinfo['localized_name']
    return None

def GetLeaguesInfo():
    path = pathlib.Path(leagues_info_file_name)
    if path.exists():
        leagues_info = pickle.load(path.open(mode='rb'))
        return leagues_info
    else:
        global api
        leagues_info = api.get_league_listing()
        pickle.dump(leagues_info, path.open(mode='wb'))
        return leagues_info

def GetLeagueIdFromName(league_name):
    leagues_info = GetLeaguesInfo()
    target_league_id = -1
    for league in leagues_info['leagues']:
        if league['name'] == target_league_name:
            target_league_id = league['leagueid']
            break
    return target_league_id

def GetMatchesDetailFor(league_name):
    path = pathlib.Path(league_name)
    if path.exists():
        matches_detail = pickle.load(path.open(mode='rb'))
        return matches_detail
    else:
        league_id = GetLeagueIdFromName(league_name)
        if league_id != -1:
            matches_id = queue.Queue()
            match_history = api.get_match_history(league_id = league_id)
            for match in match_history['matches']:
                matches_id.put(match['match_id'])
            total_matches_count = matches_id.qsize()
            print('total matches count: ' + str(total_matches_count))
            thread_count = int(total_matches_count / 10)
            matches_detail = []
            thread_pool = [GetMatchDetail(matches_id, matches_detail) for i in range(thread_count) ]
            for thread in thread_pool:
                thread.start()
            for thread in thread_pool:
                thread.join()

            pickle.dump(matches_detail, path.open(mode='wb'))
            return matches_detail
        return None



class GetMatchDetail(threading.Thread):
    matches_detail_lock = threading.RLock()
    count = 0
    def __init__(self, matches_id, matches_detail):
        threading.Thread.__init__(self)
        self.matches_id = matches_id
        self.matches_detail = matches_detail

    def run(self):
        while True:
            match_id = 0
            if not self.matches_id.empty():
                match_id = self.matches_id.get();
            else:
                break

            succeed = 0
            match_detail = {}
            while not succeed:
                try:
                    match_detail = api.get_match_details(match_id)
                    print("get " + str(match_id) + " succeed")
                    succeed = 1
                except:
                    print("get " + str(match_id) + " failed")

            GetMatchDetail.matches_detail_lock.acquire()
            GetMatchDetail.count += 1
            print("current count:" + str(GetMatchDetail.count))
            self.matches_detail.append(match_detail)
            GetMatchDetail.matches_detail_lock.release()

def GetHeroesBannedInfo(league_name):
    matches_detail = GetMatchesDetailFor(league_name)
    heroes_banned = {}
    for match_detail in matches_detail:
        for  ban_pick_info in match_detail['picks_bans']:
            if ban_pick_info['is_pick'] == False:
                if ban_pick_info['hero_id'] in heroes_banned:
                    heroes_banned[ban_pick_info['hero_id']] += 1
                else:
                    heroes_banned[ban_pick_info['hero_id']] = 1
    sorted_heroes_banned = sorted(heroes_banned.items(), key = lambda d:d[1], reverse = True)

    path = pathlib.Path(league_name + "_heroes_banned_info")
    file = path.open('w')
    info = str()
    for (hero_id,banned_count) in sorted_heroes_banned:
        info += GetLocalizedNameFromId(hero_id) + "  禁用次数: " + str(banned_count) + os.linesep
    file.writelines(info)

def GetHeroesPickedInfo(league_name):
    matches_detail = GetMatchesDetailFor(league_name)
    heroes_picked = {}
    for match_detail in matches_detail:
        for  ban_pick_info in match_detail['picks_bans']:
            if ban_pick_info['is_pick'] == True:
                if ban_pick_info['hero_id'] in heroes_picked:
                    heroes_picked[ban_pick_info['hero_id']] += 1
                else:
                    heroes_picked[ban_pick_info['hero_id']] = 1
    sorted_heroes_picked = sorted(heroes_picked.items(), key = lambda d:d[1], reverse = True)

    path = pathlib.Path(league_name + "_heroes_picked_info")
    file = path.open('w')
    info = str()
    for (hero_id,picked_count) in sorted_heroes_picked:
        info += GetLocalizedNameFromId(hero_id) + "  选择次数: " + str(picked_count) + os.linesep
    file.writelines(info)

def GetHeroesStatisticsForLeague(league_name):
    matches_detail = GetMatchesDetailFor(league_name)
    hero_info_dict = {}

    for match_detail in matches_detail:
        for player_info in match_detail['players']:
            hero_id = player_info['hero_id']
            if hero_id == 0:
                continue

            if hero_id not in hero_info_dict:
                hero_info = {'name': player_info['hero_name'], 'total_count': 1, 'total_kills': player_info['kills'],
                             'average_kills': 0, 'total_deaths': player_info['deaths'], 'average_deaths': 0, 
                             'total_assists': player_info['assists'], 'average_assists': 0, 'total_gold_per_min': player_info['gold_per_min'], 
                             'average_gold_per_min': 0, 'total_xp_per_min': player_info['xp_per_min'], 'average_xp_per_min': 0,
                             'total_hero_damage': player_info['hero_damage'], 'average_hero_damage': 0, 'total_tower_damage': player_info['tower_damage'], 
                             'average_tower_damage': 0, 'total_hero_healing': player_info['hero_healing'], 'average_hero_healing': 0}
                hero_info_dict[hero_id] = hero_info
            else:
                hero_info_dict[hero_id]['total_count'] += 1;
                hero_info_dict[hero_id]['total_kills'] += player_info['kills']
                hero_info_dict[hero_id]['total_deaths'] += player_info['deaths']
                hero_info_dict[hero_id]['total_assists'] += player_info['assists']
                hero_info_dict[hero_id]['total_gold_per_min'] += player_info['gold_per_min']
                hero_info_dict[hero_id]['total_xp_per_min'] += player_info['xp_per_min']
                hero_info_dict[hero_id]['total_hero_damage'] += player_info['hero_damage']
                hero_info_dict[hero_id]['total_tower_damage'] += player_info['tower_damage']
                hero_info_dict[hero_id]['total_hero_healing'] += player_info['hero_healing']

    for hero_id in hero_info_dict:
        hero_info = hero_info_dict[hero_id]
        total_count = hero_info['total_count']
        hero_info['average_kills'] = int(hero_info['total_kills'] / total_count)
        hero_info['average_deaths'] = int(hero_info['total_deaths'] / total_count)
        hero_info['average_assists'] = int(hero_info['total_assists'] / total_count)
        hero_info['average_gold_per_min'] = int(hero_info['total_gold_per_min'] / total_count)
        hero_info['average_xp_per_min'] = int(hero_info['total_xp_per_min'] / total_count)
        hero_info['average_hero_damage'] = int(hero_info['total_hero_damage'] / total_count)
        hero_info['average_tower_damage'] = int(hero_info['total_tower_damage'] / total_count)
        hero_info['average_hero_healing'] = int(hero_info['total_hero_healing'] / total_count)

    return hero_info_dict
    

if __name__ == '__main__':

    target_league_name = u"2016年马尼拉特级锦标赛"

    # 英雄被ban排名
    #GetHeroesBannedInfo(target_league_name)
    #GetHeroesPickedInfo(target_league_name)

    #获取联赛的英雄统计数据
    heroes_statistics = GetHeroesStatisticsForLeague(target_league_name)

    #获取英雄选择的统计数据
    heroes_pick_info = {hero_id : heroes_statistics[hero_id]['total_count'] for hero_id in heroes_statistics}
    
    sorted_heroes_pick_info = sorted(heroes_pick_info.items(), key = lambda d:d[1], reverse = True)

    #获取英雄平均杀敌数的统计数据
    heroes_kills_info = {hero_id : heroes_statistics[hero_id]['average_kills'] for hero_id in heroes_statistics}

    sorted_heroes_kills_info = sorted(heroes_kills_info.items(), key = lambda d:d[1], reverse = True)

    #for (hero_id, kills) in sorted_heroes_kills_info:
    #    msg = GetLocalizedNameFromId(hero_id) + " 场均杀敌数：" + str(kills)
    #    print(msg)

    #获取英雄平均助攻的统计数据
    heroes_assists_info = {hero_id : heroes_statistics[hero_id]['average_assists'] for hero_id in heroes_statistics}

    sorted_heroes_assists_info = sorted(heroes_assists_info.items(), key = lambda d:d[1], reverse = True)

    for (hero_id, assists) in sorted_heroes_assists_info:
        msg = GetLocalizedNameFromId(hero_id) + " 场均助攻数：" + str(assists)
        print(msg)

    print("hello world")

