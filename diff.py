def lcs(p, q):
    mem = _lcs(p, q)
    return mem[len(mem) - 1][len(mem[0]) - 1]

def _lcs(p, q):
    # initialize an array of size m x n
    m, n = len(p) + 1, len(q) + 1
    # first index with 0 <= x < m, and then index with 0 <= y < n
    # e.g. mem[x][y]
    mem = [[None for _ in range(n)] for _ in range(m)]

    # fill out the (0, y) and (x, 0) locations
    for x in range(m):
        mem[x][0] = 0
    for y in range(n):
        mem[0][y] = 0

    # fill out the other slots
    for x in range(1, m):
        for y in range(1, n):
            # what is lcs(p, q, x, y), where x, y are the length of p, q?
            if p[x - 1] == q[y - 1]:
                result = 1 + mem[x - 1][y - 1]
            else:
                temp1 = mem[x - 1][y]
                temp2 = mem[x][y - 1]
                result = max(temp1, temp2)
            mem[x][y] = result

    return mem

def print_diff(p, q):
    mem = _lcs(p, q)
    yield from _print_diff(p, q, mem, len(p), len(q))

def _print_diff(p, q, mem, x, y):
    if x > 0 and y > 0 and p[x - 1] == q[y - 1]:
        yield from _print_diff(p, q, mem, x - 1, y - 1)
        yield (' ', p[x - 1])
    elif y > 0 and (x == 0 or mem[x][y - 1] >= mem[x - 1][y]):
        yield from _print_diff(p, q, mem, x, y - 1)
        yield ('+', q[y - 1])
    elif x > 0 and (y == 0 or mem[x][y - 1] < mem[x - 1][y]):
        yield from _print_diff(p, q, mem, x - 1, y)
        yield ('-', p[x - 1])
