"""Salida de terminal para la demo (ANSI, sin dependencias)."""
import sys, textwrap, time

CODES = {"red": "31", "green": "32", "yellow": "33", "blue": "34", "magenta": "35",
         "cyan": "36", "gray": "90", "bold": "1", "dim": "2"}
DECISION_COLOR = {"ALLOW": "green", "DENY": "red", "REQUIRE_APPROVAL": "yellow"}
LEVEL_COLOR = {"LOW": "green", "MEDIUM": "yellow", "HIGH": "red", "CRITICAL": "red"}
STATUS_ICON = {"PASS": ("✔", "green"), "FAIL": ("✘", "red"), "APPROVAL": ("⚠", "yellow"), "SKIP": ("·", "gray")}


class UI:
    def __init__(self, color=True, delay=0.0, step=False):
        self.color = color and sys.stdout.isatty() or color == "force"
        self.delay, self.stepmode = delay, step

    def c(self, text, *styles):
        if not self.color:
            return str(text)
        return "\033[" + ";".join(CODES[s] for s in styles) + "m" + str(text) + "\033[0m"

    def out(self, text="", indent=0):
        print(" " * indent + text)
        if self.delay:
            time.sleep(self.delay)

    def pause(self, msg="Enter para continuar"):
        if self.stepmode:
            input(self.c(f"\n   ▸ {msg}...", "gray"))

    def banner(self, num, title, tag, proves):
        bar = "═" * 74
        self.out()
        self.out(self.c(bar, "cyan"))
        self.out(self.c(f"  DEMO {num:02d} — {title}", "bold", "cyan") + "   " + self.c(f"[{tag}]", "yellow"))
        self.out(self.c(f"  Demuestra: {proves}", "gray"))
        self.out(self.c(bar, "cyan"))
        self.pause()

    def step(self, n, text):
        self.out()
        self.out(self.c(f" {n}  ", "bold", "blue") + self.c(text, "bold"))

    def note(self, text, indent=5):
        for ln in textwrap.wrap(text, 84 - indent):
            self.out(self.c(ln, "gray"), indent)

    def kv(self, k, v, indent=5, vcolor=None):
        label = self.c(f"{k}:".ljust(18), "gray")
        self.out(f"{label} {self.c(v, vcolor) if vcolor else v}", indent)

    def col(self, text, width, *styles):
        """Rellena y luego colorea (el relleno ignora los códigos ANSI)."""
        t = str(text).ljust(width)
        return self.c(t, *styles) if styles else t

    def badge(self, decision):
        col = DECISION_COLOR.get(decision, "gray")
        return self.c(f" {decision} ", "bold", col)

    def level(self, level):
        return self.c(level, "bold", LEVEL_COLOR.get(level, "gray"))

    def rules(self, rules, indent=5):
        for r in rules:
            icon, col = STATUS_ICON[r.status]
            self.out(f"{self.c(icon, col)} {self.c(f'{r.rule:<20}', 'bold')} {self.c(r.detail, col if r.status != 'PASS' else 'gray')}", indent)

    def decision(self, d, indent=5):
        self.rules(d.rules, indent)
        codes = ("  " + self.c(", ".join(d.codes), "gray")) if d.codes else ""
        self.out()
        self.out(f"DECISION ▸{self.badge(d.decision)}{codes}", indent)
        if d.hold_id:
            self.out(f"hold_id  ▸ {self.c(d.hold_id, 'bold', 'yellow')}  (ligado a proposal {d.proposal_hash[:12]}…)", indent)
        if d.permit:
            self.out(f"permit   ▸ {self.c(d.permit['permit_id'], 'bold', 'green')}  tool={d.permit['tool']}  "
                     f"args_hash={d.permit['args_hash'][:12]}…  uses={d.permit['uses']}", indent)
