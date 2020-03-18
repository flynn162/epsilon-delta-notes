import io

class Cons(object):
    __slots__ = ('car', 'cdr', 'line')
    def __init__(self, car, cdr, line = 0):
        self.car = car
        self.cdr = cdr
        # parsing information
        self.line = line

    def _writer(self, result):
        result.write('(')
        result.write(repr(self.car))
        curr = self.cdr
        while isinstance(curr, Cons):
            result.write(' ')
            result.write(repr(curr.car))
            curr = curr.cdr
        if curr is None:
            result.write(')')
        else:
            result.write(' . ')
            result.write(repr(curr))
            result.write(')')

    def __repr__(self):
        with io.StringIO() as result:
            self._writer(result)
            result.seek(0)
            return result.read()

    def __iter__(self):
        return ListIterator(self)

class ListIterator(object):
    __slots__ = ('cons',)
    def __init__(self, cons):
        self.cons = cons

    def __iter__(self):
        return self

    def __next__(self):
        if self.cons is None:
            raise StopIteration()
        else:
            result = self.cons.car
            self.cons = self.cons.cdr
            return result

class Symbol(object):
    __slots__ = ('value',)
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return self.value

def List(*args):
    current = None
    for element in reversed(args):
        current = Cons(element, current)
    return current
