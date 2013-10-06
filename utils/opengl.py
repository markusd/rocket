'''
Created on Oct 20, 2012

@author: markus
'''

from OpenGL.GL import *
from PyQt4.QtGui import QImage
from PyQt4.QtOpenGL import QGLWidget

import glob
from os.path import basename, splitext

class Texture2D(object):
    
    def __init__(self, width=0, height=0, internalFormat=None, dataFormat=None, dataType=None, data=None):
        self.width = width
        self.height = height
        self.interalFormat = internalFormat
        self.dataFormat = dataFormat
        self.dataType = dataType
        self.id = glGenTextures(1)
        
        self.bind()
        glTexImage2D(GL_TEXTURE_2D, 0, internalFormat, width, height, 0, dataFormat, dataType, data)
        
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        
        Texture2D.unbind()
        
    def bind(self):
        glBindTexture(GL_TEXTURE_2D, self.id)
        
    @classmethod
    def unbind(cls):
        glBindTexture(GL_TEXTURE_2D, 0)
        
    def delete(self):
        print("delete texture")
        glDeleteTextures([self.id])

    @classmethod
    def loadFromFile(cls, path, internalFormat=GL_RGBA):
        image = QImage(path)
        image = QGLWidget.convertToGLFormat(image)
        dataFormat = { QImage.Format_ARGB32: GL_RGBA }.get(image.format(), None)
        dataType = GL_UNSIGNED_BYTE
        data = [0] * image.numBytes()
        bits = image.constBits()
        bits.setsize(image.numBytes())
        for i in range(image.numBytes()):
            data[i] = bits[i][0]
        return Texture2D(image.width(), image.height(), internalFormat, dataFormat, dataType, data)
    
class TextureManager(dict):
    
    __instance = None
    
    @classmethod
    def instance(cls):
        if TextureManager.__instance is None:
            TextureManager.__instance = TextureManager()
        return TextureManager.__instance
    
    def __init__(self, *args):
        dict.__init__(self, args)
        
    def loadFromFolder(self, path, prefix="", filterFunc= lambda f: True):
        for f in glob.glob(path):
            if filterFunc(f):
                self[prefix + "/" + splitext(basename(f))[0]] = Texture2D.loadFromFile(f)
                print(prefix + "/" + splitext(basename(f))[0])
            
    def cleanup(self):
        for v in self.itervalues():
            v.delete()
        
    #def __getitem__(self, key):
    #    return dict.__getitem__(self, key)

    #def __setitem__(self, key, val):
    #    dict.__setitem__(self, key, val)
