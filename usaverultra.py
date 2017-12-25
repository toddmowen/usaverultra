#!/usr/bin/env python2.7
#
# Copyright 2014 Todd Owen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import logging
import argparse
import xml.etree.ElementTree as ET
from decimal import Decimal
from collections import namedtuple

logger = logging.getLogger('usaverultra')

Txn = namedtuple('Txn', ['id', 'date', 'amount', 'description'])

def mkTxn(element):
    '''Construct a Txn from a STMTTRN element.'''
    id = element.find('FITID').text
    date = element.find('DTPOSTED').text
    amount = Decimal(element.find('TRNAMT').text)
    description = element.find('NAME').text
    return Txn(id, date, amount, description)

def read_ofx(filename):
    with open(filename) as f:
        raw_content = f.read()
    # Apparently the file is created using string interpolation; it's not valid XML.
    sanitised_content = raw_content.replace('&', '&amp;')
    root = ET.fromstring(sanitised_content)
    txn_elements = root.findall('.//STMTTRN')
    return map(mkTxn, txn_elements)

parser = argparse.ArgumentParser()
parser.add_argument('--ofx', dest='format', action='store_const', const='ofx', default='txt',
                    help='produce OFX output (default: text output)')
parser.add_argument('infiles', metavar='FILE', nargs='+',
                    help='input file, in OFX format')

def main(filenames):
    args = parser.parse_args()
    statements = [read_ofx(fn) for fn in args.infiles]

if __name__ == '__main__':
    logging.basicConfig(format='[%(levelname)s] %(msg)s')
    import sys
    main(sys.argv[1:])
