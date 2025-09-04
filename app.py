from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import uuid
import random

app = Flask(__name__, static_folder='public', static_url_path='/')
CORS(app)

# 存储游戏房间数据
rooms = {}

# 房间状态
ROOM_STATUS_LOBBY = 'lobby'
ROOM_STATUS_IN_GAME = 'in_game'


@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

# API 接口
@app.route('/create_room', methods=['POST'])
def create_room():
    # 创建一个新房间，并生成一个唯一的房间 ID
    room_id = str(uuid.uuid4())[:8]  # 简化 ID
    owner_name = request.json.get('owner_name')

    if not owner_name:
        return jsonify({'success': False, 'message': 'Owner name is required'}), 400

    rooms[room_id] = {
        'owner': owner_name,
        'players': [{'name': owner_name, 'is_owner': True}],
        'status': ROOM_STATUS_LOBBY,
        'assignments': {}, # 天使与主人的分配关系
        'tasks': {}, # 任务和愿望
    }
    return jsonify({'success': True, 'room_id': room_id, 'message': 'Room created successfully'})

@app.route('/join_room', methods=['POST'])
def join_room():
    # 玩家加入指定房间
    room_id = request.json.get('room_id')
    player_name = request.json.get('player_name')

    if room_id not in rooms:
        return jsonify({'success': False, 'message': 'Room not found'}), 404
    
    room = rooms[room_id]
    if room['status'] != ROOM_STATUS_LOBBY:
        return jsonify({'success': False, 'message': 'Game has already started'}), 400

    # 检查玩家是否已存在
    if any(p['name'] == player_name for p in room['players']):
        return jsonify({'success': False, 'message': 'Player name already exists in this room'}), 400

    room['players'].append({'name': player_name, 'is_owner': False})
    return jsonify({'success': True, 'message': 'Joined room successfully'})

@app.route('/get_room_info/<room_id>', methods=['GET'])
def get_room_info(room_id):
    # 获取房间信息
    if room_id not in rooms:
        return jsonify({'success': False, 'message': 'Room not found'}), 404
    
    room = rooms[room_id]
    # 不返回敏感信息，如分配关系
    return jsonify({
        'success': True,
        'status': room['status'],
        'owner': room['owner'],
        'players': [p['name'] for p in room['players']],
    })

@app.route('/start_game', methods=['POST'])
def start_game():
    # 游戏开始，分配天使与主人，并设置愿望
    room_id = request.json.get('room_id')
    if room_id not in rooms:
        return jsonify({'success': False, 'message': 'Room not found'}), 404

    room = rooms[room_id]
    if room['status'] != ROOM_STATUS_LOBBY:
        return jsonify({'success': False, 'message': 'Game has already started'}), 400

    player_names = [p['name'] for p in room['players']]
    if len(player_names) < 2:
        return jsonify({'success': False, 'message': 'Need at least 2 players to start'}), 400

    random.shuffle(player_names)
    
    # 核心逻辑：分配天使与主人
    assignments = {}
    for i in range(len(player_names)):
        angel = player_names[i]
        owner_index = (i + 1) % len(player_names) # 确保不分配给自己
        owner = player_names[owner_index]
        assignments[angel] = owner

    room['assignments'] = assignments
    room['status'] = ROOM_STATUS_IN_GAME
    
    # 初始化任务
    room['tasks'] = {p_name: {'wishes': [], 'completed': False} for p_name in player_names}
    
    return jsonify({'success': True, 'message': 'Game started successfully', 'assignments': assignments})


@app.route('/submit_wishes', methods=['POST'])
def submit_wishes():
    # 玩家提交愿望
    room_id = request.json.get('room_id')
    player_name = request.json.get('player_name')
    wishes = request.json.get('wishes') # 列表形式

    if room_id not in rooms or rooms[room_id]['status'] != ROOM_STATUS_IN_GAME:
        return jsonify({'success': False, 'message': 'Game not found or not in progress'}), 404

    room = rooms[room_id]
    if player_name not in room['tasks']:
        return jsonify({'success': False, 'message': 'Player not in this game'}), 400
    
    room['tasks'][player_name]['wishes'] = wishes
    
    return jsonify({'success': True, 'message': 'Wishes submitted successfully'})

@app.route('/get_my_owner/<room_id>/<angel_name>', methods=['GET'])
def get_my_owner(room_id, angel_name):
    # 天使获取自己的主人
    if room_id not in rooms or rooms[room_id]['status'] != ROOM_STATUS_IN_GAME:
        return jsonify({'success': False, 'message': 'Game not found or not in progress'}), 404
    
    room = rooms[room_id]
    owner_name = room['assignments'].get(angel_name)
    if not owner_name:
        return jsonify({'success': False, 'message': 'You are not in this game or game has not started'}), 400

    # 获取主人的愿望，作为任务
    wishes = room['tasks'].get(owner_name, {}).get('wishes', [])
    
    return jsonify({
        'success': True,
        'owner_name': owner_name,
        'tasks': wishes,
    })

@app.route('/check_all_wishes/<room_id>', methods=['GET'])
def check_all_wishes(room_id):
    if room_id not in rooms or rooms[room_id]['status'] != ROOM_STATUS_IN_GAME:
        return jsonify({'success': False, 'message': 'Game not found or not in progress'}), 404

    room = rooms[room_id]
    num_players = len(room['players'])
    # 计算已提交愿望的玩家数
    num_wishes_submitted = sum(1 for p in room['tasks'] if room['tasks'][p]['wishes'])
    
    # 判断所有玩家是否都已提交愿望
    all_submitted = num_wishes_submitted == num_players
    
    return jsonify({
        'success': True,
        'all_submitted': all_submitted,
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
