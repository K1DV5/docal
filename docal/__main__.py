'''
script handler
'''
from argparse import ArgumentParser, BooleanOptionalAction
from os import path
from docal import processor
from docal.parsers import excel, dcl
from docal.document import word, latex

def calculation_file(arg: str) -> str:
    'check if the argument is a path to a python script'
    if arg.endswith('.py') or arg.endswith('.xlsx') or arg.endswith('.dcl'):
        return arg
    raise ValueError("The calculation file name must end with '.py'.")


def document_file(arg: str) -> str:
    'same as above for documents'
    if arg.endswith('.docx') or arg.endswith('.tex'):
        return arg
    raise ValueError("The document names must end with '.docx' or '.tex'.")


# command line arguments
parser = ArgumentParser(description="Process the script file, inject it to "
                        "the input document and produce the output document")
parser.add_argument(
    'script', help='The calculation file/script', type=calculation_file, nargs='?')
parser.add_argument(
    '-i', '--input', help='The document file to be modified', type=document_file)
parser.add_argument(
    '-o', '--output', help='The destination document file', type=document_file)
parser.add_argument('-c', '--clear', action='store_true',
                    help='Clear the calculations and try to '
                    'revert the document to the previous state. '
                    'Only for the calculation ranges in LaTeX files.')
parser.add_argument('--lsp', help='Start as LSP server', action=BooleanOptionalAction)
parser.add_argument('-l', '--log-level', choices=['INFO', 'WARNING', 'ERROR', 'DEBUG'],
                    help='How much info you want to see')


args = parser.parse_args()

handlers = {
    '.tex': latex,
    '.docx': word
}

def main():
    '''
    main function in this script
    '''
    if args.lsp:
        from docal.lsp import server
        server.start_io()
        return
    extension_i = path.splitext(args.input)[1] if args.input else None
    extension_o = path.splitext(args.output)[1] if args.output else None
    try:
        handler = handlers[extension_i if extension_i else extension_o]
        doc = handler.document(args.input, args.output)
        proc = processor(handler.syntax(), doc.tags, args.log_level)
        if not args.clear:
            calculation = path.abspath(args.script)
            kind = path.splitext(calculation)[1]
            if kind == '.py':
                with open(args.script, encoding='utf-8') as file:
                    instructions = file.read()
            elif kind == '.xlsx':
                instructions = excel.parse(calculation)
            elif kind == '.dcl':
                instructions = dcl.parse(args.script)
            else:
                instructions = ''
            proc.send(instructions)
        doc.write(proc.contents)
    except Exception as exc:
        if args.log_level == 'DEBUG':
            raise
        else:
            print('ERROR:', str(exc))


if __name__ == '__main__':
    main()
