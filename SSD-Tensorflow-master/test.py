import os
import math
import random

import numpy as np
import tensorflow as tf
import cv2

slim = tf.contrib.slim
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import sys
sys.path.append('./')

from nets import ssd_vgg_512, ssd_common, np_methods
from preprocessing import ssd_vgg_preprocessing
from notebooks import visualization

gpu_options = tf.GPUOptions(allow_growth=True)
config = tf.ConfigProto(log_device_placement=False, gpu_options=gpu_options)
isess = tf.InteractiveSession(config=config)

net_shape = (512, 512)
data_format = 'NCHW'
img_input = tf.placeholder(tf.uint8, shape=(None, None, 3))


# Evaluation pre-processing: resize to SSD net shape.
image_pre, labels_pre, bboxes_pre, bbox_img = ssd_vgg_preprocessing.preprocess_for_eval(
    img_input, None, None, net_shape, data_format, resize=ssd_vgg_preprocessing.Resize.WARP_RESIZE)
image_4d = tf.expand_dims(image_pre, 0)

# Define the SSD model.
reuse = True if 'ssd_net' in locals() else None
ssd_net = ssd_vgg_512.SSDNet()

arg_scope = ssd_net.arg_scope(weight_decay=0.05,
                              data_format=data_format)

with slim.arg_scope(arg_scope):
    predictions, localisations, _, _ = ssd_net.net(image_4d, is_training=False, reuse=False)



# Restore SSD model.
# ckpt_filename = './checkpoints_fpn/model.ckpt-2901'
ckpt_filename = './checkpoints/model.ckpt-44019'
# ckpt_filename = '../checkpoints/VGG_VOC0712_SSD_300x300_ft_iter_120000.ckpt'
isess.run(tf.global_variables_initializer())
saver = tf.train.Saver()
saver.restore(isess, ckpt_filename)

ssd_anchors = ssd_net.anchors(net_shape)

def process_image(img, select_threshold=0.5, nms_threshold=.45, net_shape=(512, 512)):
    # Run SSD network.
    rimg, rpredictions, rlocalisations, rbbox_img = isess.run([image_4d, predictions, localisations, bbox_img],
                                                              feed_dict={img_input: img})
    print("rimg",rimg)
    print("rpredictions",rpredictions)
    print("rlocalisations",rlocalisations)
    print("rbbox_img",rbbox_img)
    # Get classes and bboxes from the net outputs.
    rclasses, rscores, rbboxes = np_methods.ssd_bboxes_select(
        rpredictions, rlocalisations, ssd_anchors,
        select_threshold=select_threshold, img_shape=net_shape, num_classes=11, decode=True)

    rbboxes = np_methods.bboxes_clip(rbbox_img, rbboxes)
    rclasses, rscores, rbboxes = np_methods.bboxes_sort(rclasses, rscores, rbboxes, top_k=400)
    rclasses, rscores, rbboxes = np_methods.bboxes_nms(rclasses, rscores, rbboxes, nms_threshold=nms_threshold)
    # Resize bboxes to original image shape. Note: useless for Resize.WARP!
    rbboxes = np_methods.bboxes_resize(rbbox_img, rbboxes)
    return rclasses, rscores, rbboxes

path = '/home/z840/Desktop/ECCV-task1/VisDrone2018-DET-val/images/'
image_names = sorted(os.listdir(path))
out_put_dir = "./result/"
for i in range(len(image_names)):
    img = mpimg.imread(path + image_names[i])
    rclasses, rscores, rbboxes =  process_image(img)
    name = image_names[i][:-4] + ".txt"
    file = open(out_put_dir + name,"w")

    height = img.shape[0]
    width = img.shape[1]
    # for j in range(rclasses.shape[0]):
    #     ymin = int(rbboxes[j, 0] * height)
    #     xmin = int(rbboxes[j, 1] * width)
    #     ymax = int(rbboxes[j, 2] * height)
    #     xmax = int(rbboxes[j, 3] * width)
    #
    #     # visualization.bboxes_draw_on_img(img, rclasses, rscores, rbboxes, visualization.colors_plasma)
    #     bbox_left = str(xmin)
    #     bbox_top  = str(ymin)
    #     bbox_width = str(xmax - xmin)
    #     bbox_height = str(ymax - ymin)
    #     score = str(rscores[j])
    #     object_category = str(rclasses[j])
    #     truncation = str(-1)
    #     occlusion = str(-1)
    #     file.write(bbox_left+","+bbox_top+","+bbox_width+","+bbox_height+","+score+","+object_category+","+truncation+","+occlusion+"\n")
    print("rclasses",rclasses)
    print("rbboxes",rbboxes)
    print("rscores",rscores)
    visualization.plt_bboxes(img, rclasses, rscores, rbboxes)