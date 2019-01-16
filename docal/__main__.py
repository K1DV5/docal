'''
script handler
'''
from argparse import ArgumentParser
from os import path
from glob import glob
from docal import document


def next_to(script):
    '''
    find a file that ends with .tex or .docx and is in the same directory as
    the script and return the first match, show error message and exit if none
    is found.
    '''
    matches = [f for f in glob(path.splitext(script)[0] + '.*')
               if path.splitext(f)[1] in ['.tex', '.docx']]
    if matches:
        infile = matches[0]
    else:
        print('ERROR:', 'Cannot find a word or tex file here')
        exit()

    return infile


# command line arguments
parser = ArgumentParser(description="Process the script file, inject it to "
                        "the input document and produce the output document")
parser.add_argument('script', help='The calculation file/script')
parser.add_argument('-i', '--input', help='The document file to be modified')
parser.add_argument('-o', '--output', help='The destination document file')
parser.add_argument('-c', '--clear', action='store_true',
                    help='Clear the calculations and try to '
                    'revert the document to the previous state. '
                    'Only for the calculation ranges in LaTeX files.')
args = parser.parse_args()
args.input = args.input if args.input else next_to(args.script)
args.output = 0 if args.output == '0' else args.output


def main():
    '''
    main function in this script
    '''
    with open(args.script) as file:
        instructions = file.read()

    d = document(args.input, to_clear=args.clear)
    d.send(instructions)
    d.write(args.output)


try:
    main()
except Exception as exc:
    print('ERROR:', f'[{exc.__class__.__name__}]', exc.args[0])
    exit()
