#coding=gbk

import dota2api
import threading
import pathlib
import pickle
import queue
import os
import json

heroes_info_file_name = "heroes_info"

leagues_info_file_name = "leagues_info"

legues_plain_info_file_name = "leagues_plain_info"

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
        msg = ""
        for league in leagues_info['leagues']:
            msg += league['name'] + "  " + str(league['leagueid']) + os.linesep
        file = open(legues_plain_info_file_name, mode='w')
        file.write(msg)
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
            while match_history['results_remaining'] is not 0:
                start_match_id = match_history['matches'][-1]['match_id']
                match_history = api.get_match_history(league_id = league_id, start_at_match_id=start_match_id-1)
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
                except json.JSONDecodeError as e:
                    print(e)
                except:
                    print("get " + str(match_id) + " failed")

            GetMatchDetail.matches_detail_lock.acquire()
            GetMatchDetail.count += 1
            print("current count:" + str(GetMatchDetail.count))
            self.matches_detail.append(match_detail)
            GetMatchDetail.matches_detail_lock.release()

def GetHeroesBannedInfoForLegue(league_name, **kargs):
    matches_detail = GetMatchesDetailFor(league_name)
    sub_matches_detail = []
    if 'cluster_name' in kargs:
        for match_detail in matches_detail:
            if match_detail['cluster_name'] == kargs['cluster_name']:
                sub_matches_detail.append(match_detail)
    else:
        sub_matches_detail = matches_detail

    heroes_banned = {}
    for match_detail in sub_matches_detail:
        for  ban_pick_info in match_detail['picks_bans']:
            if ban_pick_info['is_pick'] == False:
                if ban_pick_info['hero_id'] in heroes_banned:
                    heroes_banned[ban_pick_info['hero_id']] += 1
                else:
                    heroes_banned[ban_pick_info['hero_id']] = 1
    sorted_heroes_banned = sorted(heroes_banned.items(), key = lambda d:d[1], reverse = True)

    return sorted_heroes_banned

def GetHeroesStatisticsForLeague(league_name, **kargs):
    matches_detail = GetMatchesDetailFor(league_name)

    sub_matches_detail = []
    if 'cluster_name' in kargs:
        for match_detail in matches_detail:
            if match_detail['cluster_name'] == kargs['cluster_name']:
                sub_matches_detail.append(match_detail)
    else:
        sub_matches_detail = matches_detail

    hero_info_dict = {}
    hero_banned_info = {}
    hero_win_info = {}
    for match_detail in sub_matches_detail:
        for player_info in match_detail['players']:
            hero_id = player_info['hero_id']
            if hero_id == 0:
                continue

            if hero_id not in hero_info_dict:
                hero_info = {'name': player_info['hero_name'], 'total_count': 1, 'win_count': 0, 'total_kills': player_info['kills'],
                             'average_kills': 0, 'highest_kills': player_info['kills'], 'total_deaths': player_info['deaths'], 'average_deaths': 0, 
                             'highest_deaths': player_info['deaths'], 'total_assists': player_info['assists'], 'average_assists': 0, 
                             'highest_assists': player_info['assists'], 'total_gold_per_min': player_info['gold_per_min'], 
                             'average_gold_per_min': 0, 'highest_gold_per_min': player_info['gold_per_min'], 'total_xp_per_min': player_info['xp_per_min'], 
                             'average_xp_per_min': 0, 'highest_xp_per_min': player_info['xp_per_min'], 'total_hero_damage': player_info['hero_damage'], 
                             'average_hero_damage': 0, 'total_tower_damage': player_info['tower_damage'], 'average_tower_damage': 0, 
                             'total_hero_healing': player_info['hero_healing'], 'average_hero_healing': 0}
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
                if hero_info_dict[hero_id]['highest_kills'] < player_info['kills']:
                    hero_info_dict[hero_id]['highest_kills'] = player_info['kills']
                if hero_info_dict[hero_id]['highest_deaths'] < player_info['deaths']:
                    hero_info_dict[hero_id]['highest_deaths'] = player_info['deaths']
                if hero_info_dict[hero_id]['highest_assists'] < player_info['assists']:
                    hero_info_dict[hero_id]['highest_assists'] = player_info['assists']
                if hero_info_dict[hero_id]['highest_gold_per_min'] < player_info['gold_per_min']:
                    hero_info_dict[hero_id]['highest_gold_per_min'] = player_info['gold_per_min']
                if hero_info_dict[hero_id]['highest_xp_per_min'] < player_info['xp_per_min']:
                    hero_info_dict[hero_id]['highest_xp_per_min'] = player_info['xp_per_min']

        win_team = 0
        if not match_detail['radiant_win']:
            win_team = 1

        if 'picks_bans' not in match_detail:
            continue

        for ban_pick_info in match_detail['picks_bans']:
            if ban_pick_info['is_pick'] == False:
                if ban_pick_info['hero_id'] in hero_banned_info:
                    hero_banned_info[ban_pick_info['hero_id']] += 1
                else:
                    hero_banned_info[ban_pick_info['hero_id']] = 1
            else:
                if ban_pick_info['hero_id'] in hero_win_info:
                    if ban_pick_info['team'] is win_team:
                        hero_win_info[ban_pick_info['hero_id']] += 1
                else:
                    temp = {}
                    if ban_pick_info['team'] is win_team:
                        hero_win_info[ban_pick_info['hero_id']] = 1
                    else:
                        hero_win_info[ban_pick_info['hero_id']] = 0


    # Get the average statistics
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

        hero_info['win_count'] = hero_win_info[hero_id]
    
    return hero_info_dict
    

