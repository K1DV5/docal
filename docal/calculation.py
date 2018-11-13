# -ipy
'''
module procedure

does the calculations needed, sets the appropriate variables in the main
module and returns the procedure of the calsulations
'''

import re
# from sympy import latex, sympify, Symbol
from sympy.physics.units import meter, second, kilogram, convert_to
import __main__
from .equation import eqn, _surround_equation
from .formatting import format_quantity, UNIT_ABBREVIATIONS
from .parsing import latexify


class _calculation:
    '''the calculation entity'''

    def __init__(self, equation):
        '''prepare common variables for subsequent operations'''

        self.main_variable = equation.split('=')[0].strip()
        self.variable_lx = latexify(self.main_variable)
        self.expr_0_str = equation.split('=')[1].strip()

    def step_one(self):
        '''the first step of the procedure'''

        expr_1_lx = latexify(self.expr_0_str, mul_symbol=' ')
        # for full_form, short_form in UNIT_ABBREVIATIONS.items():
        #     if full_form in expr_1_lx:
        #         expr_1_lx = re.sub(
        #             fr'(?<!_{{|[a-zA-Z_]{{2}}){full_form}(?![a-zA-Z_]+)',
        #             f'\\mathrm{{{short_form}}}',
        #             expr_1_lx)

        return expr_1_lx

    def step_two(self):
        '''the second step'''

        # free_symbols = list(self.sympified.atoms(Symbol))
        # variables_list = [latex(var) for var in free_symbols]
        # values_list = [__main__.__dict__[str(var)]
        #                for var in free_symbols]
        # values_dict = dict(zip(variables_list, values_list))
        expr_2_lx = latexify(self.expr_0_str, mul_symbol='times', subs=True)
        # for var, val in values_dict.items():
        #     val_lx = format_quantity(val)
        #     expr_2_lx = re.sub(
        #         fr'(?<!_{{|[a-zA-Z_]{{2}}){re.escape(var)}\^?(?![a-zA-Z_]+)',
        #         lambda mo: (fr'\left({val_lx}\right)^'
        #                     if mo.group().endswith('^')
        #                     and '\\mathrm' in val_lx
        #                     else val_lx),
        #         expr_2_lx)

        return expr_2_lx

    def step_three(self, shown_unit):
        '''third step'''

        expr_3_lx = format_quantity(eval(self.expr_0_str, __main__.__dict__),
                                    shown_unit)

        return expr_3_lx

    def assign_variable(self, result_unit):
        '''the name says it'''

        if result_unit == (meter, kilogram, second):
            main_value = self.expr_0_str
        else:
            try:
                main_value = convert_to(eval(self.expr_0_str,
                                             __main__.__dict__),
                                        result_unit)
            except:  # if it cannot be converted
                main_value = self.expr_0_str

        exec(f'{self.main_variable} = {main_value}', __main__.__dict__)


def cal(equation, intent='full', unit=(meter, kilogram, second)):
    '''
    evaluate all the calculations, carry out the appropriate assignments,
    and return all the procedures
    (which can be inserted in a pweave or pythontex document with print())

    >>> cal('t_f = 56', 'd')
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

    calc = _calculation(equation)
    calc.assign_variable(unit)

    _var_len = len(calc.variable_lx)
    _rem = 4 - _var_len // 4
    _spaces = _var_len + _rem

    if intent in ('define', 'd'):
        output = eqn(calc.variable_lx + _rem*' ' + '= ' + calc.step_one(),
                     norm=False, disp=False)

    elif intent in ('2step', '2'):
        output = eqn(calc.variable_lx + _rem*' ' + '= ' + calc.step_one(),
                     _spaces * ' ' + '= ' + calc.step_three(unit),
                     norm=False, disp=True)

    elif intent in ('last', 'l'):
        output = eqn(calc.variable_lx + _rem*' ' + '= ' + calc.step_three(unit),
                     norm=False, disp=True)

    else:
        output = eqn(calc.variable_lx + _rem*' ' + '= ' + calc.step_one(),
                     _spaces * ' ' + '= ' + calc.step_two(),
                     _spaces * ' ' + '= ' + calc.step_three(unit),
                     norm=False, disp=True)

    return output


def fmt(quantity, unit=(meter, kilogram, second)):
    '''when just formatting is needed'''

    return _surround_equation(format_quantity(quantity, unit), disp=False)
