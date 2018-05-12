from xml.dom import minidom, Node
import cv2
import string
import os
res = r'/home/z840/Desktop/ECCV-task1/VisDrone2018-DET-val/images/'             #图像路径
# list = r'D:\workstation\POD page object detection 2017\Train\Train\Image\nameLIST.txt' #文件名称txt文件
parsedLabel = r'/home/z840/Desktop/ECCV-task1/VisDrone2018-DET-val/annotations/'#label
savePath = r'/home/z840/Desktop/ECCV-task1/VisDrone2018-DET-val/annotations_xml/'

count = 0

image_names = sorted(os.listdir(res))
for i  in range(len(image_names)):
    name = image_names[i]

    im = cv2.imread(os.path.join(res,name))
    w = im.shape[1]
    h = im.shape[0]
    d = im.shape[2]
    # print w,h,d

    doc = minidom.Document()

    annotation = doc.createElement('annotation')
    doc.appendChild(annotation)

    folder = doc.createElement('folder')
    folder.appendChild(doc.createTextNode("POD2017"))
    annotation.appendChild(folder)

    filename = doc.createElement(''
                                 '')
    filename.appendChild(doc.createTextNode(name))
    annotation.appendChild(filename)

    source = doc.createElement('source')
    database = doc.createElement('database')
    database.appendChild(doc.createTextNode("The POD2017 Database"))
    source.appendChild(database)
    annotation2 = doc.createElement('annotation')
    annotation2.appendChild(doc.createTextNode("ICDAR POD2017"))
    source.appendChild(annotation2)
    image = doc.createElement('image')
    image.appendChild(doc.createTextNode("image"))
    source.appendChild(image)
    flickrid = doc.createElement('flickrid')
    flickrid.appendChild(doc.createTextNode("NULL"))
    source.appendChild(flickrid)
    annotation.appendChild(source)

    owner = doc.createElement('owner')
    flickrid = doc.createElement('flickrid')
    flickrid.appendChild(doc.createTextNode("NULL"))
    owner.appendChild(flickrid)
    na = doc.createElement('name')
    na.appendChild(doc.createTextNode("cxm"))
    owner.appendChild(na)
    annotation.appendChild(owner)

    size = doc.createElement('size')
    width = doc.createElement('width')
    width.appendChild(doc.createTextNode("%d" % w))
    size.appendChild(width)
    height = doc.createElement('height')
    height.appendChild(doc.createTextNode("%d" % h))
    size.appendChild(height)
    depth = doc.createElement('depth')
    depth.appendChild(doc.createTextNode("%d" % d))
    size.appendChild(depth)
    annotation.appendChild(size)

    segmented = doc.createElement('segmented')
    segmented.appendChild(doc.createTextNode("0"))
    annotation.appendChild(segmented)

    txtLabel = open(parsedLabel + name[:-4] + '.txt', 'r')
    boxes = txtLabel.readlines()
    for box in boxes:
        box = box.strip().split(',')
        object = doc.createElement('object')
        nm = doc.createElement('name')
        nm.appendChild(doc.createTextNode(box[5]))
        object.appendChild(nm)
        pose = doc.createElement('pose')
        pose.appendChild(doc.createTextNode("undefined"))
        object.appendChild(pose)
        truncated = doc.createElement('truncated')
        truncated.appendChild(doc.createTextNode("0"))
        object.appendChild(truncated)
        difficult = doc.createElement('difficult')
        difficult.appendChild(doc.createTextNode("0"))
        object.appendChild(difficult)
        bndbox = doc.createElement('bndbox')
        xmin = doc.createElement('xmin')
        xmin.appendChild(doc.createTextNode(box[0]))
        bndbox.appendChild(xmin)
        ymin = doc.createElement('ymin')
        ymin.appendChild(doc.createTextNode(box[1]))
        bndbox.appendChild(ymin)
        xmax = doc.createElement('xmax')
        xmax.appendChild(doc.createTextNode(str(float(box[0])+float(box[2]))))
        bndbox.appendChild(xmax)
        ymax = doc.createElement('ymax')
        ymax.appendChild(doc.createTextNode(str(float(box[1])+float(box[3]))))
        bndbox.appendChild(ymax)
        object.appendChild(bndbox)
        annotation.appendChild(object)
    savefile = open(savePath + name[:-4] + '.XML', 'w')
    print(doc.toprettyxml())
    # savefile.write(doc.toprettyxml())
    savefile.close()
    count += 1
    print(count)