# ---------- 1) Common circuit IR ----------
@dataclass
class Component:
    name: str        # e.g. "R1", "C1", "V1"
    ctype: str       # 'R','C','V','I','D', ...
    nodes: Tuple[str, str]  # (n1, n2)
    value: str       # '10k', '1uF', '5V', etc.

components = [
    Component(name='V1', ctype='V', nodes=('in', '0'), value='PULSE(0V 1V 0s 1us 1us 100ms 200ms)'),
    Component(name='R1', ctype='R', nodes=('in', '0'), value='1Ω'),
    Component(name='R2', ctype='R', nodes=('in', '0'), value='2Ω'),
    Component(name='R3', ctype='R', nodes=('in', '0'), value='3Ω'),
    Component(name='C1', ctype='C', nodes=('in', '0'), value='1µF'),
]
