"""
CYBER TIC-TAC-TOE (Python + tkinter only)

SOURCES / CREDITS:
- Minimax algorithm: standard game-tree search (Wikipedia: "Minimax").
- tkinter GUI: https://docs.python.org/3/library/tkinter.html
- Sound: winsound.Beep (Python docs, Windows only).

KEYS: S = Start  P = Pause  X = Settings  C = Continue
"""
import tkinter as tk
import threading, queue, random, time

try:
    import winsound
except ImportError:
    winsound = None

LINES = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
BG, FG, DIM, RED, CY, PANEL = "#04100a", "#39ff88", "#1c7a45", "#ff3b5c", "#2de2ff", "#0a1f15"
MUSIC = [220, 330, 440, 330, 262, 392, 523, 392]


# ---------------- Audio ----------------
class Audio:
    def __init__(self, root):
        self.root = root
        self.q = queue.Queue()
        self.music_on = False
        self.sfx_on = True
        self.step = 0
        if winsound:
            threading.Thread(target=self._worker, daemon=True).start()
            threading.Thread(target=self._music, daemon=True).start()

    def _worker(self):
        while True:
            f, d = self.q.get()
            try:
                winsound.Beep(int(f), int(d))
            except Exception:
                pass

    def _music(self):
        while True:
            if self.music_on and self.q.empty():
                self.q.put((MUSIC[self.step % 8], 160))
                self.step += 1
            time.sleep(0.05)

    def sfx(self, notes):
        if not self.sfx_on:
            return
        if winsound:
            with self.q.mutex:
                self.q.queue.clear()
            for n in notes:
                self.q.put(n)
        else:
            self.root.bell()


