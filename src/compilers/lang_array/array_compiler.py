from lang_array.array_astAtom import *
import lang_array.array_ast as plainAst
from common.wasm import *
from common.symtab import VarInfo
import lang_array.array_tychecker as array_tychecker
import lang_array.array_transform as array_transform
from lang_array.array_compilerSupport import *
from common.compilerSupport import *
import common.utils as utils

def compileModule(m: plainAst.mod, cfg: CompilerConfig) -> WasmModule:
    """
    Compiles the given module.
    """
    vars = array_tychecker.tycheckModule(m)
    stmts = array_transform.transStmts(m.stmts, array_transform.Ctx())
    instrs = compileStmts(stmts, cfg)
    idMain = WasmId('$main')
    locals: list[tuple[WasmId, WasmValtype]] = [createLocals(ident, type) for (ident, type) in vars.items()]
    return WasmModule(imports=wasmImports(cfg.maxMemSize),
        exports=[WasmExport("main", WasmExportFunc(idMain))],
        globals= Globals.decls(),
        data= Errors.data(),
        funcTable=WasmFuncTable([]),
        funcs=[WasmFunc(idMain, [], None, locals + Locals.decls(), instrs)])

def createLocals(ident: ident, type: VarInfo[ty]) -> tuple[WasmId, WasmValtype]:
    wasmId = identToWasmId(ident)
    
    match type.ty:
        case Int():
            return (wasmId, 'i64')
        case Bool():
            return (wasmId, 'i32')
        case Array():
            return (wasmId, 'i32')

def identToWasmId(x: ident) -> WasmId:
    return WasmId("$" + x.name)

def tyOfExp(exp:exp) -> ty:
    if exp.ty is None:
        raise Exception(f'Expression {exp} is of type None')
    match exp.ty:
        case Void():
            raise Exception(f'Expression {exp} is Void')
        case NotVoid(type):
            return type

def tyOfAtomExp(atomExp: atomExp) -> ty:
    if atomExp.ty is None:
        raise Exception(f'Atomic expression {atomExp} is of type None')
    
    return atomExp.ty


block_label_count = 0
loop_label_count = 0

def generateBlockLabel() -> WasmId:
    global block_label_count
    label = "$loop_" + str(block_label_count) + "_exit"
    block_label_count += 1
    return WasmId(label)

def generateLoopLabel() -> WasmId:
    global loop_label_count
    label = "$loop_" + str(loop_label_count) + "_start"
    loop_label_count += 1
    return WasmId(label)

def compileStmts(stmts: list[stmt], cfg: CompilerConfig) -> list [WasmInstr]:
    instructions: list [WasmInstr] = []

    for stmt in stmts:
        instructions += compileStmt(stmt, cfg)

    return instructions

def compileStmt(stmt: stmt, cfg: CompilerConfig) -> list [WasmInstr]:
    instructions: list [WasmInstr] = []

    match stmt:
        case SubscriptAssign(left, index, right):
            pass
        case StmtExp(exp):
            return compileExpr(exp, cfg)
        case Assign(var, right):
            instructions += compileExpr(right, cfg)
            instructions += [WasmInstrVarLocal('set', identToWasmId(var))]
            return instructions
        case IfStmt(cond, thenBody, elseBody):
            instructions += compileExpr(cond, cfg)
            thenBodyWasmInstrs = compileStmts(thenBody, cfg)
            elseBodyWasmInstrs = compileStmts(elseBody, cfg)
            instructions += [WasmInstrIf(None, thenBodyWasmInstrs, elseBodyWasmInstrs)]
            return instructions
        case WhileStmt(cond, body):
            condition_instructions = compileExpr(cond, cfg)
            body_instructions = compileStmts(body, cfg)

            block_label = generateBlockLabel()
            loop_label = generateLoopLabel()

            start_of_loop = condition_instructions + [WasmInstrIf(None, [], [WasmInstrBranch(block_label, False)])]
            end_of_loop = [WasmInstrBranch(loop_label, False)]

            loop_instructions: list [WasmInstr] = [WasmInstrLoop(loop_label, start_of_loop + body_instructions + end_of_loop)]
            instructions += [WasmInstrBlock(block_label, None, loop_instructions)]

            return instructions



def compileExprs(exps: list [exp], cfg: CompilerConfig) -> list [WasmInstr]:
    instructions: list [WasmInstr] = []

    for exp in exps:
        instructions += compileExpr(exp, cfg)
    
    return instructions

def compileAtomicExpr(atomExp: atomExp) -> WasmInstr:
    match atomExp:
        case IntConst(value):
            return WasmInstrConst('i64', value)
        case BoolConst(value):
            if value:
                return WasmInstrConst('i32', 1)
            else:
                return WasmInstrConst('i32', 0)
        case Name(ident):
            return WasmInstrVarLocal('get', identToWasmId(ident))

