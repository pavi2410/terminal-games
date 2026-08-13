import time

from blessed import Terminal
from blessed.keyboard import Keystroke

CRLF = "\r\n"


class Board[T]:
    grid: list[T | None]
    height: int
    width: int
    active: tuple[int, int]

    def __init__(self, width: int, height: int) -> None:
        self.height = height
        self.width = width
        self.grid = [None] * (height * width)
        self.active = (0, 0)

    def _pointer(self, i: int, j: int) -> int:
        return j * self.width + i

    def get(self, i: int, j: int) -> T | None:
        return self.grid[self._pointer(i, j)]

    def set(self, i: int, j: int, v: T | None):
        self.grid[self._pointer(i, j)] = v

    def update(self, x: int, y: int):
        self.active = (x, y)

    def _is_active(self, x: int, y: int):
        return (x, y) == self.active

    def render(self, term: Terminal) -> str:
        buf = ""
        for y in range(self.height):
            ibuf = ""
            for x in range(self.width):
                v = "@" if self._is_active(x, y) else " "
                D, B = term.dimgray, term.blue
                ibuf += f"{D}[{B}{v}{D}]"
            buf += term.center(ibuf) + CRLF
        return buf + term.normal


class RainbowText:
    text: str
    tick: int

    def __init__(self, text: str):
        self.text = text
        self.tick = 0

    def update(self):
        self.tick += 1

    def render(self, term: Terminal) -> str:
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
            buf += a + b + " "
        return term.center(buf) + term.normal + CRLF


def clamp(value: int, min_val: int, max_val: int):
    if value < min_val:
        return min_val
    elif value > max_val:
        return max_val
    return value


class Game:
    board: Board[int]
    x: int
    y: int
    heading: RainbowText
    running: bool

    def __init__(self) -> None:
        w, h = 5, 10
        self.x, self.y = w // 2, 0
        self.running = True
        self.board = Board(w, h)
        self.heading = RainbowText("TETRIS")

    def update(self, key: Keystroke):
        if key == "q":
            self.running = False
            return
        h, w = self.board.height, self.board.width
        match key.name:
            case "KEY_UP":
                self.y = clamp(self.y - 1, 0, h - 1)
            case "KEY_DOWN":
                self.y = clamp(self.y + 1, 0, h - 1)
            case "KEY_LEFT":
                self.x = clamp(self.x - 1, 0, w - 1)
            case "KEY_RIGHT":
                self.x = clamp(self.x + 1, 0, w - 1)
            case _:
                pass

        self.heading.update()
        self.board.update(self.x, self.y)

    def render(self, term: Terminal) -> str:
        buf = ""
        buf += self.heading.render(term)
        buf += self.board.render(term)
        return buf


def main():
    term = Terminal()
    with term.raw(), term.cbreak(), term.hidden_cursor(), term.fullscreen():
        FPS = 10
        g = Game()
        while g.running:
            print(term.home + term.clear, end="")
            print(g.render(term), end=CRLF)
            key = term.inkey(timeout=0)
            g.update(key)
            time.sleep(1 / FPS)


if __name__ == "__main__":
    main()
