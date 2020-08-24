from flask import Flask
from flask import render_template
from flask import request

import flood_it
import os
import time

from random import Random

from google.cloud import ndb

from board import Board

_PS = 'ps'  # The 'previous seed' HTTP GET parameter name
_S = 's'    # The 'seed' HTTP GET parameter name
_M = 'm'    # The 'moves' HTTP GET parameter name

client = ndb.Client()


def ndb_wsgi_middleware(wsgi_app):
    def middleware(environ, start_response):
        with client.context():
            return wsgi_app(environ, start_response)

    return middleware


app = Flask(__name__)
app.wsgi_app = ndb_wsgi_middleware(app.wsgi_app)  # Wrap the app in middleware.


def _ParseSeed(seed):
  parsed_seed = 0
  try:
    parsed_seed = int(seed)
  except Exception:
    parsed_seed = 0
  return parsed_seed

def _ParseMoves(moves):
  parsed_moves = []
  try:
    parsed_moves = list(map(int, moves.split(',')))
  except Exception:
    parsed_moves = []
  return parsed_moves

def _GetBoardDescription(seed):
  key = ndb.Key('BoardDescription', str(seed))
  # TODO: error checking
  return key.get()

def _CreateAndGetNextBoardDescription(previous_seed):
  seed = _ParseSeed(previous_seed) + 1
  # No board exists for this seed, create one now.
  board_description = _GetBoardDescription(seed)
  if not board_description:
    board = Board(14, seed)
    board.Generate()

    # Solve the game so there is at least one completion
    num_sequences = 400
    move_sequences = flood_it.SelectNext(board, num_sequences)
    while not move_sequences[0]["board"].IsFlooded():
      move_sequences = flood_it.SelectNext(board, num_sequences, move_sequences)
    turns = move_sequences[0]["board"].turns

    # Store the solution before returning the board description
    board_description = BoardDescription(id=str(seed))
    board_description.squares = board.squares
    board_description.completions = str(turns) + ':1'
    board_description.example_move_sequence = move_sequences[0]["moves"]
    board_description.example_move_sequence_length = turns
    board_description.put()
  return board_description

def _DeserializeCompletions(completions):
  parsed_completions = {}
  for completion in completions.split(','):
    try:
      completion_data = completion.split(':')
      parsed_completions[int(completion_data[0])] = int(completion_data[1])
    except Exception:
      parsed_completions = {}
  return parsed_completions

def _AddCompletion(num_moves, completions):
  if num_moves in completions:
    completions[num_moves] += 1
  else:
    completions[num_moves] = 1
  return completions

def _SerializeCompletions(completions):
  c = []
  for key, value in sorted(completions.items()):
    c.append(str(key) + ':' + str(value))
  return ','.join(c)

class BoardDescription(ndb.Model):
  squares = ndb.IntegerProperty(repeated=True)
  completions = ndb.StringProperty()
  example_move_sequence = ndb.IntegerProperty(repeated=True)
  example_move_sequence_length = ndb.IntegerProperty()

@app.route('/', methods=['GET'])
def MainHandler():
  # TODO: pass previous seed through in case link is coming from share so begin button can pass on to PlayGame

#    board_descriptions = ndb.GqlQuery('SELECT * FROM BoardDescription')
#    boards = []
#    boards.extend(board_descriptions)
#      board_descriptions = ndb.GqlQuery('SELECT * FROM BoardDescription WHERE seed = :1', 123456)
#      boards.extend(board_descriptions)
#      key = ndb.Key('BoardDescription', 2)
#      board_description = key.get()
#      boards.append(board_description)
#      key = ndb.Key('BoardDescription', '123456')
#      board_description = key.get()
#      boards.append(board_description)
    return render_template('index.html', ps=_ParseSeed(request.args.get(_PS)))

@app.route('/PlayGame', methods=['GET'])
def PlayGame():
    board_description = _CreateAndGetNextBoardDescription(request.args.get(_PS))
    min_moves_to_complete = sorted(_DeserializeCompletions(board_description.completions))[0]
    debug = request.args.get('debug') == '1'
    return render_template(
        'play_game.html',
        seed=board_description.key.string_id(),
        squares=list(map(int, board_description.squares)),
        example_move_sequence=list(map(int, board_description.example_move_sequence)),
        min_moves_to_complete=min_moves_to_complete,
        completions=board_description.completions,
        debug=debug)

@app.route('/GetNextBoard', methods=['GET'])
def GetNextBoard():
    board_description = _CreateAndGetNextBoardDescription(request.args.get(_PS))
    return board_description.squares

# TODO: Error handling/response to user?
@app.route('/UpdateCompletions', methods=['GET'])
def UpdateCompletions():
    seed = _ParseSeed(request.args.get(_S))
    moves = _ParseMoves(request.args.get(_M))

    # Make sure someone is attempting to submit a valid completion
    if not (seed and moves):
      return

    out = f'{seed} {moves}\n'
    # Make sure there is a board description for this seed.
    board_description = _GetBoardDescription(seed)
    if not board_description:
      return out

    # Play the submitted moves
    board = Board(14, seed)
    board.squares = board_description.squares
    board.PlaySequence(moves)
    out += f'{board.IsFlooded()}\n'

    # If the board is flooded, update the recorded completions
    if board.IsFlooded():
      completions = _DeserializeCompletions(board_description.completions)
      out += f'{completions}'
      completions = _AddCompletion(len(moves), completions)
      board_description.completions = _SerializeCompletions(completions)
      board_description.put()

    return out


def main():
                                        ('/PlayGame', PlayGame),

if __name__ == '__main__':
  main()
