import re
from flask import escape
from functools import wraps
from pyparsing import Word, Literal, Optional, CharsNotIn, OneOrMore, Combine
from pyparsing import alphas, nums, quotedString
from pyparsing import nestedExpr, locatedExpr, ParserElement, ParseResults
from sqlops import is_valid_slug

# make \n significant
ParserElement.setDefaultWhitespaceChars(' \t')

ALLOWED_CHARS = frozenset(alphas + nums)
MAX_CMD_LENGTH = 100

list_opener = locatedExpr(Word('{') | Word('|{'))
list_closer = locatedExpr(Word('}|') | Word('}'))

CMD = locatedExpr(Word(alphas + nums + '-_', max=100))
list_header = Literal('@') + Optional(CMD) + list_opener

text_body = CharsNotIn('@\n|{}')
line_break = Combine(OneOrMore(Literal('\n')))
list_stuff = list_header | list_opener | list_closer
scribble = OneOrMore(text_body | line_break | list_stuff)

lstrip_regex = re.compile('^[ \t\r]+')

class Cons(object):
    __slots__ = ('data', 'params')

    def __init__(self, data, params):
        self.data = data
        self.params = params

    def __repr__(self):
        return 'Cons(%r, %r)' % (self.data, self.params)

class ParserError(RuntimeError):
    def __init__(self, parser):
        super().__init__()
        self.state = parser

    def __str__(self):
        return 'At line %d' % (self.state.line_counter,)

