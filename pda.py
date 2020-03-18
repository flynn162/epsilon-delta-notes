from enum import IntEnum
from collections import namedtuple, deque
from cons import Symbol, Cons
import io
import re

class State(IntEnum):
    TEXT = 0,
    CMD_NAME = 1,
    UNEXPECT = 2,
    ACCEPTING = 3,

class Stack(IntEnum):
    DOLLAR = 0,
    OPEN = 1
    OPEN_ALT = 2,
    CMD_OPEN = 3,
    CMD_OPEN_ALT = 4,

class Input(IntEnum):
    FALLBACK = 0,
    EOF = 1,

class Bytecode(IntEnum):
    OPEN_LIST = 0,
    CLOSE_LIST = 1,
    ADD_SYMBOL = 2,
    ADD_STRING = 3,
    ADD_LINES = 4,

from tokenizing import InputTuple, token_iter, ParserError

class PDAError(ParserError):
    pass

class Registry:
    leaving_handlers = {}
    routing_handlers = {}

    @classmethod
    def on(cls, some_state):
        def decorator(method):
            cls.entering_handlers[some_state] = method
            return method
        return decorator

    @classmethod
    def leaving(cls, some_state):
        def decorator(method):
            cls.leaving_handlers[some_state] = method
            return method
        return decorator

    @classmethod
    def route_from(cls, some_state):
        def decorator(method):
            cls.routing_handlers[some_state] = method
            return method
        return decorator

class BasePDA:
    def __init__(self, initial_state, initial_stack_symbol):
        self.state = initial_state
        self.stack = deque()
        self.stack.append(initial_stack_symbol)
        # changes on every input
        self.text = None
        self.param = None
        self.line = 0

    def try_route(self, to_state, old_stack_top, new_stack_top):
        # Check and remove the top element of the stack
        if old_stack_top is not None:
            if self.stack[0] != old_stack_top:
                return None
            else:
                self.stack.popleft()

        # Push new element onto the stack
        if new_stack_top is not None:
            self.stack.appendleft(new_stack_top)

        # Call the leaving handler
        if self.state != to_state:
            handler = Registry.leaving_handlers.get(self.state)
            if handler is not None:
                handler(self)

        # Switch to another state
        return to_state

    def route(self, to_state, old_stack_top, new_stack_top):
        new_state = self.try_route(to_state, old_stack_top, new_stack_top)
        if new_state is None:
            raise PDAError('Cannot find a suitable edge to %r' % to_state)
        else:
            return new_state

    def process_token(self, text, param, line):
        self.text = text
        self.param = param
        self.line = line
        # select which state to go to (leaving handler will be called)
        self.state = Registry.routing_handlers[self.state](self)

    def execute_asm(self):
        vm = VM()
        for instruction in self.asm:
            vm.execute(*instruction)
        return vm.root

    def run(self, tokens):
        line = 1
        for (text, param) in token_iter(tokens):
            self.process_token(text, param, line)
            if text == '\n':
                line += param

        if not self.is_in_accepting_state():
            raise PDAError(line, 'Expect more content after this token')
        else:
            return self.finish_up()

regex = re.compile('[a-zA-Z0-9_-]')

