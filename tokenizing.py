from collections import deque, namedtuple
from enum import IntEnum
import io

InputTuple = namedtuple('InputTuple', ('text', 'param'))

def token_iter(tokens):
    for t in tokens:
        # token can be a string or an InputTuple
        if isinstance(t, str):
            yield (t, None)
        else:
            yield (t.text, t.param)

class ParserError(RuntimeError):
    pass

def tokenize(string):
    tokenizer = Tokenizer()
    for ch in string:
        yield from tokenizer.process_input(ch)
    yield from tokenizer.process_input('')

class State(IntEnum):
    TEXT = 1,
    VERT = 2,
    OPEN_BRACE = 3,
    LINE_BREAK = 4

class Registry:
    routing_handlers = {}

    @classmethod
    def routes_from(cls, state):
        def decorator(function):
            cls.routing_handlers[state] = function
            return function
        return decorator

class Tokenizer:
    def __init__(self):
        self.queue = deque()
        self.line_break_count = 0
        self.buf = io.StringIO()
        # initial state
        self.state = State.TEXT

    def output(self, some_string):
        # flush buffer first
        buffer_content = self.flush_buffer()
        if buffer_content:
            self.queue.append(buffer_content)
        # put whatever string in
        if some_string:
            self.queue.append(some_string)

    def process_input(self, text):
        routing_handler = Registry.routing_handlers[self.state]

        new_state = routing_handler(self, text)
        if new_state != self.state:
            self.state = new_state

        # flush the output queue
        while len(self.queue) > 0:
            yield self.queue.popleft()

    def is_in_accepting_state(self):
        return self.state == State.TEXT

    @Registry.routes_from(State.TEXT)
    def on_text(self, text):
        if text in '@{':
            self.output(text)
            return State.TEXT
        elif text == '\r':  # ignore \r
            return State.TEXT
        elif text == '}':
            return State.VERT
        elif text == '|':
            return State.OPEN_BRACE
        elif text == '\n':
            self.line_break_count = 1
            return State.LINE_BREAK
        else:
            self.buf.write(text)
            return State.TEXT

    @Registry.routes_from(State.VERT)
    def on_vert(self, text):
        if text == '|':
            self.output('}|')
            return State.TEXT
        else:  # including the EOF string ''
            self.output('}')
            return self.on_text(text)

    @Registry.routes_from(State.OPEN_BRACE)
    def on_open_brace(self, text):
        if text == '{':
            self.output('|{')
            return State.TEXT
        else:  # including the EOF string ''
            self.output('|')
            return self.on_text(text)

    @Registry.routes_from(State.LINE_BREAK)
    def on_line_break(self, text):
        if text == '\n':
            self.line_break_count += 1
            return State.LINE_BREAK
        elif text.isspace():  # ignore whitespace
            return State.LINE_BREAK
        else:
            # leaving
            self.output(InputTuple('\n', self.line_break_count))
            self.line_break_count = 0
            return self.on_text(text)

    def flush_buffer(self):
        self.buf.seek(0)
        result = self.buf.read()
        self.buf.seek(0)
        self.buf.truncate(0)
        return result
