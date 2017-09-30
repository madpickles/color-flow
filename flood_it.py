#!/usr/bin/python

import sys
from random import Random
from board import Board
from operator import itemgetter
import math

def GenerateMovesAndState(original_board, move_sequences):
  new_move_sequences = []
  for move_sequence in move_sequences:
    if "board" in move_sequence and move_sequence["board"].IsFlooded():
      # The board is flooded. Don't add another move, just preserve it as is.
      new_move_sequences.append(move_sequence)
      continue
    for color in range(Board.NUM_COLORS):
      if "moves" in move_sequence:
        # Skip this color as it would be played twice in a row.
        if move_sequence["moves"][-1] == color:
          continue
        # Skip this color as it results in no progress.
        if not (Board.COLOR_CANDIDATE_MASK[color] &
                move_sequence["board"].next_color_candidates_mask):
          continue
        # Clone this board and the current moves.
        board = move_sequence["board"].Clone()
        moves = list(move_sequence["moves"])
      else:
        # Clone board as there are no existing moves.
        board = original_board.Clone()
        moves = []
      # Play another move.
      board.ChangeColor(color)
      moves.append(color)
      new_move_sequence = {}
      new_move_sequence["moves"] = moves
      new_move_sequence["board"] = board
      new_move_sequences.append(new_move_sequence)
  return new_move_sequences

def Metric(move_sequence):
  board = move_sequence["board"]
  if board.IsFlooded():
    # If the board is completely flooded, fewer moves are better.
    return 1 + (1 / float(board.turns))
  # More "endpoints" are better earlier since it means more candidate squares.
  metric = board.GetNumValidEndpoints() / float(board.turns)
  # More "endpoints" are also better when we've eliminated fewer colors.
  metric *= board.GetNumColorsRemaining()
  # Mmore squares flooded is always better.
  metric += board.GetNumFloodedSquares()
  # Reduce this to a number less than 1.
  metric /= board.num_squares * board.num_squares
  # Add a bonus based on the number of colors remaining, fewer is better.
  colors_remaining = float(board.GetNumColorsRemaining())
  metric += 1 - (colors_remaining / Board.NUM_COLORS)
  return metric

def SelectNext(board, num_sequences, move_sequences=[{}]):
  move_sequences = GenerateMovesAndState(board, move_sequences)
  max_metric = 0
  # Score the move sequences based on how "good" they are.
  for move_sequence in move_sequences:
    metric = Metric(move_sequence)
    if metric > max_metric:
      max_metric = metric
    move_sequence["metric"] = metric
  # Sort the moves sequences from best to worst.
  move_sequences.sort(key=itemgetter("metric"), reverse=True)
  return move_sequences[0:num_sequences]

def main(argv):
  r = Random(12345)
  num_games = int(argv[1])
  num_sequences = int(argv[2])
  games_played = 0
  while games_played < num_games:
    seed = r.randint(0, sys.maxint)
    results = str(seed)
    board = Board(14, seed)
    board.Generate()
    move_sequences = SelectNext(board, num_sequences)
    while not move_sequences[0]["board"].IsFlooded():
      move_sequences = SelectNext(board, num_sequences, move_sequences)
    turns = move_sequences[0]["board"].turns
    print move_sequences[0]["board"]
    results += ',' + str(turns)
    sys.stdout.write(results + '\n')
    sys.stdout.flush()
    games_played += 1

if __name__ == '__main__':
  main(sys.argv)
