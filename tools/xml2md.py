import xml.etree.ElementTree as ET


def xml2md(elem: ET.Element, idx=0):
    if elem.tag == 'p':
        return ((elem.text if elem.text else '') +
                ''.join(xml2md(inner) for inner in elem) +
                (elem.tail if elem.tail else '') + '\n')
    if elem.tag == 'ul':
        return ((elem.text if elem.text else '') + '\n' +
                ''.join(xml2md(inner, i) for i, inner in enumerate(elem)) +
                (elem.tail if elem.tail else '') + '\n')
    if elem.tag == 'ol':
        return ((elem.text if elem.text else '') + '\n' +
                ''.join(xml2md(inner, i) for i, inner in enumerate(elem)) +
                (elem.tail if elem.tail else '') + '\n')
    if elem.tag == 'li':
        return (f'{idx + 1}) ' + (elem.text if elem.text else '') +
                ''.join(xml2md(inner, i) for i, inner in enumerate(elem)) +
                (elem.tail if elem.tail else '') + '\n')
    if elem.tag == 'pre':
        return '```\n' + ''.join(elem.itertext()) + '\n```' + (elem.tail if elem.tail else '')
    if elem.tag == 'b':
        return '**' + ''.join(elem.itertext()) + '**' + (elem.tail if elem.tail else '')
    if elem.tag == 'tt' or elem.tag == 'code':
        return '`' + ''.join(elem.itertext()) + '`' + (elem.tail if elem.tail else '')
    if elem.tag == 'a':
        return '[' + ''.join(elem.itertext()) + '](' + elem.attrib['href'] + ')' + (elem.tail if elem.tail else '')
    if elem.tag == 'details' or elem.tag == 'summary':
        return f'<{elem.tag}>\n' + (elem.text.strip() if elem.text else '') + \
            ''.join(xml2md(inner, i) for i, inner in enumerate(elem)) + \
            (elem.tail if elem.tail else '') + f'\n</{elem.tag}>\n'
    raise RuntimeError(f"Unsupported {elem}")


tree = ET.parse('statement.xml')
root = tree.getroot()
with open('README.md', 'w') as f:
    f.write('### Statement\n\n')
    for elem in root.find('statement').find('description'):
        f.write(xml2md(elem))
        f.write('\n')
    if root.find('examples') is not None:
        for example in list(root.find('examples').findall('example')):
            f.write('### Example\n\n')
            f.write('Input:\n')
            f.write(f'```\n{''.join(example.find('input').itertext())}\n```\n\n')
            f.write('Output:\n')
            f.write(f'```\n{''.join(example.find('output').itertext())}\n```\n\n')
