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

}

}

function selectTextareaFromContainer(container) {
    container.querySelector('textarea').focus();
}




        } else {
        }




    // register listeners
    let ids = ['btn-add', 'btn-up', 'btn-down', 'btn-delete'];
    for (let i = 0; i < ids.length; i++) {
    }
}

window.addEventListener('DOMContentLoaded', editorMain);
