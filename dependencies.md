Epsilon-Delta Notes depends on the following packages

- python3.6 (with sqlite support)
- flask
- pyparsing
- katex
- font-awesome 4.7
- pytest

Create a symlink `static/font-awesome-4-dist` that points to your Font Awesome installation (a directory in which you have the `css/`, `fonts/`, `less/`, `scss/` folders). On Ubuntu, you can install the `fonts-font-awesome` package and point the symlink to `/usr/share/fonts-font-awesome`.

Create a symlink `static/katex-dist` that points to your Katex installation (a directory where you have the `katex.min.css`, `katex.min.js` files, and the `contrib/`, `font/` folders). On Ubuntu, you can install the `node-katex` package and point the symlink to `/usr/lib/nodejs/katex/dist/`.
