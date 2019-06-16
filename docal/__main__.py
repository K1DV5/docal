'''
script handler
'''
from argparse import ArgumentParser
from os import path
from glob import glob
from docal import document


def calculation_file(arg: str) -> str:
    'check if the argument is a path to a python script'
    if arg.endswith('.py') or arg.endswith('.xlsx'):
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
    'script', help='The calculation file/script', type=calculation_file)
parser.add_argument(
    '-i', '--input', help='The document file to be modified', type=document_file)
parser.add_argument(
    '-o', '--output', help='The destination document file', type=document_file)
parser.add_argument('-c', '--clear', action='store_true',
                    help='Clear the calculations and try to '
                    'revert the document to the previous state. '
                    'Only for the calculation ranges in LaTeX files.')
parser.add_argument('-l', '--log-level', choices=['INFO', 'WARNING', 'ERROR', 'DEBUG'],
                    help='How much info you want to see')


args = parser.parse_args()


def main():
    '''
    main function in this script
    '''
    try:
        d = document(args.input, to_clear=args.clear, log_level=args.log_level)
        if args.script:
            if args.script.endswith('.py'):
                with open(args.script, encoding='utf-8') as file:
                    instructions = file.read()
                d.send(instructions)
            else:
                d.from_xl(args.script)
        d.write(args.output)
    except Exception as exc:
        if args.log_level == 'DEBUG':
            raise
        else:
            print('ERROR:', exc)
            exit()


if __name__ == '__main__':
    main()
