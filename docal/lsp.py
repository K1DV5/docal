from ast import Assign, Constant, Name, parse, unparse
from lsprotocol import types
from pygls.server import LanguageServer
from importlib.metadata import version

from docal import processing

class DocalLSP(LanguageServer):
    pass

server = DocalLSP(__package__, version(__package__))
max_value_len = 50
cutoff_len = max_value_len // 2

def is_docal_file(uri: str) -> bool:
    return uri.endswith(".docal.py")

@server.feature(types.INITIALIZE)
def on_initialize(ls: DocalLSP, params: types.InitializeParams):
    return {
        'capabilities': {
            'textDocumentSync': types.TextDocumentSyncKind.Full,
        }
    }

@server.feature(types.TEXT_DOCUMENT_INLAY_HINT)
def inlay_hints(ls: DocalLSP, params: types.InlayHintParams):
    if not is_docal_file(params.text_document.uri):
        return
    items = []
    start_line = params.range.start.line
    end_line = params.range.end.line
    text = ls.workspace.get_document(params.text_document.uri).source
    globals = {}
    try:
        tree = parse(text)
    except SyntaxError:
        return
    for part in tree.body:
        try:
            exec(unparse(part), globals=globals)
        except:
            break
        if type(part) is not Assign:
            continue
        targets: list[Name] = []
        for target in part.targets:
            targets += processing.find_name_targets(target)
        len_targets = len(targets)
        if part.lineno - 1 < start_line \
            or part.end_lineno - 1 > end_line \
            or len_targets == 1 and type(part.value) is Constant:
            continue
        values = []
        for target in targets:
            value = str(globals[target])
            if len(value) > max_value_len:
                value =  f'{value[:cutoff_len]}...{value[-cutoff_len:]}'
            values.append(f'{target if len_targets > 1 else ""} = {value}'.strip())
        items.append(
            types.InlayHint(
                label=', '.join(values),
                kind=types.InlayHintKind.Type,
                padding_left=True,
                padding_right=True,
                position=types.Position(
                    line=part.end_lineno - 1,
                    character=part.value.end_col_offset,
                ),
            )
        )

    return items

@server.feature(types.INLAY_HINT_RESOLVE)
def inlay_hint_resolve(hint: types.InlayHint):
    if type(hint.label) is str:
        n = hint.label.lstrip('= ')
        hint.tooltip = f"Computed value of the variable: {n}"
    return hint

if __name__ == '__main__':
    server.start_io()
