# for word file handling
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
from xml.dom.minidom import parseString
from zipfile import ZipFile, ZIP_DEFLATED
from dataclasses import dataclass
# for file operations
from shutil import move, rmtree
# for access to resource template
from importlib.resources import files
# for temp directory
import tempfile
# for path manips
from os import path
# for regex
import re
# log info
import logging
# tag pattern
from ..processing import PATTERN
from . import Tag

logger = logging.getLogger(__name__)

DEFAULT_FILE = 'Untitled.docx'
TABLE_FLAG_INDEX = -1

GREEK_LETTERS = {
    'alpha':      'α',
    'nu':         'ν',
    'beta':       'β',
    'xi':         'ξ',
    'Xi':         'Ξ',
    'gamma':      'γ',
    'Gamma':      'Γ',
    'delta':      'δ',
    'Delta':      '∆',
    'pi':         'π',
    'Pi':         'Π',
    'epsilon':    'ϵ',
    'varepsilon': 'ε',
    'rho':        'ρ',
    'varrho':     'ϱ',
    'zeta':       'ζ',
    'sigma':      'σ',
    'Sigma':      'Σ',
    'eta':        'η',
    'tau':        'τ',
    'theta':      'θ',
    'vartheta':   'ϑ',
    'Theta':      'Θ',
    'upsilon':    'υ',
    'Upsilon':    'Υ',
    'iota':       'ι',
    'phi':        'φ',
    'varphi':     'ϕ',
    'Phi':        'Φ',
    'kappa':      'κ',
    'chi':        'χ',
    'lambda':     'λ',
    'Lambda':     'Λ',
    'psi':        'ψ',
    'Psi':        'Ψ',
    'mu':         'µ',
    'omega':      'ω',
    'Omega':      'Ω',
    }

MATH_ACCENTS = {
    'hat': '&#x0302;',
    'check': '&#x030C;',
    'breve': '&#x02D8;',
    'acute': '&#x0301;',
    'grave': '&#x0300;',
    'tilde': '&#x0303;',
    'bar': '&#x0304;',
    'vec': '&#x20D7;',
    'dot': '&#x0307;',
    'ddot': '&#x0308;',
    'dddot': '&#x20DB;',
    }

PRIMES = {'prime': "'", '2prime': "''", '3prime': "'''"}

TAG_ALT_FORM = '#{%s}'

@dataclass
class TagWord(Tag):
    alt: str
    address: list[ET.Element]
    index: int
    tbl: ET.Element | None = None
    tbl_row: ET.Element | None = None

class syntax:

    # things that are transformed, used for units and such
    transformed = {
        'degC': '<m:sSup><m:e><m:r><m:t> </m:t></m:r></m:e><m:sup><m:r><m:t>∘</m:t></m:r></m:sup></m:sSup><m:r><m:rPr><m:nor/></m:rPr><m:t>C</m:t></m:r>',
        'degF': '<m:sSup><m:e><m:r><m:t> </m:t></m:r></m:e><m:sup><m:r><m:t>∘</m:t></m:r></m:sup></m:sSup><m:r><m:rPr><m:nor/></m:rPr><m:t>F</m:t></m:r>',
        'deg': '<m:sSup><m:e><m:r><m:t> </m:t></m:r></m:e><m:sup><m:r><m:t>∘</m:t></m:r></m:sup></m:sSup>',
        'integral': '<m:r><m:t>&#x222B;</m:t></m:r>'
    }

    # some symbols
    minus = '-'
    times = '×'
    div = '÷'
    cdot = '⋅'
    halfsp = '&#8239;'
    neg = '¬'
    gt = '&gt;'
    lt = '&lt;'
    gte = '≥'
    lte = '≤'
    cdots = '⋯'
    vdots = '⋮'
    ddots = '⋱'

    greek_letters = GREEK_LETTERS
    math_accents = MATH_ACCENTS
    primes = PRIMES

    def txt(self, text):
        return f'<m:r><m:t xml:space="preserve">{text}</m:t></m:r>'

    def txt_rom(self, text):
        return f'<m:r><m:rPr><m:nor/></m:rPr><m:t xml:space="preserve">{text}</m:t></m:r>'

    def txt_math(self, text):
        return self.txt_rom(text)

    def sub(self, base, s):
        return f'<m:sSub><m:e>{base}</m:e><m:sub>{s}</m:sub></m:sSub>'

    def sup(self, base, s):
        return f'<m:sSup><m:e>{base}</m:e><m:sup>{s}</m:sup></m:sSup>'

    def rad(self, base):
        return f'<m:rad><m:radPr><m:degHide m:val="1"/></m:radPr><m:deg/><m:e>{base}</m:e></m:rad>'

    def summation(self, base, end):
        return f'<m:nary><m:naryPr><m:chr m:val="∑"/></m:naryPr><m:sub><m:r><m:t>i=1</m:t></m:r></m:sub><m:sup><m:r><m:t>{end}</m:t></m:r></m:sup><m:e>{base}</m:e></m:nary>'

    def func_name(self, name):
        return f'<m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>{name}</m:t></m:r>'

    def frac(self, num, den):
        return f'<m:f><m:num>{num}</m:num><m:den>{den}</m:den></m:f>'

    def math_disp(self, math):
        return f'<m:oMathPara><m:oMath>{math}</m:oMath></m:oMathPara>'

    def math_inln(self, math):
        return f'<m:oMath>{math}</m:oMath>'

    def greek(self, name):
        return self.txt(GREEK_LETTERS[name])

    def accent(self, acc, base):
        return f'<m:acc><m:accPr><m:chr m:val="{MATH_ACCENTS[acc]}"/></m:accPr><m:e>{base}</m:e></m:acc>'

    def prime(self, base, prime):
        return self.sup(base, self.txt(PRIMES[prime]))

    def delmtd(self, contained, kind=0):
        surround = '<m:dPr><m:begChr m:val="{}"/><m:endChr m:val="{}"/></m:dPr>'
        kinds = ['[]', '{}', '⌊⌋']
        form = '<m:d>{}<m:e>{}</m:e></m:d>'
        if kind == 0:
            return form.format('', contained)
        return form.format(surround.format(kinds[kind-1][0], kinds[kind-1][1]), contained)

    def matrix(self, elmts, full=False):
        if full:  # top level, full matrix
            m_form = '<m:m>{}</m:m>'
            rows = ''.join([f'<m:mr><m:e>{e}</m:e></m:mr>' for e in elmts])
            return self.delmtd(m_form.format(rows), 1)
        return '</m:e><m:e>'.join(elmts)

    def eqarray(self, eqns: list):
        form = '<m:eqArr>{}</m:eqArr>'
        line_form = '<m:e>{}</m:e>'
        align_chr = self.txt('&amp;=')
        return form.format(''.join([line_form.format(align_chr.join(eq)) for eq in eqns]))

