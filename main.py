import random
import time

from blessed import Terminal
from blessed.keyboard import Keystroke

type Size = tuple[int, int]
type Mat[T] = list[list[T]]
type Shape = Mat[int]
type Coord = tuple[int, int]
type Buffer = list[str]


CRLF = "\r\n"
FPS = 10
GRID_SIZE: Size = 5, 10
ORIGIN: Coord = 0, 0


SHAPES: list[Shape] = [
    [[1, 1, 0], [0, 1, 1]],
    [[1, 1, 1, 1]],
    [[1, 1], [1, 1]],
    [[1, 0], [1, 0], [1, 1]],
    [[1, 0, 1], [1, 1, 1]],
]
SYMBOLS = "#@X0"


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
    sym: str
    color: str

    def __init__(self, shape: list[list[int]], pos: Coord, sym: str, color: str):
        self.shape = shape
        self.pos = pos
        self.sym = sym
        self.color = color

    def rotate_cw(self) -> Piece:
        M, N = len(self.shape), len(self.shape[0])
        new_shape = [[self.shape[M - 1 - x][y] for x in range(M)] for y in range(N)]
        return Piece(new_shape, self.pos, self.sym, self.color)

    def size(self) -> Size:
        s = self.shape
        M, N = len(s), len(s[0])
        return M, N

    def cells(self) -> list[Coord]:
        s = self.shape
        x, y = self.pos
        M, N = len(s), len(s[0])
        return [
            (x + dx, y + dy) for dx in range(M) for dy in range(N) if s[dx][dy] != 0
        ]

    def render(self, term: Terminal) -> Buffer:
        M, N = self.size()
        buf = [""] * M
        for x in range(M):
            for y in range(N):
                v = self.shape[x][y]
                c = term.red("#") if v != 0 else "."
                buf[x] += c
        return buf


class Board[T]:
    grid: Mat[T | None]
    size: Size
    cur_piece: Piece
    placed_pieces: list[Piece]

    def __init__(self, size: Size) -> None:
        self.size = size
        self.grid = new_mat(size, None)
        self.placed_pieces = []
        self._spawn_piece()

    def get(self, i: int, j: int) -> T | None:
        return self.grid[i][j]

    def set(self, i: int, j: int, v: T | None):
        self.grid[i][j] = v

    def update(self, key: Keystroke):
        if key == " ":
            self.cur_piece = self.cur_piece.rotate_cw()
            return

        w, h = self.size
        pw, ph = self.cur_piece.size()
        ew, eh = w - pw, h - ph
        x, y = self.cur_piece.pos
        match key.name:
            case "KEY_UP":
                y = clamp(y - 1, 0, eh)
            case "KEY_DOWN":
                y = clamp(y + 1, 0, eh)
            case "KEY_LEFT":
                x = clamp(x - 1, 0, ew)
            case "KEY_RIGHT":
                x = clamp(x + 1, 0, ew)
            case _:
                pass
        self.cur_piece.pos = x, y

    def _spawn_piece(self):
        shape = random.choice(SHAPES)
        sym = random.choice(SYMBOLS)
        w, _ = self.size
        pos = w // 2, 0
        p = Piece(shape, pos, sym, "")
        self.cur_piece = p

    def _place_piece(self):
        p = self.cur_piece
        self.placed_pieces.append(p)
        self._spawn_piece()

    def _is_piece(self, x: int, y: int) -> Piece | None:
        if (x, y) in self.cur_piece.cells():
            return self.cur_piece
        return None

    def render(self, term: Terminal) -> Buffer:
        W, H = self.size
        buf = [""] * H
        for y in range(H):
            ibuf = ""
            for x in range(W):
                v = p.sym if (p := self._is_piece(x, y)) else " "
                D, B = term.dimgray, term.blue
                ibuf += f"{D}[{B}{v}{D}]"
            buf[y] = term.center(ibuf)
        return buf


class RainbowText:
    text: str
    space: int
    tick: int

    def __init__(self, text: str, space: int = 0):
        self.text = text
        self.space = space
        self.tick = 0

    def update(self):
        self.tick += 1

    def render(self, term: Terminal) -> Buffer:
        colors = [
            term.bright_red,
            term.bright_orange,
            term.bright_yellow,
            term.bright_green,
            term.bright_blue,
            term.bright_violet,
        ]

        buf = ""
        N = len(colors)
        base = self.tick % N
        for i, b in enumerate(self.text):
            k = (-base + i) % N
            a = colors[k]
            buf += a + b + (" " * self.space)
        return [term.center(buf) + term.normal]


class Game:
    board: Board[int]
    heading: RainbowText
    line: RainbowText
    running: bool

    def __init__(self) -> None:
        self.running = True
        self.board = Board(GRID_SIZE)
        self.heading = RainbowText("★TETRIS★", space=1)
        self.line = RainbowText("─" * 15)

    def update(self, key: Keystroke):
        if key == "q":
            self.running = False
            return

        self.heading.update()
        self.line.update()
        self.board.update(key)

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
    with term.raw(), term.cbreak(), term.hidden_cursor(), term.fullscreen():
        g = Game()
        while g.running:
            print(term.home + term.clear, end="")
            buf = CRLF.join(g.render(term))
            print(buf, end=CRLF)
            key = term.inkey(timeout=0)
            g.update(key)
            time.sleep(1 / FPS)


if __name__ == "__main__":
    main()