class PDA(BasePDA):
    def __init__(self):
        super().__init__(State.TEXT, Stack.DOLLAR)
        self.asm = deque()
        # initialize various accumulators
        self.symbol_acc = io.StringIO()
        self.string_acc = io.StringIO()

    def is_in_accepting_state(self):
        return self.stack[0] == Stack.DOLLAR

    def finish_up(self):
        self.leaving_text()
        return self.execute_asm()

    def _output(self, instruction):
        self._flush_and_reset_string_acc()
        self.asm.append(instruction)

    def _flush_and_reset_string_acc(self):
        self.string_acc.seek(0)
        full_text = self.string_acc.read()
        if full_text:
            self.asm.append((Bytecode.ADD_STRING, full_text))
        self.string_acc.seek(0)
        self.string_acc.truncate(0)

    @Registry.route_from(State.TEXT)
    def select_an_edge_from_state_text(self):
        if self.text == '@':
            # the start of a command
            return self.route(State.CMD_NAME, None, None)

        # check if we are closing anything
        if self.text == '}':
            if self.stack[0] == Stack.CMD_OPEN:
                self._output((Bytecode.CLOSE_LIST,))
                return self.route(State.TEXT, Stack.CMD_OPEN, None)
            elif self.stack[0] == Stack.OPEN:
                self.string_acc.write(self.text)
                return self.route(State.TEXT, Stack.OPEN, None)
        elif self.text == '}|':
            if self.stack[0] == Stack.CMD_OPEN_ALT:
                self._output((Bytecode.CLOSE_LIST,))
                return self.route(State.TEXT, Stack.CMD_OPEN_ALT, None)
            elif self.stack[0] == Stack.OPEN_ALT:
                self.string_acc.write(self.text)
                return self.route(State.TEXT, Stack.OPEN_ALT, None)

        if self.text == '{':
            self.string_acc.write(self.text)
            return self.route(State.TEXT, None, Stack.OPEN)
        elif self.text == '|{':
            self.string_acc.write(self.text)
            return self.route(State.TEXT, None, Stack.OPEN_ALT)

        # otherwise, keep consuming text
        self.on_text()
        return self.route(State.TEXT, None, None)

    def on_text(self):
        if self.text == '\n':
            # self.param is set to the number of consecutive \n's
            self._flush_and_reset_string_acc()
            self._output((Bytecode.ADD_LINES, self.param))
        else:
            self.string_acc.write(self.text)

    @Registry.leaving(State.TEXT)
    def leaving_text(self):
        self._flush_and_reset_string_acc()

    @Registry.route_from(State.CMD_NAME)
    def select_an_edge_from_state_cmd_name(self):
        if self.text == '{':
            return self.route(State.TEXT, None, Stack.CMD_OPEN)
        elif self.text == '|{':
            return self.route(State.TEXT, None, Stack.CMD_ALT_OPEN)
        else:
            self.on_cmd_name()
            return self.route(State.CMD_NAME, None, None)  # self loop

    def on_cmd_name(self):
        if self.text.isspace():
            return
        elif regex.match(self.text):
            self.symbol_acc.write(self.text)
        else:
            raise PDAError('Symbol')

    @Registry.leaving(State.CMD_NAME)
    def leaving_cmd_name(self):
        self._output((Bytecode.OPEN_LIST, self.line))
        if self.symbol_acc.tell() > 0:
            self.symbol_acc.seek(0)
            self._output((Bytecode.ADD_SYMBOL, self.symbol_acc.read()))
            self.symbol_acc.seek(0)
            self.symbol_acc.truncate(0)

    @Registry.route_from(State.UNEXPECT)
    def route_from_state_unexpect(self):
        raise PDAError(line, 'Unexpected token %s' % repr(text))


class VM:
    def __init__(self):
        self.current_node = Cons(Symbol('.p'), None)
        self.root = self.current_node
        self.stack = deque()

    def execute(self, opcode, *params):
        idx = int(opcode)
        VM.vector[idx](self, *params)

    def _append(self, car):
        if self.current_node.car is None:
            self.current_node.car = car
        else:
            new_node = Cons(car, None)
            self.current_node.cdr = new_node
            self.current_node = new_node

    def open_list(self, line):
        inner_node = Cons(None, None, line=line)
        outer_node = Cons(inner_node, None)
        self.current_node.cdr = outer_node
        self.stack.append(outer_node)
        self.current_node = inner_node

    def close_list(self):
        self.current_node = self.stack.pop()

    def add_symbol(self, symbol):
        self._append(Symbol(symbol))

    def add_string(self, string):
        self._append(string)

    def add_lines(self, n):
        self.add_string('\n' * n)

    vector = (open_list,
              close_list,
              add_symbol,
              add_string,
              add_lines)
