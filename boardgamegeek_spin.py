from bs4 import BeautifulSoup
import re
import time
from selenium import webdriver
import json
import os
import argparse
import sys
import copy
import pprint

parser = argparse.ArgumentParser()
parser.add_argument('-p','--players', nargs=1, type=int, metavar='NUMBER_OF_PLAYERS',
    help='Filter search by number of players')
#parser.add_argument('-a','--age', nargs=1, type=int, 
#    help='Filter search by age')
parser.add_argument('-u','--update', action='store_true', default=False,
    help='Update database if one exists, otherwise create one. This may take awhile depending on how many games. This requires the webdriver for chrome https://sites.google.com/a/chromium.org/chromedriver/downloads')
parser.add_argument('-c','--count', action='store_true', default=False,
    help='Return number of results')
parser.add_argument('-d','--driverpath', nargs=1, type=str, default='/home/metulburr/chromedriver',
    help='Chrome driver full path for update option. This is the path to webdriver.')
parser.add_argument('-w','--weight', nargs=2, type=float, metavar=('LOW', 'HIGH'),
    help='Filter search by weight range. Return results between LOW and HIGH.')
parser.add_argument('-s','--spin', action='store_true', default=False,
    help='Spin wheel, otherwise just print out results')
ARGS = vars(parser.parse_args())

DRIVER = ARGS['driverpath']
NO_DB_ERROR = 'Database not created. Create one with the -u argument. NOTICE: That may take awhile.'
FILENAME = 'games.json'
PP = pprint.PrettyPrinter(indent=0)

if not os.path.isfile(FILENAME):
    if not ARGS['update']:
        print(NO_DB_ERROR)
        sys.exit()

class Handler:
    def __init__(self):
        self.url = 'https://boardgamegeek.com/collection/user/robgraves?own=1&subtype=boardgame&ff=1'
        self.base_url = 'https://boardgamegeek.com'
        self.data = {}

        if ARGS['update']:
            self.browser = self.get_page(self.url)
            self.soup = self.filter_list(self.browser)
            self.populate_data()
            time.sleep(1)
            self.update_database()
        else:
            self.read_database()
        
        if ARGS['players']:
            cust_data = self.get_players()
            
        if ARGS['weight']:
            cust_data = self.get_weight()
        
        total = 'Total Results: {}'
        if ARGS['weight'] or ARGS['players']:
            PP.pprint(cust_data)
            print(total.format(len(cust_data.keys())))
        else:
            PP.pprint(self.data)
            print(total.format(len(self.data.keys())))
            
        self.delay()
        if ARGS['spin'] and (ARGS['weight'] or ARGS['players']):
            self.insert_wheel(cust_data)
            
    def get_age(self):
        datacopy = copy.deepcopy(self.data)
        for key in self.data:
            a = self.data[key]['age'][:-1]
            try:
                a = int(a)
            except TypeError:
                continue
            if a <= ARGS['age'][0]:
                datacopy.pop(key)
        return datacopy
        
    def get_weight(self):
        datacopy = copy.deepcopy(self.data)
        for key in self.data:
            w = float(self.data[key]['weight'])
            if ARGS['weight'][0] <= w <= ARGS['weight'][1]:
                pass 
            else:
                datacopy.pop(key)
        return datacopy
        
    def get_players(self):
        datacopy = copy.deepcopy(self.data)
        for key in self.data:
            if len(self.data[key]['players']) == 2:
                min_ = int(self.data[key]['players'][0])
                max_ = int(self.data[key]['players'][1])
                if min_ <= ARGS['players'][0] <= max_:
                    pass 
                else:
                    datacopy.pop(key)
            else:
                num = int(self.data[key]['players'][0])
                if not ARGS['players'][0] == num:
                    datacopy.pop(key)
        return datacopy
        
    def update_database(self):
        with open(FILENAME, 'w') as f:
            json.dump(self.data, f, indent=4)
    
    def read_database(self):
        with open(FILENAME, 'r') as f:
            data = f.read()
        self.data = json.loads(data)
        
    def get_page(self, url):
        browser = webdriver.Chrome(DRIVER)
        browser.set_window_position(0,0)
        browser.get(url)
        return browser
        
    def filter_list(self, browser):
        browser.find_element_by_xpath('//*[@id="collectionfilterform"]/table/tbody/tr[2]/td/span/a[1]').click()
        browser.find_element_by_xpath('//*[@id="filters"]/div[2]/table[1]/tbody/tr[2]/td[2]/select/option[2]').click()
        browser.find_element_by_xpath('//*[@id="filters"]/div[2]/input[1]').click()
        time.sleep(1)
        return BeautifulSoup(browser.page_source, "html.parser")

    def populate_data(self):
        table = self.soup.find('table', {'class':'collection_table'})
        trs = table.find_all('tr')
        trs = trs[1:] #remove header
        for tr in trs:
            div = tr.find('div', {'id':re.compile('results_objectname')}) #results_objectname{NUM}
            link = div.find('a')['href'] #partial link such as /boardgame/205322/oregon-trail-card-game
            link = self.base_url + link
            name = div.find('a').text #The Oregon Trail Card Game
            user_rating = tr.find_all('td')[2].text.strip().split('\n')[0]
            geek_rating = tr.find_all('td')[3].text.strip()
            self.browser.get(link)
            players, minutes, age, weight = self.crawl_link()
            
            #time.sleep(10000)
            self.data[name] = {
                'link'          :link, 
                'user_rating'   :user_rating, 
                'geek_rating'   :geek_rating,
                'players'       :players,
                'minutes'       :minutes,
                'age'           :age,
                'weight'        :weight,
            }

    def crawl_link(self):
        s = BeautifulSoup(self.browser.page_source, "html.parser")
        section = s.find('ul', {'class':'gameplay'})
        lis = section.find_all('li')
        players = lis[0].text.strip().split()[0].split('–')
        minutes = lis[1].text.strip().split()[0].split('–')
        age = lis[2].text.strip().split()[1]
        weight = lis[3].text.strip().split()[2]
        return players, minutes, age, weight
        
    def delay(self):
        time.sleep(.3)
            
    def insert_wheel(self, data):
        browser = self.get_page('http://wheeldecide.com/')
        self.delay()
        browser.find_element_by_xpath('//*[@id="content"]/form/div/div/div[2]/button').click()
        self.delay()
        browser.find_element_by_id("modalChoices").send_keys('\n'.join(data.keys()))
        self.delay()
        browser.find_element_by_xpath('//*[@id="replaceChoices"]').click()
        self.delay()
        browser.find_element_by_xpath('//*[@id="pasteModal"]/div/div/div[3]/button[1]').click()
        time.sleep(3)
        browser.find_element_by_xpath('//*[@id="content"]/form/div/div/div[2]/input[3]').click()
        #self.delay()
        time.sleep(1000000000) #wait for user to close browser
        
Handler()





