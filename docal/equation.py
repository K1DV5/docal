'''
module equation

handles equation formatting for inputs that are merely meant to be shown,
not evaluated
'''

from .parsing import latexify

def _surround_equation(equation: str, disp: bool):
    '''surround given equation by latex surroundings/ environments'''

    equation_len = 1 + equation.count('\n')

    if equation_len == 1:
        if disp:
            output_equation = ('\\begin{equation}\n'
                               f'{equation}\n'
                               '\\end{equation}')
        else:
            output_equation = f'\({equation}\)'
    else:
        output_equation = ('\\begin{align}\n\\begin{split}\n'
                           f'{equation}\n'
                           '\\end{split}\n\\end{align}')

    return output_equation

def _equation_raw(*equations):
    '''Modify [many] latex equations so they can be aligned vertically '''

    if len(equations) == 1:
        output_equation = equations[0]

    else:
        output_equation = '\\\\\n'.join(
            [equation.replace('=', '&=') for equation in equations])

    return output_equation


def _equation_normal(*equations):
    ''' convert [many] string equations from python form to latex '''

    if len(equations) > 1:
        equals = ' &= '
    else:
        equals = ' = '

    equations_formatted = [equals.join([latexify(expr.strip())
                                        for expr in equation.split('=')])
                           for equation in equations]

    output_equation = '\\\\\n'.join(equations_formatted)

    return output_equation


def eqn(*equation_list, norm: bool = True, disp: bool = True):
    '''main api for equations'''

    if norm:
        output_equation = _equation_normal(*equation_list)
    else:
        output_equation = _equation_raw(*equation_list)

    return _surround_equation(output_equation, disp)