# ---------------- Game ----------------
class Game:
    def __init__(self, root):
        self.root = root
        root.title("CYBER TIC-TAC-TOE")
        root.configure(bg=BG)
        root.resizable(False, False)
        self.audio = Audio(root)

        # settings variables
        self.mode = tk.StringVar(value="ai")      # ai / pvp
        self.side = tk.StringVar(value="X")       # human symbol
        self.diff = tk.IntVar(value=1)            # 0 easy, 1 medium, 2 hard
        self.twist = tk.BooleanVar(value=True)
        self.music = tk.BooleanVar(value=True)
        self.sfx = tk.BooleanVar(value=True)

        self.board = [""] * 9
        self.turn = "X"
        self.running = self.paused = self.over = False
        self.moves = 0
        self.twisted = False
        self.score = {"X": 0, "O": 0, "D": 0}
        self.ai_job = None
        self.win_win = None

        tk.Label(root, text="> CYBER TIC-TAC-TOE_", bg=BG, fg=FG,
                 font=("Courier New", 20, "bold")).pack(pady=(10, 0))
        self.status = tk.Label(root, text="Press S to start", bg=BG, fg=CY,
                               font=("Courier New", 12))
        self.status.pack()
        self.log = tk.Label(root, text="", bg=BG, fg=RED, font=("Courier New", 10))
        self.log.pack()

        grid = tk.Frame(root, bg=BG)
        grid.pack(padx=14, pady=8)
        self.cells = []
        for i in range(9):
            b = tk.Button(grid, text="", width=4, height=1, bg=PANEL, fg=FG,
                          activebackground="#0d3a22", font=("Courier New", 32, "bold"),
                          bd=2, relief="ridge", command=lambda i=i: self.click(i))
            b.grid(row=i // 3, column=i % 3, padx=4, pady=4)
            self.cells.append(b)

        bar = tk.Frame(root, bg=BG)
        bar.pack(pady=4)
        for txt, cmd in (("[S] Start", self.start), ("[P] Pause", self.pause),
                         ("[X] Settings", self.open_settings), ("[C] Continue", self.cont)):
            tk.Button(bar, text=txt, command=cmd, bg=PANEL, fg=FG, activebackground=FG,
                      font=("Courier New", 10)).pack(side="left", padx=4)

        self.score_lbl = tk.Label(root, bg=BG, fg=DIM, font=("Courier New", 10))
        self.score_lbl.pack(pady=(4, 10))

        root.bind_all("<Key>", self.on_key)
        self.render()

    # ----- keys -----
    def on_key(self, e):
        k = e.keysym.lower()
        if k == "s": self.start()
        elif k == "p": self.pause()
        elif k == "x": self.open_settings()
        elif k == "c": self.cont()

    # ----- helpers -----
    def is_ai(self, p):
        return self.mode.get() == "ai" and p != self.side.get()

    def set_status(self, t):
        self.status.config(text=t)

    def refresh_status(self):
        if self.over: return
        if self.paused: self.set_status("PAUSED - press C to continue")
        elif self.is_ai(self.turn): self.set_status("AI is hacking...")
        else: self.set_status("Turn: " + self.turn)

    def render(self, win=()):
        for i, v in enumerate(self.board):
            self.cells[i].config(text=v, fg=CY if v == "O" else FG,
                                 bg="#0d3a22" if i in win else PANEL)
        s = self.score
        self.score_lbl.config(text=f"X: {s['X']}  |  O: {s['O']}  |  Draws: {s['D']}")

    @staticmethod
    def winner(b):
        for l in LINES:
            a, c, d = l
            if b[a] and b[a] == b[c] == b[d]:
                return b[a], l
        return None

    # ----- flow -----
    def start(self):
        if self.ai_job: self.root.after_cancel(self.ai_job)
        self.close_settings(silent=True)
        self.board = [""] * 9
        self.turn, self.moves, self.twisted = "X", 0, False
        self.over, self.running, self.paused = False, True, False
        self.log.config(text="")
        self.audio.sfx_on = self.sfx.get()
        self.audio.music_on = self.music.get()
        self.render()
        self.refresh_status()
        self.maybe_ai()

    def pause(self):
        if not self.running or self.over or self.paused: return
        self.paused = True
        if self.ai_job: self.root.after_cancel(self.ai_job); self.ai_job = None
        self.audio.music_on = False
        self.refresh_status()

    def cont(self):
        if self.win_win:
            self.close_settings()
            return
        if self.running and self.paused:
            self.paused = False
            self.audio.music_on = self.music.get()
            self.refresh_status()
            self.maybe_ai()

    def click(self, i):
        if not self.running or self.paused or self.over or self.board[i]: return
        if self.is_ai(self.turn): return
        self.place(i)

    def place(self, i):
        self.board[i] = self.turn
        self.audio.sfx_on = self.sfx.get()
        self.audio.sfx([(660 if self.turn == "X" else 440, 80)])
        self.moves += 1
        self.render()
        if self.end_check(): return
        if self.twist.get() and not self.twisted and self.moves >= 4 and \
           (self.moves >= 6 or random.random() < 0.4):
            self.virus()
            if self.end_check(): return
        self.turn = "O" if self.turn == "X" else "X"
        self.refresh_status()
        self.maybe_ai()

    def virus(self):
        # PLOT TWIST: corrupt a random mark and flip it to the other side
        i = random.choice([k for k, v in enumerate(self.board) if v])
        self.board[i] = "O" if self.board[i] == "X" else "X"
        self.twisted = True
        self.audio.sfx([(random.randint(150, 1000), 50) for _ in range(6)])
        self.log.config(text=f"!! VIRUS BREACH: cell {i+1} corrupted, flipped to {self.board[i]} !!")
        self.render()
        self.cells[i].config(bg=RED)

    def end_check(self):
        w = self.winner(self.board)
        if w:
            p, line = w
            self.over, self.running = True, False
            self.score[p] += 1
            self.render(win=line)
            self.audio.music_on = False
            if self.is_ai(p): self.audio.sfx([(300, 200), (240, 200), (180, 300)])
            else: self.audio.sfx([(523, 120), (659, 120), (784, 120), (1047, 250)])
            self.set_status(f"ACCESS GRANTED: {p} wins! Press S to play again")
            return True
        if all(self.board):
            self.over, self.running = True, False
            self.score["D"] += 1
            self.render()
            self.audio.music_on = False
            self.audio.sfx([(330, 300)])
            self.set_status("DRAW - firewall holds. Press S to play again")
            return True
        return False

    # ----- AI -----
    def maybe_ai(self):
        if self.running and not self.paused and not self.over and self.is_ai(self.turn):
            self.ai_job = self.root.after(550, self.ai_move)

    def ai_move(self):
        self.ai_job = None
        if not self.running or self.paused or self.over: return
        free = [i for i, v in enumerate(self.board) if not v]
        d = self.diff.get()
        if d == 0 or (d == 1 and random.random() < 0.5):
            self.place(random.choice(free))
            return
        me = self.turn
        best, moves = -99, []
        for i in free:
            self.board[i] = me
            s = self.minimax(self.board, "O" if me == "X" else "X", me)
            self.board[i] = ""
            if s > best: best, moves = s, [i]
            elif s == best: moves.append(i)
        self.place(random.choice(moves))

    def minimax(self, b, p, me):
        w = self.winner(b)
        if w: return 10 if w[0] == me else -10
        free = [i for i, v in enumerate(b) if not v]
        if not free: return 0
        scores = []
        for i in free:
            b[i] = p
            scores.append(self.minimax(b, "O" if p == "X" else "X", me))
            b[i] = ""
        return max(scores) if p == me else min(scores)

    # ----- settings -----
    def open_settings(self):
        if self.win_win: return
        if self.running: self.pause()
        w = self.win_win = tk.Toplevel(self.root)
        w.title("Settings")
        w.configure(bg=PANEL)
        w.transient(self.root)
        w.protocol("WM_DELETE_WINDOW", self.close_settings)
        tk.Label(w, text="> SETTINGS", bg=PANEL, fg=FG, font=("Courier New", 14, "bold")).pack(pady=6)

        def group(title, var, options):
            tk.Label(w, text=title, bg=PANEL, fg=CY, font=("Courier New", 10)).pack(anchor="w", padx=12)
            for txt, val in options:
                tk.Radiobutton(w, text=txt, variable=var, value=val, bg=PANEL, fg=FG,
                               selectcolor=BG, activebackground=PANEL, activeforeground=FG,
                               font=("Courier New", 10)).pack(anchor="w", padx=24)

        group("Mode", self.mode, [("1 Player (vs AI)", "ai"), ("2 Players", "pvp")])
        group("Play as", self.side, [("X", "X"), ("O", "O")])
        group("Difficulty", self.diff, [("Script Kiddie (easy)", 0),
                                        ("Pentester (medium)", 1),
                                        ("Elite Hacker (hard)", 2)])
        for txt, var in (("Plot twist: virus breach", self.twist),
                         ("Music", self.music), ("Sound effects", self.sfx)):
            tk.Checkbutton(w, text=txt, variable=var, bg=PANEL, fg=FG, selectcolor=BG,
                           activebackground=PANEL, activeforeground=FG,
                           font=("Courier New", 10)).pack(anchor="w", padx=12)
        tk.Button(w, text="[C] Apply & continue", command=self.close_settings, bg=BG, fg=FG,
                  font=("Courier New", 10)).pack(pady=10)

    def close_settings(self, silent=False):
        if not self.win_win: return
        self.win_win.destroy()
        self.win_win = None
        self.audio.sfx_on = self.sfx.get()
        if silent: return
        if self.running and self.paused:
            self.paused = False
            self.audio.music_on = self.music.get()
            self.refresh_status()
            self.maybe_ai()


if __name__ == "__main__":
    root = tk.Tk()
    Game(root)
    root.mainloop()
