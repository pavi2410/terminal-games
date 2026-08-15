import itertools
import random
import time
from enum import Enum, auto
from typing import cast

from blessed import Terminal
from blessed.keyboard import Keystroke

type Size = tuple[int, int]
type Mat[T] = list[list[T]]
type Shape = Mat[int]
type Coord = tuple[int, int]
type Buffer = list[str]
type Cell = tuple[str, str]


CRLF = "\r\n"
FPS = 10
GRID_SIZE: Size = 10, 20
ORIGIN: Coord = 0, 0


SHAPES: list[Shape] = [
    [[1, 1, 0], [0, 1, 1]],
    [[1, 1, 1, 1]],
    [[1, 1], [1, 1]],
    [[1, 0], [1, 0], [1, 1]],
    [[1, 0, 1], [1, 1, 1]],
]
SYMBOLS = "#@X0"
COLORS = ["red", "orange", "yellow", "green", "blue", "violet"]

DIRS = {
    "KEY_UP": (0, -1),
    "KEY_DOWN": (0, 1),
    "KEY_LEFT": (-1, 0),
    "KEY_RIGHT": (1, 0),
}

game_instance: Game | None = None

GAME_OVER_EVENT = "_game-event::gameover"


def new_mat[T](size: Size, default: T) -> Mat[T]:
    M, N = size
    return [[default for _ in range(M)] for _ in range(N)]


def clamp(value: int, min_val: int, max_val: int) -> int:
    if value < min_val:
        return min_val
    elif value > max_val:
        return max_val
    return value


class Piece:
    shape: Shape
    pos: Coord
    cell: Cell

    def __init__(self, shape: Shape, pos: Coord, cell: Cell):
        self.shape = shape
        self.pos = pos
        self.cell = cell

    def rotate_cw(self) -> Piece:
        M, N = len(self.shape), len(self.shape[0])
        new_shape = [[self.shape[M - 1 - x][y] for x in range(M)] for y in range(N)]
        return Piece(new_shape, self.pos, self.cell)

    def size(self) -> Size:
        s = self.shape
        M, N = len(s), len(s[0])
        return M, N

    def abs_cell_coords(self) -> list[Coord]:
        s = self.shape
        x, y = self.pos
        M, N = self.size()
        return [
            (x + dx, y + dy) for dx in range(M) for dy in range(N) if s[dx][dy] != 0
        ]

    def top_edge_cells(self, y_offset: int = 0) -> list[Coord]:
        cells = self.abs_cell_coords()
        return [
            (k, min(g, key=lambda c: c[1])[1] + y_offset)
            for k, g in itertools.groupby(cells, lambda c: c[0])
        ]

    def bottom_edge_cells(self, y_offset: int = 0) -> list[Coord]:
        cells = self.abs_cell_coords()
        return [
            (k, max(g, key=lambda c: c[1])[1] + y_offset)
            for k, g in itertools.groupby(cells, lambda c: c[0])
        ]


class Board:
    grid: Mat[Cell | None]
    size: Size
    cur_piece: Piece
    _last_time: float

    def __init__(self, size: Size) -> None:
        self.size = size
        self.grid = new_mat(size, None)
        self._last_time = time.perf_counter()
        self._spawn_piece()

    def _move_piece(self, dir: Coord):
        w, h = self.size
        pw, ph = self.cur_piece.size()
        ew, eh = w - pw, h - ph
        x, y = self.cur_piece.pos
        dx, dy = dir
        x = clamp(x + dx, 0, ew)
        y = clamp(y + dy, 0, eh)
        self.cur_piece.pos = x, y

    def _fall_piece(self):
        dir = DIRS["KEY_DOWN"]
        self._move_piece(dir)

    def _is_colliding(self) -> bool:
        # bottom edge cells of the current piece
        # select the cells whose y is max
        cpc_bottom = set(self.cur_piece.bottom_edge_cells(1))

        w, h = self.size
        # coords of the board floor
        floor_cells = [(x, h) for x in range(w)]
        # coords of all the placed cells
        filled_cells = [(x, y) for x in range(w) for y in range(h) if self.grid[y][x]]
        bound_cells = set(floor_cells + filled_cells)

        # check overlap
        return not cpc_bottom.isdisjoint(bound_cells)

    def _check_row_filled(self) -> int | None:
        for y, row in enumerate(self.grid):
            # all cells in rows are filled
            if all(row):
                return y
        return None

    def _eat_cells_in_row(self, row: int):
        w, _ = self.size
        # move cells downward bottom-up
        for y in reversed(range(row)):
            self.grid[y + 1] = self.grid[y]
        self.grid[0] = [None] * w

    def update(self, key: Keystroke):
        # check if top reached
        if any(self.grid[0]):
            return GAME_OVER_EVENT

        # at every tick (each update call)
        now = time.perf_counter()
        dt = now - self._last_time
        # self._last_time = now

        # more than a second has passed
        if dt >= 1:
            self._last_time = now
            self._fall_piece()

        if self._is_colliding():
            self._place_piece()

        if row := self._check_row_filled():
            self._eat_cells_in_row(row)

        if key == " ":
            self.cur_piece = self.cur_piece.rotate_cw()
            return

        if key.name and (dir := DIRS.get(key.name)):
            self._move_piece(dir)

    def _spawn_piece(self):
        shape = random.choice(SHAPES)
        sym = random.choice(SYMBOLS)
        color = random.choice(COLORS)
        w, _ = self.size
        pos = w // 2, 0
        cell = (sym, color)
        p = Piece(shape, pos, cell)
        self.cur_piece = p

    def _place_piece(self):
        p = self.cur_piece
        for x, y in p.abs_cell_coords():
            self.grid[y][x] = p.cell
        self._spawn_piece()

    def _is_cell(self, x: int, y: int) -> Cell | None:
        coord = x, y
        cp = self.cur_piece
        if coord in cp.abs_cell_coords():
            return cp.cell
        if cell := self.grid[y][x]:
            return cell
        return None

    def render(self, term: Terminal) -> Buffer:
        W, H = self.size
        buf = [""] * H
        for y in range(H):
            ibuf = ""
            for x in range(W):
                D = term.dimgray
                if cell := self._is_cell(x, y):
                    s, c = cell
                    c = cast(str, getattr(term, c))
                    ibuf += f"{D}[{c}{s}{D}]"
                else:
                    ibuf += f"{D}[ ]"
            buf[y] = term.center(ibuf)
        return buf


