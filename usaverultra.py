#!/usr/bin/env python

import sys
from itertools import takewhile

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

	import csv
	with open(filename, 'rb') as csvfile:
		rows = list(csv.reader(csvfile))

	head, transactions, foot = split_rows(rows)


if __name__ == '__main__':
	import sys
	main(sys.argv[1:])
