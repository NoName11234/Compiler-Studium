from lang_var.var_ast import *
from common.wasm import *
import lang_var.var_tychecker as var_tychecker
from common.compilerSupport import *
#import common.utils as utils

def compileModule(m: mod, cfg: CompilerConfig) -> WasmModule:
    """
    Compiles the given module.
    """
    vars = var_tychecker.tycheckModule(m)
    instrs = compileStmts(m.stmts)
    idMain = WasmId('$main')
    locals: list[tuple[WasmId, WasmValtype]] = [(identToWasmId(x), 'i64') for x in vars]
    return WasmModule(imports=wasmImports(cfg.maxMemSize),
        exports=[WasmExport("main", WasmExportFunc(idMain))],
        globals=[],
        data=[],
        funcTable=WasmFuncTable([]),
        funcs=[WasmFunc(idMain, [], None, locals, instrs)])


def identToWasmId(x: ident) -> WasmId:
    return WasmId("$" + x.name)

def compileStmts(stmts: list[stmt]) -> list [WasmInstr]:
    instructions: list [WasmInstr] = []

    for stmt in stmts:
        instructions += compileStmt(stmt)

    return instructions

def compileStmt(stmt: stmt) -> list [WasmInstr]:
    match stmt:
        case StmtExp(exp):
            return compileExpr(exp)
        case Assign(var, right):
            instructions: list [WasmInstr] = []
            instructions += compileExpr(right)
            instructions += [WasmInstrVarLocal('set', identToWasmId(var))]
            return instructions



def compileExprs(exps: list [exp]) -> list [WasmInstr]:
    instructions: list [WasmInstr] = []

    for exp in exps:
        instructions += compileExpr(exp)
    
    return instructions


def compileExpr(exp: exp) -> list [WasmInstr]:
    match exp:
        case IntConst(intValue):
            return [WasmInstrConst('i64', intValue)]
        case Name(ident):
            return [WasmInstrVarLocal('get', identToWasmId(ident))]
        case Call(ident, args):
            if ident.name == "print":
                instructions: list [WasmInstr] = []
                instructions += compileExprs(args)
                instructions += [WasmInstrCall(WasmId("$print_i64"))]
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
            instructions += compileExpr(left)
            instructions += compileExpr(right)
            match op:
                case Add():
                    instructions += [WasmInstrNumBinOp('i64', 'add')]
                case Sub():
                    instructions += [WasmInstrNumBinOp('i64', 'sub')]
                case Mul():
                    instructions += [WasmInstrNumBinOp('i64', 'mul')]
            return instructions