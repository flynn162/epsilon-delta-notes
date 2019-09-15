from diff import *

def test_lcs():
    # ABC
    assert lcs('ABCD', 'ABC') == 3
    # BD
    assert lcs('ABCD', 'BD') == 2
    assert lcs('ABCDEF', 'D') == 1
    assert lcs('', 'ABCD') == 0
    assert lcs('AaAaAa', '') == 0
