echo "Post install script"
echo "Installing pip requirements"
pwd
echo $PREFIX
echo $PKG_NAME
ls
pip install -r $PREFIX/requirements.txt
