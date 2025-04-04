'''
module procedure

does the calculations needed, sets the appropriate variables in the main
module and returns the procedure of the calculations
'''

import ast
import logging
from .parsing import to_math, MathVisitor, UNIT_PF, build_eqn, _split, DEFAULT_MAT_SIZE

log = logging.getLogger(__name__)

# units that are not base units
DERIVED = {
    'N': 'kg*m/s**2',
    'Pa': 'kg/(m*s**2)',
    'J': 'kg*m**2/s**2',
    'W': 'kg*m**2/s**3',
    'Hz': '_/s',
}
DERIVED = {u: ast.parse(DERIVED[u]).body[0].value for u in DERIVED}

FALLBACK_OPTIONS = {
    'steps': [],
    'mat_size': DEFAULT_MAT_SIZE,
    'unit': None,
    'mode': 'default',
    'vert': True,
    'note': None,
    'hidden': False,
    'decimal': 3,
    'result' : None,
    'newlines': 0,
}


def _calculate(expr: ast.AST, options: dict, working_dict: dict, mul=' ', div='/', syntax=None):
    '''carryout the necesary calculations and assignments'''

    lx_args = lambda ex, subs=None: MathVisitor(mul=mul,
                                                div=div,
                                                subs=subs,
                                                mat_size=options['mat_size'],
                                                decimal=options['decimal'],
                                                working_dict=working_dict,
                                                syntax=syntax
                                                ).visit(ex)

    value_ast = expr if options['result'] is None else options['result']
    value = eval(compile(ast.Expression(value_ast), '<calculation>', 'eval'),
                 working_dict)
    result = [lx_args(expr)]
    result_rest = [
        lx_args(expr, True),
        lx_args(value if not isinstance(value_ast, ast.Lambda) else value_ast)]

    if options['steps']:
        result += result_rest
        result = [result[s] for s in options['steps'] if 0 <= s <= 2]
    # remove repeated steps (retaining order)
    elif isinstance(expr, ast.Constant) or isinstance(value_ast, ast.Lambda):
        result = [result_rest[1]]
    elif isinstance(expr, ast.Name):
        result = [result[0], result_rest[1]]
    else:
        last_str = str(result[0])
        for step in result_rest:
            step_str = str(step)
            if step_str != last_str:
                last_str = step_str
                result.append(step)
    # detect if the user is trying to give a different unit and give warning
    if options['unit']:
        # in their dict forms
        compared = [UnitHandler(True, working_dict).visit(options['unit']),
                    UnitHandler(False, working_dict).visit(expr)]
        # when the calculated already has a unit
        compared = [compared, [compared[1], [{}, {}]]]
        # if it is detected, warn the user but accept it anyway
        if not are_equivalent(*compared[1]) and not are_equivalent(*compared[0]):
            log.warning(
                'The input unit is not equivalent to the calculated one.')
    else:
        options['unit'] = unitize(expr, working_dict)
    
    result[-1] += to_math(options['unit'], div='/', syntax=syntax, ital=False)
    if options['note'] is not None:
        result[-1] += syntax.txt(syntax.halfsp) + syntax.txt_math(options['note'])

    return result

def _process_options(additionals, defaults=FALLBACK_OPTIONS, syntax=None):

    options = {}

    if additionals:
        for a in _split(additionals, ','):
            if a.isdigit():
                options['steps'] = [int(num) - 1 for num in a]
            # only the first # is used to split the line (see above) so others
            elif a.startswith('#'):
                note = a[1:].strip() # remove the hash
                options['note'] = note[1:-1] \
                    if note.startswith('(') and note.endswith(')') else note
            elif a.startswith('m') and a[1:].isdigit():
                options['mat_size'] = (int(a[1:]), int(a[1:]))
            elif a.startswith('d') and a[1:].isdigit():
                options['decimal'] = int(a[1:])
            elif a == '$':
                options['mode'] = 'inline'
            elif a == '$$':
                options['mode'] = 'display'
            elif a == '|':
                options['vert'] = True
            elif a == '-':
                options['vert'] = False
            elif a == ';':
                options['hidden'] = True
            elif a.startswith('='):
                try:
                    options['result'] = ast.parse(a[1:]).body[0].value
                except SyntaxError:
                    log.warning('Could not evaluate answer, using default')
            elif set(a) == {'\\'}:
                options['newlines'] = len(a)
            elif a and a != '_':
                # if it is a valid python expression, take it as a unit
                try:
                    compile(a, '', 'eval')
                except SyntaxError:
                    log.warning('Unknown option %s found, ignoring...', repr(a))
                else:
                    options['unit'] = ast.parse(a).body[0].value

    # merge the options, with the specific one taking precedence
    return {**defaults, **options}


