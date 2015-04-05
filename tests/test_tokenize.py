__author__ = 'tla'

import unittest
import wordtokenize

class Test (unittest.TestCase):

    def testLegacyTokenization(self):
        """Test with legacy TEI files from 2009, to make sure the tokenizer
        works with them."""
        testfile = 'tests/data/matenadaran_1896.xml'
        with open('tests/data/matenadaran_1896_reference.txt', encoding='utf-8') as rfh:
            rtext = rfh.read()
        reference = rtext.rstrip().split(' ')
        tokens = wordtokenize.from_file(testfile)
        for i, t in enumerate(tokens):
            self.assertEqual(t['t'], reference[i], "Mismatch at index %d: %s - %s" % (i, t, reference[i]))
