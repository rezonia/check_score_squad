import argparse
from tqdm import trange
import requests
import traceback
import os
import sys
import csv
import pandas as pd
from time import sleep, time
from datetime import datetime
import pytz

CURSOR_UP_ONE = '\x1b[1A' 
ERASE_LINE = '\x1b[2K' 


# URLs to make api calls
BASE_URL = "https://metamon-api.radiocaca.com/usm-api"
TOKEN_URL = f"{BASE_URL}/login"

# Kingdom stuffs
TEAM_LIST_URL = f"{BASE_URL}/kingdom/teamList"

ss = requests.Session()
    
def datetime_now():
    return datetime.now(pytz.timezone("Asia/Saigon")).strftime("%m/%d/%Y %H:%M:%S")

def delete_last_lines(n=1):
    for _ in range(n):
        sys.stdout.write(CURSOR_UP_ONE)
        sys.stdout.write(ERASE_LINE)

def post_formdata(payload, url="", headers=None, hasDelay=True):
    """Method to send request to game"""
    files = []
    if headers is None:
        headers = {}

    # Add delay to avoid error from too many requests per second
    if hasDelay == True:
        sleep(0.1)

    for _ in range(5):
        try:
            response = requests.request("POST",
                                        url,
                                        headers=headers,
                                        data=payload,
                                        files=files)
            return response.json()
        except:
            continue
    return {}

class MetamonPlayer:

    def __init__(self,
                 address,
                 sign,
                 msg="LogIn"):
        self.token = None
        self.address = address
        self.sign = sign
        self.msg = msg

    def init_token(self):
        """Obtain token for game session to perform battles and other actions"""
        payload = {"address": self.address, "sign": self.sign, "msg": self.msg, "network": "1", "clientType": "MetaMask"}
        
        for _ in range(15):
            response = post_formdata(payload, TOKEN_URL)
            new_token = response.get("data")['accessToken']
            if new_token != None:
                self.token = new_token
                break
            else:
                sleep(1)

    def check_team_list(self):
        self.init_token()
        #self.token = "rTZB1OjCMe6EpynrPmvmFA=="

        headers = {
            "accessToken": self.token,
        }
        payload = {
            "address": self.address,
            "teamId": -1,
            "pageSize": 20,
        }
        
        teamList_req = requests.Request('POST', TEAM_LIST_URL, data=payload, headers=headers, files=[])
        teamList_prepped = ss.prepare_request(teamList_req)
        delay = 20.0
        
        while True:
            try:
                start = time()
                result = ss.send(teamList_prepped)
                if result.status_code == 403:
                    print(f"{datetime_now()}||{result.status_code}: {result.reason}")
                    sleep(160)
                    self.init_token()
                    print(f"{datetime_now()}||Resuming...Generated new token: {self.token}")
                    continue
                team_list = result.json()
            except:
                traceback.print_exc()
                continue
                
            errorCode = team_list.get("code")
            if errorCode == "SUCCESS":
                all_teams = team_list.get("data", {}).get("list")
                
                for team in all_teams:
                    id = team.get("id")
                    name = team.get("name")
                    monsterNum = team.get("monsterNum")
                    totalSca = team.get("totalSca")
                    if totalSca == None:
                        totalSca = 0
                    else:
                        totalSca = int(totalSca)
                    if totalSca > 0 and monsterNum > 100:
                        avg = int(totalSca / monsterNum)
                        #sys.stdout.write(ERASE_LINE)
                        print(f"=={name}==[ID:{id}]")
                        print(f"{monsterNum} / 1000\t\t{totalSca}\t\tAVG:{avg}")
                        print(f"========")
                print("===========CheckTool-RezRaca==============")
                sleep(delay)
            elif errorCode == "REPEAT_FAIL":
                sleep(delay)
                continue
            else:
                print(f"Network error. Code: {errorCode}")
                break
        
        

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("-i", "--input-tsv", help="Path to tsv file with wallets' "
                                                  "access records (name, address, sign, login message) "
                                                  "name is used for filename with table of results. "
                                                  "Results for each wallet are saved in separate files",
                        default="wallets.tsv", type=str)

    args = parser.parse_args()

    if not os.path.exists(args.input_tsv):
        print(f"Input file {args.input_tsv} does not exist")
        sys.exit(-1)

    # determine delimiter char from given input file
    with open(args.input_tsv) as csvfile:
        dialect = csv.Sniffer().sniff(csvfile.readline(), "\t ;,")
        delim = dialect.delimiter

    wallets = pd.read_csv(args.input_tsv, sep=delim)

    for i, r in wallets.iterrows():
        mtm = MetamonPlayer(address=r.address,
                            sign=r.sign,
                            msg=r.msg)
        
        mtm.check_team_list()