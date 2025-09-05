# 导入所需的库
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import uuid
import random

# 初始化 Flask 应用
app = Flask(__name__, static_folder='public', static_url_path='/')
CORS(app)

# 用于存储游戏房间的内存数据
rooms = {}

# 房间状态常量
ROOM_STATUS_LOBBY = 'lobby'
ROOM_STATUS_IN_GAME = 'in_game'
ROOM_STATUS_ENDED = 'ended'
ROOM_STATUS_GAME_OVER = 'game_over'  # 新增游戏结束状态

@app.route('/')
def serve_index():
    """
    提供 index.html 文件给前端。
    """
    return send_from_directory(app.static_folder, 'index.html')

# --- API 端点 ---

@app.route('/create_room', methods=['POST'])
def create_room():
    """
    创建一个新的游戏房间。
    """
    owner_name = request.json.get('owner_name')
    if not owner_name:
        return jsonify({'success': False, 'message': '需要房主昵称'}), 400

    room_id = str(uuid.uuid4())[:8]
    rooms[room_id] = {
        'owner': owner_name,
        'players': [{'name': owner_name, 'is_owner': True}],
        'status': ROOM_STATUS_LOBBY,
        'assignments': {},
        'tasks': {},
    }
    return jsonify({'success': True, 'room_id': room_id, 'message': '房间创建成功'})

@app.route('/join_room', methods=['POST'])
def join_room():
    """
    允许玩家加入现有房间。
    """
    room_id = request.json.get('room_id')
    player_name = request.json.get('player_name')

    if room_id not in rooms:
        return jsonify({'success': False, 'message': '未找到房间'}), 404
    
    room = rooms[room_id]
    if room['status'] != ROOM_STATUS_LOBBY:
        return jsonify({'success': False, 'message': '游戏已开始'}), 400

    if any(p['name'] == player_name for p in room['players']):
        return jsonify({'success': False, 'message': '此房间已存在该玩家名'}), 400

    room['players'].append({'name': player_name, 'is_owner': False})
    return jsonify({'success': True, 'message': '加入房间成功'})

@app.route('/get_room_info/<room_id>', methods=['GET'])
def get_room_info(room_id):
    """
    获取房间信息。
    """
    if room_id not in rooms:
        return jsonify({'success': False, 'message': '未找到房间'}), 404
    
    room = rooms[room_id]
    return jsonify({
        'success': True,
        'status': room['status'],
        'owner': room['owner'],
        'players': [p['name'] for p in room['players']],
    })

@app.route('/start_game', methods=['POST'])
def start_game():
    """
    开始游戏并分配天使和主人。
    """
    room_id = request.json.get('room_id')
    if room_id not in rooms:
        return jsonify({'success': False, 'message': '未找到房间'}), 404

    room = rooms[room_id]
    if room['status'] != ROOM_STATUS_LOBBY:
        return jsonify({'success': False, 'message': '游戏已开始'}), 400

    player_names = [p['name'] for p in room['players']]
    if len(player_names) < 2:
        return jsonify({'success': False, 'message': '至少需要2名玩家才能开始'}), 400

    random.shuffle(player_names)
    
    assignments = {}
    for i in range(len(player_names)):
        angel = player_names[i]
        owner_index = (i + 1) % len(player_names)
        owner = player_names[owner_index]
        assignments[angel] = owner

    room['assignments'] = assignments
    room['status'] = ROOM_STATUS_IN_GAME
    
    room['tasks'] = {p_name: {'wishes': [], 'completed': False} for p_name in player_names}
    
    return jsonify({'success': True, 'message': '游戏开始成功', 'assignments': assignments})

@app.route('/submit_wishes', methods=['POST'])
def submit_wishes():
    """
    允许玩家提交他们的愿望。
    """
    room_id = request.json.get('room_id')
    player_name = request.json.get('player_name')
    wishes = request.json.get('wishes')

    if room_id not in rooms or rooms[room_id]['status'] != ROOM_STATUS_IN_GAME:
        return jsonify({'success': False, 'message': '未找到游戏或游戏未进行中'}), 404

    room = rooms[room_id]
    if player_name not in room['tasks']:
        return jsonify({'success': False, 'message': '玩家不在游戏中'}), 400
    
    room['tasks'][player_name]['wishes'] = wishes
    
    return jsonify({'success': True, 'message': '愿望提交成功'})