if __name__ == '__main__':

    GetLeaguesInfo()

    target_league_name = u"2016年国际邀请赛"


    #获取联赛的英雄统计数据
    heroes_statistics = GetHeroesStatisticsForLeague(target_league_name)

    #获取英雄选择的统计数据
    #heroes_pick_info = {hero_id : heroes_statistics[hero_id]['total_count'] for hero_id in heroes_statistics}
    
    #sorted_heroes_pick_info = sorted(heroes_pick_info.items(), key = lambda d:d[1], reverse = True)

    #for (hero_id, picked_count) in sorted_heroes_pick_info:
    #    msg = GetLocalizedNameFromId(hero_id) + " 选择次数： "  + str(picked_count)
    #    print(msg)



    #获取英雄被禁用次数排名
    #heroes_banned_info = GetHeroesBannedInfoForLegue(target_league_name, cluster_name = 'US West')
    #for (hero_id, banned_count) in heroes_banned_info:
    #    msg = GetLocalizedNameFromId(hero_id) + " 被禁用次数： "  + str(banned_count)
    #    print(msg)


    #获取英雄平均杀敌数的统计数据
    #heroes_kills_info = {hero_id : heroes_statistics[hero_id]['average_kills'] for hero_id in heroes_statistics}

    #sorted_heroes_kills_info = sorted(heroes_kills_info.items(), key = lambda d:d[1], reverse = True)

    #for (hero_id, kills) in sorted_heroes_kills_info:
    #    msg = GetLocalizedNameFromId(hero_id) + " 场均杀敌数：" + str(kills)
    #    print(msg)


    #获取英雄平均助攻的统计数据
    #heroes_assists_info = {hero_id : heroes_statistics[hero_id]['average_assists'] for hero_id in heroes_statistics}

    #sorted_heroes_assists_info = sorted(heroes_assists_info.items(), key = lambda d:d[1], reverse = True)

    #for (hero_id, assists) in sorted_heroes_assists_info:
    #    msg = GetLocalizedNameFromId(hero_id) + " 场均助攻数：" + str(assists)
    #    print(msg)


    #获取平均每分钟金钱统计数据
    #heroes_gold_info = {hero_id: heroes_statistics[hero_id]['average_gold_per_min'] for hero_id in heroes_statistics}

    #sorted_heroes_gold_info = sorted(heroes_gold_info.items(), key = lambda d:d[1], reverse = True)

    #for (hero_id, gold_per_min) in sorted_heroes_gold_info:
    #    msg = GetLocalizedNameFromId(hero_id) + " 场均金钱： " + str(gold_per_min)
    #    print(msg)


    #获取平均每分钟经验数据
    #heroes_xp_info = {hero_id: heroes_statistics[hero_id]['average_xp_per_min'] for hero_id in heroes_statistics}

    #sorted_heroes_xp_info = sorted(heroes_xp_info.items(), key = lambda d:d[1], reverse = True)

    #for (hero_id, xp_per_min) in sorted_heroes_xp_info:
    #    msg = GetLocalizedNameFromId(hero_id) + " 场均经验： " + str(xp_per_min)
    #    print(msg)



    #获取单场比赛平均每分钟最高金钱
    #heroes_highest_gold_info = {hero_id: heroes_statistics[hero_id]['highest_gold_per_min'] for hero_id in heroes_statistics}

    #sorted_heroes_highest_gold_info = sorted(heroes_highest_gold_info.items(), key = lambda d:d[1], reverse = True)

    #for (hero_id, highest_gold) in sorted_heroes_highest_gold_info:
    #    msg = GetLocalizedNameFromId(hero_id) + " 最高金钱： " + str(highest_gold)
    #    print(msg)



    #获取单场比赛平均每分钟最高经验
    #heroes_highest_xp_info = {hero_id: {'xp': heroes_statistics[hero_id]['highest_xp_per_min'], 'count': heroes_statistics[hero_id]['total_count']}
    #                          for hero_id in heroes_statistics}

    #sorted_heroes_highest_xp_info = sorted(heroes_highest_xp_info.items(), key = lambda d:d[1]['xp'], reverse = True)

    #for (hero_id, info_dict) in sorted_heroes_highest_xp_info:
    #    msg = GetLocalizedNameFromId(hero_id) + " 最高经验： " + str(info_dict['xp']) + "  上场次数： "  + str(info_dict['count'])
    #    print(msg)



    #获取胜率信息
    heroes_win_rate_info = {hero_id: {'win_rate': round(heroes_statistics[hero_id]['win_count']/heroes_statistics[hero_id]['total_count'], 2), 
                                      'total_count': heroes_statistics[hero_id]['total_count']} for hero_id in heroes_statistics}

    sorted_heroes_win_rate_info = sorted(heroes_win_rate_info.items(), key = lambda d:d[1]['win_rate'], reverse = True)

    for (hero_id, info_dict) in sorted_heroes_win_rate_info:
        msg = GetLocalizedNameFromId(hero_id) + " 胜率： " + str(info_dict['win_rate']) + "  上场次数： "  + str(info_dict['total_count'])
        print(msg)

