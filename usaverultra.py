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


import sys
import logging
import argparse
import xml.etree.ElementTree as ET
from decimal import Decimal
from collections import namedtuple, defaultdict

logger = logging.getLogger('usaverultra')

class TerminalError(Exception):
    '''Print message (but not stack trace) then exit program.'''

Statement = namedtuple('Statement', ['account', 'balance', 'transactions']);
Transaction = namedtuple('Transaction', ['id', 'date', 'amount', 'description'])

def mkTransaction(element):
    '''Construct a Txn from a STMTTRN element.'''
    id = element.find('FITID').text
    date = element.find('DTPOSTED').text
    amount = Decimal(element.find('TRNAMT').text.replace('--', ''))  # workaround for double negative
    description = element.find('NAME').text
    return Transaction(id, date, amount, description)

def read_ofx(filename):
    try:
        with open(filename) as f:
            raw_content = f.read()
    except IOError, e:
        raise TerminalError(e)
    # Apparently the file is created using string interpolation; it's not valid XML.
    sanitised_content = raw_content.replace('&', '&amp;')
    root = ET.fromstring(sanitised_content)
    account = root.find('.//ACCTID').text
    balance = Decimal(root.find('.//LEDGERBAL/BALAMT').text)
    txns = [mkTransaction(elem) for elem in root.findall('.//STMTTRN')
            if elem.find('FITID').text != 'null']
    return Statement(account, balance, txns)

def unify_statements(stmts):
    accounts = defaultdict(list)
    for stmt in stmts:
        accounts[stmt.account].append(stmt)
    acctnums = sorted(accounts.keys())
    logger.info('Found {0} accounts ({1})'.format(len(acctnums), ', '.join(acctnums)))
    if len(acctnums) != 2:
        raise TerminalError('The input files must relate to TWO different accounts')

parser = argparse.ArgumentParser()
parser.add_argument('--ofx', dest='format', action='store_const', const='ofx', default='txt',
                    help='produce OFX output (default: text output)')
parser.add_argument('infiles', metavar='FILE', nargs='+',
                    help='input file, in OFX format')

def main():
    args = parser.parse_args()
    statements = [read_ofx(fn) for fn in args.infiles]
    logger.info('Read {} input files'.format(len(statements)))
    unified = unify_statements(statements)


if __name__ == '__main__':
    logging.basicConfig(format='[%(levelname)s] %(msg)s', level=logging.INFO)
    try:
        main()
    except TerminalError, e:
        logging.error(e)
        sys.exit(1)
