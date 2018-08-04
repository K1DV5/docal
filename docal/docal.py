# -ipy
'''
Module docal by K1DV5
'''

from sys import argv
from shutil import rmtree
from sympy import latex, sympify, Symbol, sqrt, solve, Matrix, N
from sympy.physics.units import meter, second, kilogram, convert_to, Quantity
import re
import __main__


def equation(*eqns, inline: bool = False, raw: bool = False):
    '''prints the given equation(s) in a nice latex format.

    >>> equation('c_V = beta_ * sqrt(alpha)/5')
    <BLANKLINE>
    \\begin{equation}
    c_{V}=\\frac{\\beta_{}}{5} \\, \\sqrt{\\alpha}
    \\end{equation}
    '''
    if raw is True:
        if len(eqns) == 1:
            if inline == True:
                print(f' ${eqns[0]}$ ')
            else:
                print(
                    f'\n\\begin{{equation}}\n{eqns[0]}\n\\end{{equation}}')
        else:
            print('\n\\begin{align}\n\\begin{split}')
            for eq in eqns:
                print(f"{eq.replace('=', '&=')}\\\\")
            print('\\end{split}\n\\end{align}')

    else:
        def lxify(eq): return latex(eq, mul_symbol='dot')
        if len(eqns) == 1:
            if '=' in eqns[0]:
                eq = eqns[0].split('=')
                eqn = (lxify(sympify(eq[0])).replace('\\cdot', '\\,')
                       + '='
                       + lxify(sympify(eq[1])).replace('\\cdot', '\\,')
                       )
                if inline == True:
                    print(f'${eqn}$')
                else:
                    print(
                        f'\n\\begin{{equation}}\n{eqn}\n\\end{{equation}}')
            else:
                expr = sympify(eqns[0])
                if inline == True:
                    print(f'${lxify(expr)}$')
                else:
                    print(
                        f'\n\\begin{{equation}}\n{lxify(expr)}\n\\end{{equation}}')
        else:
            print('\n\\begin{align}\n\\begin{split}')
            for eqt in eqns:
                if '=' in eqt:
                    eq = eqt.split('=')
                    try:
                        lhand = lxify(sympify(eq[0]))
                    except:
                        lhand = ''
                    rhand = lxify(sympify(eq[1]))
                    print(f'{lhand} &= {rhand}\\\\')
                else:
                    print(f'{lxify(eqt)}\\\\')
            print('\\end{split}\n\\end{align}')


