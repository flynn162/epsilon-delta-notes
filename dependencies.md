Epsilon-Delta Notes depends on the following packages

### Python
- python3.5+ (with sqlite support)
- flask
- pyparsing
- pytest

### Font Awesome 4.7
- Create a symlink `static/font-awesome-4-dist` that points to your Font Awesome installation
- Important folders in the top level of your linked directory: `css/`, `fonts/`, `less/`, `scss/`
- On Ubuntu, you can install the `fonts-font-awesome` package and make a symlink to `/usr/share/fonts-font-awesome`

### KaTeX
- Create a symlink `static/katex-dist` that points to your Katex installation
- Important files in the top level of your linked directory: `katex.min.css`, `katex.min.js`
- On Ubuntu, you can install the `node-katex` package and make a symlink to `/usr/lib/nodejs/katex/dist/`

### CodeMirror 5
- Create a symlink `static/codemirror-dist` that points to your CodeMirror installation
- Important folders in the top level of your linked directory: `lib/`, `addon/`
- On Ubuntu, you can install the `libjs-codemirror` package and make a symlink to `/usr/share/javascript/codemirror`

For your convenience, here is a bash snippet that does exactly the same thing.

```sh
MYROOT=""
ln -s "$MYROOT"/usr/share/fonts-font-awesome    static/font-awesome-4-dist
ln -s "$MYROOT"/usr/lib/nodejs/katex/dist       static/katex-dist
ln -s "$MYROOT"/usr/share/javascript/codemirror static/codemirror-dist
```

There is a metapackage control file in `metapackage/` that describes all necessary dependencies. To build and install the metapackage, use:

```sh
equivs-build control
sudo dpkg -i *.deb
sudo apt install --fix-missing
```
