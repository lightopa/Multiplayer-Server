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

class User:
    def __init__(self, unid):
        self.unid = unid
        self.lastPing = time.time()
    
    def ping(self):
        self.lastPing = time.time()
    
    def __str__(self):
        return "_U_" + str(self.unid)
    
    def timeout(self):
        diff = time.time() - self.lastPing
        if diff > 10:
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
        unid = 0
        while True:
            unid += 1
            if not unid in dic["queue"].keys():
                u = User(unid)
                print("create user", unid)
                dic["queue"][unid] = u
                break
    return str({"key": key, "unid": unid})


@app.route('/database/')
def get_data():
    with database() as dic:
        return str(dic)
    
@app.route('/check_queue/', methods=['GET', 'POST'])
def checkQueue():
    unid = data()["unid"]
    with database() as dic:
        if unid in dic["queue"].keys():
            user = dic["queue"][unid]
            user.ping()
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
        
        for k, user in dic["queue"].items():
            if user.timeout():
                del dic["queue"][k]
    return str(out)
                

def checkDatabase():
    print("check database")
    
    dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "data"))
    if not os.path.exists(dir):
        os.makedirs(dir)
    if not os.path.exists(dab):
        with open(dab, 'wb') as f:
            pass
        
    """try:
        with open(dab, 'rb') as f:
            pass
    except FileNotFoundError:
        print("FILE NOT FOUND")
        dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "data"))
        if not os.path.exists(dir):
            os.makedirs(dir)
        with open(dab, 'wb') as f:
            pass"""
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
