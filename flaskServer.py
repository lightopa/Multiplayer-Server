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
app = flask.Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

dab = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "data/database.dab"))

class database:
    def __enter__(self):
        checkDatabase()
        with open(dab, 'rb') as f:
            self.dab = pickle.load(f)
            self._checkStruct()
        return self.dab
    def __exit__(self, type, value, traceback):
        with open(dab, 'wb') as f:
            pickle.dump(self.dab, f)
    
    def _checkStruct(self):
        if not "games" in self.dab:
            self.dab["games"] = {}
        if not "queue" in self.dab:
            self.dab["queue"] = {}
        if not "lastUNID" in self.dab:
            self.dab["lastUNID"] = 0

class User:
    def __init__(self, unid):
        self.unid = unid
        self.lastPing = time.time()
    
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

@app.route('/connect/', methods=['GET', 'POST'])
def connect():
    print(data())
    key = data()["key"]
    with database() as dic:
        unid = dic["lastUNID"]
        while True:
            unid += 1
            if not unid in dic["queue"].keys():
                u = User(unid)
                dic["lastUNID"] = unid
                print("create user", unid)
                dic["queue"][unid] = u
                break
    return str({"key": key, "unid": unid})

@app.route('/leave_queue/', methods=['GET', 'POST'])
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
                print("NEW GAME", unid, p2.unid)
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
    game = dat["game"]
    type = dat['type']
    with database() as dic:
        game = dic["games"][game]
        game["players"][unid].ping()
        if type == "update":
            events = dat["events"]
            for event in events:
                if event["type"] == "place":
                    pos = event["position"]
                    id = event["id"]
                    game["board"][pos[1]][pos[0]] = id
                    game["events"].append(event)
            return "done"
        if type == "fetch":
            events = [e for e in game["events"] if e["type"] == "place"]
            out = {"events": events}
            game["events"] = [e for e in game["events"] if not e in events]
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
            game["board"] = [[{}, {}, {}, {}],
                             [{}, {}, {}, {}],
                             [{}, {}, {}, {}]]
            game["events"] = []
        if game["state"] == "connecting2":
            game["state"] = "playing"
        out = {"starter": game["starter"], "turn": game["turn"]}
    return str(out)
        


@app.route("/get_cards/")
def getCards():
    with open(os.path.join(os.path.dirname(__file__), "cards.json"), "r") as j:
        cards = json.load(j)
    return json.dumps(cards)

@app.route("/check/")
def chechServer():
    return "online"


def checkDatabase():
    print("check database")
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

if __name__ == '__main__':
    if os.path.exists(dab):
        os.remove(dab)
    app.run(debug=True)
