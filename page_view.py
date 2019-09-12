from flask import request, render_template, escape, Response
from parser import compile_notes, Parser
from sidebar import TreeNode, compile_tree
from pathlib import Path
from sqlops import Db, is_valid_slur, slur_to_link

def get_tree():
    return TreeNode('Notes',
                    'root',
                    [TreeNode('Proof', 'p', None),
                     TreeNode('Calculus', 'calc',
                              [TreeNode("Green's Theorem", 'green', None, selected=True)])])
toc_cols = ('id', 'parent_id', 'next_id', 'first_child_id', 'first_content_id',
            'slur', 'title', 'mtime')
toc_cols_fullname = map(lambda s: 'toc.{0} as {0}'.format(s), toc_cols)

cte_template = """
{{name}} (n, {0}) AS (
SELECT 0 as n, {1} FROM toc WHERE id = :id
UNION ALL
SELECT n + 1, {1} FROM toc
INNER JOIN {{name}} ON {{comp}}
WHERE n < {{N}}
)""".format(', '.join(toc_cols),
            ', '.join(toc_cols_fullname))

cte_forward = cte_template.format(
    name='cte_forward',
    comp='cte_forward.next_id = toc.id',
    N=5
)

cte_backward = cte_template.format(
    name='cte_backward',
    comp='toc.next_id = cte_backward.id',
    N=5
)

cte_upward = cte_template.format(
    name='cte_upward',
    comp='cte_upward.parent_id = toc.id',
    N=10
)

cte_downward = cte_template.format(
    name='cte_downward',
    comp='toc.parent_id = cte_downward.id',
    N=1
)

tree_query_cte = """
WITH {1}, {2}, {3}, {4}
      SELECT {0} FROM cte_backward
UNION SELECT {0} FROM cte_forward
UNION SELECT {0} FROM cte_upward
UNION SELECT {0} FROM cte_downward
""".format(', '.join(toc_cols),
           cte_backward, cte_forward, cte_upward, cte_downward)

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
    slur = request.args.get(':')
    if not slur:
        return '<meta http-equiv="refresh" content="2; url=?:=home"> redirect'
    if not is_valid_slur(slur):
        return 'Invalid page ID'

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
