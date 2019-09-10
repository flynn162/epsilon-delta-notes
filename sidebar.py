from flask import escape

class TreeNode:
    def __init__(self, title, link, children, selected=False):
        self.title = title
        self.link = link
        self.children = children
        self.selected = selected

def compile_link(node, acc):
    acc.append('<div>')
    acc.append('<a href="%s">%s</a>' % (escape(node.link), escape(node.title)))
    acc.append('</div>')

def _compile_tree_private(current, acc):
    if current is None:
        return

    class_names = 'selected' if current.selected else ''

    if current.children is None:
        # no further expansion
        acc.append('<li class="%s">' % class_names)
        compile_link(current, acc)
        acc.append('</li>')
    else:
        # mark current as expanded
        acc.append('<li class="%s expanded">' % class_names)
        compile_link(current, acc)
        # make a new list
        acc.append('<ul>')
        for child in current.children:
            _compile_tree_private(child, acc)
        acc.append('</ul>')
        # don't forget to close the <li> tag
        acc.append('</li>')

def compile_tree(current):
    acc = []
    acc.append('<ul>')
    _compile_tree_private(current, acc)
    acc.append('</ul>')
    return acc
