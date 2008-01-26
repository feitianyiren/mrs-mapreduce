#!/usr/bin/env python
# We wanted to figure out how to sort data as its coming in from multiple
# sources.  This script compares a few different ways to do this.  It turns
# out that "Method 1" is much faster than "Method 2" or "Method 3".
#
# Thus, the best way to do this is to heapify the data as they arrive, and
# then to sort the final result.

from random import random
from heapq import heapify, heappop
from itertools import chain
from timeit import Timer

NLISTS = 1000
SIZE = 10000

lists = [[random() for i in xrange(SIZE)] for j in xrange(NLISTS)]

heap = list(chain(*lists))
heapify(heap)

for lst in lists:
    lst.sort()

# Now lists is a list of sorted lists and heap is a heap.

def method1():
    heap_sorted = sorted(heap)
timer1 = Timer('method1()', 'from __main__ import method1')

def method2():
    heap_popped = []
    while heap:
        heap_popped.append(heappop(heap))
timer2 = Timer('method2()', 'from __main__ import method2')

def method3():
    list_sorted = sorted(chain(*lists))
timer3 = Timer('method3()', 'from __main__ import method3')

if __name__ == '__main__':
    print 'Method 1:', timer1.timeit(1)
    print 'Method 2:', timer2.timeit(2)
    print 'Method 3:', timer3.timeit(3)

# vim: et sw=4 sts=4