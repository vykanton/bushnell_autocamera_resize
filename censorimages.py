#from __future__ import print_function
import json
import os
from datetime import datetime
 
from PIL import Image, ImageDraw, ImageFilter
 
 
class censorimages:
    """
    Censors images based on rules in censorsettings.json 
    This is to remove peoples houses etc from the images.
    Usage:
        censorimages.censorfile(source,dest,censorsettings)
        Where:
            source = Source location
            dest = destination
            censorsettings =  a json file with censor rulesets
    """
    
    def __init__(self):
        self.primary_json='censorsettings.json'
        self.resized_json='censorsettingsResize.json'
    
    def _blurbox(self,im,box):
        #box = ( (box[0], box[1])  ,(box[2],box[3] ) )
        blur_region=self._cropto(im,box)
        #blur_region = blur_region.filter(ImageFilter.GaussianBlur(radius=50))
        for i in range(40):
            blur_region=blur_region.filter(ImageFilter.BLUR)
        im.paste(blur_region,box)
        return im
        
        
    def _blackbox(self,im,box):
        box = ( (box[0], box[1])  ,(box[2],box[3] ) )
        drawcanv = ImageDraw.Draw(im)
        drawcanv.rectangle( box, fill="black", outline="black")
        
    def _cropto(Self,im,box):
        im = im.crop(box)
        return im
    
    def resize_json(self,ratio):
        """
        Resize all the json settings by the ratio specified
        This should only be run once, write the output to an
        output json file and check for its existance
        """
        if not os.path.isfile(self.resized_json):
            with open(self.primary_json,'rb') as f:
                self.originalsettings=json.load(f)
            #self.settings=self.resize_json(self.originalsettings,ratio)
            for camkey in self.originalsettings:
                camcensoring = self.originalsettings[camkey]
                #resize all value in settings with resized values
                for key in camcensoring:
                    camsettings=camcensoring[key]
                    for i, settingsrow in enumerate(camsettings):
                        for k, setting in enumerate(settingsrow):
                            if setting == "width": 
                                pass
                            elif setting == "height": 
                                pass
                            else:
                                camsettings[i][k]=int(setting*ratio)
            
            #write modified JSON
            with open(self.resized_json,'wb') as f: 
                json.dump(self.originalsettings,f,indent=2)
        
    
    def _replace_placeholder(self,im,camsettings):
        """
        Replace "width" and "height" with the correct pixels for the
        image's height and width.
        """
        
        imwidth = im.size[0]
        imheight = im.size[1]
        
        #replace width and height with image sizes
        for i, settingsrow in enumerate(camsettings):
            for k, setting in enumerate(settingsrow):
                if setting == "width": 
                    camsettings[i][k] = imwidth
                elif setting == "height": camsettings[i][k] = imheight
                else:
                    pass
        return camsettings
    
    
    def _modifybycamera(self,camera,im):
        """
        Make modifcations to an image based on its 
        settings, derived from its camsite
        """
        camcensoring = self.settings[camera]
            
        #replace width and height for all image operations on the camera
        for key in camcensoring:
            camcensoring[key] = self._replace_placeholder(im,camcensoring[key])
        for key in camcensoring:
            if key=='black':
                blacking = camcensoring['black']
                for settingsrow in blacking:
                    self._blackbox(im,settingsrow)
            if key=='crop':
                cropping = camcensoring['crop']
                for settingsrow in cropping:
                    im=self._cropto(im,settingsrow)
            if key=='blur':
                blurring = camcensoring['blur']
                for settingsrow in blurring:
                    im=self._blurbox(im,settingsrow)
        
        return im
        
    def censorfile(self,im,dest):
        
        #load Settings JSON
        with open(self.resized_json,'rb') as f:
            self.settings=json.load(f)
        self.source=im.filename
        self.dest=dest
        
        #open image
        #im=Image.open(self.source)
        camera = self.source[-8:-5]  # TODO what if there are more than 10
                                    #images and the filename gets longer by 1?
                                    
        try:
            self._modifybycamera(camera,im)
        except:
            pass
            #print "no censoring rules for camera "
        im=self._modifybycamera("xxx",im)
        im.save(self.dest)
