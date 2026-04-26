from lang_var.var_ast import *
from lark import ParseTree
from parsers.common import *
#import common.log as log

grammarFile = "./src/parsers/lang_var/var_grammar.lark"

def parseModule(args: ParserArgs) -> mod:
    parseTree = parseAsTree(args, grammarFile, 'lvar')
    module = parseTreeToModuleAst(parseTree)
    return module

def parseTreeToModuleAst(t: ParseTree) -> mod:
    # get stmt_list subtree from lvar tree
    return Module(parseTreeToStmtListAst(asTree(t.children[0])))

def parseTreeToStmtAst(t: ParseTree) -> stmt:
    match t.data:
        case 'assign_stmt':
            return Assign(Ident(str(asToken(t.children[0]))), parseTreeToExpAst(asTree(t.children[1])))
        case 'exp':
            return StmtExp(parseTreeToExpAst(asTree(t.children[0])))
        case 'stmt':
            return parseTreeToStmtAst(asTree(t.children[0]))
        case kind:
            raise Exception(f'unhandled parse tree of kind {kind} for stmt: {t}')
    
def parseTreeToStmtListAst(t: ParseTree) -> list[stmt]:
    return [parseTreeToStmtAst(asTree(c)) for c in t.children]

def parseTreeToExpAst(t: ParseTree) -> exp:
    match t.data:
        case 'int_exp':
            return IntConst(int(asToken(t.children[0])))
        case 'variable_exp':
            return Name(Ident(str(asToken(t.children[0]))))
        case 'add_exp':
            e1, e2 = [asTree(c) for c in t.children]
            return BinOp(parseTreeToExpAst(e1), Add(), parseTreeToExpAst(e2))
        case 'mul_exp':
            e1, e2 = [asTree(c) for c in t.children]
            return BinOp(parseTreeToExpAst(e1), Mul(), parseTreeToExpAst(e2))
        case 'sub_exp':
            e1, e2 = [asTree(c) for c in t.children]
            return BinOp(parseTreeToExpAst(e1), Sub(), parseTreeToExpAst(e2))
        case 'unary_sub_exp':
            return UnOp(USub(), parseTreeToExpAst(asTree(t.children[0])))
        case 'call_exp':
            return Call(Ident(str(asToken(t.children[0]))), [parseTreeToExpAst(asTree(c)) for c in t.children[1:]])
        case 'exp_1' | 'exp_2' | 'exp_3' | 'exp_4' | 'paren_exp':
            return parseTreeToExpAst(asTree(t.children[0]))
        case kind:
            raise Exception(f'unhandled parse tree of kind {kind} for exp: {t}')
