
class DCLCalc:

    dcl_pre_code = ['from math import *']

    def process():
        processed = []
        doc_tree = ET.fromstring(what)
        for child in doc_tree:
            if child.tag in ('ascii', 'python'):
                if child.tag == 'ascii':
                    child.text = self.repl_asc(child.text)
                for part in self.process_content(child.text):
                    processed.append(part)
            elif child.tag == 'excel':
                for part in self.repl_xl(child.text):
                    processed.append(part)
        return processed

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


