'''
module procedure

does the calculations needed, sets the appropriate variables in the main
module and returns the procedure of the calsulations
'''

import ast # to know deduce which steps are needed
from __main__ import __dict__
from .formatting import format_quantity
from .parsing import latexify, eqn

DEFAULT_MAT_SIZE = 5

def _calculate(expr, mat_size):
    '''carryout the necesary calculations and assignments'''

    expr_1_lx = latexify(expr, mul_symbol='.', mat_size=mat_size)
    expr_2_lx = latexify(expr, mul_symbol='*', subs=True, mat_size=mat_size)
    expr_3_lx = format_quantity(eval(expr, __dict__), mat_size)

    return [expr_1_lx, expr_2_lx, expr_3_lx]

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

    input_parts = [part.strip() for part in input_str.strip().split('#')]
    if len(input_parts) == 1:
        additionals = ''
        equation = input_str
    else:
        equation = input_parts[0]
        additionals = input_parts[1]

    var_name, expression = [part.strip() for part in equation.split('=')]
    expr_dump = ast.dump(ast.parse(expression))

    steps = figure_out_steps(expr_dump)
    mat_size = DEFAULT_MAT_SIZE
    unit = ''
    for a in [a.strip() for a in additionals.split(',')]:
        if a.isdigit():
            steps = [int(num) - 1 for num in a]
        elif a.startswith('m') and a[1:].isdigit():
            if len(a) == 2:
                mat_size = int(a[1])
            else:
                mat_size = (int(a[1]), int(a[2]))
        else:
            unit = a

    if unit:
        if unit == 'deg':
            unit = '^\\circ'
        else:
            unit = f" \, \mathrm{{{latexify(unit, mul_symbol=' ', div_symbol='/')}}}"

    return var_name, expression, unit, steps, mat_size

def cal(input_str):
    '''
    evaluate all the calculations, carry out the appropriate assignments,
    and return all the procedures
    (which can be inserted in a pweave or pythontex document with print())

    >>> cal('t_f = 56 #1')
    $t_{f} = 56$

    >>> print(cal('r_d = sqrt(t_f/56)+78'))
    <BLANKLINE>
    \\begin{align}
    \\begin{split}
    r_{d}       &= \\frac{\\sqrt{14}}{28} \\cdot \\sqrt{t_{f}} + 78\\\\
                &= \\frac{\\sqrt{14}}{28} \\times \\sqrt{56} + 78\\\\
                &= 79\\\\
    \\end{split}
    \\end{align}
    '''

    var_name, expr, unit, steps, mat_size = _assort_input(input_str)
    result = _calculate(expr, mat_size)
    var_lx = latexify(var_name)
    result[2] += unit

    if len(steps) == 1 and steps[0] == 0 or steps[0] == 2:
        displ = False
    else:
        displ = True

    procedure = [f'{var_lx} = {result[steps[0]]}']
    for step in [result[step] for step in steps[1:]]:
        procedure.append('    = ' + step)

    output = eqn(*procedure, norm=False, disp=displ)

    return output
