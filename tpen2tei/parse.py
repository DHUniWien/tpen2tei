import argparse
import json
import re
import sys
from io import BytesIO
from lxml import etree
from warnings import warn

__author__ = 'tla'


def from_sc(jsondata,
            metadata=None,
            members=None,
            special_chars=None,
            numeric_parser=None,
            text_filter=None,
            postprocess=None):
    """Extract the textual transcription from a JSON file, probably exported
    from T-PEN according to a Shared Canvas specification. It has a series of
    sequences (should be 1 sequence), and each sequence has a set of canvases,
    each of which is a page.

    The optional metadata parameter is a dictionary of keys whose values should
    appear in certain places in the TEI header. This is not yet fully documented.

    The optional members parameter is a dictionary of T-PEN project members,
    which is keyed on T-PEN user ID and should be of the form
      {"1234": {"name": "T. Pen Transcriber", "uname": "tpt@example.org"}}
    This is used to add a respStmt and @resp attributes to the individual lines.

    The optional special_chars parameter is a dictionary of glyphs that have
    been referenced in the transcription. The dictionary key is the normalized
    character form of the given glyph; the value is a tuple of the glyph's
    xml:id and the Unicode-like description of the glyph.

    The optional numeric_parser parameter is a function that takes a string and
    is expected to return a numeric value. It will be passed the text content of
    any <num> elements that have no 'value' attribute, or an empty 'value'.

    The optional text_filter parameter is a function that takes a string and is
    expected to return a string. It will be passed the text content of each line
    of transcription in the canvas, and its return value will be stored as the
    content of that line.

    The optional postprocess parameter is a function that takes an etree Element
    object, which is the otherwise final parsed TEI document, and modifies it.
    """
    if len(jsondata['sequences']) > 1:
        warn("Your data has more than one sequence. Check to see what's going on.", UserWarning)
    # Merge the JSON-supplied metadata into the user-supplied. If a user has
    # supplied a key, don't override it.
    if 'metadata' in jsondata:
        if metadata is None:
            metadata = {}
        for item in jsondata['metadata']:
            if item['label'] not in metadata and len(item['value']) > 0 and not item['value'].isspace():
                metadata[item['label']] = item['value']

    pages = jsondata['sequences'][0]['canvases']
    notes = []
    columns = {}
    xmlstring = ''
    nblines = set()  # Keep track of the line IDs that occur mid-word
    breaking = False
    seen_members = {}
    for page in pages:
        pn = re.sub('^[^\d]+(\d+\w)\.jpg', '\\1', page['label'])
        thetext = []
        xval = -1
        # Find the annotation list.
        linelist = None
        for content in page['otherContent']:
            if content['@type'] == 'sc:AnnotationList':
                linelist = content
                break
        # Did we find a list of annotations for this page?
        if linelist is None:
            continue
        for line in linelist['resources']:
            if line['resource']['@type'] == 'cnt:ContentAsText':
                transcription = line['resource']['cnt:chars']
                if text_filter is not None:
                    transcription = text_filter(transcription)
                if len(transcription) == 0:
                    continue
                # Get the line ID, for later attachment of notes.
                lineid = re.match('^.*line/(\d+)$', line['_tpen_line_id'])
                agent = "%d" % line.get('_tpen_creator')
                if lineid is None:
                    raise ValueError('Could not find a line ID on line %s' % json.dumps(line))
                # Note whether the previous line break element needs a 'break' attribute
                # (never the first line)
                if breaking:
                    nblines.add(lineid.group(1))
                # Note whether the next line break element needs a 'break' attribute
                # (never the last line)
                breaking = not transcription.endswith(' ')
                if line['motivation'] == 'oad:transcribing':
                    # This is a transcription of a manuscript line.
                    # Get the column y value and see if we are starting a new column.
                    coords = re.match('^.*#xywh=-?(\d+)', line['on'])
                    if coords is None:
                        raise ValueError('Could not find the coordinates for line %s' % line['@id'])
                    if xval < int(coords.group(1)):
                        # Start a new 'column' in thetext.
                        thetext.append([])
                        xval = int(coords.group(1))
                    if members is not None:
                        if agent in members:
                            seen_members[agent] = members.get(agent)
                        else:
                            print("WARNING: T-PEN user %s not in members list" % agent)
                    thetext[-1].append((lineid.group(1), transcription, agent))
                if '_tpen_note' in line:
                    # This 'transcription' is actually a transcriber's note.
                    if line['_tpen_note'] != "":
                        notes.append((lineid.group(1), line['_tpen_note'], agent))
        # Spit out the text
        if len(thetext):
            xmlstring += '<pb n="%s"/>\n' % pn
            for cn, col in enumerate(thetext):
                if len(thetext) > 1:
                    xmlstring += '<cb n="%d"/>\n' % (cn + 1)
                for ln, line in enumerate(col):
                    attrstring = 'xml:id="l%s" n="%d"' % (line[0], ln + 1)
                    if line[2] in seen_members:
                        attrstring += ' resp="#u%s"' % line[2]
                    if line[0] in nblines:
                        attrstring += ' break="no"'
                    xmlstring += '<lb %s/>%s\n' % (attrstring, line[1])
            # Keep track of the number of columns.
            if len(thetext) in columns:
                columns[len(thetext)].append(pn)
            else:
                columns[len(thetext)] = [pn]
    # and then add the notes.
    for n in notes:
        attrstring = 'type="transcriptional" target="#l%s"' % n[0]
        if n[2] in seen_members:
            attrstring += ' resp="#u%s"' % n[2]
        xmlstring += '<note %s>%s</note>\n' % (attrstring, n[1])
    return _xmlify("<body>%s</body>" % xmlstring, metadata, members=seen_members,
                   special_chars=special_chars, numeric_parser=numeric_parser, postprocess=postprocess)


