import os
from jenkinsutils import BuildHelper

package = 'SAValidation'
type = 'install'

bh = BuildHelper(package, type)

# delete & re-create the venv
bh.venv_create()

# install package
bh.vecall('pip', 'install', package)

# import module as our "test"
bh.vecall('python', '-c', 'import savalidation')
