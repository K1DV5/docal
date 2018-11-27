# -ipy

import re
from .parsing import latexify

def _format_number(number):
    '''make the number part of a quantity more readable'''

    if any([isinstance(number, typ) for typ in [float, int]]):
        if number != 0 and (abs(number) > 1000 or abs(number) < 0.1):
            # in scientific notation
            return re.sub(r'([0-9]+)E([-+])([0-9]+)',
                            r'\1\\left(10^{\2'+r'\g<3>'.lstrip(r'0')+r'}\\right)',
                            f'{number:.2E}').replace('+', '')
        if number == int(number):
            return str(int(number))
        number = str(round(number, 3))
    else:
        number = format_quantity(number)

    return number


def _format_array(array, max_size=5):
    '''look above'''

    if len(array) > max_size:
        array = [*[_format_number(element) for element in array[:max_size - 2]],
                 '\\vdots',
                 _format_number(array[-1])]
    else:
        array = [_format_number(element) for element in array]

    number = ('\\left[\\begin{matrix}\n'
              + '\\\\\n'.join(array)
              + '\n\\end{matrix}\\right]')

    return f'{number}'


def _format_big_matrix(matrix, size):
    '''look above'''

    rows, cols = size
    cut_matrix = matrix[:rows - 2, :cols - 2].tolist()
    last_col = matrix[:rows - 2, -1].tolist()
    last_row = matrix[-1, :cols - 2].tolist()
    last_element = matrix[-1,-1]

    mat_ls = [' & '.join(
        [_format_number(element) for element in cut_matrix[index]]) + ' & \\cdots & ' + _format_number(last_col[index][0])
        for index in range(len(cut_matrix))] \
        + [' & '.join(['\\vdots'] * (cols - 2) + ['\\ddots', '\\vdots'])] \
        + [' & '.join([_format_number(element) for element in last_row[0]]) + ' & \\cdots & ' + _format_number(last_element)]

    return mat_ls


def _format_wide_matrix(matrix, max_cols):
    '''look above'''

    cut_matrix = matrix[:, :max_cols - 2].tolist()
    last_col = matrix[:, -1].tolist()

    mat_ls = [' & '.join(
        [_format_number(element) for element in cut_matrix[index]]) + ' & \\cdots & ' + _format_number(last_col[index][0])
        for index in range(matrix.shape[0])]

    return mat_ls

def _format_long_matrix(matrix, max_rows):
    '''look above'''

    mat_ls = [' & '.join(
                          [_format_number(element) for element in matrix[:max_rows - 2, :].tolist()[index]])
                          for index in range(matrix[:max_rows - 2, :].shape[0])]
    mat_ls.append(' & '.join(['\\vdots'] * matrix.shape[1]))
    mat_ls.append(' & '.join([_format_number(element) for element in matrix[-1, :].tolist()[0]]))

    return mat_ls


def _format_matrix(matrix, max_size=(5,5)):
    '''look above'''

    # too big -> small
    if matrix.shape[0] > max_size[0] and matrix.shape[1] > max_size[1]:
        mat_ls = _format_big_matrix(matrix, max_size)
    # too long -> small
    elif matrix.shape[0] > max_size[0] and matrix.shape[1] < max_size[1]:
        mat_ls = _format_long_matrix(matrix, max_size[0])
    # too wide -> small
    elif matrix.shape[0] < max_size[0] and matrix.shape[1] > max_size[1]:
        mat_ls = _format_wide_matrix(matrix, max_size[1])
    # already small so :)
    else:
        mat_ls = [' & '.join(
            [_format_number(element) for element in matrix.tolist()[index]])
            for index in range(matrix.shape[0])]

    braces = ['\\{', '\\}'] if matrix.shape[1] == 1 else ['[', ']']
    return ('\\left' + braces[0] + '\\begin{matrix}\n' +
              '\\\\\n'.join(mat_ls) +
              '\n\\end{matrix}\\right' + braces[1])


def format_quantity(quantity, mat_size=(5,5)):
    '''returns a nicely latex formatted string of the quantity'''

    if isinstance(mat_size, int):
        size_mat = (mat_size, mat_size)
        size_arr = mat_size
    else:
        size_mat = mat_size
        size_arr = mat_size[0]

    quantity_type = str(type(quantity))

    if any([isinstance(quantity, typ) for typ in [float, int]]):
        formatted = _format_number(quantity)

    elif 'array' in quantity_type or 'Array' in quantity_type:
        formatted = _format_array(quantity, size_arr)

    elif 'matrix' in quantity_type:
        formatted = _format_matrix(quantity, size_mat)

    else:
        formatted = latexify(str(quantity))

    return formatted