def cal(input_str: ast.AST, working_dict={}, mul=' ', div='frac', syntax=None, options={}) -> str:
    '''
    evaluate all the calculations, carry out the appropriate assignments,
    and return all the procedures

    '''
    result = _calculate(input_str.value, options, working_dict, mul, div, syntax=syntax)
    if options['mode'] == 'inline':
        displ = False
    elif options['mode'] == 'display':
        displ = True
    else:
        if len(options['steps']) == 1 and options['steps'][0] == 0:
            displ = False
        else:
            displ = True

    disp = 'disp' if displ else 'inline'

    if isinstance(input_str, ast.Assign):
        var_names = [v.id for v in input_str.targets]
        var_lx = syntax.txt('=').join([to_math(var_name, syntax=syntax) for var_name in input_str.targets])

        procedure = [[var_lx, result[0]]]
        for step in result[1:]:
            procedure.append([syntax.txt(''), step])

        if options['result'] is not None:
            input_str.value = options['result'] # override the value stored
        # carry out normal op in main script
        co = compile(ast.Module([input_str], []), '<calculation>', 'exec')
        exec(co, working_dict)
        # for later unit retrieval
        for var in var_names:
            working_dict[var + UNIT_PF] = options['unit']

    else:
        if len(result) > 1:
            procedure = [[result[0], result[1]]]
            if result[2:]:
                procedure.append([syntax.txt(''), result[2]])
        else:
            procedure = [result]

    if options['hidden']:
        return ('text', '')

    output = build_eqn(procedure, displ, options['vert'], syntax)

    return (disp, output)


class UnitHandler(ast.NodeVisitor):
    '''
    simplify the given expression as a combination of units
    '''

    def __init__(self, norm=False, working_dict={}):
        self.norm = norm
        self.dict = working_dict

    def visit_Name(self, n):
        if self.norm:
            unit = n
        else:
            if n.id + UNIT_PF in self.dict:
                unit = self.dict[n.id + UNIT_PF]
            else:
                unit = ast.parse('_').body[0].value
        if isinstance(unit, ast.Name):
            if unit.id in DERIVED:
                unit = DERIVED[unit.id]
            elif hasattr(n, 'upper') and not n.upper:
                return [{}, {unit.id: 1}]
            else:
                return [{unit.id: 1}, {}]
        unit.upper = n.upper if hasattr(n, 'upper') else True
        # store and temporarily disregard the state self.norm
        prev_norm = self.norm
        self.norm = True
        ls = self.visit(unit)
        # revert to the previous state
        self.norm = prev_norm
        return ls

    def visit_Call(self, n):
        if isinstance(n.func, ast.Attribute):
            func = n.func.attr
        elif isinstance(n.func, ast.Name):
            func = n.func.id
        else:
            func = self.visit(n.func)
        if func == 'sqrt':
            return self.visit(ast.BinOp(left=n.args[0], op=ast.Pow(), right=ast.Constant(value=1/2)))
        return [{}, {}]

    def visit_BinOp(self, n):
        if hasattr(n, 'upper') and not n.upper:
            upper = False
        else:
            upper = True
        n.left.upper = upper
        left = self.visit(n.left)
        if isinstance(n.op, ast.Pow):
            if isinstance(n.right, ast.BinOp):
                if isinstance(n.right.left, ast.Constant) and isinstance(n.right, ast.Constant):
                    if isinstance(n.right.op, ast.Add):
                        p = n.right.left.value + n.right.value
                    elif isinstance(n.right.op, ast.Sub):
                        p = n.right.left.value - n.right.value
                    elif isinstance(n.right.op, ast.Mult):
                        p = n.right.left.value * n.right.value
                    elif isinstance(n.right.op, ast.Div):
                        p = n.right.left.value / n.right.value
                    elif isinstance(n.right.op, ast.Pow):
                        p = n.right.left.value ** n.right.value
                else:
                    # XXX
                    p = 1
            elif isinstance(n.right, ast.UnaryOp):
                if isinstance(n.right.operand, ast.Constant):
                    if isinstance(n.right.op, ast.USub):
                        p = - n.right.operand.value
                    elif isinstance(n.right.op, ast.UAdd):
                        p = n.right.operand.value
            elif isinstance(n.right, ast.Constant):
                p = n.right.value
            else:
                # XXX
                p = 1
            for u in left[0]:
                left[0][u] *= p
            for u in left[1]:
                left[1][u] *= p
            return left
        elif isinstance(n.op, ast.Mult):
            n.right.upper = upper
            right = self.visit(n.right)
            for u in right[0]:
                if u in left[0]:
                    left[0][u] += right[0][u]
                else:
                    left[0][u] = right[0][u]
            for u in right[1]:
                if u in left[1]:
                    left[1][u] += right[1][u]
                else:
                    left[1][u] = right[1][u]
            return left
        elif isinstance(n.op, ast.Div):
            n.right.upper = not upper
            right = self.visit(n.right)
            for u in right[0]:
                if u in left[0]:
                    left[0][u] += right[0][u]
                else:
                    left[0][u] = right[0][u]
            for u in right[1]:
                if u in left[1]:
                    left[1][u] += right[1][u]
                else:
                    left[1][u] = right[1][u]
            return left
        elif isinstance(n.op, ast.Add) or isinstance(n.op, ast.Sub):
            n.right.upper = upper
            left = reduce(left)
            right = reduce(self.visit(n.right))
            if are_equivalent(left, right):
                return left
            log.warning('The units of the two sides are not equivalent.')
            return [{}, {}]

    def visit_UnaryOp(self, n):
        return self.visit(n.operand)

    def visit_Expr(self, n):
        return self.visit(n.value)

    def generic_visit(self, n):
        return [{}, {}]


