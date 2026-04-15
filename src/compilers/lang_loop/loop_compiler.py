from common.symtab import VarInfo
from lang_loop.loop_ast import *
from common.wasm import *
import lang_loop.loop_tychecker as loop_tychecker
from common.compilerSupport import *
#import common.utils as utils

def compileModule(m: mod, cfg: CompilerConfig) -> WasmModule:
    """
    Compiles the given module.
    """
    vars = loop_tychecker.tycheckModule(m)
    instrs = compileStmts(m.stmts)
    idMain = WasmId('$main')
    locals: list[tuple[WasmId, WasmValtype]] = [createLocals(ident, type) for (ident, type) in vars.items()]
    return WasmModule(imports=wasmImports(cfg.maxMemSize),
        exports=[WasmExport("main", WasmExportFunc(idMain))],
        globals=[],
        data=[],
        funcTable=WasmFuncTable([]),
        funcs=[WasmFunc(idMain, [], None, locals, instrs)])

def createLocals(ident: ident, type: VarInfo[ty]) -> tuple[WasmId, WasmValtype]:
    wasmId = identToWasmId(ident)
    
    match type.ty:
        case Int():
            return (wasmId, 'i64')
        case Bool():
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

def compileStmts(stmts: list[stmt]) -> list [WasmInstr]:
    instructions: list [WasmInstr] = []

    for stmt in stmts:
        instructions += compileStmt(stmt)

    return instructions

def compileStmt(stmt: stmt) -> list [WasmInstr]:
    instructions: list [WasmInstr] = []

    match stmt:
        case StmtExp(exp):
            return compileExpr(exp)
        case Assign(var, right):
            instructions += compileExpr(right)
            instructions += [WasmInstrVarLocal('set', identToWasmId(var))]
            return instructions
        case IfStmt(cond, thenBody, elseBody):
            instructions += compileExpr(cond)
            thenBodyWasmInstrs = compileStmts(thenBody)
            elseBodyWasmInstrs = compileStmts(elseBody)
            instructions += [WasmInstrIf(None, thenBodyWasmInstrs, elseBodyWasmInstrs)]
            return instructions
        case WhileStmt(cond, body):
            condition_instructions = compileExpr(cond)
            body_instructions = compileStmts(body)

            block_label = generateBlockLabel()
            loop_label = generateLoopLabel()

            start_of_loop = condition_instructions + [WasmInstrBranch(block_label, True)]
            end_of_loop = condition_instructions + [WasmInstrBranch(loop_label, True)]

            loop_instructions = [WasmInstrLoop(loop_label,  body_instructions + end_of_loop)]
            instructions += [WasmInstrBlock(block_label, None, start_of_loop + loop_instructions)]

            return instructions



def compileExprs(exps: list [exp]) -> list [WasmInstr]:
    instructions: list [WasmInstr] = []

    for exp in exps:
        instructions += compileExpr(exp)
    
    return instructions


def compileExpr(exp: exp) -> list [WasmInstr]:
    match exp:
        case BoolConst(boolValue):
            if boolValue:
                return [WasmInstrConst('i32', 1)]
            else:
                return [WasmInstrConst('i32', 0)]
        case IntConst(intValue):
            return [WasmInstrConst('i64', intValue)]
        case Name(ident):
            return [WasmInstrVarLocal('get', identToWasmId(ident))]
        case Call(ident, args):
            if ident.name == "print":
                instructions: list [WasmInstr] = []

                if tyOfExp(args[-1]) == Int():
                    instructions += compileExprs(args)
                    instructions += [WasmInstrCall(WasmId("$print_i64"))]

                if tyOfExp(args[-1]) == Bool():
                    instructions += compileExprs(args)
                    instructions += [WasmInstrCall(WasmId("$print_bool"))]
                
                return instructions
            elif ident.name == "input_int":
                return [WasmInstrCall(WasmId("$input_i64"))]
            else:
                return []
        case UnOp(op, arg):
            instructions: list [WasmInstr] = []
            instructions += [WasmInstrConst('i64', 0)]
            instructions += compileExpr(arg)
            instructions += [WasmInstrNumBinOp('i64', 'sub')]
            return instructions
        case BinOp(left, op, right):
            instructions: list [WasmInstr] = []
            instructionsLeft: list [WasmInstr] = []
            instructionsRight: list [WasmInstr] = []
            instructionsLeft += compileExpr(left)
            instructionsRight += compileExpr(right)
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

            return instructions