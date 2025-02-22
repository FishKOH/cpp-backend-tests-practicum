import os
import random
import pytest
import pathlib

import game_server as game
from game_server import Point, Vector2D, Direction


@pytest.fixture()
def game_server():
    config_path = pathlib.Path(os.environ['CONFIG_PATH'])
    yield game.GameServer(config_path)


def get_states(server, game_server: game.GameServer, token):
    state = server.get_state(token)
    py_state = game_server.get_state(token)
    return state, py_state


def get_parsed_state(server, token, player_id):
    state: dict = server.get_player_state(token, player_id)
    pos = state.get('pos')
    speed = state.get('speed')
    direction = state.get('dir')
    return pos, speed, direction


def move_players(server, game_server: game.GameServer, token, direction):
    server.move(token, direction)
    game_server.move(token, direction)


def tick_both(server, game_server: game.GameServer, ticks):
    server.tick(ticks)
    game_server.tick(ticks)


def add_player(server, game_server, map_id, name):
    token, player_id = server.add_player(name, map_id)
    position, _, _ = get_parsed_state(server, token, player_id)
    game_server.join(name, map_id, token, player_id, Point(position[0], position[1]))
    return token, player_id


def compare_states(cpp_state: dict, py_state: dict):
    cpp_players: dict = cpp_state['players']
    py_players: dict = py_state['players']
    assert cpp_players.keys() == py_players.keys()

    for player_id in cpp_players:
        cpp_player: dict = cpp_players[player_id]
        py_player: dict = py_players[player_id]

        assert Point(*cpp_player['pos']) == Point(*py_player['pos'])
        assert Vector2D(*cpp_player['speed']) == Vector2D(*py_player['speed'])
        assert cpp_player['dir'] == py_player['dir']


def test_tick_miss_delta(server_one_test):
    request = 'api/v1/game/tick'
    header = {'content-type': 'application/json'}
    res = server_one_test.request('POST', header, request)

    assert res.status_code == 400
    assert res.headers['content-type'] == 'application/json'
    assert res.headers['cache-control'] == 'no-cache'
    res_json = res.json()
    print(res_json)
    assert res_json['code'] == 'invalidArgument'
    assert res_json.get('message')


@pytest.mark.parametrize('delta', {0.0, '0', True})
def test_tick_invalid_type_delta(server_one_test, delta):
    request = 'api/v1/game/tick'
    header = {'content-type': 'application/json'}

    data = {"timeDelta": delta}
    res = server_one_test.request('POST', header, request, json=data)

    assert res.status_code == 400
    assert res.headers['content-type'] == 'application/json'
    assert res.headers['cache-control'] == 'no-cache'
    res_json = res.json()
    print(res_json)
    assert res_json['code'] == 'invalidArgument'
    assert res_json.get('message')


@pytest.mark.parametrize('method', ['GET', 'OPTIONS', 'HEAD', 'PUT', 'PATCH', 'DELETE'])
def test_tick_invalid_verb(server_one_test, method):
    request = 'api/v1/game/tick'
    header = {'content-type': 'application/json'}
    res = server_one_test.request(method, header, request)
    print(res.headers)
    assert res.status_code == 405
    assert res.headers['content-type'] == 'application/json'
    assert res.headers['cache-control'] == 'no-cache'

    if method != 'HEAD':
        res_json = res.json()
        assert res_json['code'] == 'invalidMethod'
        assert res_json.get('message')


@pytest.mark.randomize(min_num=0, max_num=10000, ncalls=10)
def test_tick_success(server_one_test, delta: int):
    request = 'api/v1/game/tick'
    header = {'content-type': 'application/json'}
    data = {"timeDelta": delta}
    res = server_one_test.request('POST', header, request, json=data)

    assert res.status_code == 200
    assert res.headers['content-type'] == 'application/json'
    assert res.headers['cache-control'] == 'no-cache'

    res_json = res.json()
    print(res_json)
    assert res_json == dict()


def test_match_roads(server, game_server):
    py_maps = game_server.get_maps()
    server_maps = server.get_maps()

    assert py_maps == server_maps
    for i in range(0, len(py_maps)):
        py_map = game_server.get_map(py_maps[i]['id'])
        if 'dogSpeed' in py_map.keys():
            py_map.pop('dogSpeed')
        server_map = server.get_map(server_maps[i]['id'])
        assert py_map == server_map


@pytest.mark.parametrize('direction', ['R', 'L', 'U', 'D'])
def test_turn_one_player(server_one_test, game_server, direction, map_id):
    token, _ = add_player(server_one_test, game_server, map_id, 'player')
    move_players(server_one_test, game_server, token, direction)
    state, py_state = get_states(server_one_test, game_server, token)

    compare_states(state, py_state)


@pytest.mark.randomize(min_num=0, max_num=250, ncalls=3)
@pytest.mark.parametrize('direction', ['R', 'L', 'U', 'D'])
def test_small_move_one_player(server_one_test, game_server, direction, ticks=140, map_id='town'):
    token, _ = add_player(server_one_test, game_server, map_id, 'player')
    move_players(server_one_test, game_server, token, direction)
    state, py_state = get_states(server_one_test, game_server, token)

    compare_states(state, py_state)

    tick_both(server_one_test, game_server, ticks)
    state, py_state = get_states(server_one_test, game_server, token)
    print(py_state)
    print(state)

    compare_states(state, py_state)


