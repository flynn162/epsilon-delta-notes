from flask import request, render_template, escape, Response
from parser import compile_notes, Parser
from sidebar import TreeNode, compile_tree
import re
from pathlib import Path
from sqlops import Db, auto_rollback

def get_tree():
    return TreeNode('Notes',
                    'root',
                    [TreeNode('Proof', 'p', None),
                     TreeNode('Calculus', 'calc',
                              [TreeNode("Green's Theorem", 'green', None, selected=True)])])

tree_cols = """
toc.id as id, toc.parent_id as parent_id, toc.next_id as next_id,
toc.slur as slur, toc.title as title
"""

adjacent_cte_template = """
{name} (n, id, parent_id, next_id, slur, title) AS (
SELECT 1 as n, {cols} FROM tree
WHERE id = :id

UNION ALL

SELECT {step}, {cols} FROM tree
INNER JOIN {name} ON {comp}
WHERE {stop}
)"""

adjacent_cte_forward = adjacent_cte_template.format(**{
    'name': 'cte_forward',
    'cols': tree_cols,
    'comp': 'cte_forward.next_id = tree.id',
    'step': 'n + 1',
    'stop': 'n <= 5'
})

adjacent_cte_backward = adjacent_cte_template.format(**{
    'name': 'cte_backward',
    'cols': tree_cols,
    'comp': 'tree.next_id = cte_backward.id',
    'step': 'n - 1',
    'stop': 'n >= -4'
})

tree_query_cte = """
WITH {}, {}
SELECT * from cte_backward
UNION
SELECT * from cte_forward
""".format(adjacent_cte_forward, adjacent_cte_backward)

class DbTree(Db):
    @auto_rollback
    def get_tree(self, c, slur):
        # needs to be in one transaction
        page_id = Db.check_page_id(c, slur)
        c.execute(tree_query_cte, {'id': page_id})
        rows = c.fetchmany()
        # convert rows into dict


def list_files():
    yield '<ul>'
    links = sorted(map(lambda p: p.stem, Path('.').glob('*.scrbl')))
    for ln in links:
        yield '<li>'
        esc = escape(ln)
        yield '<a href="?:=%s">%s</a>' % (esc, esc)
        yield '</li>'
    yield '</ul>'

def handle(app):
    filename = request.args.get(':')
    if not filename or not re.match('^[a-zA-Z0-9_\\-]{1,100}$', filename):
        return Response(list_files())

    tree = get_tree()
    tree_html = compile_tree(tree)

    content = open('%s.scrbl' % filename).read()
    cons = Parser().parse_string(content)
    notes_html = compile_notes(cons)

    return render_template(
        'view.html',
        title='Test Title',
        directory_of_page=[('Notes', '#'), ('Calculus', '#calc')],
        prev_article=('a', 'b'),
        next_article=('some thing2', 'some thing2'),
        sidebar_html=tree_html,
        notes_html=notes_html
    )