@app.route('/get_my_owner/<room_id>/<angel_name>', methods=['GET'])
def get_my_owner(room_id, angel_name):
    """
    获取给定天使的主人名字和愿望。
    """
    if room_id not in rooms or rooms[room_id]['status'] != ROOM_STATUS_IN_GAME:
        return jsonify({'success': False, 'message': '未找到游戏或游戏未进行中'}), 404
    
    room = rooms[room_id]
    owner_name = room['assignments'].get(angel_name)
    if not owner_name:
        return jsonify({'success': False, 'message': '你不在游戏中或游戏未开始'}), 400

    wishes = room['tasks'].get(owner_name, {}).get('wishes', [])
    
    return jsonify({
        'success': True,
        'owner_name': owner_name,
        'tasks': wishes,
    })

@app.route('/check_all_wishes/<room_id>', methods=['GET'])
def check_all_wishes(room_id):
    """
    检查所有玩家是否都已提交愿望。
    """
    if room_id not in rooms or rooms[room_id]['status'] != ROOM_STATUS_IN_GAME:
        return jsonify({'success': False, 'message': '未找到游戏或游戏未进行中'}), 404

    room = rooms[room_id]
    num_players = len(room['players'])
    num_wishes_submitted = sum(1 for p in room['tasks'] if room['tasks'][p]['wishes'])
    
    all_submitted = num_wishes_submitted == num_players
    
    return jsonify({
        'success': True,
        'all_submitted': all_submitted,
    })

@app.route('/end_game', methods=['POST'])
def end_game():
    """
    结束游戏并返回分配结果。
    """
    room_id = request.json.get('room_id')
    player_name = request.json.get('player_name')

    if room_id not in rooms:
        return jsonify({'success': False, 'message': '未找到房间'}), 404
    
    room = rooms[room_id]
    if room['status'] != ROOM_STATUS_IN_GAME:
        return jsonify({'success': False, 'message': '游戏未进行中'}), 400

    if player_name != room['owner']:
        return jsonify({'success': False, 'message': '只有房主可以结束游戏'}), 403

    room['status'] = ROOM_STATUS_GAME_OVER  # 将状态更改为'game_over'以匹配前端
    
    return jsonify({
        'success': True,
        'message': '游戏结束成功',
        'assignments': room['assignments']
    })

@app.route('/get_assignments/<room_id>', methods=['GET'])
def get_assignments(room_id):
    """
    游戏结束后获取天使和主人的分配结果。
    """
    if room_id not in rooms:
        return jsonify({'success': False, 'message': '未找到房间'}), 404
    room = rooms[room_id]
    if room['status'] != ROOM_STATUS_GAME_OVER:  # 检查是否为 'game_over' 状态
        return jsonify({'success': False, 'message': '游戏尚未结束'}), 400
    
    return jsonify({
        'success': True,
        'assignments': room['assignments']
    })

# 新增端点以匹配前端请求
@app.route('/get_all_relationships/<room_id>', methods=['GET'])
def get_all_relationships(room_id):
    """
    游戏结束后获取所有天使-主人关系。
    """
    if room_id not in rooms:
        return jsonify({'success': False, 'message': '未找到房间'}), 404
    room = rooms[room_id]
    if room['status'] != ROOM_STATUS_GAME_OVER:
        return jsonify({'success': False, 'message': '游戏尚未结束'}), 400
    
    return jsonify({
        'success': True,
        'relationships': room['assignments']
    })

@app.route('/get_wishes/<room_id>/<player_name>', methods=['GET'])
def get_wishes(room_id, player_name):
    """
    获取玩家的愿望。
    """
    if room_id not in rooms:
        return jsonify({'success': False, 'message': '未找到房间'}), 404
    
    room = rooms[room_id]
    wishes = room['tasks'].get(player_name, {}).get('wishes', [])
    
    return jsonify({
        'success': True,
        'wishes': wishes
    })

@app.route('/clear_all_data', methods=['POST'])
def clear_all_data():
    """
    清除服务器内存中的所有房间数据。
    """
    global rooms
    rooms.clear()
    return jsonify({'success': True, 'message': '所有房间数据清除成功'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)