class document:

    # the xml declaration
    declaration = '<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n'

    def __init__(self, infile=None, outfile=None):
        # the tag pattern
        self.pattern = PATTERN
        # temp folder for converted files
        self.temp_dir = tempfile.mkdtemp()
        self.infile = infile
        if infile:
            # input file specified
            tmp_fname = infile
        else:
            # file taken as input file when not explicitly set:
            tmp_fname = DEFAULT_FILE
            infile = files(__name__).joinpath('word.docx')

        with ZipFile(infile, 'r') as zin:
            file_contents = zin.read('word/document.xml')
            tmp_filename_full = path.join(self.temp_dir, path.splitext(path.basename(tmp_fname))[0])
            self.tmp_file = ZipFile(tmp_filename_full, 'w', compression=ZIP_DEFLATED)
            self.tmp_file.comment = zin.comment
            for file in zin.namelist():
                if file != 'word/document.xml':
                    self.tmp_file.writestr(file, zin.read(file))

        # extract always required namespaces
        self.namespaces = {}
        minidoc = parseString(file_contents)
        for k, v in minidoc.documentElement.attributes.items():
            if not k.startswith('xmlns:'):
                continue
            self.namespaces[k.replace('xmlns:', '', count=1)] = v

        # the xml tree representation of the document contents
        self.doc_tree = ET.fromstring(file_contents)
        for prefix, uri in self.namespaces.items():
            ET.register_namespace(prefix, uri)

        # the tags in the document
        self.tags = self.extract_tags(self.doc_tree)

        if outfile:
            self.outfile = path.abspath(outfile) 
        elif self.infile:
            base, ext = path.splitext(self.infile)
            self.outfile = base + '-out' + ext
        else:
            self.outfile = DEFAULT_FILE

    def normalized_contents(self, paragraph):
        pref_w = f'{{{self.namespaces["w"]}}}'
        ignored = [pref_w + tag for tag in ['bookmarkStart', 'bookmarkEnd', 'proofErr']]
        conts = []
        for child in paragraph:
            if child.tag == pref_w + 'r':
                if conts:
                    if type(conts[-1]) == list:
                        conts[-1].append(child)
                    else:
                        conts.append(['', child])
                else:
                    conts.append(['', child])
                for t in child:
                    if t.tag == pref_w + 't':
                        conts[-1][0] += t.text
            elif conts and type(conts[-1]) != list or child.tag not in ignored:
                conts.append(child)
        return conts

    def extract_paragraph_tags(self, parent: ET.Element, para: ET.Element, index: int) -> list[TagWord]:
        pref_w = f'{{{self.namespaces["w"]}}}'
        # get its contents and clear it
        contents = self.normalized_contents(para)
        para.clear()
        tags: list[TagWord] = []
        for cont in contents:
            if type(cont) != list:
                para.append(cont)
                continue
            if '#' not in cont[0]:
                # preserve properties
                for r in cont[1:]:
                    para.append(r)
                continue
            # replace with a new element
            w_r = ET.SubElement(para, pref_w + 'r')
            w_t = ET.SubElement(w_r, pref_w + 't',
                                {'xml:space': 'preserve'})
            # store full info about the tags inside
            for match in self.pattern.finditer(cont[0]):
                tags.append(TagWord(
                    name=match.group(2),
                    alt=TAG_ALT_FORM % match.group(2),
                    address=[parent, para, w_r, w_t],
                    block=cont[0].strip() == '#' + match.group(2),
                    table=False, # can be modified by caller
                    index=index,
                ))
            # remove \'s from the escaped #'s and change the tags form
            w_t.text = (re.sub(r'\\#', '#', self.pattern.sub(
                lambda tag:
                    tag.group(1) +
                    TAG_ALT_FORM % tag.group(2) +
                    tag.group(3),
                cont[0])))
        return tags

    def extract_tags(self, tree) -> list[TagWord]:
        pref_w = f'{{{self.namespaces["w"]}}}'
        tags = []
        for index, child in enumerate(tree[0]):
            if child.tag == pref_w + 'p':
                tags += self.extract_paragraph_tags(tree[0], child, index)
            elif child.tag == pref_w + 'tbl':
                for tr in child:
                    if tr.tag != pref_w + 'tr':
                        continue
                    for tc in tr:
                        cell_tags: list[TagWord] = []
                        for i, p in enumerate(tc):
                            if p.tag == pref_w + 'p':
                                cell_tags += self.extract_paragraph_tags(tc, p, i)
                        if len(cell_tags) != 1:
                            # no or many tags, cannot be considered for table
                            tags += cell_tags
                            continue
                        tag = cell_tags[0]
                        if not tag.block:
                            # inline, may be with other content
                            tags.append(tag)
                            continue
                        # table tag
                        tag.table = True
                        tag.tbl = child
                        tag.tbl_row = tr
                        tags.append(tag)
        return tags

    def _subs_tags(self, values={}):
        matched_tags = {}
        added: dict[ET.Element, int] = {}  # the added index to make up for the added elements
        for tag in self.tags:
            loc_parent, loc_para, loc_run, loc_text = tag.address
            if tag.name not in values:
                logger.warning(f'There is nothing to send to #{tag.name}.')
                # remove this entry to revert the left ones from their alt form
                loc_text.text = loc_text.text.replace(tag.alt, '#' + tag.name)
                continue
            matched_tags[tag.name] = True
            if tag.table:
                # fill table with matrix values
                for position, value in values[tag.name]:
                    if position != 'table':
                        continue
                    i_row_init = None
                    j_col_init = None
                    n_init_rows = None
                    n_init_cols = None
                    pref_w = f'{{{self.namespaces["w"]}}}'
                    for i, cr in enumerate(tag.tbl):
                        if cr.tag != pref_w + 'tr':
                            continue
                        if n_init_rows is not None:
                            n_init_rows += 1
                        if cr != tag.tbl_row:
                            continue
                        n_init_rows = 1
                        i_row_init = i
                        for j, cc in enumerate(cr):
                            if cc.tag != pref_w + 'tc':
                                continue
                            if n_init_cols is not None:
                                n_init_cols += 1
                            if cc == loc_parent:
                                n_init_cols = 1
                                j_col_init = j
                    for i, row_val in enumerate(value):
                        if n_init_rows < i + 1:
                            row_val_element = ET.Element(pref_w + 'tr')
                            for j in range(n_init_cols):
                                row_val_element.append(ET.Element(pref_w + 'tc'))
                                j_col_init = 0 # because this is a new row
                            tag.tbl.append(row_val_element)
                        else:
                            row_val_element = tag.tbl[i + i_row_init]
                        for j, val in enumerate(row_val):
                            if n_init_cols < j + 1:
                                col_val_element = ET.Element(pref_w + 'tc')
                                row_val_element.append(col_val_element)
                            else:
                                col_val_element = row_val_element[j + j_col_init]
                                for elm in col_val_element:
                                    if elm.tag == pref_w + 'p':
                                        col_val_element.remove(elm)
                            value_para = self.para_elts([('inline', val)])[0]
                            col_val_element.append(value_para)
                else:
                    matched_tags[tag.name] = False
                continue
            ans_parts = [*self.para_elts(values[tag.name])]
            added_current = added.setdefault(loc_para, 0)
            if tag.block:
                ans_parts.reverse()  # because they are inserted at the same index
                for ans in ans_parts:
                    loc_parent.insert(tag.index + added_current, ans)
                loc_parent.remove(loc_para)
                added[loc_para] += len(ans_parts) - 1  # minus the tag para (removed)
                continue
            # inline
            split_text = loc_text.text.split(tag.alt, 1)
            loc_text.text = split_text[1]
            index_run = list(loc_para).index(loc_run)
            pref_w = f'{{{self.namespaces["w"]}}}'
            # if there is only one para, insert its contents into the para
            if len(ans_parts) == 1:
                ans_runs = list(ans_parts[0])
                ans_runs.reverse()  # same reason as above
                for run in ans_runs:
                    loc_para.insert(index_run, run)
                beg_run = ET.Element(pref_w + 'r')
                beg_text = ET.SubElement(beg_run, pref_w + 't',
                                         {'xml:space': 'preserve'})
                beg_text.text = split_text[0]
                loc_para.insert(index_run, beg_run)
                continue
            # split the para and make new paras between the splits
            beg_para = ET.Element(pref_w + 'p')
            beg_run = ET.SubElement(beg_para, pref_w + 'r')
            beg_text = ET.SubElement(beg_run, pref_w + 't',
                                     {'xml:space': 'preserve'})
            beg_text.text = split_text[0]
            ans_parts.reverse()  # same reason as above
            for ans in ans_parts:
                loc_parent.insert(tag.index + added_current, ans)
            beg_index = tag.index + added_current
            loc_parent.insert(beg_index, beg_para)
            added[loc_para] += len(ans_parts) + 1
        for tag in values:
            if tag not in matched_tags:
                logger.warning(f'#{tag.name} not found in the document.')

    def collect_txt(self, content):
        paras = []
        para = [['text', '']]
        for cont in content:
            # so that it has a space before the inline eqn
            space = '' if para[-1][1].endswith(' ') or not para[-1][1] else ' '
            if para[-1][0] == 'text':
                if cont[0] == 'text':
                    if cont[1].strip():
                        para[-1][1] += space + escape(cont[1])
                    elif para[-1][1].strip():
                        paras.append(para)
                        para = [['text', '']]
                else:
                    if cont[0] == 'inline':
                        if para[-1][1].strip():
                            para[-1][1] += space
                        para.append(cont)
                    else:
                        if para[0][1].strip() or len(para) > 1:
                            paras.append(para)
                            para = [['text', '']]
                        paras.append([cont])
            else:
                if cont[0] == 'inline':
                    para.append(['text', space])
                    para.append(cont)
                elif cont[0] == 'text':
                    if cont[1].strip():
                        para.append(['text', space + escape(cont[1])])
                    elif len(para) > 1 or para[0][1].strip():
                        paras.append(para)
                        para = [['text', '']]
                else:
                    if para[0][1].strip() or len(para) > 1:
                        paras.append(para)
                        para = [['text', '']]
                    paras.append([cont])
        if para[0][1].strip() or len(para) > 1:
            paras.append(para)
        return paras

    def para_elts(self, content: list):
        w = self.namespaces['w']
        m = self.namespaces['m']
        para_start = f'<w:p xmlns:w="{w}" xmlns:m="{m}">'
        para_form = para_start + '{}</w:p>'
        run_form = '<w:r><w:t xml:space="preserve">{}</w:t></w:r>'
        paras = []
        for para in self.collect_txt(content):
            para_xml_ls = []
            for part in para:
                if part[0] == 'text':
                    if part[1].strip():
                        para_xml_ls.append(run_form.format(part[1]))
                else:
                    para_xml_ls.append(part[1])
            para_xml = para_form.format(''.join(para_xml_ls))
            paras.append(ET.fromstring(para_xml))

        return paras

    def write(self, values={}):
        if self.infile:
            self._subs_tags(values)
        else:
            for child in self.doc_tree[0]:
                self.doc_tree[0].remove(child)
            for val in values.values():
                for para in self.para_elts(val):
                    self.doc_tree[0].append(para)
        # take care of namespaces and declaration
        doc_xml = ET.tostring(self.doc_tree, encoding='unicode')
        searched = re.match(r'\<w:document.*?\>', doc_xml).group(0)
        used_nses = re.findall(r'(?<=xmlns\:)\w+', searched)
        for prefix, uri in self.namespaces.items():
            if prefix not in used_nses:
                self.doc_tree.set('xmlns:' + prefix, uri)

        doc_xml = self.declaration + \
            ET.tostring(self.doc_tree, encoding='unicode')
        self.tmp_file.writestr('word/document.xml', doc_xml)
        tmp_filename = self.tmp_file.filename
        self.tmp_file.close()

        logger.info('[writing file] %s', self.outfile)
        move(tmp_filename, self.outfile)

        rmtree(self.temp_dir)


