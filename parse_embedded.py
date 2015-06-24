# -*- encoding: utf-8 -*-
__author__ = 'tla'

import json
import re
import sys
import os.path
import yaml
from io import BytesIO
from lxml import etree
from warnings import warn

def from_sc(jsondata, glyph_correction=None, special_chars=None):
    """Extract the textual transcription from a JSON file, probably exported
    from T-PEN according to a Shared Canvas specification. It has a series of
    sequences (should be 1 sequence), and each sequence has a set of canvases,
    each of which is a page.

    The optional special_chars parameter is a dictionary of glyphs that have
    been referenced in the transcription. The dictionary key is the normalized
    character form of the given glyph; the value is a tuple of the glyph's
    xml:id and the Unicode-like description of the glyph."""
    if len(jsondata['sequences']) > 1:
        warn("Your data has more than one sequence. Check to see what's going on.", UserWarning)
    pages = jsondata['sequences'][0]['canvases']
    notes = []
    columns = {}
    xmlstring = ''
    if pages:
        xmlstring = '<sourceDoc>\n  <surfaceGrp>\n'

    for page in pages:
        pn = re.sub('^[^\d]+(\d+\w)\.jpg', '\\1', page['label'])
        pwidth = page['width']
        pheight = page['height']
        thetext = []
        xval = 0
        for line in page['resources']:
            if line['resource']['@type'] == 'cnt:ContentAsText':
                transcription = line['resource']['cnt:chars']
                if len(transcription) == 0:
                    continue
                if line['motivation'] == 'sc:painting':
                    # This is a transcription of a manuscript line.
                    # Get the column y value and see if we are starting a new column.
                    coords = re.match('^.*#xywh=-?(\d+),(\d+),(\d+),(\d+)', line['on'])
                    if coords is None:
                        raise ValueError('Could not find the coordinates for line %s' % line['@id'])
                    if xval < int(coords.group(1)):
                        # Start a new 'column' in thetext.
                        thetext.append([])
                        xval = int(coords.group(1))
                    yval = int(coords.group(2))
                    wval = int(coords.group(3))
                    hval = int(coords.group(4))
                    # Get the line ID, for later attachment of notes.
                    lineid = re.match('^.*line/(\d+)$', line['@id'])
                    if lineid is None:
                        raise ValueError('Could not find a line ID on line %s' % json.dumps(line))
                    thetext[-1].append((lineid.group(1), transcription, xval, yval, wval, hval))
                elif line['motivation'] == 'oa:commenting':
                    # This 'transcription' is actually a transcriber's note.
                    lineid = re.match('^.*line/(\d+)$', line['on'])
                    if lineid is None:
                        raise ValueError('Could not find a line ID on comment %s' % json.dumps(line))
                    notes.append((lineid.group(1), transcription))
        # Spit out the text
        if len(thetext):
            xmlstring += '    <surface ulx="{:d}" uly="{:d}" lrx="{:d}" lry="{:d}">\n'.format(0, 0, pwidth, pheight)
            xmlstring += '      <zone xml:id="P{:s}" ulx="{:d}" uly="{:d}" lrx="{:d}" lry="{:d}">\n'.format(pn, 0, 0, pwidth, pheight)
            xmlstring += '        <graphic url="{:s}" />\n'.format(page['label'])
            xmlstring += '      </zone>\n'
            xmlstring += '      <pb n="%s" />\n' % (pn)
            for cn, col in enumerate(thetext):
                if len(thetext) > 1:
                    xmlstring += '      <cb n="%d"/>\n' % (cn+1)
                for ln, line in enumerate(col):
                    xmlstring += '      <zone xml:id="z{:s}" ulx="{:d}" uly="{:d}" lrx="{:d}" lry="{:d}">\n'. format(line[0], line[2], line[3], line[2]+line[4], line[3]+line[5])
                    xmlstring += '        <lb xml:id="l%s" n="%d" />%s\n' % (line[0], ln+1, line[1])
                    xmlstring += '      </zone>\n'
            xmlstring += '    </surface>\n'
            # Keep track of the number of columns.
            if len(thetext) in columns:
                columns[len(thetext)].append(pn)
            else:
                columns[len(thetext)] = [pn]
    # and then add the notes.
    if pages:
        xmlstring += '  </surfaceGrp>\n</sourceDoc>\n'
    for n in notes:
        xmlstring += '<note type="transcriptional" target="#l%s">%s</note>\n' % n

    # # Report how many columns per page.
    # for n in sorted(columns.keys()):
    #     print("%d columns for pages %s\n" % (n, " ".join(columns[n])), file=sys.stderr)
    return _xmlify("<body><ab>\n%s</ab></body>" % xmlstring, glyph_correction=glyph_correction, special_chars=special_chars)


