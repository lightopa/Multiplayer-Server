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
app = flask.Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

dab = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "data/database.dab"))

class database:
    def __enter__(self):
        print("enter")
        checkDatabase()
        with open(dab, 'rb') as f:
            self.dab = pickle.load(f)
            print("dab:", self.dab)
        return self.dab
    def __exit__(self, type, value, traceback):
        print("exit")
        with open(dab, 'wb') as f:
            print("end:", self.dab)
            pickle.dump(self.dab, f)

def data():
    out = ast.literal_eval(ast.literal_eval(flask.request.data.decode('ascii')))
    return out

@app.route('/connect/', methods=['GET', 'POST'])
def connect():
    print(data())
    key = data()["key"]
    with database() as dic:
        if not "queue" in dic:
            dic["queue"] = []
        unid = 0
        while True:
            unid += 1
            if not unid in dic["queue"]:
                dic["queue"].append(unid)
                break
    return str({"key": key, "unid": unid})

@app.route('/check_queue/', methods=['GET', 'POST'])
def checkQueue():
    unid = data()["unid"]
    with database() as dic:
        if unid in dic["queue"]:
            if len(dic["queue"]) >= 2:
                if not "games" in dic:
                    dic["games"] = {}
                g = 0
                while True:
                    g += 1
                    if not "g" + str(g) in dic["games"]:
                        dic["games"]["g" + str(g)] = {}
                        game = dic["games"]["g" + str(g)]
                        game["players"] = []
                        game["state"] = "connecting"
                        break
                
                dic["queue"].remove(unid)
                game["players"].append(unid)
                p2 = dic["queue"][0]
                dic["queue"].remove(p2)
                game["players"].append(p2)
                out = [True ,"g" + str(g)]
            else:
                out = [False]
        else:
            out = [False]
            for k, v in dic["games"].items():
                if unid in v["players"] and v["state"] == "connecting":
                    out = [True, k]
            
    return str(out)
                

def checkDatabase():
    print("check database")
    try:
        with open(dab, 'rb') as f:
            pass
    except FileNotFoundError:
        print("FILE NOT FOUND")
        dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "data"))
        if not os.path.exists(dir):
            os.makedirs(dir)
        with open(dab, 'wb') as f:
            pass
    try:
        with open(dab, 'rb') as f: 
            pickle.load(f)
    except EOFError as e:
        print("EOFERROR")
        print(e)
        f.close()
        with open(dab, 'wb') as f: 
            pickle.dump({}, f)

if __name__ == '__main__':
    app.run(debug=True)
