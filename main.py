#!/usr/bin/env python

import cgi
import flood_it
import os
import time

from random import Random

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import util

from board import Board

_PS = 'ps'  # The 'previous seed' HTTP GET parameter name
_S = 's'    # The 'seed' HTTP GET parameter name
_M = 'm'    # The 'moves' HTTP GET parameter name

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
    parsed_moves = map(int, moves.split(','))
  except Exception:
    parsed_moves = []
  return parsed_moves

def _GetBoardDescription(seed):
  key = db.Key.from_path('BoardDescription', str(seed))
  # TODO: error checking
  return db.get(key)

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
    board_description = BoardDescription(key_name=str(seed))
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
  for key, value in sorted(completions.iteritems()):
    c.append(str(key) + ':' + str(value))
  return ','.join(c)

class BoardDescription(db.Model):
  squares = db.ListProperty(item_type=int)
  completions = db.StringProperty()
  example_move_sequence = db.ListProperty(item_type=int)
  example_move_sequence_length = db.IntegerProperty()

class MainHandler(webapp.RequestHandler):
  def get(self):
  # TODO: pass previous seed through in case link is coming from share so begin button can pass on to PlayGame

#    board_descriptions = db.GqlQuery('SELECT * FROM BoardDescription')
#    boards = []
#    boards.extend(board_descriptions)
#      board_descriptions = db.GqlQuery('SELECT * FROM BoardDescription WHERE seed = :1', 123456)
#      boards.extend(board_descriptions)
#      key = db.Key.from_path('BoardDescription', 2)
#      board_description = db.get(key)
#      boards.append(board_description)
#      key = db.Key.from_path('BoardDescription', '123456')
#      board_description = db.get(key)
#      boards.append(board_description)
    path = os.path.join(os.path.dirname(__file__), 'index.html')
    self.response.out.write(template.render(path, {'ps': _ParseSeed(self.request.get(_PS))}))


class PlayGame(webapp.RequestHandler):
  def get(self):
    board_description = _CreateAndGetNextBoardDescription(self.request.get(_PS))
    min_moves_to_complete = sorted(_DeserializeCompletions(board_description.completions))[0]
    debug = self.request.get('debug') == '1'
    template_values = {
      'seed': board_description.key().name(),
      'squares': map(int, board_description.squares),
      'example_move_sequence': map(int, board_description.example_move_sequence),
      'min_moves_to_complete': min_moves_to_complete,
      'completions': board_description.completions,
      'debug': debug
    }
    path = os.path.join(os.path.dirname(__file__), 'play_game.html')
    self.response.out.write(template.render(path, template_values))

class GetNextBoard(webapp.RequestHandler):
  def get(self):
    board_description = _CreateAndGetNextBoardDescription(self.request.get(_PS))
    self.response.out.write(board_description.squares)

# TODO: Error handling/response to user?
class UpdateCompletions(webapp.RequestHandler):
  def get(self):
    seed = _ParseSeed(self.request.get(_S))
    moves = _ParseMoves(self.request.get(_M))

    # Make sure someone is attempting to submit a valid completion
    if not (seed and moves):
      return

    self.response.out.write('%s %s' % (seed, moves))
    # Make sure there is a board description for this seed.
    board_description = _GetBoardDescription(seed)
    if not board_description:
      return

    # Play the submitted moves
    board = Board(14, seed)
    board.squares = board_description.squares
    board.PlaySequence(moves)
    self.response.out.write(board.IsFlooded())

    # If the board is flooded, update the recorded completions
    if board.IsFlooded():
      completions = _DeserializeCompletions(board_description.completions)
      self.response.out.write(completions)
      completions = _AddCompletion(len(moves), completions)
      board_description.completions = _SerializeCompletions(completions)
      board_description.put()


def main():
  application = webapp.WSGIApplication([('/', MainHandler),
                                        ('/GetNextBoard', GetNextBoard),
                                        ('/PlayGame', PlayGame),
                                        ('/UpdateCompletions', UpdateCompletions)],
                                       debug=False)
  util.run_wsgi_app(application)

if __name__ == '__main__':
  main()
