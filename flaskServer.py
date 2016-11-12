import sys
try:
    import flask
except ImportError:
    sys.path.append("lib")
    import flask

import os  
import pickle
import random
import json
import ast
import time
import filelock

app = flask.Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

dab = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "data/database.dab"))
lockFile = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "data/database.lock"))

class database:
    def __enter__(self):
        self.lock = filelock.FileLock(lockFile)
        self.lock.acquire(None, 0.05)
        self._checkFile()
        with open(dab, 'rb') as f:
            self.dab = pickle.load(f)
            self._checkStruct()
        return self.dab
    def __exit__(self, type, value, traceback):
        with open(dab, 'wb') as f:
            pickle.dump(self.dab, f)
        self.lock.release()
    
    def _checkStruct(self):
        if not "games" in self.dab:
            self.dab["games"] = {}
        if not "queue" in self.dab:
            self.dab["queue"] = {}
        if not "lastUNID" in self.dab:
            self.dab["lastUNID"] = 0
    
    def _checkFile(self):
        dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "data"))
        if not os.path.exists(dir):
            os.makedirs(dir)
        if not os.path.exists(dab):
            with open(dab, 'wb') as f:
                pass
        try:
            with open(dab, 'rb') as f: 
                pickle.load(f)
        except Exception as e:
            print("Error")
            print(e)
            f.close()
            with open(dab, 'wb') as f: 
                pickle.dump({}, f)

class User:
    def __init__(self, unid):
        self.unid = unid
        self.lastPing = time.time()
        self.name = "no name"
    
    def ping(self):
        self.lastPing = time.time()
    
    def __str__(self):
        return "_U_" + str(self.unid)
    
    def timeout(self, t=10):
        diff = time.time() - self.lastPing
        if diff > t:
            return True
        else:
            return False

def data():
    out = ast.literal_eval(ast.literal_eval(flask.request.data.decode('ascii')))
    return out

@app.route('/clean_db/')
def cleanGames():
    i = 0
    with database() as dic:
        for key in list(dic["games"].keys()):
            if dic["games"][key]["players"][list(dic["games"][key]["players"])[0]].timeout(50) and dic["games"][key]["players"][list(dic["games"][key]["players"])[0]].timeout(50):
                dic["games"].pop(key)
                i += 1
    return "Removed " + str(i) + " dormant games"

@app.route('/connect/', methods=['POST'])
def connect():
    key = data()["key"]
    name = data()["name"]
    cleanGames()
    with database() as dic:
        unid = dic["lastUNID"]
        while True:
            unid += 1
            if not unid in dic["queue"].keys():
                u = User(unid)
                u.name = name
                dic["lastUNID"] = unid
                dic["queue"][unid] = u
                break
    return str({"key": key, "unid": unid})

@app.route('/leave_queue/', methods=['POST'])
def leaveQueue():
    unid = data()["unid"]
    with database() as dic:
        if unid in list(dic["queue"].keys()):
            del dic["queue"][unid]

@app.route('/database/')
def get_data():
    with database() as dic:
        return str(dic)
    
@app.route('/check_queue/', methods=['POST'])
def checkQueue():
    unid = data()["unid"]
    with database() as dic:
        if unid in dic["queue"].keys():
            user = dic["queue"][unid]
            user.ping()
            for k in list(dic["queue"].keys()):
                if dic["queue"][k].timeout(t=2):
                    del dic["queue"][k]
            if len(dic["queue"].keys()) >= 2:
                g = 0
                while True:
                    g += 1
                    if not "g" + str(g) in dic["games"]:
                        dic["games"]["g" + str(g)] = {}
                        game = dic["games"]["g" + str(g)]
                        game["players"] = {}
                        game["state"] = "connecting"
                        break
                
                del dic["queue"][unid]
                game["players"][unid] = user
                
                p2 = dic["queue"][list(dic["queue"])[0]]
                del dic["queue"][list(dic["queue"])[0]]
                game["players"][p2.unid] = p2
                out = [True ,"g" + str(g)]
            else:
                out = [False]
        else:
            out = [False]
            for k, v in dic["games"].items():
                if unid in v["players"].keys() and v["state"] == "connecting":
                    out = [True, k]
        
    return str(out)

@app.route("/game_loop/", methods=['POST'])
def gameLoop():
    dat = data()
    unid = dat['unid']
    gamen = dat["game"]
    type = dat['type']
    with database() as dic:
        game = dic["games"][gamen]
        game["players"][unid].ping()
        if type == "update":
            events = dat["events"]
            for event in events:
                #print("In Events", event)
                if event["type"] == "turn":
                    for player in game["players"].keys():
                        if player != unid:
                            game["turn"] = {"player": player, "time": time.time()}
                    game["events"].append({"type": "turn", "turn": game["turn"], "got": []})
                else:
                    event["got"] = [unid]
                    game["events"].append(event)
        
        for i, player in game["players"].items():
            if player.timeout():
                game["events"].append({"type": "stop", "reason": "timeout", "got":[]})
                game["state"] = "-stopping"
        
        events = [e for e in game["events"] if not unid in e["got"]]
        #print("out events", events)
        for event in game["events"]:
            if not unid in event["got"]:
                event["got"].append(unid)
        out = str({"events": events})
        game["events"] = [e for e in game["events"] if not len(e["got"]) >= 2]
        if game["state"] == "-stopping":
            game["state"] = "stopping"
        elif game["state"] == "stopping":
            dic["games"].pop(gamen)
        return str(out)
        
    
@app.route("/game_start/", methods=['POST'])
def gameStart():
    dat = data()
    unid = dat['unid']
    game = dat["game"]
    with database() as dic:
        game = dic["games"][game]
        game["players"][unid].ping()
        if game["state"] == "connecting":
            game["starter"] = random.choice(list(game["players"].keys()))
            game["turn"] = {"player": game["starter"], "time": time.time()}
            game["state"] = "connecting2"
            """game["board"] = [[{}, {}, {}, {}],
                             [{}, {}, {}, {}],
                             [{}, {}, {}, {}]]"""
            game["events"] = []
        if game["state"] == "connecting2":
            game["state"] = "playing"
        for p in game["players"].keys():
            if p != unid:
                opUnid = p
                opName = game["players"][opUnid].name
        out = {"starter": game["starter"], "turn": game["turn"], "opponent": opUnid, "opName": opName}
    return str(out)
        
@app.route("/game_leave/", methods=['POST'])
def gameLeave():
    dat = data()
    unid = dat['unid']
    game = dat["game"]
    with database() as dic:
        game = dic["games"][game]
        game["players"][unid].ping()
        game["events"].append({"type": "stop", "reason": "disconnect", "got":[unid]})
        game["state"] = "stopping"
        
    return ""

@app.route("/get_cards/")
def getCards():
    with open(os.path.join(os.path.dirname(__file__), "cards.json"), "r") as j:
        cards = json.load(j)
    return json.dumps(cards)

@app.route("/check/")
def chechServer():
    return "online"

if __name__ == '__main__':
    if os.path.exists(dab):
        os.remove(dab)
    app.run(debug=True)
