# -*- encoding: utf-8 -*-
__author__ = 'tla'

import json
import unittest

from tpen2tei.parse import from_sc
from config import config as config

class Test (unittest.TestCase):

    # Our default (and example) list of special characters that might occur as
    # glyph (<g/>) elements. A true list should be passed to the from_sc call.
    # The key is the normalized form; the tuple is (xml:id, description).
    _armenian_glyphs = {
        'աշխարհ': ('asxarh', 'ARMENIAN ASHXARH SYMBOL'),
        'ամենայն': ('amenayn', 'ARMENIAN AMENAYN SYMBOL'),
        'որպէս': ('orpes', 'ARMENIAN ORPES SYMBOL'),
        'երկիր': ('erkir', 'ARMENIAN ERKIR SYMBOL'),
        'երկին': ('erkin', 'ARMENIAN ERKIN SYMBOL'),
        'ընդ': ('und', 'ARMENIAN END SYMBOL'),
        'ըստ': ('ust', 'ARMENIAN EST SYMBOL'),
        'պտ': ('ptlig', 'ARMENIAN PEH-TIWN LIGATURE'),
        'թե': ('techlig', 'ARMENIAN TO-ECH LIGATURE'),
        'թի': ('tinilig', 'ARMENIAN TO-INI LIGATURE'),
        'թէ': ('tehlig', 'ARMENIAN TO-EH LIGATURE'),
        'էս': ('eslig', 'ARMENIAN EH-SEH LIGATURE'),
        'ես': ('echslig', 'ARMENIAN ECH-SEH LIGATURE'),
        'յր': ('yrlig', 'ARMENIAN YI-REH LIGATURE'),
        'զմ': ('zmlig', 'ARMENIAN ZA-MEN LIGATURE'),
        'թգ': ('tglig', 'ARMENIAN TO-GIM LIGATURE'),
        'ա': ('avar', 'ARMENIAN AYB VARIANT'),
        'հ': ('hvar', 'ARMENIAN HO VARIANT'),
        'յ': ('yabove', 'ARMENIAN YI SUPERSCRIPT VARIANT')
    }

    def setUp(self):
        settings = config()

        self.tei_ns = settings['namespaces']['tei']
        self.xml_ns = settings['namespaces']['xml']

        self.ns_id = '{{{:s}}}id'.format(self.xml_ns)
        self.ns_lb = '{{{:s}}}lb'.format(self.tei_ns)
        self.ns_note = '{{{:s}}}note'.format(self.tei_ns)
        self.ns_pb = "{{{:s}}}pb".format(self.tei_ns)
        self.ns_text = '{{{:s}}}text'.format(self.tei_ns)

        self.testfiles = settings['testfiles']
        msdata = load_JSON_file(self.testfiles['json'])
        self.testdoc = from_sc(msdata, special_chars=self._armenian_glyphs)

    def test_basic(self):
        self.assertIsNotNone(self.testdoc.getroot())
        self.assertEqual(self.testdoc.getroot().tag, '{{{:s}}}TEI'.format(self.tei_ns))

    def test_comment(self):
        """Need to check that any TPEN annotations on a line get passed as
        <note> elements linked to the correct line in the @target attribute."""
        root = self.testdoc.getroot()
        text_part = root.find(self.ns_text)
        self.assertIsNotNone(text_part)
        for tag in text_part.iterfind(".//{:s}".format(self.ns_note)):
            target = tag.attrib.get('target')
            self.assertTrue(target and target == '#l101280110')

    def test_glyphs(self):
        """Need to make sure that the glyph elements present in the JSON
        transcription appear as glyph elements in the char_decl header, and
        appear correctly referenced as g elements in the text."""

        # input is <g ref="աշխարհ">աշխար</g>
        # output should be <g ref="#asxarh">աշխար</g>
        # another input is <g ref="">աշխարհ</g>

        test_input = [('#պտ', ''), ('աշխարհ', 'աշխար'), ('#asxarh', ''), ('', 'աշխարհ'), ('', 'ա'), ('', 'աշխարհ')]

        # check if 'char_decl' exists and is defined at the right place
        root = self.testdoc.getroot()
        tei_header = root.find("{{{:s}}}teiHeader".format(self.tei_ns))
        self.assertIsNotNone(tei_header)
        encoding_desc = tei_header.find("{{{:s}}}encodingDesc".format(self.tei_ns))
        self.assertIsNotNone(encoding_desc)
        char_decl = encoding_desc.find("{{{:s}}}charDecl".format(self.tei_ns))
        self.assertIsNotNone(char_decl)

        focused_tags = ['glyphName', 'mapping']
        file_tags = {"{{{:s}}}{:s}".format(self.tei_ns, tag): tag for tag in focused_tags}

        # for every test-tag check, if it is declaration
        char_decls = []
        for declaration in char_decl:
            self.assertEqual(declaration.tag, "{{{:s}}}glyph".format(self.tei_ns))
            id = declaration.attrib.get(self.ns_id)
            self.assertTrue(id)

            values = {}
            for child in declaration:
                if child.tag in file_tags:
                    values[file_tags[child.tag]] = child.text

            # check, if the declaration contains a 'mapping' and 'glyphName' part
            for entry in focused_tags:
                self.assertTrue(values.get(entry))
            char_decls.append((id, values['mapping']))

        # check if all tags from test_input are declared
        for tag in test_input:
            if tag[0]:
                key = tag[0][1:] if tag[0].startswith('#') else tag[0]
            else:
                key = tag[1]
            for decl in char_decls:
                if key in decl:
                    break
            else:
                self.assertTrue(False, 'Could not find declaration for tag <g ref="{0}">{1}</g>'.format(*tag))

    def test_linebreaks(self):
        """Need to make sure line breaks are added, while preserving any
        trailing space on the original transcription line. Also check that
        line xml:id is being calculated correctly."""

        # test results 'xml:id': ('n', 'trailing space)
        test_results = {"l101276867": ("1", False), "l101276826": ("1", False),
                        "l101276868": ("2", True), "l101276922": ("2", True),
                        "l101276869": ("3", True), "l101276923": ("3", False),
                        "l101276870": ("4", False), "l101276924": ("4", False),
                        "l101276871": ("5", False), "l101276925": ("5", False),
                        "l101276872": ("6", False), "l101276926": ("6", False),
                        "l101276873": ("7", True), "l101276834": ("7", True),
                        "l101276874": ("8", False), "l101276927": ("8", True),
                        "l101276875": ("9", True), "l101276928": ("9", False),
                        "l101276876": ("10", True), "l101276929": ("10", True),
                        "l101280110": ("11", True), "l101276930": ("11", True),
                        "l101276878": ("12", False), "l101276931": ("12", True),
                        "l101276879": ("13", False), "l101276840": ("13", False),
                        "l101276880": ("14", False), "l101276841": ("14", False),
                        "l101276881": ("15", True), "l101276932": ("15", True),
                        "l101276882": ("16", True), "l101276843": ("16", True),
                        "l101276883": ("17", True), "l101276933": ("17", False),
                        "l101276884": ("18", False), "l101276845": ("18", False),
                        "l101276885": ("19", False), "l101276934": ("19", False),
                        "l101276886": ("20", True), "l101276848": ("20", True),
                        "l101276887": ("21", False), "l101276935": ("21", True),
                        "l101276888": ("22", False), "l101276850": ("22", True),
                        "l101276889": ("23", True), "l101276936": ("23", False),
                        "l101276890": ("24", False), "l101276937": ("24", False),
                        "l101276891": ("25", False), "l101276853": ("25", False)}
        unchecked_lines = {key for key in test_results.keys()}

        for parent_element in self.testdoc.getroot().iterfind(".//{{{:s}}}ab".format(self.tei_ns)):
            line_id = None
            line_text = ""
            for element in parent_element:
                tag = element.tag
                if tag in [self.ns_pb, self.ns_note]:
                    line_id = None
                    line_text = ""
                    continue
                elif tag == self.ns_lb:
                    n = element.attrib.get('n')
                    line_id = element.attrib.get(self.ns_id)
                    self.assertTrue(line_id and line_id in test_results, 'Id not defined')
                    self.assertTrue(n, 'Number not defined')

                    # check that line xml:id is being calculated correctly.
                    self.assertEqual(n, test_results.get(line_id)[0], "Wrong Number/Id")

                if line_id and element.text:
                    line_text += element.text
                if line_id and element.tail:
                    line_text += element.tail

                if line_text.endswith("\n"):
                    self.assertTrue(line_id)

                    # check trailing spaces
                    if line_text.endswith(" \n"):
                        self.assertTrue(test_results.get(line_id)[1])
                    else:
                        self.assertFalse(test_results.get(line_id)[1])
                    unchecked_lines.discard(line_id)
                    line_text = ""
                    line_id = None

            self.assertEqual(0, len(unchecked_lines), "Test file seems incomplete!")
            break
        else:
            self.assertFalse(True, "No content found!")

    def test_columns(self):
        """Need to check that column transitions within the same page are
        detected and an appropriate XML element is inserted."""

        for lb_element in self.testdoc.getroot().iterfind(".//{:s}".format(self.ns_lb)):
            n = lb_element.attrib.get('n')
            line_id = lb_element.attrib.get(self.ns_id)
            if line_id == "l101276891" and n == "25":
                pb = False
                for sibling in lb_element.itersiblings():
                    if sibling.tag == "{{{:s}}}lb".format(self.tei_ns):
                        self.assertTrue(pb == True)
                        self.assertEqual(sibling.attrib.get('n'), "1", "Unexpected line")
                        self.assertEqual(sibling.attrib.get(self.ns_id), "l101276826", "Unexpected line")
                        break
                    if sibling.tag == "{{{:s}}}pb".format(self.tei_ns):
                        self.assertEqual(sibling.attrib.get('n'), '075v')
                        pb = True
                else:
                    self.assertTrue(False, "Missing Pagebreak")
                break

    def test_functioning_namespace(self):
        """Just need to check that the XML document that gets returned has
        the correct namespace settings for arbitrary elements in the middle."""

        tei_ns = "{{{:s}}}".format(self.tei_ns)
        xml_ns = "{{{:s}}}".format(self.xml_ns)

        for element in self.testdoc.getroot().getiterator():
            self.assertEqual(element.nsmap, {None: '{:s}'.format(self.tei_ns)})
            for key in element.attrib.keys():
                if key.startswith('{'):
                    self.assertTrue(key.startswith(tei_ns) or key.startswith(xml_ns), 'Undefined Namespace')

    # Correction code for the early conventions
    def test_cert_correction(self):
        pass

    def test_glyph_correction(self):
        pass

    def test_type_to_rend(self):
        pass

    def test_corr_to_subst(self):
        pass


def load_JSON_file(filename, encoding='utf-8'):
    data = ""
    try:
        with open(filename, encoding=encoding) as testfile:
            data = json.load(testfile)
        testfile.close()
    except FileNotFoundError:
        print("""File "{:s}" not found!""".format(filename))
    except ValueError:
        print("""File "{:s}" might not be a valid JSON file!""".format(filename))
    return data
