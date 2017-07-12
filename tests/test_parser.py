import unittest

from tpen2tei.parse import from_sc
from contextlib import redirect_stderr
from config import config as config
import helpers
import io

__author__ = 'tla'


class Test (unittest.TestCase):

    def setUp(self):
        settings = config()

        self.namespaces = settings['namespaces']
        self.tei_ns = settings['namespaces']['tei']
        self.xml_ns = settings['namespaces']['xml']

        self.ns_id = '{{{:s}}}id'.format(self.xml_ns)
        self.ns_lb = '{{{:s}}}lb'.format(self.tei_ns)
        self.ns_note = '{{{:s}}}note'.format(self.tei_ns)
        self.ns_pb = "{{{:s}}}pb".format(self.tei_ns)
        self.ns_text = '{{{:s}}}text'.format(self.tei_ns)

        self.glyphs = helpers.glyph_struct(settings['armenian_glyphs'])

        self.testfiles = settings['testfiles']
        msdata = helpers.load_JSON_file(self.testfiles['json'])
        self.testdoc = from_sc(
            msdata,
            special_chars=self.glyphs
        )

        user_defined = {'title': 'Ժամանակագրութիւն', 'author': 'Մատթէոս Ուռհայեցի'}
        legacydata = helpers.load_JSON_file(self.testfiles['legacy'])
        self.legacydoc = from_sc(legacydata, metadata=user_defined,
                                 special_chars=self.glyphs,
                                 numeric_parser=helpers.armenian_numbers,
                                 text_filter=helpers.tpen_filter)
        self.brokendata = helpers.load_JSON_file(self.testfiles['broken'])

    def test_basic(self):
        self.assertIsNotNone(self.testdoc.getroot())
        self.assertEqual(self.testdoc.getroot().tag, '{{{:s}}}TEI'.format(self.tei_ns))

    def test_armenian_numbers(self):
        """This actually tests my number parsing algorithm in the helpers module. It should eventually
        move outside tpen2tei."""
        self.assertEqual(helpers.armenian_numbers('ա'), 1)
        self.assertEqual(helpers.armenian_numbers('ի'), 20)
        self.assertEqual(helpers.armenian_numbers('ո'), 600)
        self.assertEqual(helpers.armenian_numbers('վ'), 3000)
        self.assertEqual(helpers.armenian_numbers('ճիա'), 121)
        self.assertEqual(helpers.armenian_numbers('դ՟ճ՟. և լ՟գ՟.'), 433)
        self.assertEqual(helpers.armenian_numbers('.ժ՟ե՟ \nռ՟'), 15000)

    def test_parse_error(self):
        """Check that a reasonable error message is returned from a JSON file that
        contains badly-formed XML."""
        md = {'short_error': True}
        with io.StringIO() as buf, redirect_stderr(buf):
            badresult = from_sc(self.brokendata, md)
            errormsg = buf.getvalue()
        self.assertRegex(errormsg, 'Parsing error in the JSON')
        errorlines = errormsg.splitlines()[1:]
        self.assertEqual(len(errorlines), 55)
        self.assertRegex(errorlines[0], 'Affected portion of XML is 493: \<pb')

    def test_comment(self):
        """Need to check that any TPEN annotations on a line get passed as
        <note> elements linked to the correct line in the @target attribute."""
        root = self.testdoc.getroot()
        text_part = root.find(self.ns_text)
        self.assertIsNotNone(text_part)
        for tag in text_part.iterfind(".//{:s}".format(self.ns_note)):
            target = tag.attrib.get('target')
            self.assertTrue(target and target == '#l101280110')

    def test_numbers(self):
        """Check that all the 'num' elements have well-defined values when we have used a number parser.
        Ideally this would check against the xsd: datatypes but I am not sure how to easily accomplish that."""
        for number in self.legacydoc.getroot().findall(".//{%s}num" % self.tei_ns):
            self.assertIn('value', number.keys())
            try:
                self.assertIsInstance(float(number.get('value')), float)
            except ValueError:
                self.fail()

    def test_filter(self):
        """Check that the text filter is producing the desired output in the transcription."""
        testlb = self.legacydoc.getroot().find(".//tei:lb[@xml:id='l100784691']",
                                               namespaces={'tei': 'http://www.tei-c.org/ns/1.0',
                                                           'xml':'http://www.w3.org/XML/1998/namespace'})
        self.assertEqual(testlb.getnext().tag, '{http://www.tei-c.org/ns/1.0}num')
        self.assertEqual(testlb.getnext().tail, " վանք. և ե՛տ զայս ")
        self.assertEqual(testlb.getnext().getnext().tail, " գը֊\n")


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
            charid = declaration.attrib.get(self.ns_id)
            self.assertTrue(charid)

            values = {}
            for child in declaration:
                if child.tag in file_tags:
                    values[file_tags[child.tag]] = child.text

            # check, if the declaration contains a 'mapping' and 'glyphName' part
            for entry in focused_tags:
                self.assertTrue(values.get(entry))
            char_decls.append((charid, values['mapping']))

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
                        self.assertTrue(pb)
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

    def test_included_metadata_M1731(self):
        """Check that the TPEN-supplied metadata ends up in the TEI header of the output."""

        # Check for correct TEI schema
        pis = self.testdoc.xpath('//processing-instruction()')
        self.assertEqual(len(pis), 1)
        for pi in pis:
            if pi.target is 'xml-model':
                self.assertEqual(pi.get('href'),
                                 'http://www.tei-c.org/release/xml/tei/custom/schema/relaxng/tei_all.rng')

        # Check for correct title
        titlestmt = self.testdoc.getroot().find(".//{%s}titleStmt" % self.tei_ns)
        for child in titlestmt:
            if child.tag is 'title':
                self.assertEqual(child.text, "M1731 (F) 1")

        # Check for correct MS description
        msdesc = self.testdoc.getroot().find(".//{%s}msDesc" % self.tei_ns)
        self.assertEqual(len(msdesc), 1)
        for child in msdesc:
            if child.tag is 'msIdentifier':
                self.assertEqual(child['{%s}id' % self.xml_ns], 'F')
                self.assertEqual(len(child), 3)
                for grandchild in child:
                    if grandchild.tag is 'settlement':
                        self.assertEqual(grandchild.text, "Yerevan")
                    if grandchild.tag is 'repository':
                        self.assertEqual(grandchild.text, "Matenadaran")
                    if grandchild.tag is 'idno':
                        self.assertEqual(grandchild.text, "1731")

    def test_passed_metadata_M1896(self):
        """Check that user-supplied metadata has its effect on the TEI header."""
        # Check for correct title
        titlestmt = self.legacydoc.getroot().find(".//{%s}titleStmt" % self.tei_ns)
        self.assertEqual(len(titlestmt), 2)
        for child in titlestmt:
            if child.tag is 'title':
                self.assertEqual(child.text, "Ժամանակագրութիւն")
            if child.tag is 'author':
                self.assertEqual(child.text, "Մատթէոս Ուռհայեցի")

        # Check for correct MS description
        msdesc = self.legacydoc.getroot().find(".//{%s}msDesc" % self.tei_ns)
        self.assertEqual(len(msdesc), 2)
        for child in msdesc:
            if child.tag is 'msIdentifier':
                self.assertEqual(child['{%s}id' % self.xml_ns], 'A')
                self.assertEqual(len(child), 3)
                for grandchild in child:
                    if grandchild.tag is 'settlement':
                        self.assertEqual(grandchild.text, "Yerevan")
                    if grandchild.tag is 'repository':
                        self.assertEqual(grandchild.text, "Matenadaran")
                    if grandchild.tag is 'idno':
                        self.assertEqual(grandchild.text, "1896")
            if child.tag is 'history':
                self.assertEqual(len(child), 2)
                for grandchild in child:
                    if grandchild.tag is 'origDate':
                        self.assertEqual(grandchild.text, "1689")
                    if grandchild.tag is 'origPlace':
                        self.assertEqual(grandchild.text, "Bitlis")

    # Correction code for the early conventions
    def test_cert_correction(self):
        """Test that all numeric 'cert' values in a transcription are converted to one of high/medium/low."""
        cert_attributes = self.legacydoc.getroot().xpath('.//attribute::cert')
        self.assertEquals(len(cert_attributes), 32)
        cert_values = {'low': 11, 'medium': 20, 'high': 1}
        for attr in cert_attributes:
            self.assertIn(attr, ['high', 'medium', 'low'])
            cert_values[attr] -= 1
        for v in cert_values.values():
            self.assertEqual(v, 0)

    def test_glyph_correction(self):
        """Test that the various old ways glyphs got encoded in the transcription have the correct end result"""
        # աշխարհ: 134 + 6
        # թե: 114 + 10
        # թէ: 210 + 4
        # պտ: 320 + 18
        # ընդ: 57 + 9
        # որպէս: 17 + 2
        # Get the allowed glyphs
        glyphs = set(['#%s' % x.get('{%s}id' % self.xml_ns)
                      for x in self.legacydoc.getroot().findall('.//{%s}glyph' % self.tei_ns)])
        # Get all the 'g' elements and check that they have valid refs
        gs = self.legacydoc.getroot().findall('.//{%s}g' % self.tei_ns)
        for g in gs:
            self.assertIn(g.get('ref'), glyphs)

        expected = {'#asxarh': 140, '#techlig': 124, '#tehlig': 214, '#ptlig': 338, '#und': 66, '#orpes': 19}
        for k, v in expected.items():
            thisg = self.legacydoc.getroot().xpath('.//tei:g[@ref="%s"]' % k, namespaces=self.namespaces)
            self.assertEqual(len(thisg), v)

    def test_type_to_rend(self):
        """Test that the erroneous 'type' attribute on the 'del' element gets corrected to 'rend'"""
        dels = self.legacydoc.getroot().findall('.//{%s}del' % self.tei_ns)
        self.assertEqual(len(dels), 241)
        for d in dels:
            self.assertTrue('type' not in d)

    def test_corr_to_subst(self):
        """Tests that the erroneous 'corr' elements were turned into 'subst' ones"""
        corrs = self.legacydoc.getroot().findall('.//{%s}corr' % self.tei_ns)
        substs = self.legacydoc.getroot().findall('.//{%s}subst' % self.tei_ns)
        self.assertEqual(len(corrs), 0)
        self.assertEqual(len(substs), 115)
