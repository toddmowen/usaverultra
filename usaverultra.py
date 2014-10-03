#!/usr/bin/env python

import sys
from itertools import takewhile


class History(object):
	def __init__(self, account_type, account_number, transactions):
		self.account_type = account_type
		self.account_number = account_number
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
		print row
		_, s_transdate, description, s_amount, s_balance = row
		transdate = datetime.strptime(s_transdate, '%d/%m/%Y').date()
		amount = Decimal(s_amount.replace('$', '').replace(',', '')
				.replace('--', ''))  # workaround for double negative
		print s_balance
		m = re.match(r'^\$([0-9,.]+) ([CD]R)$', s_balance)
		balance = Decimal(m.group(1).replace(',', ''))
		if m.group(2) == 'DR':
			balance = -balance
		return (transdate, description, amount, balance)

	import csv
	with open(filename, 'rb') as csvfile:
		rows = list(csv.reader(csvfile))

	head, body, foot = split_rows(rows)
	account_type, account_number = get_account(head)
	transactions = [get_transaction(row) for row in body
			if not row[2].startswith('PLEASE NOTE')]
	return History(account_type, account_number, transactions)


if __name__ == '__main__':
	import sys
	main(sys.argv[1:])
