__author__ = 'tla'

import unittest

from tpen2tei.parse import from_sc
from tpen2tei.wordtokenize import Tokenizer
from lxml.etree import fromstring, XMLSyntaxError
from json.decoder import JSONDecodeError

from config import config as config
import helpers

class Test (unittest.TestCase):

    def setUp(self):
        self.settings = config()

        self.tei_ns = self.settings['namespaces']['tei']
        self.xml_ns = self.settings['namespaces']['xml']

        self.glyphs = helpers.glyph_struct(self.settings['armenian_glyphs'])

        self.testfiles = self.settings['testfiles']
        msdata = helpers.load_JSON_file(self.testfiles['json'])
        self.testdoc_noglyphs = from_sc(msdata)
        self.testdoc = from_sc (
            msdata,
            special_chars = self.glyphs
        )

    # def setUp(self):
    #     with open('./data/M1731.json', encoding='utf-8') as fh:
    #         jdata = json.load(fh)
    #     self.testdoc = from_sc(jdata)

    def test_simple(self):
        """Test that basic parsing with no specified options works properly."""
        tokens = Tokenizer().from_etree(self.testdoc_noglyphs)['tokens']
        first = {'t': 'եղբայրն', 'n': 'եղբայրն', 'lit': 'եղբայրն', 'context': 'text/body/ab',
                 'page': {'n': '075r'}, 'line': {'n': '1', 'xml:id': 'l101276867'}}
        last  = {'t': 'զօրա֊', 'n': 'զօրա֊', 'lit': 'զօրա֊', 'context': 'text/body/ab',
                 'page': {'n': '075v'}, 'line': {'n': '25', 'xml:id': 'l101276853'}}
        self.assertEqual(tokens[0], first)
        self.assertEqual(tokens[-1], last)
        self.assertEqual(313, len(tokens))
        origtext = 'եղբայրն ներսէսի ի կարմիր վանգն. և նա՛ յաջորդեաց ի հոռոմ կլայն. և յետ նր ներսէս մինչև ի ոհաննէս. ' \
                   'և յայնմ ժմկի դաւիթ անուն ոմն ձեռնադրեա՛լ մինչև ի ստեփա֊նոս որ գերեցաւ ի յեգիոս և ի սիս ձեռնա֊' \
                   'դրեալ կթղս. մինչև ցթումավդպտն. և բաժա֊նեա՛լ նր եղև աթոռն սահմանել յէջմիածին և զբունն ոչ ' \
                   'խափանեալ զի դեռևս կենդա֊նի էր կաթղսն սըսա՛. զի ի լուսաւորչէն մինչև ի նայ էր հասեալ կթղսութի. և ' \
                   'նա՛ ոչ եղև, քաղաքն զօրավար եդաք և անտի կամեցաք զի նա՛ դեռևս կենդանի էր։ թ. եղբայրք զա֊' \
                   'քարիայ և իւանա՛ դարձաւ վրացի և եղբայրըն ոչ. նա՛ խնդրէր վրան զի պատարագ ա֊րասցեն։ Իսկ ընդ ' \
                   'աւուրսն ընդ այնոսիկ, և ի ամին ն՟ա՟. եղև սով սաստիկ ի բզմ տեղիս. բայց յաշխարհն հարաւոյ ի յերկրին ' \
                   'տաճկա՛ց եղև նեղութի մեծ և առաւել քան զամ ի միջա֊գետս. և ի խստութե սովոյն տագնապ և տատանում ' \
                   'լինէր ի բզմ տեղիս, և ի հռչա֊կաւոր մայրաքղքն ուռհայ, զորս կանգընեաց տիգրան արքայ հայոց և կացեալ ' \
                   'սովն յա՛յնմ աշխարհին զա՛մս .է՟. և անթիւ լինէր կոտո֊րածն յերեսաց սովոյն այն. և աշխարհին տաճըկաց ' \
                   'լինէր անցումն մեծ և քրիստոնէիցն անթիւք մեռան յերեսաց բարկութե սովոյն. և զկնի ե ամի եկեալ մորեխ ' \
                   'յայնմ գաւա֊ռէն որպ զաւազ ծովու և ապականեաց, զըերկիր. և սաստկանայր սովն առաւել քան զըառաւեն, և ' \
                   'զայրացեալ բազմացան և գա֊զանաբար անողորմ յարձակեալ զմիմեանսս ուտէին, և իշխանքն և մեծամեծքն ' \
                   'ընդաւք և մըրգաւք կերակրէին. և եղև անցումն ա֊նասնոցն. բզմ գեղք և գաւառք յանմարդ լինէին, և այլ ոչ ' \
                   'շինեցան մինչև ցայսօր ժամկի։ Դարձլ ի թվականութես հայոց ի ն՟ և է՟. ամին զօրա՛ժողով լինէր ազգն ' \
                   'արապկաց ուռհայ և ամ եդեսացոց աշխարհն ահա֊գին բազմութբ անցխալ ընդ մեծ գետն եփրատ և եկեա՛լ ի վր ' \
                   'ամուր քաղաքին որ կոչի սամուսատ. և ելանէր ի պտզմն, զօրապե֊տըն հոռոմոց, որում անուն ասէին պա֊' \
                   'ռակամանոս, ա՛յր զօրաւոր և քաջ. և ի դուռըն քաղաքին բախէին զմիմեանս և աւուր յայնմիկ հարին ' \
                   'տաճկունք զօրսն հոռոմոց և արարին կոտորած առ դրան քաղաքին. և յե՛տ աւուրց ինչ առաւ քաղաքն ' \
                   'սամուսատ մերձ ի քղք ուռհայ։ Իսկ ի թուակա֊նութես ազգիս հայոց ի դ՟ճ՟ և ի ը՟ ամին, զօրա֊'
        tokentext = ' '.join(x['t'] for x in tokens)
        self.assertEqual(tokentext, origtext)

    def test_witnessid(self):
        struct = Tokenizer(id_xpath='//t:msIdentifier/*/text()').from_etree(self.testdoc_noglyphs)
        self.assertEqual(struct['id'], 'Yerevan Matenadaran 1731')

        struct = Tokenizer(id_xpath='//t:msDesc/@xml:id').from_etree(self.testdoc_noglyphs)
        self.assertEqual(struct['id'], 'F')


    def test_glyphs(self):
        """Test the correct detection and rendering of glyphs. The characters in
        the resulting token should be the characters that are the content of the
        g tag. """
        testdata_noglyphs = {'յեգի<g ref="#&#x57A;&#x57F;"/>ոս': 'յեգիոս',
                    'յ<g ref="&#x561;&#x577;&#x56D;&#x561;&#x580;&#x570;">աշխար</g>հն': 'յաշխարհն',
                    '<g ref="asxarh">աշխարհ</g>ին': 'աշխարհին',
                    '<g ref="">աշխարհ</g>ին': 'աշխարհին',
                    'ար<g ref="">ա</g>պ<lb xml:id="l101276841" n="14"/>կաց': 'արապկաց',
                    '<g ref="">աշխարհ</g>ն': 'աշխարհն'}

        testdata_glyphs = {'յեգի<g ref="#ptlig">պտ</g>ոս': {'token': 'յեգիպտոս', 'occurrence': 1},
                            'յ<g ref="#asxarh">աշխար</g>հն': {'token': 'յաշխարհն', 'occurrence': 1},
                            '<g ref="#asxarh">աշխարհ</g>ին': {'token': 'աշխարհին', 'occurrence': 2},
                            'ար<g ref="#avar">ա</g>պ<lb xml:id="l101276841" n="14"/>կաց': {'token': 'արապկաց', 'occurrence': 1},
                            '<g ref="#asxarh">աշխարհ</g>ն': {'token': 'աշխարհն', 'occurrence': 1}}

        tokens = Tokenizer().from_etree(self.testdoc_noglyphs)['tokens']
        # Find the token that has our substitution
        for t in tokens:
            if '<g ref="' in t['lit']:
                self.assertIsNotNone(testdata_noglyphs.get(t['lit']), "Error in rendering glyphs (input data not covered by testdata)")
                self.assertTrue(t['t'] == testdata_noglyphs.get(t['lit']), "Error in rendering glyphs")
                del testdata_noglyphs[t['lit']]
        self.assertEqual(len(testdata_noglyphs), 0, "Did not find any test token")

        tokens = Tokenizer().from_etree(self.testdoc)['tokens']
        # Find the token that has our substitution
        for t in tokens:
            if '<g ref="' in t['lit']:
                self.assertIsNotNone(testdata_glyphs.get(t['lit']), "Error in rendering glyphs (input data not covered by testdata)")
                self.assertTrue(t['t'] == testdata_glyphs.get(t['lit'])['token'], "Error in rendering glyphs")
                testdata_glyphs[t['lit']]['occurrence'] -= 1
                if testdata_glyphs[t['lit']]['occurrence'] == 0:
                    del testdata_glyphs[t['lit']]
        self.assertEqual(len(testdata_glyphs), 0, "Did not find any test token")

    def test_substitution(self):
        """Test that the correct words are picked out of a subst tag."""
        tokens = Tokenizer().from_etree(self.testdoc)['tokens']
        # Find the token that has our substitution
        for t in tokens:
            if t['lit'] != 'դե<add>ռ</add>ևս':
                continue
            self.assertEqual(t['t'], 'դեռևս')
            break
        else:
            self.assertTrue(False, "Did not find the testing token")

    def test_substitution_layer(self):
        """Test that the first_layer option works correctly."""
        tokens = Tokenizer(first_layer=True).from_etree(self.testdoc)['tokens']
        # Find the token that has our substitution
        for t in tokens:
            if t['lit'] != 'դե<del>ղ</del>ևս':
                continue
            self.assertEqual(t['t'], 'դեղևս')
            break
        else:
            self.assertTrue(False, "Did not find the testing token")

    def test_token_context(self):
        """Test that each token has a context, and each 'lit' string is parseable."""
        tok = Tokenizer(normalisation=helpers.normalise)
        tokens = tok.from_file(self.testfiles['xmlreal'])['tokens']
        for t in tokens:
            self.assertTrue('context' in t)
            self.assertTrue('lit' in t)
            try:
                fromstring('<word>' + t['lit'] + '</word>')
            except XMLSyntaxError:
                self.fail()

        # Again, with first layer
        tok = Tokenizer(normalisation=helpers.normalise, first_layer=True)
        tokens = tok.from_file(self.testfiles['xmlreal'])['tokens']
        for t in tokens:
            self.assertTrue('context' in t)
            self.assertTrue('lit' in t)
            try:
                fromstring('<word>' + t['lit'] + '</word>')
            except XMLSyntaxError:
                self.fail()

    def test_normalisation(self):
        """Test that passing a normalisation function works as intended"""
        tok = Tokenizer(milestone='401', normalisation=helpers.normalise)
        tokens = tok.from_etree(self.testdoc)['tokens']
        normal = {0: 'իսկ',
                  4: 'այնոսիկ',
                  8: '401',
                  13: 'բզմ',
                  17: 'հարօոյ',
                  20: 'տաճկաց',
                  43: 'հռչակօոր'}
        for i, n in normal.items():
            self.assertEqual(tokens[i]['n'], n)

        tok = Tokenizer(milestone='407', normalisation=helpers.bad_normalise)
        try:
            result = tok.from_etree(self.testdoc)
            self.fail("should have raised an error")
        except Exception as e:
            self.assertIsInstance(e, JSONDecodeError)

    def test_location(self):
        tokens = Tokenizer(milestone='407').from_etree(self.testdoc)['tokens']
        self.assertEqual(tokens[0]['page'], {'n': '075v'})
        self.assertEqual(tokens[0]['line'], {'xml:id': 'l101276931', 'n': '12'})   # first token
        self.assertEqual(tokens[10]['line'], {'xml:id': 'l101276840', 'n': '13'})  # line broken
        self.assertEqual(tokens[22]['line'], {'xml:id': 'l101276843', 'n': '16'})    # beginning of line

    # def test_del_word_boundary(self):
    #     """Test that a strategically placed del doesn't cause erroneous joining of words.
    #     TODO add testing data"""
    #     pass

    def test_gap(self):
        """Test that gaps are handled correctly. At the moment this means that no token
        should be generated for a gap."""
        tokens = Tokenizer(milestone='410').from_file(self.testfiles['xmlreal'])['tokens']
        gaptoken = {'t': 'զ', 'n': 'զ', 'lit': 'զ<gap extent="5"/>', 'context': 'text/body/ab',
                    'page': {'n': '002r'}, 'column': {'n': '1'},
                    'line': {'xml:id': 'l101252731', 'n': '26'}}
        found = False
        for t in tokens:
            if t['lit'].find('gap') > 0:
                self.assertEqual(t, gaptoken)
                found = True
                break
        self.assertTrue(found)

    def test_milestone_element(self):
        """Test that milestone elements (not <milestone>, but e.g. <lb/> or <cb/>)
         are passed through correctly in the token 'lit' field."""
        pass

    def test_milestone_option(self):
        """Test that passing a milestone option gives back only the text from the
        relevant <milestone/> element to the next one."""
        tokens = Tokenizer(milestone="401").from_etree(self.testdoc)['tokens']
        self.assertEqual(len(tokens), 132)
        self.assertEqual(tokens[0]['t'], 'Իսկ')
        self.assertEqual(tokens[-1]['t'], 'ժամկի։')

        tokens407 = Tokenizer(milestone="407").from_etree(self.testdoc)['tokens']
        self.assertEqual(len(tokens407), 76)
        self.assertEqual(tokens407[0]['t'], 'Դարձլ')
        self.assertEqual(tokens407[-1]['t'], 'ուռհայ։')

    # def test_arbitrary_element(self):
    #     """Test that arbitrary tags (e.g. <abbr>) are passed into 'lit' correctly."""
    #     pass

    def test_file_input(self):
        """Make sure we get a result when passing a file path."""
        filename = self.testfiles['xmlreal']
        tok = Tokenizer(milestone="412")
        tokens = tok.from_file(filename, )['tokens']
        first_word = {'t': 'Իսկ', 'n': 'Իսկ',
                      'lit': '<supplied reason="missing highlight">Ի</supplied>սկ',
                      'context': 'text/body/ab',
                      'page': {'n': '002v'}, 'column': {'n': '1'},
                      'line': {'xml:id': 'l101252792', 'n': '3'}}
        last_word = {'t': 'փառւրութբ։', 'n': 'փառւրութբ։',
                     'lit': 'փառ<abbr>ւ</abbr>րու<abbr>թբ</abbr>։',
                     'context': 'text/body/ab',
                     'page': {'n': '002v'}, 'column': {'n': '2'},
                     'line': {'xml:id': 'l101252825', 'n': '5'}}
        self.assertEqual(len(tokens), 155)
        self.assertEqual(tokens[0], first_word)
        self.assertEqual(tokens[-1], last_word)

    # def test_fh_input(self):
    #     """Make sure we get a result when passing an open filehandle object."""
    #     pass

    # def test_string_input(self):
    #     """Make sure we get a result when passing a string containing XML."""
    #     pass

    # def test_object_input(self):
    #     """Make sure we get a result when passing an lxml.etree object."""
    #     pass

    def testLegacyTokenization(self):
        """Test with legacy TEI files from 2009, to make sure the tokenizer
        works with them."""
        testfile = self.testfiles['tei_2009']
        with open(self.testfiles['tei_2009_reference'], encoding='utf-8') as rfh:
            rtext = rfh.read()

        reference = rtext.rstrip().split(' ')
        tokens = Tokenizer().from_file(testfile)['tokens']
        for i, t in enumerate(tokens):
            self.assertEqual(t['t'], reference[i], "Mismatch at index %d: %s - %s" % (i, t, reference[i]))
