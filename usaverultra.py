#!/usr/bin/env python

import sys

def main(args):
	if len(args) == 0:
		sys.stderr.write('Usage: usaverultra.py FILES...'\n)
		sys.exit(1)
	histories = [read_history(filename) for filename in args]
	unified = unify_histories(histories)
	print_history(unified)


if __name__ == '__main__':
	import sys
	main(sys.argv[1:])
