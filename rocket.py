'''
Created on Oct 2, 2013

@author: markus
'''

import rocket
from rocket import window

from PyQt4 import QtCore, QtGui
import os
import sys
import random


if __name__ == "__main__":
    print(rocket.get_version())
    print(rocket.get_authors())
    
    os.system("pwd")
    random.seed()
    
    # create game window
    app = QtGui.QApplication(sys.argv)
    main = rocket.window.Main()
    main.createLevel("data/levels/level2.json")
    main.show()
    sys.exit(app.exec_())