def _xmlify(txdata, glyph_correction=None, special_chars=None):
    """Take the extracted XML structure of from_sc and make sure it is
    well-formed. Also fix any shortcuts, e.g. for the glyph tags."""
    if glyph_correction is None:
        glyph_correction = {}
    try:
        content = etree.fromstring(txdata)
    except etree.XMLSyntaxError as e:
        print("Parsing error in the JSON: %s" % e.msg, file=sys.stderr)
        print("Full string was %s" % txdata, file=sys.stderr)
        return

    # Now fix the glyph references.
    glyphs_seen = {}
    if special_chars is not None:
        # LATER get this hard-coded list into a settings file. Or better yet, correct
        # the transcriptions.
        for glyph in content.xpath('//g'):
            # Find the characters that we have glyph-marked. It could have been done
            # in a couple of different ways.
            gchars = ''
            gtext_explicit = ''
            if glyph.get('ref'):
                gchars = glyph.get('ref')
                if gchars.find('#') == 0:
                    gchars = gchars[1:]
            if glyph.text:
                if gchars == '':
                    gchars = glyph.text
                else:
                    gtext_explicit = True
            if gchars in glyph_correction:
                gchars = glyph_correction[gchars]
            # Now figure out what the reference is for this glyph. Make the
            # XML element if necessary.
            if gchars not in glyphs_seen:
                try:
                    glyphs_seen[gchars] = _get_glyph(gchars, special_chars)
                except ValueError as e:
                    print("In g element %s:" % etree.tostring(glyph, encoding='unicode', with_tail=False),
                          file=sys.stderr)
                    raise e
            gref = '#%s' % glyphs_seen[gchars].get('{http://www.w3.org/XML/1998/namespace}id')
            # Finally, fix the 'g' element here so that it is canonical.
            glyph.set('ref', gref)
            if not gtext_explicit:
                glyph.text = gchars

    for el in content.xpath('//corr'):
        el.tag = 'subst'
    # We should be using 'rend' and not 'type' for the subst and del tags.
    for edit in content.xpath('//subst | //del'):
        if edit.get('type'):
            rend = edit.get('type')
            edit.set('rend', rend)
            edit.attrib.pop('type')

    # And 'certainty' attributes have to have the value 'high, 'medium', or 'low'.
    for el in content.xpath('//*[@cert]'):
        certval = el.get('cert')
        if re.match('^\d+$', certval):
            if int(certval) > 40:
                el.set('cert', 'medium')
            else:
                el.set('cert', 'low')

    return _tei_wrap(content, sorted(glyphs_seen.values(),
                                     key=lambda x: x.get('{http://www.w3.org/XML/1998/namespace}id')))


def _get_glyph(gname, special_chars):
    """Returns a TEI XML 'glyph' element for the given string."""
    # LATER get this hard-coded list into a settings file.
    if gname not in special_chars:
        raise ValueError("Glyph %s not recognized" % gname)

    glyph_el = etree.Element('glyph')
    glyph_el.set('{http://www.w3.org/XML/1998/namespace}id', '%s' % special_chars[gname][0])
    etree.SubElement(glyph_el, 'glyphName').text = special_chars[gname][1]
    etree.SubElement(glyph_el, 'mapping').text = gname
    return glyph_el


def _tei_wrap(content, glyphs):
    """Wraps the content, and the glyphs that were found, into TEI XML format."""
    # First make the skeleton
    tei = etree.Element('TEI')
    file_desc = etree.SubElement(etree.SubElement(tei, 'teiHeader'), 'fileDesc')
    etree.SubElement(etree.SubElement(file_desc, 'titleStmt'), 'title').text = 'This is the title'
    etree.SubElement(etree.SubElement(file_desc, 'publicationStmt'), 'p').text = 'This is the publication statement'
    etree.SubElement(etree.SubElement(file_desc, 'sourceDesc'), 'p').text = 'This is the source description'
    # Then add the glyphs we used
    if len(glyphs):
        etree.SubElement(etree.SubElement(tei.find('teiHeader'), 'encodingDesc'), 'charDecl').extend(glyphs)
    # Then add the content.
    etree.SubElement(tei, 'text').append(content)
    # Finally, set the appropriate namespace and schema.
    tei.set('xmlns', 'http://www.tei-c.org/ns/1.0')
    tei_doc = etree.ElementTree(tei)
    schema = etree.ProcessingInstruction('xml-model', 'href="http://www.tei-c.org/release/xml/tei/custom/schema/relaxng/tei_all.rng" type="application/xml" schematypens="http://relaxng.org/ns/structure/1.0"')
    tei.addprevious(schema)
    # Now that we've done this, serialize and re-parse the entire TEI doc
    # so that the namespace functionality works.
    tei_doc = etree.parse(BytesIO(etree.tostring(tei_doc)))
    return tei_doc

def load_settings(filename):
    if filename and os.path.isfile(filename):
        try:
            file_pointer = open(filename, 'r')
            config = yaml.load(file_pointer)
            file_pointer.close()
        except IOError:
            sys.exit("Invalid or missing config file")

        if 'settings' not in config:
            sys.exit('No default configuration found')
        settings = config['settings']
    else:
        settings = {}
    return settings

if __name__ == '__main__':
    settings = load_settings('config.yaml')
    with open(sys.argv[1], encoding='utf-8') as jfile:
        msdata = json.load(jfile)
    xmltree = from_sc(msdata, settings['glyph_correction'])
    if xmltree is not None:
        sys.stdout.buffer.write(etree.tostring(xmltree, encoding='utf-8', pretty_print=True, xml_declaration=True))