def convert_error(method):
    @wraps(method)
    def result(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except (ValueError, TypeError, StopIteration) as e:
            raise ParserError(self) from e
    return result

def rescan_for_line_breaks(params):
    """Delete whitespaces between line breaks and detect line breaks,
    handling situtations such as '^[ \t]+\n' """
    # tokenizer confusion example:
    # tokenized: ['ring.', '\n', '     ', '\n', '    For example,']
    # should be treated as: ['ring.', '\n\n', '    For example,']
    linewrap_acc = 0
    for p in params:
        if isinstance(p, str):
            if lstrip_regex.fullmatch(p):  # all characters are whitespaces
                continue
            elif p.startswith('\n'):  # \n and \n+ have their own strings
                linewrap_acc += len(p)
            else:
                if linewrap_acc > 0:
                    yield ('\n' * linewrap_acc)
                yield p
                linewrap_acc = 0
        else:
            yield p
    if linewrap_acc > 0:
        yield ('\n' * linewrap_acc)

class ParserAcc(object):
    __slots__ = ('_slugs', 'slug_title_map')

    def __init__(self):
        self._slugs = set()
        self.slug_title_map = {}

    def add_slug(self, slug):
        self._slugs.add(slug)

    def put_title(self, slug, title):
        if title is not None:
            self.slug_title_map[slug] = title

    def get(self, slug, default=None):
        return self.slug_title_map.get(slug, default)

    def unprocessed_slugs(self):
        for slug in self._slugs:
            if slug not in self.slug_title_map:
                yield slug

class Parser(object):
    __slots__ = ('unesc_mode',
                 'bracket_counter',
                 'line_counter',
                 'last_open_bracket',
                 'acc')

    def __init__(self):
        self.unesc_mode = False
        self.bracket_counter = 0
        self.line_counter = 1
        self.last_open_bracket = None
        self.acc = ParserAcc()

    def tokenize(self, string):
        tokens = scribble.parseString(string.replace('\r', ''))
        tokens = rescan_for_line_breaks(tokens)
        return iter(tokens)

    @convert_error
    def parse_string(self, string):
        tokens = self.tokenize(string)
        return self.parse_into_list(tokens)

    @convert_error
    def parse_into_list(self, tokens):
        """Converts tokens into a linked list (AST)
        tokens: an iterator that yields tokens
        token: String | LocationObject
        return value: Cons with strings as car, list of (strings/Cons) as cdr
        """
        result = Cons('p', [])
        while True:
            try:
                token = next(tokens)
            except StopIteration:
                break
            if isinstance(token, str):
                if token == '@':
                    self.handle_list_start(tokens, result)
                elif token.startswith('\n'):
                    self.handle_line_break(token, result)
                else:
                    # just strings
                    result.params.append(token)
            elif isinstance(token, ParseResults):
                raise TypeError('Unexpected stuff')
            else:
                raise TypeError()
        return result

    def handle_line_break(self, token, result):
        self.line_counter += len(token)
        if len(token) == 1:
            result.params.append(token)
        elif len(token) >= 2:
            result.params.append('\n\n')

    @convert_error
    def handle_list_start(self, tokens, result):
        token = next(tokens)
        # get operator name
        operator_name = None
        mode = None
        if not isinstance(token, ParseResults):
            raise ValueError('Expecting an operator, or list')
        if token.value in ('{', '|{'):
            # list start "open bracket"
            operator_name = 'list'
            mode = token.value
        else:
            if token.value not in HANDLERS:
                raise ValueError('Unknown operator %s' % token)
            operator_name = token.value
            # consume an open bracket
            token = next(tokens)
            if token.value not in ('{', '|{'):
                raise ValueError('Expecting { or |{')
            mode = token.value
        self.bracket_counter += 1
        # get parameters
        cons = Cons(operator_name, [])
        if mode == '|{':
            self.handle_list_unesc(tokens, cons)
        else:
            self.handle_list_regular(tokens, cons)
        # check if we need to fetch something from db later
        self.put_links_in_accumulator(cons)
        result.params.append(cons)

    @convert_error
    def handle_list_unesc(self, tokens, result):
        # read everything as string until the first '}|'
        token = next(tokens)
        while not(isinstance(token, ParseResults) and token.value == '}|'):
            if isinstance(token, ParseResults):
                result.params.append(token.value)
            else:
                if token.startswith('\n'):
                    self.handle_line_break(token, result)
                else:
                    result.params.append(token)
            token = next(tokens)
        self.bracket_counter -= 1

    @convert_error
    def handle_list_regular(self, tokens, result):
        # read the contents following (strings or signs of cons start)
        token = next(tokens)
        while not(isinstance(token, ParseResults) and token.value == '}'):
            if isinstance(token, str):
                if token.startswith('\n'):
                    # if \n, increase line counter
                    self.handle_line_break(token, result)
                elif token == '@':
                    # if Cons '@', recursively parse the rest of the stuff
                    self.handle_list_start(tokens, result)
                else:
                    # otherwise, they are regular strings
                    result.params.append(token)
            token = next(tokens)
        # return control to the caller
        self.bracket_counter -= 1

    @convert_error
    def put_links_in_accumulator(self, current_node):
        if current_node.data != 'page':
            return
        # probe the first word and check if it is valid
        done = False
        def params_lstrip(s):
            nonlocal done
            if done:
                return True
            if not(isinstance(s, str)) or len(s.strip()) > 0:
                done = True
                return s
        iterator = filter(params_lstrip, current_node.parms)
        try:
            first_word = next()
        except StopIteration as e:
            raise ParserError('page link: no valid strings found') from e
        try:
            first_word = first_word.strip()
        except AttributeError as e:
            raise ParserError('page link: first word must be a string') from e
        # check if we need title
        needs_title = True
        if first_word.endswith(':'):
            needs_title = False
            first_word = first_word[:-1]
        if not is_valid_slug(first_word):
            raise ParserError('Invalid slug: %r' % (first_word,))
        if need_title:
            self.acc.add_slug(first_word)
        else:
            # put in the rest of the iterator as title
            self.acc.put_title(first_word, list(iterator))

# 1st pass: tokenize
# 2nd pass: convert tokens into Cons (AST)
# 3rd pass: convert AST into HTML

# html transpiler

class Accumulator:
    def __init__(self, parser_acc):
        self.output = []
        self.footnotes = []
        self.parser_acc = parser_acc

    def append(self, s):
        self.output.append(s)

    def queue_footnote(self, footnote):
        self.footnotes.append(footnote)

    def get_title(self, slug, default=None):
        return self.parser_acc.get(slug, default)

HANDLERS = {}

def handles(name):
    def decorator(method):
        HANDLERS[name] = method
        return method
    return decorator

def compile_notes(ast, parser_acc):
    acc = Accumulator(parser_acc)
    acc.append('\n<!-- compilation starts -->\n')
    continuation = iter(ast.params)
    while continuation:
        acc.append('<div class="has-left-margin">')
        continuation = _compile_notes(continuation, acc)
        acc.append('</div>')
        # _compile_notes pauses, so we process footnotes
        if acc.footnotes:
            acc.append('<div class="has-right-margin">')
            for fn in acc.footnotes:
                compile_footnote(fn, acc)
            acc.append('</div>')
            acc.footnotes = []
        # by looping back, we continue processing, with the new `continuation`

    acc.append('\n<!-- compilation ends -->\n')
    return acc.output

def _compile_notes(params, acc, use_p=True):
    if use_p:
        acc.append('\n<div class="paragraph">')
    for item in params:
        if isinstance(item, Cons):
            compile_function = HANDLERS[item.data]
            compile_function(item.params, acc)
        elif item == '\n\n':
            if not use_p:
                raise ValueError('You said not to have paragraphs')
            if acc.footnotes:
                # bail out and let the caller compile footnotes
                acc.append('</div>')
                return params
            else:
                # just start a new paragraph
                acc.append('</div>\n<div class="paragraph">')
        else:
            acc.append('<span>')
            acc.append(escape(item))
            acc.append('</span>')
    if use_p:
        acc.append('</div>')
    return None

@handles('twocol')
def compile_two_cols(params, acc):
    params = list(filter(lambda a: isinstance(a, Cons), params))
    if len(params) != 2:
        raise ValueError('Left and right, not %d' % len(params))
    acc.append('<div class="col-container">')
    _compile_single_col('col-left', params[0], acc)
    _compile_single_col('col-right', params[1], acc)
    acc.append('</div>')

@handles('note')
@handles('margin-note')
def queue_footnote(params, acc):
    acc.queue_footnote(params)

def _compile_single_col(name, the_list, acc):
    if not isinstance(the_list, Cons) or the_list.data != 'list':
        raise ValueError('Syntax error when processing col %s' % name)

    acc.append('\n<div class="%s">' % name)
    _compile_notes(the_list.params, acc)
    acc.append('</div>\n')

def compile_footnote(params, acc):
    acc.append('''
    <div class="margin-note">
    <div class="margin-note-content">
    <p class="visually-hidden">[[ Margin note: ]]</p>
    ''')
    _compile_notes(params, acc)
    acc.append('</div></div>')

@handles('Math')
def compile_display_math(params, acc):
    _compile_math(params, acc, display=True)

@handles('math')
def compile_inline_math(params, acc):
    _compile_math(params, acc, display=False)

def _compile_math(params, acc, display):
    math = ''.join(params)
    escaped_string = escape(math)
    cls = 'tex-display' if display else 'tex-inline'
    dollar_sign = '$$' if display else '$'
    acc.append('<div class="%s math" data-tex="%s">' % (cls, escaped_string))
    acc.append('<span class="temp">%s' % dollar_sign)
    acc.append(escaped_string)
    acc.append('%s</span>' % dollar_sign)
    acc.append('</div>')

@handles('list')
@handles('p')
def no_operation(params, acc):
    pass

@handles('italic')
def compile_italic(params, acc):
    _compile_single_tag('i', params, acc)

@handles('bold')
def compile_bold(params, acc):
    _compile_single_tag('b', params, acc)

def _compile_single_tag(tag, params, acc):
    acc.append('<%s>' % tag)
    _compile_notes(params, acc, use_p=False)
    acc.append('</%s>' % tag)

content = None
result = None

if __name__ == '__main__':
    content = open('sample.scrbl').read()
    result = scribble.parseString(content)