def _xmlify(txdata, metadata, members=None, special_chars=None, numeric_parser=None, postprocess=None):
    """Take the extracted XML structure of from_sc and make sure it is
    well-formed. Also fix any shortcuts, e.g. for the glyph tags."""
    try:
        content = etree.fromstring(txdata)
    except etree.XMLSyntaxError as e:
        message = "Parsing error in the JSON: %s\n" % e.msg
        # This is an option, not default, to reduce the amount of XML parsing error data generated.
        if metadata.get('short_error', False):
            message += _show_parsing_short_error(e, txdata)
        else:
            message += "Full string was %s" % txdata
        safeerrmsg(message)
        return

    # Does the 'body' element have any direct text nodes? If so, wrap the whole thing in an
    # anonymous block, so that it becomes valid TEI.
    wrap_ab = content.text is not None and not re.match(r'\s+', content.text)
    for el in content:
        if el.tail is not None and not re.match(r'\s+', el.tail):
            wrap_ab = True
    if wrap_ab:
        print("WARNING: unblocked text detected. Wrapping in anonymous block", file=sys.stderr)
        txdata = txdata.replace('<body>', '<body><ab>').replace('</body>', '</ab></body>')
        try:
            content = etree.fromstring(txdata)
        except etree.XMLSyntaxError as e:
            message = "Parsing error in block wrap: %s\n" % e.msg
            if metadata.get('short_error', False):
                message += _show_parsing_short_error(e, txdata)
            else:
                message += "Full string was %s" % txdata
            safeerrmsg(message)
            return

    # First add values to the numbers if we have a way to.
    if numeric_parser is not None:
        for num in content.xpath('//num'):
            if 'value' in num.keys():
                try:
                    float(num.get('value'))
                    continue
                except ValueError:
                    pass
            # If we get here, we haven't got a valid value.
            numtext = etree.tostring(num, method='text', with_tail=False, encoding='utf-8').decode('utf-8')
            try:
                numval = numeric_parser(numtext)
                float(numval)
                num.set('value', numval.__str__())
            except ValueError:
                warn("Numeric parser could not parse data %s" % numtext)

    # Now fix the glyph references.
    glyphs_seen = {}
    if special_chars is not None:
        # LATER get this hard-coded list into a settings file. Or better yet, correct
        # the transcriptions.
        glyph_correction = {
            'the': 'թե',
            'thE': 'թէ',
            'und': 'ընդ',
            'thi': 'թի',
            'asxarh': 'աշխարհ',
            'pt': 'պտ',
            'yr': 'յր',
            'orpes': 'որպէս',
        }
        for glyph in content.xpath('//g'):
            # Find the characters that we have glyph-marked. It could have been done
            # in a couple of different ways.
            glyphid = ''
            gtext_explicit = False
            # There might be an explicit 'ref' attribute, which may or may not have a non-empty value.
            if glyph.get('ref'):
                glyphid = glyph.get('ref')
                if glyphid.find('#') == 0:  # The ref is meaningful and should be preserved.
                    glyphid = glyphid[1:]
            if glyph.text:
                if glyphid == '':  # The glyph should be identified from the element text content.
                    glyphid = glyph.text
                else:
                    gtext_explicit = True  # We have set a real ref and also text; both should be preserved.
            if glyphid in glyph_correction:  # Check whether we need to use the hardcoded hack.
                glyphid = glyph_correction[glyphid]
            # Now figure out what the reference is for this glyph. Make the
            # XML element if necessary.
            if glyphid not in glyphs_seen:
                try:
                    glyphs_seen[glyphid] = _get_glyph(glyphid, special_chars)
                except ValueError as e:
                    lb = glyph.xpath('./preceding::lb[1]')[0]
                    message = "In g element %s, line %s / %s, page %s:\n" % \
                              (etree.tostring(glyph, encoding='utf-8', with_tail=False).decode('utf-8'),
                               lb.get('{http://www.w3.org/XML/1998/namespace}id').lstrip('l'),
                               lb.get('n'),
                               glyph.xpath('./preceding::pb[1]')[0].get('n'))
                    message += e.__str__() + "\n"
                    safeerrmsg(message)
                    return None
            gref = '#%s' % glyphs_seen[glyphid].get('{http://www.w3.org/XML/1998/namespace}id')
            # Finally, fix the 'g' element here so that it is canonical.
            glyph.set('ref', gref)
            if not gtext_explicit:
                glyph.text = glyphid

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
            if int(certval) >= 70:
                el.set('cert', 'high')
            elif int(certval) >= 45:
                el.set('cert', 'medium')
            else:
                el.set('cert', 'low')

    return _tei_wrap(content, metadata, members,
                     sorted(glyphs_seen.values(),
                            key=lambda x: x.get('{http://www.w3.org/XML/1998/namespace}id')),
                     postprocess)


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