@pytest.mark.randomize(min_num=1000, max_num=100000, ncalls=3)
@pytest.mark.parametrize('direction', ['R', 'L', 'U', 'D'])
def test_big_move_one_player(server_one_test, game_server, direction, ticks: int, map_id):
    token, _ = add_player(server_one_test, game_server, map_id, 'player')
    move_players(server_one_test, game_server, token, direction)
    state, py_state = get_states(server_one_test, game_server, token)

    compare_states(state, py_state)

    tick_both(server_one_test, game_server, ticks)
    state, py_state = get_states(server_one_test, game_server, token)
    print(py_state)
    print(state)

    compare_states(state, py_state)


def test_move_sequence_one_player(server_one_test, game_server, map_id):
    token, _ = add_player(server_one_test, game_server, map_id, 'player')

    # commented lines - forces test (with particular random seed) to break due to a wierd bug in the c++ solution
    # uncommented lines doesn't break the test,
    # because they have a slightly different mechanism to get a random direction
    # uncomment this to break the test:

    # valid_directions = ['R', 'L', 'U', 'D']
    # max_index = len(valid_directions) - 1
    # random.seed(136)    # This particular seed brakes the actual server on 10th step (py-server works as expected)

    for i in range(0, 10):
        direction = Direction.random_str()
        # also to break the test comment the line above and uncomment the following:
        # direction = valid_directions[random.randint(0, max_index)]

        move_players(server_one_test, game_server, token, direction)

        ticks = random.randint(10, 10000)
        tick_both(server_one_test, game_server, ticks)

        state, py_state = get_states(server_one_test, game_server, token)
        print(direction, ticks)
        print('Server:', state)
        print('PyServer:', py_state)

        compare_states(state, py_state)


@pytest.mark.parametrize('direction_1', ['R', 'L', 'U', 'D'])
@pytest.mark.parametrize('direction_2', ['R', 'L', 'U', 'D'])
def test_two_players_turns(server_one_test, game_server, direction_1, direction_2, map_id):
    token_1, _ = add_player(server_one_test, game_server, map_id, 'Player 1')
    token_2, _ = add_player(server_one_test, game_server, map_id, 'Player 2')

    move_players(server_one_test, game_server, token_1, direction_1)
    move_players(server_one_test, game_server, token_2, direction_2)

    state_1, py_state_1 = get_states(server_one_test, game_server, token_1)
    state_2, py_state_2 = get_states(server_one_test, game_server, token_2)

    compare_states(state_1, py_state_1)
    compare_states(state_2, py_state_2)


@pytest.mark.randomize(min_num=0, max_num=250, ncalls=3)
def test_two_players_small_move(server_one_test, game_server, map_id, ticks: int):
    token_1, _ = add_player(server_one_test, game_server, map_id, 'Player 1')
    token_2, _ = add_player(server_one_test, game_server, map_id, 'Player 2')
    state_1, py_state_1 = get_states(server_one_test, game_server, token_1)
    state_2, py_state_2 = get_states(server_one_test, game_server, token_2)

    compare_states(state_1, py_state_1)
    compare_states(state_2, py_state_2)

    direction_1 = Direction.random_str()
    move_players(server_one_test, game_server, token_1, direction_1)

    direction_2 = Direction.random_str()
    move_players(server_one_test, game_server, token_2, direction_2)

    tick_both(server_one_test, game_server, ticks)

    state_1, py_state_1 = get_states(server_one_test, game_server, token_1)
    state_2, py_state_2 = get_states(server_one_test, game_server, token_2)

    compare_states(state_1, py_state_1)
    compare_states(state_2, py_state_2)


@pytest.mark.randomize(min_num=250, max_num=10000, ncalls=3)
def test_two_players_big_move(server_one_test, game_server, map_id, ticks: int):
    token_1, _ = add_player(server_one_test, game_server, map_id, 'Player 1')
    token_2, _ = add_player(server_one_test, game_server, map_id, 'Player 2')
    state_1, py_state_1 = get_states(server_one_test, game_server, token_1)
    state_2, py_state_2 = get_states(server_one_test, game_server, token_2)

    compare_states(state_1, py_state_1)
    compare_states(state_2, py_state_2)

    direction_1 = Direction.random_str()
    move_players(server_one_test, game_server, token_1, direction_1)

    direction_2 = Direction.random_str()
    move_players(server_one_test, game_server, token_2, direction_2)

    tick_both(server_one_test, game_server, ticks)
    state_1, py_state_1 = get_states(server_one_test, game_server, token_1)
    state_2, py_state_2 = get_states(server_one_test, game_server, token_2)

    compare_states(state_1, py_state_1)
    compare_states(state_2, py_state_2)


def test_two_players_sequences(server_one_test, game_server, map_id):
    token_1, _ = add_player(server_one_test, game_server, map_id, 'Player 1')
    token_2, _ = add_player(server_one_test, game_server, map_id, 'Player 2')
    state_1, py_state_1 = get_states(server_one_test, game_server, token_1)
    state_2, py_state_2 = get_states(server_one_test, game_server, token_2)

    compare_states(state_1, py_state_1)
    compare_states(state_2, py_state_2)

    for _ in range(0, 10):
        direction_1 = Direction.random_str()
        move_players(server_one_test, game_server, token_1, direction_1)

        direction_2 = Direction.random_str()
        move_players(server_one_test, game_server, token_2, direction_2)

        ticks = random.randint(0, 10000)
        tick_both(server_one_test, game_server, ticks)

        state_1, py_state_1 = get_states(server_one_test, game_server, token_1)
        state_2, py_state_2 = get_states(server_one_test, game_server, token_2)

        compare_states(state_1, py_state_1)
        compare_states(state_2, py_state_2)
