from flask import Flask

app = Flask(__name__)

@app.route('/')
def index():
    return "首页!!!"



@app.route('/leader')
def leader():
    return "我是领队"


@app.route('/member')
def member():
    return "我是队员"

