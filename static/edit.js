let state = {};

function Node(data, prev, next) {
    this.data = data;
    this.prev = prev;
    this.next = next;
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

function initializeState() {
    state.linkedList = new LinkedList();
    state.selected = null;
    state.toolbar = {};
    state.textboxes = document.querySelector('#textboxes');
    for (let key of ['btn-add', 'btn-up', 'btn-down', 'btn-delete']) {
        state.toolbar[key] = document.getElementById(key);
    }
}

function enableButtons() {
    for (let key of ['btn-up', 'btn-down', 'btn-delete']) {
        state.toolbar[key].removeAttribute('disabled');
    }
}

function disableButtons() {
    for (let key of ['btn-up', 'btn-down', 'btn-delete']) {
        state.toolbar[key].setAttribute('disabled', 'yeah');
    }
}

function setSelectedStyle(el, tf) {
    if (tf) {
        el.classList.add('selected');
    } else {
        el.classList.remove('selected');
    }
}

function addTextareaListeners(el, node) {
    el.addEventListener('focus', function () {
        if (state.selected != null) {
            setSelectedStyle(state.selected.data, false);
        }
        state.selected = node;
        setSelectedStyle(node.data, true);
        enableButtons();
    });
    el.addEventListener('input', function () {
        el.style['height'] = el.scrollHeight + 'px';
    });
}

function loadTextIntoLinkedList() {
    // change the textarea's listeners such that
    // they change the state when they are focused
    for (var el of document.querySelectorAll('textarea')) {
        let node = state.linkedList.append(el.parentElement);
        addTextareaListeners(el, node);
    }
}

function selectTextareaFromContainer(container) {
    container.querySelector('textarea').focus();
}

function onAdd(node) {
    // build our textbox element
    let idField = createElementWithDict('input', {
        type: 'hidden',
        name: 'par_id',
        value: 'new'
    });
    let textarea = createElementWithDict('textarea', {
        name: 'text'
    });
    let container = createElementWithDict('div', {
        'class': 'textbox-container'
    });
    container.appendChild(textarea);
    container.appendChild(idField);
    // add element into linked list
    let newNode = state.linkedList.append(container);
    if (node != null) {
        // shuffle its position
        state.linkedList.remove(newNode);
        state.linkedList.insertAfter(node, newNode);
    }

    // add element to dom
    if (node != null) {
        node.data.insertAdjacentElement('afterend', container);
    } else {
        state.textboxes.appendChild(container);
    }

    addTextareaListeners(textarea, newNode);
    textarea.focus();
}

function onMoveUp(node) {
    let targetElement = state.linkedList.moveUp(node);
    if (targetElement != -1) {
        state.textboxes.removeChild(node.data);
        if (targetElement != null) {
            targetElement.insertAdjacentElement('afterend', node.data);
        } else {
            state.textboxes.insertAdjacentElement('afterbegin', node.data);
        }
    }
}

function onMoveDown(node) {
    let targetElement = state.linkedList.moveDown(node);
    if (targetElement != -1) {
        state.textboxes.removeChild(node.data);
        targetElement.insertAdjacentElement('afterend', node.data);
    }
}

function onDelete(node) {
    if (node == null) {
        return;
    }
    if (node.next != null) {
        selectTextareaFromContainer(node.next.data);
    } else if (node.prev != null) {
        selectTextareaFromContainer(node.prev.data);
    } else {
        state.selected = null;
        disableButtons();
    }
    state.linkedList.remove(node);
    state.textboxes.removeChild(node.data);
}


function editorMain() {
    initializeState();
    loadTextIntoLinkedList();
    // register listeners
    disableButtons();
    let ids = ['btn-add', 'btn-up', 'btn-down', 'btn-delete'];
    let fns = [onAdd, onMoveUp, onMoveDown, onDelete];
    for (let i = 0; i < ids.length; i++) {
        state.toolbar[ids[i]].addEventListener('click',  () => {
            fns[i](state.selected);
        });
    }
}

window.addEventListener('DOMContentLoaded', editorMain);
