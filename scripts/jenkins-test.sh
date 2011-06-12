PACKAGE="savalidation"
TAPACKAGE="savalidation"
# script should be run from package root if not being run in Jenkins
if [ -z "$WORKSPACE" ]; then
    VENVDIR="/tmp/$PACKAGE-jenkins-venv"
else
    VENVDIR="$WORKSPACE/.venv-dev"
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

# install test requirements
pip install -r pip-jenkins-reqs.txt

# install as dev package
pip install -e ./

# run tests
nosetests "$PACKAGE" --with-coverage --cover-package="$PACKAGE" --with-xunit --with-xcoverage --cover-tests
