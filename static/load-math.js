window.macros = {
    '\\N': '\\mathbb{N}',
    '\\Z': '\\mathbb{Z}',
    '\\Q': '\\mathbb{Q}',
    '\\R': '\\mathbb{R}',
    '\\C': '\\mathbb{C}',
    '\\F': '\\mathbb{F}'
}

function renderMathOn(element) {
    let math = element.getAttribute('data-tex');
    katex.render(math, element, {
        displayMode: element.classList.contains('tex-display'),
        throwOnError: false,
        macros: window.macros
    });
}

function main(event) {
    for (element of document.querySelectorAll('div.math')) {
        renderMathOn(element);
    }
}

window.addEventListener('DOMContentLoaded', main);
