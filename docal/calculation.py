'''
module procedure

does the calculations needed, sets the appropriate variables in the main
module and returns the procedure of the calsulations
'''

import ast  # to know deduce which steps are needed
from .document import DICT
from .parsing import latexify, eqn, DEFAULT_MAT_SIZE, UNIT_PF


def _calculate(expr, steps, mat_size):
    '''carryout the necesary calculations and assignments'''

    result = []
    for step in steps:
        if step == 0:
            result.append(latexify(expr, mat_size=mat_size))
        elif step == 1:
            result.append(latexify(expr, subs=True, mat_size=mat_size))
        elif step == 2:
            result.append(latexify(eval(expr, DICT), mat_size))

    return result


def figure_out_steps(expr_dump):
    '''used when nothing about the steps comes from the user to prevent repetition
    when the calculation is sent to the pdf. return necessary steps based on the
    expression content.'''

    # there are no calls or ops in the expression
    if not (any([typ in expr_dump for typ in ['Call', 'BinOp', 'UnaryOp']])):
        if 'Name' in expr_dump:
            steps = [0, 2]
        else:
            steps = [2]
    else:
        if 'Name' in expr_dump:
            steps = [0, 1, 2]
        else:
            steps = [0, 2]

    return steps


def _assort_input(input_str):
    '''look above'''

    # only split once, because the # char is used for notes below
    input_parts = [part.strip() for part in input_str.strip().split('#', 1)]
    if len(input_parts) == 1:
        additionals = ''
        equation = input_str
    else:
        equation = input_parts[0]
        additionals = input_parts[1]

    var_name, expression = [part.strip() for part in equation.split('=', 1)]
    unp_vars = [n.id
                for n in ast.walk(ast.parse(var_name).body[0].value)
                if isinstance(n, ast.Name)]
    expr_dump = ast.dump(ast.parse(expression))

    steps = figure_out_steps(expr_dump)
    mat_size = DEFAULT_MAT_SIZE
    unit = ''
    mode = 'default'
    note = ''

    for a in [a.strip() for a in additionals.split(',')]:
        if a.isdigit():
            steps = [int(num) - 1 for num in a]
        # only the first # is used to split the line (see above) so others
        elif a.startswith('#'):
            note = a[1:]
        elif a.startswith('m') and a[1:].isdigit():
            if len(a) == 2:
                mat_size = int(a[1])
            else:
                mat_size = (int(a[1]), int(a[2]))
        elif a == '$':
            mode = 'inline'
        elif a == '$$':
            mode = 'display'
        else:
            unit = a

    if note:
        note = f'\\quad\\text{{{note}}}'

    return var_name, unp_vars, expression, unit, steps, mat_size, mode, note


def cal(input_str):
    '''
    evaluate all the calculations, carry out the appropriate assignments,
    and return all the procedures

    '''
    var_name, unp_vars, expr, unit, steps, mat_size, mode, note = _assort_input(
        input_str)
    result = _calculate(expr, steps, mat_size)
    var_lx = latexify(var_name)
    if unit == 'deg':
        unit_lx = '^\\circ'
    elif unit:
        unit_lx = f" \, \mathrm{{{latexify(unit, mul_symbol=' ', div_symbol='/')}}}"
    else:
        unit_lx = f" \, \mathrm{{{unitize(expr)}}}"
    result[-1] += unit_lx + note

    if mode == 'inline':
        displ = False
    elif mode == 'display':
        displ = True
    else:
        if len(steps) == 1 and steps[0] == 0:
            displ = False
        else:
            displ = True

    procedure = [f'{var_lx} = {result[0]}']
    for step in result[1:]:
        procedure.append('    = ' + step)

    output = eqn(*procedure, norm=False, disp=displ)

    # carry out normal op in main script
    exec(input_str, DICT)
    # for later unit retrieval
    for var in unp_vars:
        exec(f'{var}{UNIT_PF} = "{unit}"', DICT)

    return output

class UnitHandler(ast.NodeVisitor):
    '''
    simplify the given expression as a combination of units
    '''
    def __init__(self, norm=False):
        self.norm = norm

    def visit_Name(self, n):
        if self.norm:
            unit = n
        else:
            un = DICT[n.id + UNIT_PF]
            unit = ast.parse(un if un else '_').body[0].value
        if isinstance(unit, ast.Name):
            if hasattr(n, 'upper') and not n.upper:
                return [[], [unit.id]]
            else:
                return [[unit.id], []]
        else:
            unit.upper = n.upper
            self.norm = True
            l = self.visit(unit)
            self.norm = False
            return l

    def visit_BinOp(self, n):
        if hasattr(n, 'upper') and not n.upper:
            upper = False
        else:
            upper = True
        n.left.upper = upper
        if isinstance(n.op, ast.Pow):
            ls = [[], []]
            for i in range(n.right.n):
                ls[0] += self.visit(n.left)[0]
                ls[1] += self.visit(n.left)[1]
            return ls
        elif isinstance(n.op, ast.Mult):
            n.right.upper = upper
            ls = self.visit(n.left)
            ls[0] += self.visit(n.right)[0]
            ls[1] += self.visit(n.right)[1]
            return ls
        elif isinstance(n.op, ast.Div):
            n.right.upper = not upper
            ls = self.visit(n.left)
            ls[1] += self.visit(n.right)[1]
            ls[0] += self.visit(n.right)[0]
            return ls
        elif isinstance(n.op, ast.Add) or isinstance(n.op, ast.Sub):
            n.right.upper = upper
            l = self.visit(n.left)
            r = self.visit(n.right)
            if (len(l[0]) == len(r[0]) and all([e in r[0] for e in l[0]])) \
                    and (len(l[1]) == len(r[1]) and all([e in r[1] for e in l[1]])):
                return l
            print('error')
            return [[], []]

    def generic_visit(self, n):
        return [[], []]


def unitize(s, norm=False):
    pu = ast.parse(s).body[0].value if s else ast.Name(id='_', ctx=ast.Load())
    ls = UnitHandler(norm).visit(pu)
    num = list(set([e + '**' + str(ls[0].count(e))
                    if ls[0].count(e) > 1
                    else e for e in ls[0]]))
    den = list(set([e + '**' + str(ls[1].count(e))
                    if ls[1].count(e) > 1
                    else e for e in ls[1]]))
    for u in num:
        if u in den:
            num.remove(u)
            den.remove(u)
    s_num = f'({"*".join(num)})' if num else '_'
    s_den = f'/({"*".join(den)})' if den else ''
    return latexify(s_num + s_den, div_symbol='/')