def compileExpr(exp: exp, cfg: CompilerConfig) -> list [WasmInstr]:
    match exp:
        case AtomExp(atomExp):
            return [compileAtomicExpr(atomExp)]
        case ArrayInitDyn(length, elemInit):
            # leaves array address on top of stack
            instructions = compileInitArray(length, tyOfAtomExp(elemInit), cfg)
            # set $@tmp_i32 to array address, leave it on top of stack
            instructions += [WasmInstrVarLocal('tee', WasmId('$@tmp_i32'))]
            instructions += [WasmInstrVarLocal('get', WasmId('$@tmp_i32'))]
            instructions += [WasmInstrConst('i32', 4)] # length of header
            instructions += [WasmInstrNumBinOp('i32', 'add')]
            instructions += [WasmInstrVarLocal('set', WasmId('$@tmp_i32'))] # set $@tmp_i32 to the first array element

            # loop for initializing array elements
            block_label = generateBlockLabel()
            loop_label = generateLoopLabel()

            condition_instructions = [
                WasmInstrVarLocal('get', WasmId('$@tmp_i32')), 
                WasmInstrVarGlobal('get', WasmId('$@free_ptr')), 
                WasmInstrIntRelOp('i32', 'lt_u') # compare against end of array
                ]
            condition_check = [WasmInstrIf(None, [], [WasmInstrBranch(block_label, False)])]

            body_instructions: list[WasmInstr] = []
            if tyOfAtomExp(elemInit) == Int():
                size_in_bytes = 8

                body_instructions += [
                    WasmInstrVarLocal('get', WasmId('$@tmp_i32')),
                    compileAtomicExpr(elemInit), # instruction for the initial value
                    WasmInstrMem('i64', 'store'),
                    WasmInstrVarLocal('get', WasmId('$@tmp_i32')),
                    WasmInstrConst('i32', size_in_bytes),
                    WasmInstrNumBinOp('i32', 'add'),
                    WasmInstrVarLocal('set', WasmId('$@tmp_i32'))
                    ]
            else:
                size_in_bytes = 4
                body_instructions += [
                    WasmInstrVarLocal('get', WasmId('$@tmp_i32')),
                    compileAtomicExpr(elemInit), # instruction for the initial value
                    WasmInstrMem('i32', 'store'),
                    WasmInstrVarLocal('get', WasmId('$@tmp_i32')),
                    WasmInstrConst('i32', size_in_bytes),
                    WasmInstrNumBinOp('i32', 'add'),
                    WasmInstrVarLocal('set', WasmId('$@tmp_i32'))
                    ]

            end_of_loop = [WasmInstrBranch(loop_label, False)]
            start_of_loop = condition_instructions + condition_check

            loop_instructions: list [WasmInstr] = [WasmInstrLoop(loop_label, start_of_loop + body_instructions + end_of_loop)]
            instructions += [WasmInstrBlock(block_label, None, loop_instructions)]

            return instructions

        case ArrayInitStatic(elemsInit):
            # leaves array address on top of stack
            instructions = compileInitArray(IntConst(len(elemsInit)), tyOfAtomExp(elemsInit[0]), cfg)

            if tyOfAtomExp(elemsInit[0]) == Int():
                offset = 8
            else:
                offset = 4

            for idx, atomExp in enumerate(elemsInit):
                instructions += [WasmInstrVarLocal('tee', WasmId('$@tmp_i32'))]
                instructions += [WasmInstrVarLocal('get', WasmId('$@tmp_i32'))]
                instructions += [WasmInstrConst('i32', 4 + offset * idx)]
                instructions += [WasmInstrNumBinOp('i32', 'add')]
                instructions += [compileAtomicExpr(atomExp)]

                if tyOfAtomExp(elemsInit[0]) == Int():
                    instructions += [WasmInstrMem('i64', 'store')]
                else:
                    instructions += [WasmInstrMem('i32', 'store')]

            return instructions

        case Subscript(array, index):
            instructions: list [WasmInstr] = []

            arraySizeErrorInstructions = Errors.outputError('ArraySizeError')
            terminateInstructions: list[WasmInstr] = [WasmInstrTrap()]

            # size check
            ## check whether size of array is greater than index
            ### get array address on stack (this value is expected by the instructions for the array length)
            instructions += [compileAtomicExpr(array)]
            ### get instructions for size of array
            instructions += arrayLenInstrs()
            ### load index on stack
            instructions += [compileAtomicExpr(index)]
            instructions += [WasmInstrIntRelOp('i32', 'gt_u')]
            instructions += [WasmInstrIf(None, [], arraySizeErrorInstructions + terminateInstructions)]
            ## check whether index is greater then 0
            instructions += [compileAtomicExpr(index)]
            instructions += [WasmInstrConst('i32', 0)]
            instructions += [WasmInstrIf(None, [], arraySizeErrorInstructions + terminateInstructions)]

            #compute the address of the element
            instructions += [compileAtomicExpr(array)]
            instructions += [compileAtomicExpr(index)]
            instructions += [WasmInstrConvOp('i32.wrap_i64')]

            if tyOfAtomExp(array) == Int():
                instructions += [WasmInstrConst('i32', 8)]
            else:
                instructions += [WasmInstrConst('i32', 4)]
            
            instructions += [WasmInstrNumBinOp('i32', 'mul')]
            instructions += [WasmInstrConst('i32', 4)]
            instructions += [WasmInstrNumBinOp('i32', 'add')] #now on top of the stack: offset of the element
            instructions += [WasmInstrNumBinOp('i32', 'add')] #now on top of the stack: address of the element

            if tyOfAtomExp(array) == Int():
                instructions += [WasmInstrMem('i64', 'load')]
            else:
                instructions += [WasmInstrMem('i32', 'load')]

            return instructions
            
        case Call(ident, args):
            if ident.name == "print":
                instructions: list [WasmInstr] = []

                if tyOfExp(args[-1]) == Int():
                    instructions += compileExprs(args, cfg)
                    instructions += [WasmInstrCall(WasmId("$print_i64"))]

                if tyOfExp(args[-1]) == Bool():
                    instructions += compileExprs(args, cfg)
                    instructions += [WasmInstrCall(WasmId("$print_bool"))]
                
                return instructions
            elif ident.name == "input_int":
                return [WasmInstrCall(WasmId("$input_i64"))]
            elif ident.name == "len":
                instructions: list [WasmInstr] = []

                #get array address from args
                instructions += compileExpr(args[0], cfg)

                instructions += arrayLenInstrs()

                return instructions
            else:
                raise Exception(f'Call {ident} with args {args} is not known to the compiler')
        case UnOp(op, arg):
            instructions: list [WasmInstr] = []
            match op:
                case USub():
                    instructions += [WasmInstrConst('i64', 0)]
                    instructions += compileExpr(arg, cfg)
                    instructions += [WasmInstrNumBinOp('i64', 'sub')]
                    return instructions
                case Not():
                    instructions += compileExpr(arg, cfg)
                    instructions += [WasmInstrIf('i32', [WasmInstrConst('i32', 0)], [WasmInstrConst('i32', 1)])]
                    return instructions
        case BinOp(left, op, right):
            instructions: list [WasmInstr] = []
            instructionsLeft: list [WasmInstr] = []
            instructionsRight: list [WasmInstr] = []
            instructionsLeft += compileExpr(left, cfg)
            instructionsRight += compileExpr(right, cfg)
            match op:
                case Add():
                    instructions += instructionsLeft + instructionsRight + [WasmInstrNumBinOp('i64', 'add')]
                case Sub():
                    instructions += instructionsLeft + instructionsRight + [WasmInstrNumBinOp('i64', 'sub')]
                case Mul():
                    instructions += instructionsLeft + instructionsRight + [WasmInstrNumBinOp('i64', 'mul')]
                case Less():
                    instructions += instructionsLeft + instructionsRight + [WasmInstrIntRelOp('i64', 'lt_s')]
                case LessEq():
                    instructions += instructionsLeft + instructionsRight + [WasmInstrIntRelOp('i64', 'le_s')]
                case Greater():
                    instructions += instructionsLeft + instructionsRight + [WasmInstrIntRelOp('i64', 'gt_s')]
                case GreaterEq():
                    instructions += instructionsLeft + instructionsRight + [WasmInstrIntRelOp('i64', 'ge_s')]
                case Eq():
                    if left.ty == NotVoid(Int()):
                        instructions += instructionsLeft + instructionsRight + [WasmInstrIntRelOp('i64', 'eq')]
                    if left.ty == NotVoid(Bool()):
                        instructions += instructionsLeft + instructionsRight + [WasmInstrIntRelOp('i32', 'eq')]
                case NotEq():
                    if left.ty == NotVoid(Int()):
                        instructions += instructionsLeft + instructionsRight + [WasmInstrIntRelOp('i64', 'ne')]
                    if left.ty == NotVoid(Bool()):
                        instructions += instructionsLeft + instructionsRight + [WasmInstrIntRelOp('i32', 'ne')]
                case And():
                    instructions += instructionsLeft
                    instructions += [WasmInstrIf('i32', instructionsRight, [WasmInstrConst('i32', 0)])]
                case Or():
                    instructions += instructionsLeft
                    instructions += [WasmInstrIf('i32', [WasmInstrConst('i32', 1)], instructionsRight)]
                case Is():
                    instructions += instructionsLeft
                    instructions += instructionsRight
                    instructions += [WasmInstrIntRelOp('i32', 'eq')]
            return instructions
        

