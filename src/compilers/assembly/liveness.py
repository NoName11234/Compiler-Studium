from assembly.common import *
from assembly.graph import Graph
import assembly.tac_ast as tac

def instrDef(instr: tac.instr) -> set[tac.ident]:
    """
    Returns the set of identifiers defined by some instrucution.
    """
    match instr:
        case tac.Assign(var, _):
            return set([var])
        case tac.Call(var, _, _):
            if var == None:
                return set([])
            else:
                return set([var])
        case tac.GotoIf(_, _):
            return set([])
        case tac.Goto(_):
            return set([])
        case tac.Label(_):
            return set([])

        

def instrUse(instr: tac.instr) -> set[tac.ident]:
    """
    Returns the set of identifiers used by some instrucution.
    """
    match instr:
        case tac.Assign(_, exp):
            return instrUseExp(exp)
        case tac.Call(var, _, args):
            returnSet:set[tac.ident] = set([])

            for arg in args:
                match arg:
                    case tac.Name(var):
                        returnSet.add(var)
                    case _:
                        pass

            return returnSet
        case tac.GotoIf(test, _):
            match test:
                case tac.Name(var):
                    return set([var])        
                case _:
                    return set([])
        case tac.Goto(_):
            return set([])
        case tac.Label(_):
            return set([])
        
def instrUseExp(exp: tac.exp) -> set[tac.ident]:
    match exp:
        case tac.Prim(p):
            match p:
                case tac.Name(var):
                    return set([var])
                case tac.Const(_):
                    return set([])
        case tac.BinOp(left, _, right):
            returnSet:set[tac.ident] = set([])

            match left:
                case tac.Name(var):
                    returnSet.add(var)
                case tac.Const(_):
                    pass
            
            match right:
                case tac.Name(var):
                    returnSet.add(var)
                case tac.Const(_):
                    pass

            return returnSet

# Each individual instruction has an identifier. This identifier is the tuple
# (index of basic block, index of instruction inside the basic block)
type InstrId = tuple[int, int]

class InterfGraphBuilder:
    def __init__(self):
        # self.before holds, for each instruction I, to set of variables live before I.
        self.before: dict[InstrId, set[tac.ident]] = {}
        # self.after holds, for each instruction I, to set of variables live after I.
        self.after: dict[InstrId, set[tac.ident]] = {}

    def liveStart(self, bb: BasicBlock, s: set[tac.ident]) -> set[tac.ident]:
        """
        Given a set of variables s and a basic block bb, liveStart computes
        the set of variables live at the beginning of bb, assuming that s
        are the variables live at the end of the block.

        Essentially, you have to implement the subalgorithm "Computing L_start" from
        slide 46 here. You should update self.after and self.before while traversing
        the instructions of the basic block in reverse.
        """
        raise ValueError('todo')

    def liveness(self, g: ControlFlowGraph):
        """
        This method computes liveness information and fills the sets self.before and
        self.after.

        You have to implement the algorithm for computing liveness in a CFG from
        slide 46 here.
        """
        raise ValueError('todo')

    def __addEdgesForInstr(self, instrId: InstrId, instr: tac.instr, interfG: InterfGraph):
        """
        Given an instruction and its ID, adds the edges resulting from the instruction
        to the interference graph.

        You should implement the algorithm specified on the slide
        "Computing the interference graph" (slide 50) here.
        """
        raise ValueError('todo')

    def build(self, g: ControlFlowGraph) -> InterfGraph:
        """
        This method builds the interference graph. It performs three steps:

        - Use liveness to fill the sets self.before and self.after.
        - Setup the interference graph as an undirected graph containing all variables
          defined or used by any instruction of any basic block. Initially, the
          graph does not have any edges.
        - Use __addEdgesForInstr to fill the edges of the interference graph.
        """
        raise ValueError('todo')

def buildInterfGraph(g: ControlFlowGraph) -> InterfGraph:
    builder = InterfGraphBuilder()
    return builder.build(g)
