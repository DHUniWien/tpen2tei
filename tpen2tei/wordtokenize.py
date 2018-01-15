# -*- encoding: utf-8 -*-
import json
from lxml import etree
import re
import sys

__author__ = 'tla'


class Tokenizer:
    """Instantiate a word/reading tokenizer that reads a TEI XML file and returns JSON output
    suitable for passing to CollateX. Options include:

    * milestone: Restrict the output to text between the given milestone ID and the next.
    * first_layer: Instead of using the final layer (e.g. <add> tags, use the first (a.c.)
      layer of the text (e.g. <del> tags).
    * normalisation: A function that takes a token and rewrites that token's normalised form,
      if desired.
    * id_xpath: An XPath expression that returns a string that should be used as the manuscript's
      identifier in CollateX output. Defaults to '//t:msDesc/@xml:id'. (Note that the TEI namespace
      should be abbreviated as 't'.)"""

    IDTAG = '{http://www.w3.org/XML/1998/namespace}id'   # xml:id; useful for debugging
    MILESTONE = None
    INMILESTONE = True
    first_layer = None
    normalisation = None
    id_xpath = None
    xml_doc = None

    def __init__(self, milestone=None, first_layer=False, normalisation=None, id_xpath=None):
        if milestone is not None:
            self.MILESTONE = milestone
            self.INMILESTONE = False
        self.first_layer = first_layer
        self.normalisation = normalisation
        self.id_xpath = id_xpath

    def from_file(self, xmlfile, encoding='utf-8'):
        with open(xmlfile, encoding=encoding) as fh:
            return self.from_fh(fh)

    def from_fh(self, xml_fh):
        xmldoc = etree.parse(xml_fh)           # returns an ETree
        return self.from_etree(xmldoc)

    def from_string(self, xml_string):
        xmlobj = etree.fromstring(xml_string)  # returns an Element
        return self.from_element(xmlobj)

    def from_etree(self, xml_doc):
        return self.from_element(xml_doc.getroot())

    def from_element(self, xml_object):
        """Take a TEI XML file as input, and return a JSON structure suitable
        for passing to CollateX."""

        # (Re)set xml_doc from the element we are now using
        self.xml_doc = etree.ElementTree(xml_object)

        ns = {'t': 'http://www.tei-c.org/ns/1.0'}

        # Extract a witness ID from the XML
        sigil = "TEI MS"
        if self.id_xpath is not None:
            ids = xml_object.xpath(self.id_xpath, namespaces=ns)
            if len(ids):
                sigil = ' '.join(ids)

        # Extract the text itself from the XML
        thetext = xml_object.xpath('//t:text', namespaces=ns)[0]
        tokens = []

        # For each section-like block remaining in the text, break it up into words.
        blocks = thetext.xpath('.//t:div | .//t:ab', namespaces=ns)
        for block in blocks:
            tokens.extend(self._find_words(block, self.first_layer))
        # Back to the top level: remove any empty tokens that were left over
        # in case they were needed to close a seemingly incomplete word.
        tokens = [t for t in tokens if not _is_blank(t)]

        # Now go through all the tokens and apply our function, if any, to normalise
        # the token.
        if self.normalisation is not None:
            try:
                normed = [self.normalisation(t) for t in tokens]
            except:
                raise
            tokens = normed

        # Account for the possibility that a space was forgotten at the end of the
        # section or document
        if len(tokens) > 0 and 'join_next' in tokens[-1]:
            del tokens[-1]['join_next']

        return {'id': sigil, 'tokens': tokens}

    def _find_words(self, element, first_layer=False):
        """Detect word boundaries and add an anchor to each."""
        tokens = []
        # First handle the text of the element, if any
        if element.tag is not etree.Comment and element.text is not None:
            self._split_text_node(element, element.text, tokens)

        # Now tokens has only the tokenized contents of the element itself.
        # If there is a single token, then we 'lit' the entire element and will use the
        # parent context below.
        singlewordelement = False
        if len(tokens) == 1 and len(element) == 0:
            tokens[0]['lit'] = _shortform(etree.tostring(element, encoding='unicode', with_tail=False))
            singlewordelement = True

        # Next handle the child elements of this one, if any.
        for child in element:
            child_tokens = self._find_words(child, first_layer)
            if len(child_tokens) == 0:
                continue
            if len(tokens) and 'join_next' in tokens[-1]:
                # Try to combine the last of these with the first child token.
                combolit = "<word>%s</word>" % (tokens[-1]['lit'] + child_tokens[0]['lit'])
                try:
                    etree.fromstring(combolit)
                    # If this didn't cause an exception, merge the tokens
                    prior = tokens[-1]
                    partial = child_tokens.pop(0)
                    prior['t'] += partial['t']
                    prior['n'] += partial['n']
                    # Now figure out 'lit'. Did the child have children?
                    if child.text is None and len(child) == 0:
                        # It's a milestone element. Stick it into 'lit'.
                        prior['lit'] += _shortform(etree.tostring(child, encoding='unicode', with_tail=False))
                    prior['lit'] += partial['lit']
                    if 'join_next' not in partial:
                        del prior['join_next']
                except etree.XMLSyntaxError:
                    pass
            # Add the remaining tokens onto our list.
            tokens.extend(child_tokens)

        # Now we handle our tag-specific logic, after the child text and child tags
        # have been processed but before the tail is processed.
        # First, are we in the milestone we want?
        if _tag_is(element, 'milestone'):
            if element.get('n') == self.MILESTONE:
                self.INMILESTONE = True
            elif self.MILESTONE is not None:
                self.INMILESTONE = False
        if not self.INMILESTONE:
            return tokens

        # Move on with life

        # Deal with specific tag logic
        if (_tag_is(element, 'del') and first_layer is False) \
                or (_tag_is(element, 'add') and first_layer is True) or _tag_is(element, 'note'):
            # If we are looking at a del tag for the final layer, or an add tag for the
            # first layer, discard all the tokens we just got, replacing them with either an
            # empty joining token or nothing at all. TODO why the empty token?
            if len(tokens):
                final = tokens[-1]
                if 'join_next' in final:
                    tokens = [{'t': '', 'n': '', 'lit': '', 'join_next': True}]
                else:
                    tokens = []
                    singlewordelement = False
        elif _tag_is(element, 'abbr'):
            # Mark a sort of regular expression in the token data, for matching.
            if len(tokens) > 0:
                tokens[0]['re'] = '.*%s.*' % '.*'.join(tokens[0]['t'])
        elif _tag_is(element, 'num'):
            # Combine all the word tokens into a single one, and set 'n' to the number value.
            mytoken = {'n': element.get('value'),
                       't': ' '.join([x['t'] for x in tokens]),
                       'lit': ' '.join([x['lit'] for x in tokens])
                       }
            for k in tokens[0]:
                if k not in mytoken:
                    mytoken[k] = tokens[0][k]
            if 'join_next' in tokens[-1]:
                mytoken['join_next'] = True
            elif 'join_next' in mytoken:
                del mytoken['join_next']
            tokens = [mytoken]

        # Set the context on all the tokens created thus far
        context = _shortform(self.xml_doc.getelementpath(element))
        parentcontext = _shortform(self.xml_doc.getelementpath(element.getparent()))
        if singlewordelement:
            tokens[0]['context'] = parentcontext
        for t in tokens:
            if 'context' not in t:
                t['context'] = context

        # Finally handle the tail text of this element, if any.
        # Our XML context is now the element's parent.
        if element.tail is not None:
            # Strip any insignificant whitespace from the tail.
            tnode = element.tail
            if re.match('.*\}[clp]b$', str(element.tag)):
                tnode = re.sub('^[\s\n]*', '', element.tail, re.S)
            if tnode != '':
                self._split_text_node(element, tnode, tokens)
            # Set the outer context on all the new tokens created
            for t in tokens:
                if 'context' not in t:
                    t['context'] = parentcontext

        # Get rid of any final empty tokens.
        if len(tokens) and _is_blank(tokens[-1]):
            tokens.pop()
        return tokens

    def _split_text_node(self, context, tnode, tokens):
        if not self.INMILESTONE:
            return tokens
        ns = {'t': 'http://www.tei-c.org/ns/1.0'}
        tnode = tnode.rstrip('\n')
        words = re.split('\s+', tnode)
        # Filter out any blank spaces at the end (but not at the beginning! We may need the
        # empty token to close out a join_next token that ends the outer layer.)
        if words[-1] == '':
            words.pop()
        for word in words:
            if len(tokens) and 'join_next' in tokens[-1]:
                open_token = tokens.pop()
                open_token['t'] += word
                open_token['n'] += word
                open_token['lit'] += word
                del open_token['join_next']
                tokens.append(open_token)
            elif len(tokens) and word == '':
                # In this case we can discard any blank-space token at the beginning.
                continue
            else:
                token = {'t': word, 'n': word, 'lit': word}
                # Put the word location into the token
                divisions = {
                    'section': ('./ancestor::t:div', 'div'),
                    'paragraph': ('./ancestor::t:p', 'p'),
                    'page': ('./preceding::t:pb[1]', 'pb'),
                    'column': ('./preceding::t:cb[1]', 'cb'),
                    'line': ('./preceding::t:lb[1]', 'lb')
                }
                for k in divisions.keys():
                    xmlpath = divisions.get(k)
                    mydiv = context.xpath(xmlpath[0], namespaces=ns)
                    if _tag_is(context, xmlpath[1]):
                        token[k] = _xmljson(context).get('attr')
                    elif len(mydiv):
                        token[k] = _xmljson(mydiv[-1]).get('attr')
                # Stash the token
                tokens.append(token)
        if len(tokens) and re.search('\s+$', tnode) is None:
            tokens[-1]['join_next'] = True
        return tokens


