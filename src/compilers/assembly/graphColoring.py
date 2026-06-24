from assembly.common import *
import assembly.tac_ast as tac
import common.log as log
from common.prioQueue import PrioQueue

def chooseColor(x: tac.ident, forbidden: dict[tac.ident, set[int]]) -> int:
    """
    Returns the lowest possible color for variable x that is not forbidden for x.
    """
    forbiddenColors = forbidden[x]

    color:int = 0

    while True:
        if color in forbiddenColors:
            color = color + 1
        else:
            break
    
    return color

def colorInterfGraph(g: InterfGraph, secondaryOrder: dict[tac.ident, int]={},
                     maxRegs: int=MAX_REGISTERS) -> RegisterMap:
    """
    Given an interference graph, computes a register map mapping a TAC variable
    to a TACspill variable. You have to implement the "simple graph coloring algorithm"
    from slide 58 here.

    - Parameter maxRegs is the maximum number of registers we are allowed to use.
    - Parameter secondaryOrder is used by the tests to get deterministic results even
      if two variables have the same number of forbidden colors.
    """
    log.debug(f"Coloring interference graph with maxRegs={maxRegs}")
    colors: dict[tac.ident, int] = {}
    forbidden: dict[tac.ident, set[int]] = {}
    queue = PrioQueue(secondaryOrder)
    
    #initialise queue and dictionary for forbidden colors
    for vertex in g.vertices:
        forbidden[vertex] = set()
        queue.push(vertex, 0)
    

    while not queue.isEmpty():
        nextVertex = queue.pop()
        color = chooseColor(nextVertex, forbidden)
        colors[nextVertex] = color

        #get connected vertices of vertex for updating forbidden colors
        succeccors = g.succs(nextVertex)

        for succeccor in succeccors:
            forbidden[succeccor].add(color)
            queue.incPrio(succeccor, 1)

    m = RegisterAllocMap(colors, maxRegs)
    return m