def unitize(s: ast.AST, working_dict={}) -> str:
    '''
    look for units of the variable names in the expression, cancel-out units
    that can be canceled out and return an expression of units that can be
    converted into latex using to_math
    '''

    ls = reduce(UnitHandler(False, working_dict).visit(s))

    # the var names that are of units in the main dict that are not _
    in_use = {working_dict[u] for u in working_dict
              if u.endswith(UNIT_PF) and working_dict[u] != ast.Name(id='_')}
    # var names in in_use whose values contain one of the DERIVED units
    in_use = [u for u in in_use
              if any([n.id in DERIVED
                      for n in [n for n in ast.walk(u) if isinstance(n, ast.Name)]])]
    # search in reverse order to choose the most recently used unit
    in_use.reverse()
    # if this unit is equivalent to one of them, return that
    for unit in in_use:
        if are_equivalent(UnitHandler(True, working_dict).visit(unit), ls):
            return unit

    upper = "*".join([u if ls[0][u] == 1 else f'{u}**{ls[0][u]}'
                      for u in ls[0]])
    lower = "*".join([u if ls[1][u] == 1 else f'{u}**{ls[1][u]}'
                      for u in ls[1]])

    s_upper = f'({upper})' if ls[0] else "_"
    s_lower = f'/({lower})' if ls[1] else ""
    return ast.parse(s_upper + s_lower).body[0].value


def are_equivalent(unit1: dict, unit2: dict) -> bool:
    '''
    return True if the units are equivalent, False otherwise
    '''

    unit1, unit2 = reduce(unit1), reduce(unit2)
    conditions = [
        # the numerators have the same elements
        set(unit1[0]) == set(unit2[0]) and \
        # each item's value (power) is the same in both
        all([unit1[0][e] == unit2[0][e] for e in unit1[0]]),
        # the denominators have the same elements
        set(unit1[1]) == set(unit2[1]) and \
        # and each item's value (power) is the same in both
        all([unit1[1][e] == unit2[1][e] for e in unit1[1]]),
    ]

    return all(conditions)


def reduce(ls: list) -> list:
    '''
    cancel out units that appear in both the numerator and denominator, those
    that have no name (_) and those with power of 0
    '''
    upper = {**ls[0]}
    lower = {**ls[1]}
    for u in ls[0]:
        if u in ls[1]:
            if upper[u] > lower[u]:
                upper[u] -= lower[u]
                del lower[u]
            elif upper[u] < lower[u]:
                lower[u] -= upper[u]
                del upper[u]
            else:
                del upper[u]
                del lower[u]
    for u in {**upper}:
        if upper[u] == 0 or u == '_':
            del upper[u]
    for u in {**lower}:
        if lower[u] == 0 or u == '_':
            del lower[u]
    return [upper, lower]
