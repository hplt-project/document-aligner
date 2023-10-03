#!/usr/bin/env python3
import sys
import math

max_diff = float(sys.argv[1])

has_diff = False

with open(sys.argv[2], 'r') as file1, open(sys.argv[3], 'r') as file2:
	for n, (line1, line2) in enumerate(zip(file1, file2)):
		is_diff = False

		if n == 0: # header
			is_diff |= line1 != line2
		else:
			cols1 = line1.split()
			cols2 = line2.split()

			# Diff score
			is_diff |= math.fabs(float(cols1[0]) - float(cols2[0])) > max_diff

			# Diff translated index
			is_diff |= cols1[1] != cols2[1]

			# Diff ref index
			is_diff |= cols1[2] != cols2[2]

		if is_diff:
			sys.stderr.write(f"--- Line {n} ---\n")
			sys.stderr.write("< ")
			sys.stderr.write(line1)
			sys.stderr.write("> ")
			sys.stderr.write(line2)

		has_diff |= is_diff
	
	if has_diff:
		sys.exit(1)