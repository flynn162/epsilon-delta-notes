You can generate a metapackage (.deb) that describes the dependencies of
Epsilon-Delta Notes. The following recipe is from
[this answer](https://askubuntu.com/a/33417).

```sh
# build the metapackage
equivs-build control
# install the metapackage
sudo dpkg -i *.deb
sudo apt install --fix-missing
```
