
class DCLCalc:

    dcl_pre_code = ['from math import *']

    def repl_asc(self, lines: str):

        lines = lines.split('\n')
        # by value! not to repeat the last ones
        py_lines = self.dcl_pre_code[:]
        comment_pat = re.compile(r'^(?=[^#:].*?(\w+\s+?\w+)|(\\\w+).*?$)')
        for line in lines:
            # import statements and the like preceded with :
            line = comment_pat.sub('# ', line)
            py_lines.append(re.sub(r'^\:', '', line))
        py_legal = '\n'.join(py_lines)
        # change power symbol, not in comments
        py_legal = re.sub(r'(?sm)^([^\#].*?)\^', r'\1**', py_legal)
        # number coefficients like 2x
        py_legal = re.sub(r'(?<=[0-9])( ?[a-df-zA-Z_]|\()', '*\\1', py_legal)

        return py_legal

