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
import itertools
import re
import xml.etree.ElementTree as ET
from decimal import Decimal
from collections import namedtuple, defaultdict

logger = logging.getLogger('usaverultra')

class TerminalError(Exception):
    '''Print message (but not stack trace) then exit program.'''

# Important: for each statement, transactions must be in *reverse* chronological order
# (which is the order that UBank lists them in the OFX file).
Statement = namedtuple('Statement', ['account', 'opening_balance', 'transactions']);
Transaction = namedtuple('Transaction', ['id', 'date', 'amount', 'description'])

def start_date(stmt):
    return stmt.transactions[0].date[:8]

def end_date(stmt):
    return stmt.transactions[-1].date[:8]

def mkTransaction(element):
    '''Construct a Txn from a STMTTRN element.'''
    id = element.find('FITID').text
    date = element.find('DTPOSTED').text
    amount = Decimal(element.find('TRNAMT').text.replace('--', ''))  # workaround for double negative
    description = element.find('NAME').text
    return Transaction(id, date, amount, description)

def sanitise_xml(content):
    '''Fix common XML errors in the files that UBank provides.'''
    for pattern, replacement in [
        (r'&(?![a-z])', '&amp;'),  # ampersand that doesn't appear to be an entity code
        (r'^\d\d\d\d-\d\d-\d\d</(DTSTART|DTEND)>', ''),  # delete DTSTART/DTEND missing opening tag
    ]:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    return content

def read_ofx(filename):
    try:
        with open(filename) as f:
            raw_content = f.read()
    except IOError, e:
        raise TerminalError(e)
    try:
        root = ET.fromstring(sanitise_xml(raw_content))
    except ET.ParseError, e:
        raise TerminalError("Failed to parse '{0}': {1}".format(filename, e))
    account = root.find('.//ACCTID').text
    ledgerbal = Decimal(root.find('.//LEDGERBAL/BALAMT').text)
    txns = [mkTransaction(elem) for elem in root.findall('.//STMTTRN')
            if elem.find('FITID').text != 'null']
    # LEDGERBAL that UBank gives us is actually the balance *after* the earliest transaction
    return Statement(account, ledgerbal - txns[-1].amount, txns)

def closing_balance(stmt):
    '''Calculating forward from the opening balance, compute statement closing balance.'''
    return stmt.opening_balance + sum(txn.amount for txn in stmt.transactions)

def group_statements(stmts):
    accounts = defaultdict(list)
    for stmt in stmts:
        accounts[stmt.account].append(stmt)
    acctnums = sorted(accounts.keys())
    logger.info('Found {0} accounts ({1})'.format(len(acctnums), ', '.join(acctnums)))
    if len(acctnums) != 2:
        raise TerminalError('The input files must relate to TWO different accounts')
    # Return in sorted order, not just accounts.values()
    return [accounts[num] for num in acctnums]

def splice_statements(stmts):
    '''Take one or more statements FOR THE SAME ACCOUNT, and concatenate into a single statement.'''

    def count_transactions_on_most_recent_day(stmt):
        return len(itertools.groupby(stmt.transactions, key=lambda t: t.date).next())

    # First sort into *reverse* chronological order
    def compare(*stmts):
        dates = [s.transactions[0].date for s in stmts]
        if dates[0] == dates[1]:
            # A statement listing 2 transactions on the most recent day is more
            # up-to-date than a statement listing only 1 transaction for the same day.
            counts = [count_transactions_on_most_recent_day(s) for s in stmts]
            return -cmp(*counts)
        else:
            return -cmp(*dates)

    logger.info('Splicing {0} statements for account {1}:'.format(len(stmts), stmts[0].account))
    ordered = sorted(stmts, cmp=compare)
    spliced = None
    for s in ordered:
        logger.info('+ {0} to {1} ({2} transactions; close ${3}, open ${4}):'
                    .format(start_date(s), end_date(s), len(s.transactions),
                            closing_balance(s), s.opening_balance))
        if len(s.transactions) == 0:
            outcome = 'Ignored empty statement'
        elif spliced is None:
            spliced = s
            outcome = 'Initialized master statement'
        else:
            for (i, txn) in enumerate(s.transactions):
                if txn == spliced.transactions[-1]:
                    assert spliced.transactions[-(i+1):] == s.transactions[:(i+1)]
                    if i >= len(spliced.transactions):
                        spliced = s
                        outcome = 'Replaced master statement with strict supersequence'
                    else:
                        spliced_txns = spliced.transactions + s.transactions[(i+1):]
                        spliced = Statement(spliced.account, s.opening_balance, spliced_txns)
                        outcome = 'Appended {0} transactions (verified precise overlap of {1} transactions)' \
                                  .format(len(s.transactions) - i - 1, i + 1)
                    break
            else:
                if spliced.opening_balance == closing_balance(s):
                    spliced_txns = spliced.transactions + s.transactions
                    spliced = Statement(spliced.account, s.opening_balance, spliced_txns)
                    outcome = 'Appended all transactions (verified opening/closing balances align)'
                else:
                    raise TerminalError('Merge failure: expected closing balance ${0}, instead found ${1}'
                                        .format(spliced.opening_balance, closing_balance(s)))
        logger.info('  ' + outcome)
    return spliced

def merge_statements(stmt1, stmt2):
    '''Produce a single statement from two statements for DIFFERENT ACCOUNTS.'''
    logger.info('Merging master statements with {0} and {1} transactions'
                .format(len(stmt1.transactions), len(stmt2.transactions)))
    transfers = set((t.id, t.amount) for t in stmt1.transactions).intersection(
                set((t.id, -t.amount) for t in stmt2.transactions))
    logger.info('Removed {0} inter-account transfers'.format(len(transfers)))
    merged_txns = sorted(
        [t for t in stmt1.transactions if (t.id, t.amount) not in transfers] +
        [t for t in stmt2.transactions if (t.id, -t.amount) not in transfers],
        key=lambda t: t.date, reverse=True)
    merged = Statement(
        '{0}/{1}'.format(stmt1.account, stmt2.account),
        stmt1.opening_balance + stmt2.opening_balance,
        merged_txns)
    logger.info('= {0} to {1} ({2} transactions; close ${3}, open ${4})'
                .format(end_date(merged), start_date(merged), len(merged.transactions),
                        closing_balance(merged), merged.opening_balance))
    return merged

def unify_statements(stmts):
    groups = group_statements(stmts)
    spliced = [splice_statements(acctstmts) for acctstmts in groups]
    unified = merge_statements(*spliced)
    return unified

def print_statement(stmt):
    template = '{date:<12}{description:<38}{payment:>10}{deposit:>10}{balance:>10}'
    balance = stmt.opening_balance
    for trans in reversed(stmt.transactions):
        balance += trans.amount
        if trans.amount > 0:
            payment, deposit = '', trans.amount
        else:
            payment, deposit = -trans.amount, ''
        print template.format(
            date='/'.join([trans.date[6:8], trans.date[4:6], trans.date[0:4]]),
            description=trans.description[:37],
            payment=payment, deposit=deposit, balance=balance)


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
    print_statement(unified)


if __name__ == '__main__':
    logging.basicConfig(format='[%(levelname)s] %(msg)s', level=logging.INFO)
    try:
        main()
    except TerminalError, e:
        logging.error(e)
        sys.exit(1)
