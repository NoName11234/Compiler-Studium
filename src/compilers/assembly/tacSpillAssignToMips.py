#import assembly.tac_ast as tac
import assembly.tacSpill_ast as tacSpill
import assembly.mips_ast as mips
from typing import *
from assembly.common import *
#import assembly.tacInterp as tacInterp
from assembly.mipsHelper import *
from common.compilerSupport import *


def getOperandI(operand: str) -> mips.opI:
    match operand:
        case 'ADD':
            return mips.AddI()
        case 'LT_S':
            return mips.LessI()
        case _: 
            raise ValueError(f'Unhandled operator: {operand}')

def getOperand(operand: str) -> mips.op:
    match operand:
        case 'ADD':
            return mips.Add()
        case 'SUB':
            return mips.Sub()
        case 'MUL':
            return mips.Mul()
        case 'EQ':
            return mips.Eq()
        case 'NE':
            return mips.NotEq()
        case 'LT_S':
            return mips.Less()
        case 'GT_S':
            return mips.Greater()
        case 'LE_S':
            return mips.LessEq()
        case 'GE_S':
            return mips.GreaterEq()
        case _:
            raise ValueError(f'Unhandled operator: {operand}')

def assignToMips(i: tacSpill.Assign) -> list[mips.instr]:
    instructions: list[mips.instr] = list()

    match i.right:
        case tacSpill.Prim(p):
            match p:
                case tacSpill.Const(value):
                    instructions.append(mips.LoadI(reg(i.var), imm(value)))
                case tacSpill.Name(var):
                    instructions.append(mips.Move(reg(i.var), reg(var)))
        case tacSpill.BinOp(left, op, right):
            match left:
                case tacSpill.Const(leftValue):
                    match right:
                        case tacSpill.Const(rightValue):
                            if op.name == 'ADD' or op.name == 'LT_S':
                                #load left const in register
                                instructions.append(mips.LoadI(reg(i.var), imm(leftValue)))
                                #get operand
                                operand = getOperandI(op.name)
                                #add right const to register value
                                instructions.append(mips.OpI(operand, reg(i.var), reg(i.var), imm(rightValue)))
                            else:
                                secondRegister = Regs.t1 if i.var == Regs.t0 else Regs.t0
                                #load left const in own register
                                instructions.append(mips.LoadI(reg(i.var), imm(leftValue)))
                                #load right const in other spill register
                                instructions.append(mips.LoadI(reg(secondRegister), imm(rightValue)))
                                #get operand
                                operand = getOperand(op.name)
                                #execute operation with both registers
                                instructions.append(mips.Op(operand, reg(i.var), reg(i.var), reg(secondRegister)))
                        case tacSpill.Name(rightName):
                            #load left const in register
                            instructions.append(mips.LoadI(reg(i.var), imm(leftValue)))
                            #get operand
                            operand = getOperand(op.name)
                            #apply right register value to own register
                            instructions.append(mips.Op(operand, reg(i.var), reg(i.var), reg(rightName)))
                case tacSpill.Name(leftName):
                    match right:
                        case tacSpill.Const(rightValue):
                            if op.name == 'ADD' or op.name == 'LT_S':
                                #load left register in own register
                                instructions.append(mips.Move(reg(i.var), reg(leftName)))
                                #get operand
                                operand = getOperandI(op.name)
                                #apply right constant to own register
                                instructions.append(mips.OpI(operand, reg(i.var), reg(i.var), imm(rightValue)))
                            else:
                                #load right constant to own register
                                instructions.append(mips.LoadI(reg(i.var), imm(rightValue)))
                                #get operand
                                operand = getOperand(op.name)
                                #apply left register to own register
                                instructions.append(mips.Op(operand, reg(i.var), reg(leftName), reg(i.var)))
                        case tacSpill.Name(rightName):
                            #load left register in own register
                            instructions.append(mips.Move(reg(i.var), reg(leftName)))
                            #get operand
                            operand = getOperand(op.name)
                            #apply right register to own register
                            instructions.append(mips.Op(operand, reg(i.var), reg(i.var), reg(rightName)))
    
    return instructions