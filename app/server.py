import json
import os
import random

import bottle
from bottle import HTTPResponse


def getAdjacentMoves(head):
    # Given a square, return adjacent squares.
    return [
        {'x': head['x']+1, 'y': head['y']},
        {'x': head['x']-1, 'y': head['y']},
        {'x': head['x'], 'y': head['y']+1},
        {'x': head['x'], 'y': head['y']-1}
    ]


def removeOutBounds(moves, height, width):
    # Given list of squares, return inbound squares (0 < x && y width && height).
    return [
        move
        for move in moves
        if move['x'] >= 0
        and move['y'] >= 0
        and move['x'] < width
        and move['y'] < height
    ]


def removeSnakePositions(moves, snakePositions):
    # Given list of squares, return squares to be unnoccupied next turn.
    return [
        move
        for move in moves
        if move not in snakePositions
    ]


def nonLethalSquares(head, data):
    # Given a starting square, return any squares that are
    #   adjacent, inbounds, and not guaranteed to be occupied.
    adjacent = getAdjacentMoves(head)
    inBounds = removeOutBounds(adjacent, data['board']['height'], data['board']['width'])
    nonLethal = removeSnakePositions(inBounds, data['board']['snakePositions'])
    return nonLethal


def getBestCaverns(moves, data):
    # Compare "sizes" corresponding to each move, return those tied for highest.
    #   Relies upon 'moves' being a list of non-lethal squares.
    cavernSizes = []
    largestCavern = 0
    for move in moves:
        size = getSizeOfCavern(move, data)
        cavernSizes.append([move, size])
        if size > largestCavern:
            largestCavern = size
    return [ moveSize[0] for moveSize in cavernSizes if moveSize[1] == largestCavern ]


def getSizeOfCavern(cavernStart, data):
    # Iterate through and count nonLethal adjacent squares, up to your body length.
    curSize = 0
    expendedMoves = []
    toCount = [cavernStart]
    while toCount:
        # Mark square as counted for this cavernStart
        curSquare = toCount[0]
        expendedMoves += curSquare
        toCount.remove(curSquare)
        curSize += 1
        # If up to body size, stop counting
        if curSize >= len(data['you']['body']):
            return curSize
        # Append unvisited squares to counting queue
        toCount += [ move for move in nonLethalSquares(curSquare, data) if move not in expendedMoves ]
    return curSize


def getDirection(head, move):
    # Given head & move objs, return direction str eg. 'left', 'right'.
    if move['x'] > head['x']:
        assert move['y'] == head['y'], 'Cannot move diagonally'
        return 'right'
    elif move['x'] < head['x']:
        assert move['y'] == head['y'], 'Cannot move diagonally'
        return 'left'
    elif move['y'] > head['y']:
        assert move['x'] == head['x'], 'Cannot move diagonally'
        return 'down'
    elif move['y'] < head['y']:
        assert move['x'] == head['x'], 'Cannot move diagonally'
        return 'up'


@bottle.route("/")
def index():
    return "Your Battlesnake is alive!"


@bottle.post("/ping")
def ping():
    """
    Used by the Battlesnake Engine to make sure your snake is still working.
    """
    return HTTPResponse(status=200)


@bottle.post("/start")
def start():
    """
    Called every time a new Battlesnake game starts and your snake is in it.
    Your response will control how your snake is displayed on the board.
    """
    data = bottle.request.json
    print("START:", json.dumps(data))

    response = {"color": "#00FF00", "headType": "regular", "tailType": "regular"}
    return HTTPResponse(
        status=200,
        headers={"Content-Type": "application/json"},
        body=json.dumps(response),
    )


@bottle.post("/move")
def move():
    """
    Called when the Battlesnake Engine needs to know your next move.
    The data parameter will contain information about the board.
    Your response must include your move of up, down, left, or right.
    """
    # Update boardState
    data = bottle.request.json
    head = data['you']['body'][0]
    data['board']['snakePositions'] = []
    for snake in data['board']['snakes']:
        data['board']['snakePositions'] += snake['body']

    # Get moves that won't kill you
    nonLethal = nonLethalSquares(head, data)
    # Judge options with crappy flood-filly thing
    bestCaverns = getBestCaverns(nonLethal, data)
    # Pick random from remaining
    move = random.choice(bestCaverns)
    # Generate response payload
    moveDirection = getDirection(head, move)
    response = {"move": moveDirection, "shout": "I am a python snake!"}
    return HTTPResponse(
        status=200,
        headers={"Content-Type": "application/json"},
        body=json.dumps(response),
    )


@bottle.post("/end")
def end():
    """
    Called every time a game with your snake in it ends.
    """
    data = bottle.request.json
    print("END:", json.dumps(data))
    return HTTPResponse(status=200)


def main():
    bottle.run(
        application,
        host=os.getenv("IP", "0.0.0.0"),
        port=os.getenv("PORT", "8080"),
        debug=os.getenv("DEBUG", True),
    )


# Expose WSGI app (so gunicorn can find it)
application = bottle.default_app()

if __name__ == "__main__":
    main()
