import multiprocessing
import operator
import os
import random
from datetime import datetime



from PIL import Image, ImageDraw, ImageFilter
from censorimages import censorimages
from sqlalchemy import Boolean, Column, Integer, Sequence, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


# image base folder
basefolder = "sample_images/"

# output folder
outfolder = "output_images/"

# width 1045, 784ish
size = 1045, 784
ratio = 1045./3264 # hand caculate the ratio of the output image size (1045) to the original image width (3264)


dbname = 'resizeimage.db'

now = datetime.now()

# setup a database to store the image locations
engine = create_engine('sqlite:///'+dbname)

Base = declarative_base()

#cpus for multiprocessing
cpucount=multiprocessing.cpu_count()

#how many images are run per multiprocessing run, bigger is better
#until memory runs low.  This will be split between the mutiprocessor
#worker functions
muti_worker_image_count =  100

#setup image censoring
imagecensoring = censorimages()
imagecensoring.resize_json(ratio)

# images class
class MyImage(Base):
    __tablename__ = "images"

    id = Column(Integer, Sequence('iamge_id_seq'), primary_key=True)
    path = Column(String)
    name = Column(String)
    resized = Column(Boolean)

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()
mycount = 0

# get all the images
for path, subdirs, files in os.walk(basefolder):
    for name in files:
        if name.endswith((".JPG", ".jpg")):
            mycount = mycount + 1
            # print os.path.join(path, name)
            #print name
            new_image = MyImage(path=path, name=name, resized=False)
            if not session.query(MyImage).filter_by(name=name).count():
                session.add(new_image)
            if mycount > 100:
                session.commit()
                mycount = 0
session.commit()

def chunks(l, n):
    """
    Yield successive n-sized chunks from l.
    """
    if n < 1:
        n = 1
    return [l[i:i + n] for i in range(0, len(l), n)]

def image_path(image_query):
    imagepath = []
    for elem in image_query:
        imagepath.append((elem.path, elem.name))
    return imagepath

def equalize(im):
    '''
    Performs Histogram_equalization see: https://en.wikipedia.org/wiki/Histogram_equalization
    The code comes from stackoverflow here: http://stackoverflow.com/questions/7116113/normalize-histogram-brightness-and-contrast-of-a-set-of-images-using-python-im
    '''
    h = im.convert("L").histogram()
    lut = []
    for b in range(0, len(h), 256):
        # step size
        step = reduce(operator.add, h[b:b+256]) / 255
        # create equalization lookup table
        n = 0
        for i in range(256):
            lut.append(n / step)
            n = n + h[i+b]
    # map image through lookup table
    return im.point(lut*im.layers)

def imageprocess_worker(imagepathsubset):
    """
    A multiprocessing working which modifies a set of images listed
    in imagepathsubset.
    """
    for elem in imagepathsubset:

        elem_name=elem[1]
        elem_path=elem[0]
        #print elem_name
        # make directory
        try:
            os.makedirs(os.path.join(outfolder, elem_path.strip("../")))
        except:
            pass
        im = Image.open(os.path.join(elem_path, elem_name))
        # im.thumbnail(size,Image.ANTIALIAS)
        im.thumbnail(size)
        filename=im.filename #weird fix as equalize strips the filename attribute out
        im = equalize(im)
        im.filename=filename #put the filename, back in.
        imagecensoring.censorfile(im,os.path.join(outfolder, elem_path.strip("../"), elem_name))



#print images remaining to be processe
print( "files to process: " +
        str(session.query(MyImage).filter_by(resized=False).count()) )

# load an image, resize it and resave it in the outfolder, maintaining
# file struture
imageset = session.query(MyImage).filter_by(
    resized=False).limit(muti_worker_image_count)  # initial imageset
imagepath = image_path(imageset)
random.shuffle(imagepath) #as only some images need blur, farm them out more randomly
imagepathgroup=chunks(imagepath,int(len(imagepath)/cpucount))

files_remaining = True
while files_remaining == True:
    """
    farm out images to multiprocessing workers in groups
    until no images remain
    """
    jobs=[]
    #multiprocesss
    for imagepathsubset in imagepathgroup:
        p = multiprocessing.Process(target = imageprocess_worker,
                args=(imagepathsubset,))
        jobs.append(p)
        p.start()
    # single cpu for debugging
    # imageprocess_worker(imagepath)

    # Wait for all worker process to finish
    for p in jobs:
        p.join()

    #end of multiprocessing round

    #apply the resized flag to all the images in this round.
    for elem in imageset:
        elem.resized=True
    session.commit()

    #report state
    tdiff = datetime.now() - now
    tdiff = str(tdiff.total_seconds())
    print ("Time so far: " + tdiff +" seconds")
    imageset = session.query(MyImage).filter_by(resized=False)
    print ("remaining images: " +str(imageset.count()))

    imageset = session.query(MyImage).filter_by(
        resized=False).limit(muti_worker_image_count)  # initial imageset
    imagepath = image_path(imageset)
    imagepathgroup=chunks(imagepath,int(len(imagepath)/cpucount))
    #check if task compleate
    if len(imagepath)<=0:
        break



print ("Done")
tdiff = datetime.now() - now
tdiff = str(tdiff.total_seconds())
# num images
num_im = session.query(MyImage).count()
