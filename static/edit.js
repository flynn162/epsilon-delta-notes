function Node(data, prev, next) {
    this.data = data;
    this.prev = prev;
    this.next = next;
}

function Data(cmInstance, container) {
    this.cm = cmInstance;
    this.container = container;
}

function LinkedListIterator(linkedList) {
    this.current = linkedList.front;
    this.next = function () {
        if (this.next == null) {
            return {done: true};
        } else {
            let result = this.current.data;
            this.current = this.current.next;
            return {done: false, value: result};
        }
    };
}

function LinkedList() {
    this.front = null;
    this.back = null;

    this.append = function (data) {
        let node = new Node(data, null, null);
        if (this.front == null) {
            this.front = node;
            this.back = node;
        } else {
            // I should point to:
            node.next = null;
            node.prev = this.back;
            // Who should point to me?
            this.back.next = node;
            this.back = node;
        }
        return node;
    };

    this.insertAfter = function (node, nodeWithData) {
        if (node == null) {
            // insert at front
            // I should point to:
            nodeWithData.prev = null;
            nodeWithData.next = this.front;
            // Who should point to me?
            if (this.front == null) {
                this.back = nodeWithData;
            } else {
                this.front.prev = nodeWithData;
            }
            this.front = nodeWithData;
        } else {
            // I should point to:
            nodeWithData.prev = node;
            nodeWithData.next = node.next;
            // Who should point to me?
            if (node.next == null) {
                this.back = nodeWithData;
            } else {
                node.next.prev = nodeWithData;
            }
            node.next = nodeWithData;
        }
    };

    this.remove = function (node) {
        // Who is pointing to me?
        if (node.prev == null) {
            this.front = node.next;
        } else {
            node.prev.next = node.next;
        }

        if (node.next == null) {
            this.back = node.prev;
        } else {
            node.next.prev = node.prev;
        }
        // I should point to:
        node.prev = null;
        node.next = null;
    };

    this.moveUp = function (node) {
        // goal: remove myself and insert me after my prev's prev
        if (node.prev == null) {
            return -1;
        }
        let target = node.prev.prev;
        this.remove(node);
        this.insertAfter(target, node);

        if (target == null) {
            return null;
        } else {
            return target.data;
        }
    };

    this.moveDown = function (node) {
        // goal: remove myself and insert me after my next
        if (node.next == null) {
            return -1;
        }
        let target = node.next;
        this.remove(node);
        this.insertAfter(target, node);

        // here, target is not null
        return target.data;
    };

    this[Symbol.iterator] = function () {
        return new LinkedListIterator(this);
    };
}

function createElementWithDict(name, dict) {
    let element = document.createElement(name);
    for (let key in dict) {
        if (dict.hasOwnProperty(key)) {
            element.setAttribute(key, dict[key]);
        }
    }
    return element;
}

function setSelectedStyle(el, tf) {
    if (tf) {
        el.classList.add('selected');
    } else {
        el.classList.remove('selected');
    }
}

function changeA11yAttribs(divTextarea) {
    divTextarea.removeAttribute('aria-hidden');
    divTextarea.setAttribute('role', 'textbox');
    divTextarea.setAttribute('aria-multiline', 'true');
}

function focusOnTextareaInContainer(container) {
    container.querySelector('div.textarea').focus();
}

function loadCm(el, value) {
    let cm = CodeMirror(el, {
        value: value,
        mode: 'scribblemode',
        lineWrapping: true,
        lineNumbers: true,
        extraKeys: {
            'Tab': 'indentMore',
            'Shift-Tab': 'indentLess',
            'Ctrl-K': 'killLine'
        }
    });
    return cm;
}

