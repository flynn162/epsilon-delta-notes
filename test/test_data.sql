BEGIN TRANSACTION;
INSERT INTO toc (id, parent_id, next_id, first_child_id, slur, title, first_content_id)
VALUES (0, NULL, NULL, 1, 'home', 'Home', 1);

INSERT INTO toc (id, parent_id, next_id, first_child_id, slur, title, first_content_id)
VALUES (1, 0, NULL, 2, 'math', 'Math', NULL);

INSERT INTO toc (id, parent_id, next_id, first_child_id, slur, title, first_content_id)
VALUES (2, 1, NULL, NULL, 'units-of-zi', 'Units of Z[i]', 100);

INSERT INTO content (id, parent_id, next_id, content)
VALUES (1, 0, 2, 'First paragraph');

INSERT INTO content (id, parent_id, next_id, content)
VALUES (2, 0, 3, 'Second paragraph');

INSERT INTO content (id, parent_id, next_id, content)
VALUES (3, 0, 4, 'Third paragraph');

INSERT INTO content (id, parent_id, next_id, content)
VALUES (4, 0, NULL, 'Fourth paragraph');

COMMIT;