def _show_parsing_short_error(e, st):
    # Figure out where the error is
    txlines = st.splitlines()
    problemstart = e.position[0] - 1
    # Is it an error that spans multiple lines? If so figure out where it starts
    tagmismatch = re.search('Opening and ending tag mismatch: \w+ line (\d+)', e.msg)
    if tagmismatch is not None:
        problemstart = int(tagmismatch.group(1)) - 1
    # Look up the page where the error starts
    pagestart = problemstart
    for i in range(problemstart, -1, -1):
        if '<pb n=' in txlines[i]:
            pagestart = i
            break
    diagnostic_loc = ["%d: %s" % (i + 1, txlines[i]) for i in range(pagestart, e.position[0])]
    if e.position[0] - problemstart > 100:
        # Restrict the output to the single page of the problem
        for i in range(1, len(diagnostic_loc)):
            if '<pb n=' in diagnostic_loc[i]:
                diagnostic_loc = diagnostic_loc[:i]
                break
    return "Affected portion of XML is %s" % '\n'.join(diagnostic_loc)


def safeerrmsg(message):
    if sys.platform.startswith("win"):
        sys.stdout.buffer.write(message.encode(sys.getdefaultencoding()))
    else:
        print(message, file=sys.stderr)


def _tei_wrap(content, metadata, members, glyphs, postprocess):
    """Wraps the content, and the glyphs that were found, into TEI XML format."""
    # Set some trivial default TEI header values, if they are not already set
    defaults = {
        'title': 'A manuscript transcribed with T-PEN',
        'publicationStmt': 'Unpublished manuscript',
        'teiSchema': 'http://www.tei-c.org/release/xml/tei/custom/schema/relaxng/tei_all.rng'
    }
    if metadata is None:
        metadata = {}
    for key in defaults.keys():
        if key not in metadata:
            metadata[key] = defaults[key]

    # Now make the outer TEI wrapper and the header for the content we have been passed.
    tei = etree.Element('TEI')
    file_desc = etree.SubElement(etree.SubElement(tei, 'teiHeader'), 'fileDesc')
    title_stmt = etree.SubElement(file_desc, 'titleStmt')
    etree.SubElement(title_stmt, 'title').text = metadata['title']
    if 'author' in metadata:
        etree.SubElement(title_stmt, 'author').text = metadata['author']
    edition_stmt = etree.SubElement(file_desc, 'editionStmt')
    etree.SubElement(edition_stmt, 'edition').text = 'T-Pen transcription'
    if members is not None:
        # Add the transcribers that we have seen
        for mid, minfo in members.items():
            resp_stmt = etree.SubElement(edition_stmt, 'respStmt')
            resp_stmt.set('{http://www.w3.org/XML/1998/namespace}id', "u%s" % mid)
            etree.SubElement(resp_stmt, 'resp').text = 'T-Pen transcriber'
            key = 'name'
            if key not in minfo:
                key = 'uname'
            etree.SubElement(resp_stmt, 'name').text = minfo.get(key, 'Anonymous')
    etree.SubElement(etree.SubElement(file_desc, 'publicationStmt'), 'p').text = metadata['publicationStmt']

    # Source and manuscript description
    msdesc = etree.SubElement(etree.SubElement(file_desc, 'sourceDesc'), 'msDesc')
    # Do we have a settlement/repository/ID defined? If so make the msIdentifier an XML ID.
    has_rich_id = 'msSettlement' in metadata or 'msRepository' in metadata or 'msIdNumber' in metadata
    if 'msIdentifier' in metadata:
        desc_container = etree.SubElement(msdesc, 'msIdentifier')
        if has_rich_id:
            msdesc.set('{http://www.w3.org/XML/1998/namespace}id', metadata['msIdentifier'])
            if 'msSettlement' in metadata:
                etree.SubElement(desc_container, 'settlement').text = metadata['msSettlement']
            if 'msRepository' in metadata:
                etree.SubElement(desc_container, 'repository').text = metadata['msRepository']
            if 'msIdNumber' in metadata:
                etree.SubElement(desc_container, 'idno').text = metadata['msIdNumber']
        else:  # If not, use the text content of the identifier as the XML msIdentifier content.
            desc_container.text = metadata['msIdentifier']
    has_origin = 'date' in metadata or 'location' in metadata
    if has_origin:
        origin = etree.SubElement(etree.SubElement(msdesc, 'history'), 'origin')
        if 'date' in metadata:
            etree.SubElement(origin, 'origDate').text = metadata['date']
        if 'location' in metadata:
            etree.SubElement(origin, 'origPlace').text = metadata['location']
    if 'description' in metadata:
        etree.SubElement(msdesc, 'p').text = metadata['description']
    # TODO consider filling out msContents / msItem

    # Then add the glyphs we used
    if len(glyphs):
        etree.SubElement(etree.SubElement(tei.find('teiHeader'), 'encodingDesc'), 'charDecl').extend(glyphs)
    # Then add the content.
    etree.SubElement(tei, 'text').append(content)
    # Finally, set the appropriate namespace and schema.
    tei.set('xmlns', 'http://www.tei-c.org/ns/1.0')
    tei_doc = etree.ElementTree(tei)
    pi = 'href="%s" type="application/xml" schematypens="http://relaxng.org/ns/structure/1.0"' % metadata['teiSchema']
    schema = etree.ProcessingInstruction('xml-model', pi)
    tei.addprevious(schema)
    # Now that we've done this, serialize and re-parse the entire TEI doc
    # so that the namespace functionality works.
    try:
        tei_doc = etree.parse(BytesIO(etree.tostring(tei_doc)))
    except etree.XMLSyntaxError as e:
        message = "Error in final parse: "
        message += _show_parsing_short_error(e, etree.tostring(tei_doc, encoding="utf-8").decode('utf-8'))
        safeerrmsg(message)
    if postprocess is not None:
        postprocess(tei_doc)
    return tei_doc


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-t", "--title",
        default="A text generated by tpen2tei",
        help="Title that should be passed to the text",
    )
    parser.add_argument(
        "--short-error",
        action="store_true",
        help="Reduce the amount of error output on XML parsing failures"
    )
    parser.add_argument(
        "infile",
        help="SC-JSON file containing a T-PEN transcription",
    )
    args = parser.parse_args()
    with open(args.infile, encoding='utf-8') as jfile:
        msdata = json.load(jfile)
    default_metadata = {'title': args.title, 'short_error': args.short_error}
    xmltree = from_sc(msdata, metadata=default_metadata)
    if xmltree is not None:
        sys.stdout.buffer.write(etree.tostring(xmltree, encoding='utf-8', pretty_print=True, xml_declaration=True))
