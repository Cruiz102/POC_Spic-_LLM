import schemdraw
import schemdraw.elements as elm

with schemdraw.Drawing() as d:
    top = d.add(elm.Dot(open=True).label('n1'))

    d.push()
    d.add(elm.SourceV().down().label('V1 1V'))
    d.add(elm.Ground())
    d.pop()

    d += elm.Line().right().length(2)
    d.push()
    d.add(elm.Resistor().down().label('R1 1ohm'))
    d.add(elm.Ground())
    d.pop()

    d += elm.Line().right().length(2)
    d.push()
    d.add(elm.Resistor().down().label('R2 2ohm'))
    d.add(elm.Ground())
    d.pop()

    d += elm.Line().right().length(2)
    d.push()
    d.add(elm.Resistor().down().label('R3 3ohm'))
    d.add(elm.Ground())
    d.pop()

    d += elm.Line().right().length(2)
    d.push()
    d.add(elm.Resistor().down().label('R4 4ohm'))
    d.add(elm.Ground())
    d.pop()

    d += elm.Line().right().length(2)
    d.push()
    d.add(elm.Capacitor().down().label('C1 3uF'))
    d.add(elm.Ground())
    d.pop()

    d.save('circuit.png')