def aserar(eqn, intent='full', unit=None):
    '''
    evaluates all the calculations and assignment needed in the eqn
    and prints all the procedures
    (which can be inserted in a pweave or pythontex document)
    
    >>> aserar('t_f = 56', 'd')
    $t_{f} = 56$

    >>> aserar('r_d = sqrt(t_f/56)+78')
    <BLANKLINE>
    \\begin{align}
    \\begin{split}
    r_{d}       &= \\frac{\\sqrt{14}}{28} \\cdot \\sqrt{t_{f}} + 78\\\\
                &= \\frac{\\sqrt{14}}{28} \\times \\sqrt{56} + 78\\\\
                &= 79\\\\
    \\end{split}
    \\end{align}
    '''

    abb = {'meter': 'm', 'millimeter': 'mm', 'second': 's', 'centimeter': 'cm',
           'inch': 'in', 'kilogram': 'kg', 'pascal': 'Pa', 'newton': 'N'}

    def format_quantity(qty, unit_internal=None):
        '''returns a nicely latex formatted string of the quantity
        including the units (if any)'''

        if unit_internal == None:
            default_units = [meter, kilogram, second]
        else:
            default_units = unit_internal

        qty_type = str(type(qty))

        def units_count(Qty):
            try:
                return len(Qty.atoms(Quantity))
            except:
                return 0

        def fmt_un_num(Qty):
            try:
                Num = float(convert_to(Qty, [meter, kilogram, second]))
            except:
                if unit_internal == None:
                    if 'Add' in str(type(Qty)):
                        comps = list(convert_to(Qty, default_units).evalf(
                        ).as_coefficients_dict().values())
                        Num = float(comps[0])
                    else:
                        comps = list(
                            Qty.evalf().as_coefficients_dict().values())
                        Num = float(comps[0])
                else:
                    comps = list(convert_to(Qty, default_units).evalf(
                    ).as_coefficients_dict().values())
                    Num = float(comps[0])

            if Num > 1000 or Num < 0.1:
                return re.sub(r'([0-9]+)E([-+])([0-9]+)',
                              r'\1(10^{\2'+r'\g<3>'.lstrip(r'0')+r'})',
                              f'{Num:.2E}').replace('+', '')

            else:
                if Num == int(Num):
                    return str(int(Num))
                else:
                    return str(round(Num, 3))

        def fmt_un_un(Qty):
            try:
                Num = float(convert_to(Qty, [meter, kilogram, second]))
                if type(Num) == float:
                    return ''
            except:
                if unit_internal == None:
                    if 'Add' in str(type(Qty)):
                        return '\\mathrm{' \
                            + latex(list(convert_to(Qty.evalf(), default_units)
                                         .as_coefficients_dict().keys())[0],
                                    mul_symbol='dot') \
                            .replace('\\cdot', '\\,') + '}'
                    else:
                        return '\\mathrm{' \
                            + latex(list(Qty.evalf()
                                         .as_coefficients_dict().keys())[0],
                                    mul_symbol='dot') \
                            .replace('\\cdot', '\\,') + '}'
                else:
                    return '\\mathrm{' \
                        + latex(list(convert_to(Qty.evalf(), default_units)
                                     .as_coefficients_dict().keys())[0],
                                mul_symbol='dot') \
                        .replace('\\cdot', '\\,') + '}'

        def fmt_ul(Qty):
            if Qty > 1000 or Qty < 0.1:
                return re.sub(r'([0-9]+)E([-+])([0-9]+)',
                              r'\1(10^{\2' + r'\g<3>'.lstrip('0') + r'})',
                              f'{Qty:.2E}').replace('+', '')
            else:
                if Qty == int(Qty):
                    return str(int(Qty))
                else:
                    return str(round(Qty, 3))

        if 'array' in qty_type or 'Array' in qty_type:

            def shorten_array(fpart, Ffunc):
                return fpart.replace(
                    '\\end{matrix}',
                    f'\\\\\\vdots\\\\{Ffunc(qty[-1])}\\end{{matrix}}')

            def format_array(Qty, Ffunc):
                Arr_lx = latex(Matrix(Qty))
                for ele in Qty:
                    Arr_lx = Arr_lx.replace(latex(ele), Ffunc(ele))
                return Arr_lx

            if units_count(qty[0]) != 0:
                # array + unit
                if len(qty) < 4:
                    # very long array
                    number = format_array(qty, fmt_un_num)
                else:
                    # normal length array
                    number = shorten_array(format_array(
                        qty[0:2], fmt_un_num), fmt_un_num)

                un = fmt_un_un(qty[0]).replace('\\frac', '')\
                    .replace('}{', '}\\slash{')
                for full_form, short_form in abb.items():
                    un = re.sub(
                        fr'(?<!_{{|[a-zA-Z_]{{2}}){full_form}(?![a-zA-Z_]+)',
                        short_form, un)

                return f'{number}\\,{un}'

            else:
                # array + num
                if len(qty) < 4:
                    return latex(Matrix(qty).applyfunc(fmt_ul))
                else:
                    return shorten_array(latex(Matrix(qty[0:2])
                                               .applyfunc(fmt_ul)), fmt_ul)

        elif 'matrix' in qty_type or 'Matrix' in qty_type:

            def shrink_matrix(fpart, Ffunc):
                return fpart.replace('\\\\',
                                     f' & \\cdots & {str(Ffunc(qty[0, -1]))}\\\\')\
                    .replace('\\end{matrix}',
                             (f' & \\cdots & {Ffunc(qty[1, -1])}'
                              '\\\\\\vdots & \\vdots & \\ddots & \\vdots\\\\'
                              f'{Ffunc(qty[-1, 0])} & {Ffunc(qty[-1, 1])}'
                              f' & \\cdots & {Ffunc(qty[-1, -1])}'
                              '\\end{matrix}'))

            def narrow_matrix(fpart, Ffunc):
                line_breaks = fpart.count('\\\\')
                narrowed = fpart
                for row in range(0, line_breaks):
                    narrowed = narrowed.replace(
                        '\\\\', f' & \\cdots & {Ffunc(qty[row, -1])}\\temp', 1)
                return narrowed.replace('\\temp', '\\\\')\
                    .replace('\\end{matrix}',
                             f' & \\cdots & {Ffunc(qty[line_breaks, -1])}\\end{{matrix}}')

            def shorten_matrix(fpart, Ffunc):
                end_part = '\\\\\\vdots'
                ands = fpart.count('&', 0, fpart.find('\\\\'))
                for col in range(1, ands + 1):
                    end_part += ' & \\vdots'
                end_part += f'\\\\{Ffunc(qty[-1, 0])}'
                for col in range(1, ands + 1):
                    end_part += f' & {Ffunc(qty[-1, col])}'
                return fpart.replace('\\end{matrix}', end_part + '\\end{matrix}')

            def format_matrix(Mat, Ffunc):
                Mat_lx = latex(Mat)
                for ele in Mat:
                    Mat_lx = Mat_lx.replace(latex(ele), Ffunc(ele))
                return Mat_lx

            qty_mat = Matrix(qty)
            if units_count(qty[0]) != 0:
                # matrix + unit
                if qty_mat.rows > 4 and qty_mat.cols > 4:
                    # very big matrix
                    number = shrink_matrix(format_matrix(
                        qty_mat[0:2, 0:2], fmt_un_num), fmt_un_num)
                elif qty_mat.rows > 4 and qty_mat.cols < 5:
                    # very long matrix
                    number = shorten_matrix(format_matrix(
                        qty_mat[0:2, :], fmt_un_num), fmt_un_num)
                elif qty_mat.rows < 5 and qty_mat.cols > 4:
                    # very wide matrix
                    number = narrow_matrix(format_matrix(
                        qty_mat[:, 0:2], fmt_un_num), fmt_un_num)
                else:
                    # normal size matrix
                    number = format_matrix(qty_mat, fmt_un_num)

                un = fmt_un_un(qty[0, 0]).replace('\\frac', '')\
                    .replace('}{', '}\\slash{')
                for full_form, short_form in abb.items():
                    un = re.sub(
                        fr'(?<!_{{|[a-zA-Z_]{{2}}){full_form}(?![a-zA-Z_]+)',
                        short_form,
                        un)

                return f'{number}\\,{un}'

            else:
                # matrix + num
                if qty_mat.rows > 4 and qty_mat.cols > 4:
                    # very big matrix
                    return shrink_matrix(format_matrix(
                        qty_mat[0:2, 0:2], fmt_ul), fmt_ul)
                elif qty_mat.rows > 4 and qty_mat.cols < 5:
                    # very long matrix
                    return shorten_matrix(format_matrix(
                        qty_mat[0:2, :], fmt_ul), fmt_ul)
                elif qty_mat.rows < 5 and qty_mat.cols > 4:
                    # very wide matrix
                    return narrow_matrix(format_matrix(
                        qty_mat[:, 0:2], fmt_ul), fmt_ul)
                else:
                    # normal size matrix
                    return format_matrix(qty_mat, fmt_ul)

        else:
            if units_count(qty) != 0:
                # single + unit
                number = fmt_un_num(qty)
                un = fmt_un_un(qty).replace('\\frac', '')\
                    .replace('}{', '}\\slash{')
                for full_form, short_form in abb.items():
                    un = re.sub(
                        fr'(?<!_{{|[a-zA-Z_]{{2}}){full_form}(?![a-zA-Z_]+)',
                        short_form,
                        un)

                return f'{number}\\,{un}'

            else:
                # single + num
                return fmt_ul(N(qty))

    # main variable:
    ዋና_ተጠሪ = eqn.split('=')[0].strip()
    variable_lx = latex(sympify(ዋና_ተጠሪ))

    # expression 1:
    expr_0_str = eqn.split('=')[1].strip()
    str_exp = re.sub(r'(?<![a-zA-Z_])[a-zA-Z]+\.(?=[a-zA-Z_]+)',
                     '', expr_0_str)
    sympified = sympify(str_exp)
    expr_1_lx = latex(sympified, mul_symbol='dot')
    for full_form, short_form in abb.items():
        if full_form in expr_1_lx:
            expr_1_lx = re.sub(
                fr'(?<!_{{|[a-zA-Z_]{{2}}){full_form}(?![a-zA-Z_]+)',
                f'\\mathrm{{{short_form}}}',
                expr_1_lx)

    # expression 2:
    free_symbols = list(sympified.atoms(Symbol))
    variables_list = [latex(var) for var in free_symbols]
    values_list = [eval(str(var), __main__.__dict__)
                   for var in free_symbols]
    values_dict = dict(zip(variables_list, values_list))
    expr_2_lx = latex(sympified, mul_symbol='times')
    for var, val in values_dict.items():
        val_lx = format_quantity(val).replace('\\', '\\\\')
        if '\\mathrm{' in val_lx:
            expr_2_lx = re.sub(
                fr'(?<!_{{|[a-zA-Z_]{{2}}){re.escape(var)}(?![a-zA-Z_^]+)',
                val_lx,
                expr_2_lx)
            expr_2_lx = re.sub(
                fr'(?<!_{{|[a-zA-Z_]{{2}}){re.escape(var)}(?=\^)',
                fr'\\left({val_lx}\\right)',
                expr_2_lx)
        else:
            expr_2_lx = re.sub(
                fr'(?<!_{{|[a-zA-Z_]{{2}}){re.escape(var)}(?![a-zA-Z_]+)',
                val_lx,
                expr_2_lx)

    # variable assignment:
    if unit == None:
        ዋጋ = expr_0_str
    else:
        try:
            ዋጋ = convert_to(eval(expr_0_str, __main__.__dict__),
                             unit)
        except:
            ዋጋ = expr_0_str
    exec(f'{ዋና_ተጠሪ} = {ዋጋ}', __main__.__dict__)

    # expression 3:
    expr_3_lx = format_quantity(eval(expr_0_str, __main__.__dict__),
                                unit_internal=unit)

    # write equations:
    _tabs_ = len(variable_lx)//4
    if intent == 'define' or intent == 'd':
        equation(
            variable_lx + ' = ' + expr_3_lx,
            inline=True, raw=True)
    elif intent == '2step' or intent == '2':
        equation(variable_lx + '\t= ' + expr_1_lx,
                 _tabs_*'\t' + '\t= ' + expr_3_lx,
                 raw=True)
    elif intent == 'last' or intent == 'l':
        equation(variable_lx + '\t= ' + expr_3_lx,
                 raw=True)
    else:
        equation(variable_lx + '\t= ' + expr_1_lx,
                 _tabs_*'\t' + '\t= ' + expr_2_lx,
                 _tabs_*'\t' + '\t= ' + expr_3_lx,
                 raw=True)


def solveStr(strg, var):
    ጥያቄ = sympify(strg)
    ተጠሪ = sympify(var)
    return solve(ጥያቄ, ተጠሪ)