# Helper functions that don't need instance variables #
# Return the LXML-style element name with namespace
def _tag_is(el, tag):
    return el.tag == '{http://www.tei-c.org/ns/1.0}%s' % tag


# Return a JSON structure that represents an XML element and attributes
def _xmljson(el):
    tag = _shortform(el.tag)
    attr = {}
    for k in el.attrib.keys():
        attr[_shortform(k)] = el.get(k)
    return {'tag': tag, 'attr': attr}


# Helper function to convert namespaces back to short forms
def _shortform(xmlstr):
    nsmap = {
        'http://www.w3.org/XML/1998/namespace': 'xml',
        'http://www.tei-c.org/ns/1.0': None
    }

    for k in nsmap.keys():
        v = nsmap.get(k)
        # Undo lxml namespace handling
        if '{%s}' % k in xmlstr:
            if v is None:
                return xmlstr.replace('{%s}' % k, '')
            else:
                return xmlstr.replace('{%s}' % k, v + ':')
        # Undo explicit namespace declaration in string ouptut
        elif k in xmlstr and v is None:
            return xmlstr.replace(' xmlns="%s"' % k, '')
    return xmlstr


# Check to see if a token counts as blank
def _is_blank(token):
    if token['n'] != '':
        return False
    if token['t'] != '':
        return False
    # if token['lit'] != '':
    #     return False
    return True


if __name__ == '__main__':
    witness_array = []
    textms = None
    xmlfiles = None
    if re.match('.*\.xml$', sys.argv[1]) is None:
        textms = sys.argv[1]
        xmlfiles = sys.argv[2:]
    else:
        xmlfiles = sys.argv[1:]
    tok = Tokenizer(milestone=textms, first_layer=True)
    for fn in xmlfiles:
        result = tok.from_file(fn)
        if len(result):
            witness_array.append(result)
    result = json.dumps({'witnesses': witness_array}, ensure_ascii=False)
    sys.stdout.buffer.write(result.encode('utf-8'))