class AnimtedText:
    text: str
    space: int
    colors: list[str]
    colorwidth: int
    _tick: int
    _is_animating: bool

    def __init__(
        self, text: str, space: int = 0, colors: list[str] = COLORS, colorwidth: int = 1
    ):
        self.text = text
        self.space = space
        self.colors = colors
        self.colorwidth = colorwidth
        self._tick = 0
        self._is_animating = True

    def animate(self, value: bool):
        self._is_animating = value

    def update(self):
        if self._is_animating:
            self._tick += 1

    def render(self, term: Terminal) -> Buffer:
        buf = rainbow_text(
            term, self.text, self.colors, self.colorwidth, self.space, self._tick
        )
        return [term.center(buf) + term.normal]


def rainbow_text(
    term: Terminal,
    text: str,
    colors: list[str] = COLORS,
    colorwidth: int = 1,
    space: int = 0,
    tick: int = 0,
) -> str:
    buf = ""
    N = len(colors)
    CW = colorwidth or 1
    base = tick % N
    for i, b in enumerate(text):
        k = (-base + i) // CW % N
        a = cast(str, getattr(term, colors[k]))
        buf += a + b + (" " * space)
    return buf


class GameState(Enum):
    RUNNING = auto()
    QUIT = auto()
    PAUSED = auto()
    OVER = auto()


class Game:
    board: Board
    heading: AnimtedText
    line: AnimtedText
    state: GameState

    def __init__(self) -> None:
        self.state = GameState.RUNNING
        self.board = Board(GRID_SIZE)

        s = "★"
        grid_w, _ = GRID_SIZE
        cell_w = 3
        self.heading = AnimtedText(s + "TETRIS".center(grid_w) + s, space=1)
        self.line = AnimtedText("─" * grid_w * cell_w, colorwidth=1)

    def update(self, key: Keystroke):
        match key:
            case "q":
                self.state = GameState.QUIT
                return
            case "p":
                if self.state == GameState.PAUSED:
                    self.state = GameState.RUNNING
                    self.line.animate(True)
                else:
                    self.state = GameState.PAUSED
                    self.line.animate(False)
            case "r":
                global game_instance
                game_instance = Game()
            case _:
                pass

        self.heading.update()
        self.line.update()
        if self.state not in (GameState.PAUSED, GameState.OVER):
            e = self.board.update(key)
            if e == GAME_OVER_EVENT:
                self.state = GameState.OVER

    def render(self, term: Terminal) -> Buffer:
        renderables = [
            self.line,
            self.heading,
            self.line,
            self.board,
            self.line,
        ]
        return [CRLF.join(r.render(term)) for r in renderables]


def main():
    term = Terminal()
    print(term.center(rainbow_text(term, "TETRIS!")))
    with term.raw(), term.cbreak(), term.hidden_cursor(), term.fullscreen():
        global game_instance
        game_instance = Game()
        frame_dur = 1 / FPS
        while game_instance.state != GameState.QUIT:
            print(term.home + term.clear, end="")
            buf = CRLF.join(game_instance.render(term))
            print(buf, end=CRLF)
            key = term.inkey(timeout=0)
            game_instance.update(key)
            time.sleep(frame_dur)


if __name__ == "__main__":
    main()