def compileInitArray(lenExp: atomExp, elemTy: ty, cfg: CompilerConfig) -> list[WasmInstr]:
    instructions: list [WasmInstr] = []

    # check length
    arraySizeErrorInstructions = Errors.outputError('ArraySizeError')
    terminateInstructions: list[WasmInstr] = [WasmInstrTrap()]

    ## check length is greater than zero
    instructions += [compileAtomicExpr(lenExp)]
    instructions += [WasmInstrConst('i64', 0)]
    instructions += [WasmInstrIntRelOp('i64', 'gt_s')]
    instructions += [WasmInstrIf(None, [], arraySizeErrorInstructions + terminateInstructions)]

    ## check length is smaller than maximum array size
    instructions += [compileAtomicExpr(lenExp)]
    instructions += [WasmInstrConst('i64', cfg.defaultMaxArraySize)]
    instructions += [WasmInstrIntRelOp('i64', 'lt_s')]
    instructions += [WasmInstrIf(None, [], arraySizeErrorInstructions + terminateInstructions)]
    
    # compute header value
    ## load $@free_ptr
    instructions += [WasmInstrVarGlobal('get', WasmId('$@free_ptr'))]

    ## instructions for computing the header
    instructions += [compileAtomicExpr(lenExp)]
    instructions += [WasmInstrConvOp('i32.wrap_i64')]
    instructions += [WasmInstrConst('i32', 4)]
    instructions += [WasmInstrNumBinOp('i32', 'shl')]
    instructions += [WasmInstrConst('i32', 3)]
    instructions += [WasmInstrNumBinOp('i32', 'xor')]

    ## store header at address $@free_ptr
    instructions += [WasmInstrMem('i32', 'store')]

    # move $@free_ptr and return array address
    ## save old value $@free_ptr (now address of the array)
    ## this is left behind by the instructions of this function on the stack as "return value"
    instructions += [WasmInstrVarGlobal('get', WasmId('$@free_ptr'))]

    ## calculate new position of $@free_ptr
    instructions += [compileAtomicExpr(lenExp)]
    instructions += [WasmInstrConvOp('i32.wrap_i64')]

    if elemTy == Int():
        instructions += [WasmInstrConst('i32', 8)]
    else:
        instructions += [WasmInstrConst('i32', 4)]

    instructions += [WasmInstrNumBinOp('i32', 'mul')] # multiply length with the size of each element

    instructions += [WasmInstrConst('i32', 4)]
    instructions += [WasmInstrNumBinOp('i32', 'add')] # add 4 for the header

    instructions += [WasmInstrVarGlobal('get', WasmId('$@free_ptr'))]
    instructions += [WasmInstrNumBinOp('i32', 'add')] # add the space required by the array to $@free_ptr

    instructions += [WasmInstrVarGlobal('set', WasmId('$@free_ptr'))] # save new $@free_ptr

    return instructions # these instructions leave the address of the created array on the stack

# expects address of array on stack
def arrayLenInstrs() -> list[WasmInstr]:
    instructions: list [WasmInstr] = []

    # load array header
    instructions += [WasmInstrMem('i32', 'load')]
    #shift right by 4 bit to get the length
    instructions += [WasmInstrConst('i32', 4)]
    instructions += [WasmInstrNumBinOp('i32', 'shr_u')]
    # convert to i64
    instructions += [WasmInstrConvOp('i64.extend_i32_u')]

    return instructions

def arrayOffsetInstrs(arrayExp: atomExp, indexExp: atomExp) -> list[WasmInstr]:
    instructions: list [WasmInstr] = []

    if tyOfAtomExp(arrayExp) == Int():
        offset = 8
    else:
        offset = 4

    # get index value on stack
    instructions += [compileAtomicExpr(indexExp)]
    # convert i64 to i32
    instructions += [WasmInstrConvOp('i32.wrap_i64')]
    instructions += [WasmInstrConst('i32', offset)]
    # multiply index with offset
    instructions += [WasmInstrNumBinOp('i32', 'mul')]

    # add 4 for the array header
    instructions += [WasmInstrConst('i32', 4)]
    instructions += [WasmInstrNumBinOp('i32', 'add')]

    return instructions