function Editor() {
    this.enableButtons = function () {
        for (let key of ['btn-up', 'btn-down', 'btn-delete']) {
            this.toolbar[key].removeAttribute('disabled');
        }
    };

    this.disableButtons = function () {
        for (let key of ['btn-up', 'btn-down', 'btn-delete']) {
            this.toolbar[key].setAttribute('disabled', 'yeah');
        }
    };

    this.addCmListeners = function (cm, node) {
        // change the textarea's listeners such that
        // they change the state when they are focused
        let onFocus = function () {
            if (this.selected != null) {
                setSelectedStyle(this.selected.data.container, false);
            }
            this.selected = node;
            setSelectedStyle(this.selected.data.container, true);
            this.enableButtons();
        };
        // lol js: in my handler above,
        // `this` refers to the class instance, not the element
        // rebinding `this`
        cm.on('focus', onFocus.bind(this));
    };

    this.onAdd = function (node) {
        // build our textbox element
        let anchor = createElementWithDict('div', {
            'class': 'scroll-anchor'
        });
        let inputHidden = createElementWithDict('input', {
            'type': 'hidden',
            'name': 'text'
        });
        let divTextarea = createElementWithDict('div', {
            'class': 'textbox'
        });
        let container = createElementWithDict('div', {
            'class': 'textbox-container'
        });
        changeA11yAttribs(divTextarea);
        let cm = loadCm(divTextarea, '');
        container.appendChild(anchor);
        container.appendChild(inputHidden);
        container.appendChild(divTextarea);

        // add element into linked list
        let newNode = this.linkedList.append(new Data(cm, container));
        if (node != null) {
            // shuffle its position
            this.linkedList.remove(newNode);
            this.linkedList.insertAfter(node, newNode);
        }

        // add element to dom
        if (node != null) {
            node.data.container.insertAdjacentElement('afterend', container);
        } else {
            this.textboxes.appendChild(container);
        }

        this.addCmListeners(cm, newNode);
        cm.refresh();
        cm.focus();
    };

    this.onMoveUp = function (node) {
        let targetNode = this.linkedList.moveUp(node);
        if (targetNode != -1) {
            if (targetNode != null) {
                this.textboxes.removeChild(node.data.container);
                let targetElement = targetNode.container;
                targetElement.insertAdjacentElement('afterend',
                                                    node.data.container);
            } else {
                this.textboxes.insertAdjacentElement('afterbegin',
                                                     node.data.container);
            }
            node.data.container
                .querySelector('.scroll-anchor').scrollIntoView();
        }
    };

    this.onMoveDown = function (node) {
        let targetNode = this.linkedList.moveDown(node);
        if (targetNode != -1) {
            let targetElement = targetNode.container;
            this.textboxes.removeChild(node.data.container);
            targetElement.insertAdjacentElement('afterend',
                                                node.data.container);
            node.data.container
                .querySelector('.scroll-anchor').scrollIntoView();
        }
    };

    this.onDelete = function (node) {
        if (node == null) {
            return;
        }
        if (node.next != null) {
            focusOnTextareaInContainer(node.next.data.container);
        } else if (node.prev != null) {
            focusOnTextareaInContainer(node.prev.data.container);
        } else {
            this.selected = null;
            this.disableButtons();
        }
        this.linkedList.remove(node);
        this.textboxes.removeChild(node.data.container);
    };

    this.onSubmit = function () {
        for (data of this.linkedList) {
            // migrate cm text into hidden fields
            let inputHidden = data.container.querySelector('input');
            inputHidden.value = data.cm.getValue();
        }
        return true;
    };

    this.initializeState = function () {
        this.linkedList = new LinkedList();
        this.selected = null;
        this.toolbar = {};
        this.textboxes = document.querySelector('#textboxes');
        for (let key of ['btn-add', 'btn-up', 'btn-down', 'btn-delete']) {
            this.toolbar[key] = document.getElementById(key);
        }
    };

    this.loadTextIntoLinkedList = function () {
        for (var el of document.querySelectorAll('div.textarea')) {
            let container = el.parentElement;
            // migrate text
            let formTextarea = container.querySelector('textarea');
            let inputHidden = createElementWithDict('input', {
                'type': 'hidden',
                'name': 'text',
                'value': ''
            });
            let cm = loadCm(el, formTextarea.value);
            let node = this.linkedList.append(new Data(cm, container));
            formTextarea.remove();
            container.appendChild(inputHidden);
            el.classList.remove('visually-hidden');
            changeA11yAttribs(el);
            this.addCmListeners(cm, node);
            cm.refresh();
        }
    };

    this.initializeState();
    // prepare text
    this.loadTextIntoLinkedList();
    // register listeners
    this.disableButtons();
    let ids = ['btn-add', 'btn-up', 'btn-down', 'btn-delete'];
    let fns = [this.onAdd, this.onMoveUp, this.onMoveDown, this.onDelete];
    for (let i = 0; i < ids.length; i++) {
        this.toolbar[ids[i]].addEventListener(
            'click',
            // lol js: handler was called with a spurious `this` argument
            () => fns[i].bind(this)(this.selected)
        );
    }
    document.querySelector('#form').addEventListener(
        'submit',
        // rebind `this`
        () => this.onSubmit()
    );
}

function editorMain() {
    window.editor = new Editor();
}

window.addEventListener('DOMContentLoaded', editorMain);
