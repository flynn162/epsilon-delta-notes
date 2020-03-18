import pytest
from tokenizing import tokenize
from pda import Bytecode, VM, PDA

test_data = [
    ["Hello @bold{World}@italic{!!} This is a note. @bold{@italic{Bye!}}",

     "(.p 'Hello ' (bold 'World') (italic '!!') ' This is a note. '" +
     " (bold (italic 'Bye!')))"],

    ["Curly braces like these @bold{are {totally {acceptable}}} " +
     "as long as {they {are} balanced}!",

     "(.p 'Curly braces like these ' (bold 'are {totally {acceptable}}') " +
     "' as long as {they {are} balanced}!')"],
]

@pytest.fixture(params=test_data)
def datum(request):
    yield request.param

def test_convert_scribble(datum):
    pushdown_automata = PDA()
    print(list(tokenize(datum[0])))
    ast = pushdown_automata.run(tokenize(datum[0]))
    print('Got:\n', repr(ast))
    print('Expecting:\n', datum[1])
    assert repr(ast) == datum[1]

def test_asm():
    asm = (
        # bold
        (Bytecode.OPEN_LIST, 2),
        (Bytecode.ADD_SYMBOL, 'bold'),
        (Bytecode.ADD_STRING, 'Henlo'),
        (Bytecode.ADD_STRING, 'World'),
        # italic
        (Bytecode.OPEN_LIST, 5),
        (Bytecode.ADD_SYMBOL, 'italic'),
        (Bytecode.ADD_STRING, '!!'),
        (Bytecode.CLOSE_LIST,),
        # end of italic
        (Bytecode.ADD_LINES, 3),
        (Bytecode.CLOSE_LIST,),
        # end of bold
        (Bytecode.ADD_STRING, 'Bye'),
    )

    vm = VM()
    for instruction in asm:
        vm.execute(*instruction)

    expect = "(.p (bold 'Henlo' 'World' (italic '!!') '\\n\\n\\n') 'Bye')"
    assert repr(vm.root) == expect
