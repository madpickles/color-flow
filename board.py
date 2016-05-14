from random import Random
from operator import itemgetter

class Board:

  NUM_COLORS = 6
  NUM_COLORS_FOR_RAND = NUM_COLORS - 1
  BOARD_SET = None
  COLOR_CANDIDATE_MASK = [0x000001, 0x000010, 0x000100, 0x001000, 0x010000, 0x100000]
  NEIGHBORS = {}

  def __init__(self, size, seed):
    # These variables should not change after construction
    self.size = size
    self.num_squares = size * size
    self.seed = seed
    # These variables only need to be initialized once.
    if not Board.BOARD_SET:
      Board.BOARD_SET = set([i for i in range(self.num_squares)])
    if not Board.NEIGHBORS:
      for i in range(self.num_squares):
        Board.NEIGHBORS[i] = self._GenerateNeighborList(i)
    # These variables get mutated during play.
    self.next_color_candidates_mask = 0x111111
    self.valid_endpoints = set([0])
    self.flooded = set()
    self.squares = []
    self.turns = 0

  def PlaySequence(self, moves):
    for color in moves:
      self.ChangeColor(color)

  def IsFlooded(self):
    return len(self.flooded) == self.num_squares

  def GetNumFloodedSquares(self):
    return len(self.flooded)

  def GetNumValidEndpoints(self):
    return len(self.valid_endpoints);

  def GetNumColorsRemaining(self):
    colors = 0
    not_flooded = Board.BOARD_SET.difference(self.flooded)
    color_candidates_mask = 0x000000
    for i in not_flooded:
      # All colors remain, stop looking.
      if colors == Board.NUM_COLORS:
        break
      color_mask = Board.COLOR_CANDIDATE_MASK[self.squares[i]]
      # Add color to candidates and increment count if necessary.
      if not color_mask & color_candidates_mask:
        color_candidates_mask |= color_mask
        colors += 1
    return colors

  def Clone(self):
    board = Board(self.size, self.seed)
    board.next_color_candidates_mask = self.next_color_candidates_mask
    board.turns = self.turns
    board.squares = list(self.squares)
    board.valid_endpoints = set(self.valid_endpoints)
    board.flooded = set(self.flooded)
    return board

  def _GenerateNeighborList(self, i):
    x = i % self.size
    y = i / self.size
    end = self.size - 1
    neighbors = []
    if i > self.size:  # There's a square above this one
      neighbors.append(i - self.size)
    if x != end:  # There's a square to the right of this one
      neighbors.append(i + 1)
    if y != end:  # There's a square below this one
      neighbors.append(i + self.size)
    if x != 0:  # There's a square to the left of this one
      neighbors.append(i - 1)
    return neighbors

  def Generate(self):
    r = Random(self.seed)
    self.squares = []
    for i in range(self.num_squares):
      color = r.randint(0, Board.NUM_COLORS_FOR_RAND)
      self.squares.append(color)

  def ChangeColor(self, color):
    neighbor_endpoints = {}  # Candidates for next iteration of valid_endpoints.
    # Go through valid_endpoints (initially [0]) and propogate color change.
    self._ChangeColorSet(self.valid_endpoints, color, neighbor_endpoints)

    # Count the number of times an endpoint is linked to a neighbor.
    endpoint_counts = {}
    for neighbor, endpoints in neighbor_endpoints.iteritems():
      for endpoint in endpoints:
        endpoint_counts[endpoint] = endpoint_counts.get(endpoint, 0) + 1

    # Collect the next color candidates and the smallest set of endpoints which
    # will link to all the neighbors
    color_candidates_mask = 0x000000
    valid_endpoints = set()
    for neighbor, endpoints in neighbor_endpoints.iteritems():
      color_candidates_mask |= Board.COLOR_CANDIDATE_MASK[self.squares[neighbor]]
      max_endpoint = 0
      for endpoint in endpoints:
        if endpoint_counts[endpoint] > max_endpoint:
          max_endpoint = endpoint
      valid_endpoints.add(max_endpoint)
    self.next_color_candidates_mask = color_candidates_mask
    self.valid_endpoints = valid_endpoints

    # Increment # of turns.
    self.turns += 1

  def _ChangeColorSet(self, squares, color, neighbor_endpoints):
    self.flooded.update(squares)
    squares_to_flood = set()
    for i in squares:
      square_color = self.squares[i]
      for neighbor in Board.NEIGHBORS[i]:
        if neighbor in self.flooded:
          continue
        neighbor_color = self.squares[neighbor]
        # Continue flooding neighbor as it's the same color as i used to be or
        # Continue flooding neighber as it's already the flooded color
        if (neighbor_color == square_color or
            neighbor_color == color):
          squares_to_flood.add(neighbor)
        # we're at an endpoint i where this neighbor's color differs
        # from that of i and is not the new color
        elif neighbor in neighbor_endpoints:
          neighbor_endpoints[neighbor].append(i)
        else:
          neighbor_endpoints[neighbor] = [i]
    # Still work to do...
    if squares_to_flood:
      self._ChangeColorSet(squares_to_flood, color, neighbor_endpoints)

  def __repr__(self):
    return str(self.squares)

  def __str__(self):
    s = ""
    for i in range(self.num_squares):
      if i and i % self.size == 0:
        s += "\n"
      if i in self.flooded:
        s += "X"
      else:
        s += str(self.squares[i])
    s += "\n"
    return s
