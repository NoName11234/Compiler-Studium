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
        self.after[(bb.index, len(bb.instrs)-1)] = s.copy()

        for index, instruction in reversed(list(enumerate(bb.instrs))):
            variablesDefined = instrDef(instruction)
            variablesUsed = instrUse(instruction)
            variablesBefore = self.after[bb.index, index].copy()

            #remove defined variables
            for definedVariable in variablesDefined:
                if definedVariable in variablesBefore:
                    variablesBefore.remove(definedVariable)
            
            #add used variables
            for usedVariable in variablesUsed:
                variablesBefore.add(usedVariable)
            
            #add new set to the global dictionary before and after
            self.before[(bb.index, index)] = variablesBefore.copy()
            
            if index > 0:
                self.after[(bb.index, index-1)] = variablesBefore.copy()

        return self.before[(bb.index, 0)]

    def liveness(self, g: ControlFlowGraph):
        """
        This method computes liveness information and fills the sets self.before and
        self.after.

        You have to implement the algorithm for computing liveness in a CFG from
        slide 46 here.
        """
        #initialise before and after for the basic blocks
        for vertex in g.vertices:
            basicBlock = g.getData(vertex)
            if len(basicBlock.instrs) > 0:
                self.before[basicBlock.index, 0] = set()
                self.after[basicBlock.index, len(basicBlock.instrs)-1] = set()

        liveBeforeForBlocks: dict[int, set[tac.ident]] = {}

        while True:
            changeOccured = False

            for vertex in g.vertices:
                basicBlock = g.getData(vertex)

                if len(basicBlock.instrs) > 0:
                    #check whether liveBefore was already computed for successors -> these variables must be live at the end of this basic block
                    liveBeforeSuccessorsCombined: set[tac.ident] = set()

                    for successorVertex in g.succs(vertex):
                        #check whether there is a set of variables live at the beginning of successorVertex
                        if successorVertex in liveBeforeForBlocks:
                            for variable in liveBeforeForBlocks[successorVertex]:
                                liveBeforeSuccessorsCombined.add(variable)
                
                    #use liveStart for calculating set of variables live at the beginning of the block
                    liveBefore = self.liveStart(g.getData(vertex), liveBeforeSuccessorsCombined)

                    #add liveBefore to internal dictionary and check whether a change occured
                    if vertex in liveBeforeForBlocks:
                        if liveBeforeForBlocks[vertex] != liveBefore:
                            changeOccured = True
                            liveBeforeForBlocks[vertex] = liveBefore
                    else:
                        changeOccured = True
                        liveBeforeForBlocks[vertex] = liveBefore
            
            if not changeOccured:
                break



    def __addEdgesForInstr(self, instrId: InstrId, instr: tac.instr, interfG: InterfGraph):
        """
        Given an instruction and its ID, adds the edges resulting from the instruction
        to the interference graph.

        You should implement the algorithm specified on the slide
        "Computing the interference graph" (slide 50) here.
        """
        definedVariables = instrDef(instr)
        variablesUsedAfterInstruction = self.after[instrId]

        for definedVariable in definedVariables:
            for variableUsedAfter in variablesUsedAfterInstruction:
                if definedVariable != variableUsedAfter:
                    if not interfG.hasVertex(definedVariable):
                        interfG.addVertex(definedVariable, None)
                    
                    if not interfG.hasVertex(variableUsedAfter):
                        interfG.addVertex(variableUsedAfter, None)
                    
                    interfG.addEdge(definedVariable, variableUsedAfter)

    def build(self, g: ControlFlowGraph) -> InterfGraph:
        """
        This method builds the interference graph. It performs three steps:

        - Use liveness to fill the sets self.before and self.after.
        - Setup the interference graph as an undirected graph containing all variables
          defined or used by any instruction of any basic block. Initially, the
          graph does not have any edges.
        - Use __addEdgesForInstr to fill the edges of the interference graph.
        """
        interfGraph: InterfGraph = Graph('undirected')

        #fill sets before and after
        self.liveness(g)

        #fill the edges of the interference graph
        for vertex in g.vertices:
            basicBlock = g.getData(vertex)
            
            for index, instruction in enumerate(basicBlock.instrs):
                self.__addEdgesForInstr((basicBlock.index, index), instruction, interfGraph)

        print(self.before)
        print(self.after)

        return interfGraph


def buildInterfGraph(g: ControlFlowGraph) -> InterfGraph:
    builder = InterfGraphBuilder()
    return builder.build(g)
