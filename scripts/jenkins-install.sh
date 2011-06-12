DISTNAME="SAValidation"
PACKAGE="savalidation"
# script should be run from package root if not being run in Jenkins
if [ -z "$WORKSPACE" ]; then
    VENVDIR="/tmp/$PACKAGE-jenkins-venv"
else
    VENVDIR="$WORKSPACE/.venv-install"
    cd "$WORKSPACE"
fi

# delete the virtualenv, this ensures all packages are installed from scratch
# to make sure our dependencies are specified correctly
rm -rf "$VENVDIR"

# create the venv
virtualenv "$VENVDIR" --no-site-packages -q

# If in jenkins, assuming the PATH has been set
# correctly already, otherwise activate the VENV
if [ -z "$WORKSPACE" ]; then
    source "$VENVDIR/bin/activate"
fi

# install from pypi
pip install "$DISTNAME"

# import it
python -c "import $PACKAGE; print $PACKAGE.VERSION"
