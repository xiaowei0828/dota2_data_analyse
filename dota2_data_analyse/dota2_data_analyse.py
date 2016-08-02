#coding=gbk

import dota2api
import threading
import copy


target_league_name = u"2016年马尼拉特级锦标赛"
target_league_id = -1
matches_id = []
matches_detail = []

lock = threading.RLock()
count = 0

heroes = {}

def GetHeroNameFromId(id):
    global heroes
    if len(heroes) == 0:
        heroes = api.get_heroes()
    heroes_info = heroes['heroes']
    for heroinfo in heroes_info:
        if heroinfo['id'] == id:
            return heroinfo['localized_name']
    no_name = "Can't find name for:" + str(id)
    return no_name

class GetMatchDetail(threading.Thread):
    def __init__(self, sub_matches_id):
        threading.Thread.__init__(self)
        self.sub_matches_id = sub_matches_id

    def run(self):
        global matches_detail
        global count
        for match_id in self.sub_matches_id:
            succeed = 0
            match_detail = {}
            while succeed == 0:
                try:
                    match_detail = api.get_match_details(match_id)
                    print("get " + str(match_id) + " succeed")
                    succeed = 1
                except:
                    print("get " + str(match_id) + " failed")
            lock.acquire()
            count += 1
            print("total count:" + str(count))
            matches_detail.append(match_detail)
            lock.release()


api = dota2api.Initialise(api_key = "4F2D3BB4373BAF59B8317005373E4954", language = "zh-cn")

leagues = api.get_league_listing()
for league in leagues['leagues']:
    if league['name'] == target_league_name:
        target_league_id = league['leagueid']
        break

if target_league_id != -1:
    match_history = api.get_match_history(league_id = target_league_id)
    for match in match_history['matches']:
        matches_id.append(match['match_id'])

if matches_id.count != 0:
    sub_matches_id = []
    thread_pool = []
    count = 0
    for match_id in matches_id:
        sub_matches_id.append(match_id);
        if count == 10:                
           thread = GetMatchDetail(copy.deepcopy(sub_matches_id))
           thread.start()
           thread_pool.append(thread)
           sub_matches_id.clear()

    if len(sub_matches_id) != 0:
        thread = GetMatchDetail(copy.deepcopy(sub_matches_id))
        thread.start()
        thread_pool.append(thread)

    for thread in thread_pool:
        thread.join()

    heroes_banned = {}
    for match_detail in matches_detail:
       for  ban_pick_info in match_detail['picks_bans']:
           if ban_pick_info['is_pick'] == False:
               if ban_pick_info['hero_id'] in heroes_banned:
                   heroes_banned[ban_pick_info['hero_id']] += 1
               else:
                   heroes_banned[ban_pick_info['hero_id']] = 1
    sorted_heroes_banned = sorted(heroes_banned.items(), key = lambda d:d[1], reverse = True)

    for (hero_id,banned_count) in sorted_heroes_banned:
        print(GetHeroNameFromId(hero_id) + "  禁用次数: " + str(banned_count))

print("hello world")