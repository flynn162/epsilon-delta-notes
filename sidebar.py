from flask import escape
from collections import deque
from sqlops import slur_to_link

class TreeNode:
    def __init__(self, title, slur, children=None, selected=False):
        self.title = title
        self.slur = slur
        self.children = children
        self.selected = selected

    def __repr__(self):
        return '<TreeNode selected=%r title=%r slur=%r children=%r>' % (
            self.selected,
            self.title,
            self.slur,
            self.children
        )

    def append(self, child):
        if self.children is None:
            self.children = deque()
        self.children.append(child)

    def prepend(self, child):
        if self.children is None:
            self.children = deque()
        self.children.appendleft(child)

    def link(self):
        return slur_to_link(self.slur)

def compile_link(node, acc):
    acc.append('<div>')
    if node.slur == '...':
        acc.append('<span>...</span>')
    else:
        acc.append('<a href="%s">%s</a>' %
                   (escape(node.link()), escape(node.title)))
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
    for node in current.children:
        _compile_tree_private(node, acc)
    acc.append('</ul>')
    return acc
