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
from itertools import takewhile, groupby, chain
from collections import namedtuple


Transaction = namedtuple(
	'Transaction',
	['date', 'description', 'amount', 'balance']
)

class History(object):
	def __init__(self, account_type, account_number,
			opening_balance, transactions):
		self.account_type = account_type
		self.account_number = account_number
		self.opening_balance = opening_balance
		self.transactions = transactions


def main(args):
	if len(args) == 0:
		sys.stderr.write('Usage: usaverultra.py FILES...\n')
		sys.exit(1)
	histories = [read_history(filename) for filename in args]
	unified = unify_histories(histories)
	print_history(unified)


def read_history(filename):
	def error(msg):
		raise Exception(filename + ': ' + msg)

	def split_rows(rows):
		def get_head(rows):
			pattern = ['','Transaction date','Description','Amount','Balance']
			head = list(takewhile(lambda r: r != pattern, rows))
			if len(head) == len(rows):
				error('Does not contain table header row.\n'
					'Expected: ' + ','.join(pattern))
			return head + [pattern]

		def isfootrow(row):
			return row == [] \
				or row[1].startswith('UBank is a division') \
				or row[1].startswith('Date')

		def get_foot(rows):
			return list(reversed(list(takewhile(isfootrow, reversed(rows)))))

		head = get_head(rows)
		foot = get_foot(rows)
		body = rows[len(head):-len(foot)]
		return head, body, foot

	def get_account(rows):
		import re
		for row in rows:
			if len(row) >= 2:
				m = re.match(r'^(.*) \| (\d+)$', row[1])
				if m:
					return m.groups()
		error('Cannot find account number')

	def get_transaction(row):
		from datetime import datetime
		from decimal import Decimal
		import re

		if len(row) != 5:
			error('Transaction row with incorrect number of columns')
		_, s_transdate, description, s_amount, s_balance = row
		transdate = datetime.strptime(s_transdate, '%d/%m/%Y').date()
		amount = Decimal(s_amount.replace('$', '').replace(',', '')
				.replace('--', ''))  # workaround for double negative
		m = re.match(r'^\$([0-9,.]+) ([CD]R)$', s_balance)
		balance = Decimal(m.group(1).replace(',', ''))
		if m.group(2) == 'DR':
			balance = -balance
		return Transaction(transdate, description, amount, balance)

	import csv
	with open(filename, 'rb') as csvfile:
		rows = list(csv.reader(csvfile))

	head, body, foot = split_rows(rows)
	account_type, account_number = get_account(head)
	transactions = [get_transaction(row) for row in reversed(body)
			if not row[2].startswith('PLEASE NOTE')]
	if len(transactions) == 0:
		error('No transactions listed (cannot obtain account balance)')
	opening_balance = transactions[0].balance - transactions[0].amount
	return History(account_type, account_number, opening_balance, transactions)


def unify_histories(histories):
	def remove_corresponding(acnum0, trans0, acnum1, translist1):
		def fmt(s): return s.format(acnum0, acnum1)
		prefix_pairs = [(fmt(x), fmt(y)) for x, y in [
			('Sweep from {1}', 'Sweep out to {0}'),
			('Sweep out to {1}', 'Sweep from {0}'),
			('Sweep from {1}', 'Sweep out to {0} .'),
			('Sweep out to {1} .', 'Sweep from {0}'),
			('Sweep from {1}', 'Sweep into {0}'),
			('Sweep into {1}', 'Sweep from {0}'),
			('Funds Transfer to {1}', 'Funds Transfer'),
			('Funds Transfer', 'Funds Transfer to {0}'),
			('Regular Transfer between accounts', 'Regular Transfer to {0} between accounts'),
			('Regular Transfer to {1} between accounts', 'Regular Transfer between accounts'),
		]]

		for prefix, co_prefix in prefix_pairs:
			if trans0.description.startswith(prefix):
				co_description = trans0.description.replace(
						prefix, co_prefix)
				co_amount = -trans0.amount
				if remove_transaction(translist1, trans0.date,
						co_description, co_amount):
					return True
		else:
			return False


	def remove_transaction(translist, date, description, amount):
		for i, trans in enumerate(translist):
			if trans.date == date \
					and trans.description == description \
					and trans.amount == amount:
				translist.pop(i)
				return True
		else:
			return False


	acnums = [h.account_number for h in histories]
	if len(acnums) != 2 or acnums[0] == acnums[1]:
		raise Exception('Requires exactly two different accounts. ' +
				'Account numbers were: ' +
				','.join(acnums))

	a = list(histories[0].transactions)
	b = [t for t in histories[1].transactions
			if not remove_corresponding(acnums[1], t, acnums[0], a)]

	alltrans = sorted(a + b, key=lambda trans: trans.date)
	opening_balance = sum(h.opening_balance for h in histories)
	return History('Unified', ' & '.join(acnums), opening_balance, alltrans)


def print_history(history):
	template = '{date:<12}{description:<38}{payment:>10}{deposit:>10}{balance:>10}'
	balance = history.opening_balance
	for trans in history.transactions:
		balance += trans.amount
		if trans.amount > 0:
			payment, deposit = '', trans.amount
		else:
			payment, deposit = -trans.amount, ''
		print template.format(
				date=trans.date.strftime('%d/%m/%Y'),
				description=trans.description[:37],
				payment=payment, deposit=deposit, balance=balance)


if __name__ == '__main__':
	import sys
	main(sys.argv[1:])
