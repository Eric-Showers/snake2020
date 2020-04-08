import json
import os
import random
import time

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


def isInBounds(move, height, width):
    # Given a square, return True if inbounds otherwise False
        if move['x'] < 0:
            return False
        elif move['y'] < 0:
            return False
        elif move['x'] >= width:
            return False
        elif move['y'] >= height:
            return False
        else:
            return True


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
    inBounds = [ square for square in adjacent if isInBounds(square, data['board']['height'], data['board']['width']) ]
    nonLethal = removeSnakePositions(inBounds, data['board']['snakePositions'])
    return nonLethal


def getBestCaverns(moves, data):
    # Compare "sizes" corresponding to each move, return those tied for highest.
    #   Relies upon 'moves' being a list of non-lethal squares.
    if len(moves) == 0:
        return ([], 0)
    cavernSizes = []
    largestCavern = 0
    for move in moves:
        size = getSizeOfCavern(move, data)
        cavernSizes.append([move, size])
        if size > largestCavern:
            largestCavern = size
    return ([ moveSize[0] for moveSize in cavernSizes if moveSize[1] == largestCavern ], largestCavern)


def getSizeOfCavern(entrance, data):
    # Iterate through and count nonLethal adjacent squares, up to your body length.
    curSize = 0
    visitedSquares = []
    toVisit = [entrance]
    while toVisit:
# Nick wuz here
        # Mark square as counted for this cavernStart
        curSquare = toVisit[0]
        toVisit = toVisit[1:]
        visitedSquares.append(curSquare)
        curSize += 1
        # If up to body size, stop counting
        if curSize >= len(data['you']['body'])*2:
            return curSize
        # Get adjacent, nonLethal squares
        adjNonLethal = nonLethalSquares(curSquare, data)
        # Add into toVisit, the ones that are in neither visitedSquares OR toVisit
        toVisit += [
            square
            for square in adjNonLethal
            if square not in visitedSquares
            and square not in toVisit
        ]
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


def foodPriority(squares, food):
    # Return only food squares, or else return all moves (if no food)
    foodSquares = [ square for square in squares if square in food ]
    if foodSquares:
        return foodSquares
    else:
        return squares


def foldPriority(squares, head, board, yourLength):
    # Return squares that help maximize space used
    # Basically prioritises covering up new body segments rather than old ones
    squarePriorities = []  # Store priority score of each square
    for square in squares:
        priority = 0
        adjacents = getAdjacentMoves(square)
        for adjacentSquare in adjacents:
            if adjacentSquare != head:
                # If adjacent square is wall or snake then add one to priority score
                if not isInBounds(adjacentSquare, board['height'], board['width']):
                    priority += yourLength
                elif adjacentSquare in board['snakePositions']:
                    priority += board['bodyStaleness'][adjacentSquare['x']][adjacentSquare['y']]
        squarePriorities.append(priority)
    highestPriority = max(squarePriorities)
    options = []
    for i, square in enumerate(squares):
        if squarePriorities[i] == highestPriority:
            options.append(square)
    return options


def avoidHeads(squares, board, yourId):
    # Returns squares that are out of reach of opponents, or else return all squares
    enemyAdjacent = []
    for snake in board['snakes']:
        if snake['id'] != yourId:
            enemyAdjacent += getAdjacentMoves(snake['body'][0])
    safeSquares = [ square for square in squares if square not in enemyAdjacent ]
    if safeSquares:
        return safeSquares
    else:
        return squares


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

    response = {"color": "#187eb5", "headType": "regular", "tailType": "regular"}
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
    data['board']['bodyStaleness'] = []
    for column in range(data['board']['width']):
        column = []
        for row in range(data['board']['height']):
            column.append(0)
        data['board']['bodyStaleness'].append(column)
    for snake in data['board']['snakes']:
        # Tail piece will move next turn, don't avoid it
        for i, square in enumerate(snake['body'][:-1]):
            data['board']['snakePositions'].append(square)
            # Track the number of turns until this body square is the tail
            data['board']['bodyStaleness'][square['x']][square['y']] = len(snake['body'])-i-1

    # Get moves that won't kill you
    options = nonLethalSquares(head, data)
    # Avoid other snakes next moves, if possible
    options = avoidHeads(options, data['board'], data['you']['id'])
    # Judge options with flood-filly thing to avoid tight spaces
    options, cavernSize = getBestCaverns(options, data)
    # If under 3/4 health prioritise food
    if data['you']['health'] < 75:
        options = foodPriority(options, data['board']['food'])
    # If biggest cavern is less than 3/2 body size prioritise folding
    if cavernSize <= len(data['you']['body'])*1.5:
        options = foldPriority(options, head, data['board'], len(data['you']['body']))
    if options:
        moveDirection = getDirection(head, random.choice(options))
    else:
        moveDirection = random.choice(['right','left','down','up'])
    #TODO
    # Navigate to opponent heads from choices
    # Suggest picking one furthest from heads
    # Hint use this - pip install pathfinding

    # Generate response payload
    response = {"move": moveDirection, "shout": "There can only be one"}
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
