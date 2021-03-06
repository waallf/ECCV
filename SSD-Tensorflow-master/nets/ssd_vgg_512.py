# Copyright 2016 Paul Balanca. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Definition of 512 VGG-based SSD network.

This model was initially introduced in:
SSD: Single Shot MultiBox Detector
Wei Liu, Dragomir Anguelov, Dumitru Erhan, Christian Szegedy, Scott Reed,
Cheng-Yang Fu, Alexander C. Berg
https://arxiv.org/abs/1512.02325

Two variants of the model are defined: the 300x300 and 512x512 models, the
latter obtaining a slightly better accuracy on Pascal VOC.

Usage:
    with slim.arg_scope(ssd_vgg.ssd_vgg()):
        outputs, end_points = ssd_vgg.ssd_vgg(inputs)
@@ssd_vgg
"""
import math
from collections import namedtuple

import numpy as np
import tensorflow as tf

import tf_extended as tfe
from nets import custom_layers
from nets import ssd_common
from nets import ssd_vgg_300

import tensorflow.contrib.slim as slim


# =========================================================================== #
# SSD class definition.
# =========================================================================== #
SSDParams = namedtuple('SSDParameters', ['img_shape',
                                         'num_classes',
                                         'no_annotation_label',
                                         'feat_layers',
                                         'feat_shapes',
                                         'anchor_size_bounds',
                                         'anchor_sizes',
                                         'anchor_ratios',
                                         'anchor_steps',
                                         'anchor_offset',
                                         'normalizations',
                                         'prior_scaling'
                                         ])


class SSDNet(object):
    """Implementation of the SSD VGG-based 512 network.

    The default features layers with 512x512 image input are:
      conv4 ==> 64 x 64
      conv7 ==> 32 x 32
      conv8 ==> 16 x 16
      conv9 ==> 8 x 8
      conv10 ==> 4 x 4
      conv11 ==> 2 x 2
      conv12 ==> 1 x 1
    The default image size used to train this network is 512x512.
    """
    default_params = SSDParams(
        img_shape=(512, 512),
        num_classes=11,
        no_annotation_label=11,
        feat_layers=['block4', 'block7', 'block8', 'block9', 'block10', 'block11', 'block12'],
        feat_shapes=[(64, 64), (32, 32), (16, 16), (8, 8), (4, 4), (2, 2), (1, 1)],
        anchor_size_bounds=[0.10, 0.90],
        anchor_sizes=[(20.48, 51.2),
                      (51.2, 133.12),
                      (133.12, 215.04),
                      (215.04, 296.96),
                      (296.96, 378.88),
                      (378.88, 460.8),
                      (460.8, 542.72)],
        anchor_ratios=[[2, .5,3./5,5./3],
                       [2, .5, 3, 1./3,3./5,5./3],
                       [2, .5, 3, 1./3,3./5,5./3],
                       [2, .5, 3, 1./3,3./5,5./3],
                       [2, .5, 3, 1./3,3./5,5./3],
                       [2, .5,3./5,5./3],
                       [2, .5,3./5,5./3]],
        # anchor_ratios=[[2, .5],
        #                [2, .5, 3, 1. / 3],
        #                [2, .5, 3, 1. / 3],
        #                [2, .5, 3, 1. / 3],
        #                [2, .5, 3, 1. / 3,],
        #                [2, .5],
        #                [2, .5]],
        anchor_steps=[8, 16, 32, 64, 128, 256, 512],
        anchor_offset=0.5,
        normalizations=[20, -1, -1, -1, -1, -1, -1],
        prior_scaling=[0.1, 0.1, 0.2, 0.2]
        )

    def __init__(self, params=None):
        """Init the SSD net with some parameters. Use the default ones
        if none provided.
        """
        if isinstance(params, SSDParams):
            self.params = params
        else:
            self.params = SSDNet.default_params

    # ======================================================================= #
    def net(self, inputs,
            is_training=True,
            update_feat_shapes=True,
            dropout_keep_prob=0.5,
            prediction_fn=slim.softmax,
            reuse=None,
            scope='ssd_512_vgg',
            DSSD_FLAG  = False):
        """Network definition.
        """
        r = ssd_net(inputs,
                    num_classes=self.params.num_classes,
                    feat_layers=self.params.feat_layers,
                    anchor_sizes=self.params.anchor_sizes,
                    anchor_ratios=self.params.anchor_ratios,
                    normalizations=self.params.normalizations,
                    is_training=is_training,
                    dropout_keep_prob=dropout_keep_prob,
                    prediction_fn=prediction_fn,
                    reuse=reuse,
                    scope=scope,
                    DSSD_FLAG=DSSD_FLAG)
        # Update feature shapes (try at least!)
        if update_feat_shapes:
            shapes = ssd_feat_shapes_from_net(r[0], self.params.feat_shapes)
            self.params = self.params._replace(feat_shapes=shapes)
        return r

    def arg_scope(self, weight_decay=0.0005, data_format='NHWC'):
        """Network arg_scope.
        """
        return ssd_arg_scope(weight_decay, data_format=data_format)

    def arg_scope_caffe(self, caffe_scope):
        """Caffe arg_scope used for weights importing.
        """
        return ssd_arg_scope_caffe(caffe_scope)

    # ======================================================================= #
    def anchors(self, img_shape, dtype=np.float32):
        """Compute the default anchor boxes, given an image shape.
        """
        return ssd_anchors_all_layers(img_shape,
                                      self.params.feat_shapes,
                                      self.params.anchor_sizes,
                                      self.params.anchor_ratios,
                                      self.params.anchor_steps,
                                      self.params.anchor_offset,
                                      dtype)

    def bboxes_encode(self, labels, bboxes, anchors,
                      scope=None):
        """Encode labels and bounding boxes.
        """
        return ssd_common.tf_ssd_bboxes_encode(
            labels, bboxes, anchors,
            self.params.num_classes,
            self.params.no_annotation_label,
            ignore_threshold=0.5,
            prior_scaling=self.params.prior_scaling,
            scope=scope)

    def bboxes_decode(self, feat_localizations, anchors,
                      scope='ssd_bboxes_decode'):
        """Encode labels and bounding boxes.
        """
        return ssd_common.tf_ssd_bboxes_decode(
            feat_localizations, anchors,
            prior_scaling=self.params.prior_scaling,
            scope=scope)

    def detected_bboxes(self, predictions, localisations,
                        select_threshold=None, nms_threshold=0.5,
                        clipping_bbox=None, top_k=400, keep_top_k=200):
        """Get the detected bounding boxes from the SSD network output.
        """
        # Select top_k bboxes from predictions, and clip
        rscores, rbboxes = \
            ssd_common.tf_ssd_bboxes_select(predictions, localisations,
                                            select_threshold=select_threshold,
                                            num_classes=self.params.num_classes)
        rscores, rbboxes = \
            tfe.bboxes_sort(rscores, rbboxes, top_k=top_k)
        # Apply NMS algorithm.
        rscores, rbboxes = \
            tfe.bboxes_nms_batch(rscores, rbboxes,
                                 nms_threshold=nms_threshold,
                                 keep_top_k=keep_top_k)
        # if clipping_bbox is not None:
        #     rbboxes = tfe.bboxes_clip(clipping_bbox, rbboxes)
        return rscores, rbboxes

    def losses(self, logits, localisations,
               gclasses, glocalisations, gscores,
               match_threshold=0.5,
               negative_ratio=3.,
               alpha=1.,
               label_smoothing=0.,
               scope='ssd_losses'):
        """Define the SSD network losses.
        """
        return ssd_losses(logits, localisations,
                          gclasses, glocalisations, gscores,
                          match_threshold=match_threshold,
                          negative_ratio=negative_ratio,
                          alpha=alpha,
                          label_smoothing=label_smoothing,
                          scope=scope)


# =========================================================================== #
# SSD tools...
# =========================================================================== #
def layer_shape(layer):
    """Returns the dimensions of a 4D layer tensor.
    Args:
      layer: A 4-D Tensor of shape `[height, width, channels]`.
    Returns:
      Dimensions that are statically known are python integers,
        otherwise they are integer scalar tensors.
    """
    if layer.get_shape().is_fully_defined():
        return layer.get_shape().as_list()
    else:
        static_shape = layer.get_shape().with_rank(4).as_list()
        dynamic_shape = tf.unstack(tf.shape(layer), 3)
        return [s if s is not None else d
                for s, d in zip(static_shape, dynamic_shape)]


def ssd_size_bounds_to_values(size_bounds,
                              n_feat_layers,
                              img_shape=(512, 512)):
    """Compute the reference sizes of the anchor boxes from relative bounds.
    The absolute values are measured in pixels, based on the network
    default size (512 pixels).

    This function follows the computation performed in the original
    implementation of SSD in Caffe.

    Return:
      list of list containing the absolute sizes at each scale. For each scale,
      the ratios only apply to the first value.
    """
    assert img_shape[0] == img_shape[1]

    img_size = img_shape[0]
    min_ratio = int(size_bounds[0] * 100)
    max_ratio = int(size_bounds[1] * 100)
    step = int(math.floor((max_ratio - min_ratio) / (n_feat_layers - 2)))
    # Start with the following smallest sizes.
    sizes = [[img_size * 0.04, img_size * 0.1]]
    for ratio in range(min_ratio, max_ratio + 1, step):
        sizes.append((img_size * ratio / 100.,
                      img_size * (ratio + step) / 100.))
    return sizes


def ssd_feat_shapes_from_net(predictions, default_shapes=None):
    """Try to obtain the feature shapes from the prediction layers.

    Return:
      list of feature shapes. Default values if predictions shape not fully
      determined.
    """
    feat_shapes = []
    for l in predictions:
        shape = l.get_shape().as_list()[1:4]
        if None in shape:
            return default_shapes
        else:
            feat_shapes.append(shape)
    return feat_shapes


def ssd_anchor_one_layer(img_shape,
                         feat_shape,
                         sizes,
                         ratios,
                         step,
                         offset=0.5,
                         dtype=np.float32):
    """Computer SSD default anchor boxes for one feature layer.

    Determine the relative position grid of the centers, and the relative
    width and height.

    Arguments:
      feat_shape: Feature shape, used for computing relative position grids;
      size: Absolute reference sizes;
      ratios: Ratios to use on these features;
      img_shape: Image shape, used for computing height, width relatively to the
        former;
      offset: Grid offset.

    Return:
      y, x, h, w: Relative x and y grids, and height and width.
    """
    # Compute the position grid: simple way.
    # y, x = np.mgrid[0:feat_shape[0], 0:feat_shape[1]]
    # y = (y.astype(dtype) + offset) / feat_shape[0]
    # x = (x.astype(dtype) + offset) / feat_shape[1]
    # Weird SSD-Caffe computation using steps values...
    y, x = np.mgrid[0:feat_shape[0], 0:feat_shape[1]]
    y = (y.astype(dtype) + offset) * step / img_shape[0]
    x = (x.astype(dtype) + offset) * step / img_shape[1]

    # Expand dims to support easy broadcasting.
    y = np.expand_dims(y, axis=-1)
    x = np.expand_dims(x, axis=-1)

    # Compute relative height and width.
    # Tries to follow the original implementation of SSD for the order.
    num_anchors = len(sizes) + len(ratios)
    h = np.zeros((num_anchors, ), dtype=dtype)
    w = np.zeros((num_anchors, ), dtype=dtype)
    # Add first anchor boxes with ratio=1.
    h[0] = sizes[0] / img_shape[0]
    w[0] = sizes[0] / img_shape[1]
    di = 1
    if len(sizes) > 1:
        h[1] = math.sqrt(sizes[0] * sizes[1]) / img_shape[0]
        w[1] = math.sqrt(sizes[0] * sizes[1]) / img_shape[1]
        di += 1
    for i, r in enumerate(ratios):
        h[i+di] = sizes[0] / img_shape[0] / math.sqrt(r)
        w[i+di] = sizes[0] / img_shape[1] * math.sqrt(r)
    return y, x, h, w


def ssd_anchors_all_layers(img_shape, #得到一副图像7个特征图的每个特征图的anchors
                           layers_shape,
                           anchor_sizes,
                           anchor_ratios,
                           anchor_steps,
                           offset=0.5,
                           dtype=np.float32):
    """Compute anchor boxes for all feature layers.
    """
    layers_anchors = []
    for i, s in enumerate(layers_shape):
        anchor_bboxes = ssd_anchor_one_layer(img_shape, s,
                                             anchor_sizes[i],
                                             anchor_ratios[i],
                                             anchor_steps[i],
                                             offset=offset, dtype=dtype)
        layers_anchors.append(anchor_bboxes)
    return layers_anchors

def upbilinear(input, name,mode):
    if mode =='bnwh':
        up = tf.transpose(input[0],perm=(0,2,3,1))
        up_h = tf.shape(input[1])[2]
        up_w = tf.shape(input[1])[3]
        up = tf.image.resize_bilinear(up, [up_h, up_w], name=name)
        up = tf.transpose(up, perm=(0, 3, 1, 2))
    else:
        up_h = tf.shape(input[1])[1]
        up_w = tf.shape(input[1])[2]
        up = tf.image.resize_bilinear(input[0], [up_h, up_w], name=name)

    return up


# =========================================================================== #
# Functional definition of VGG-based SSD 512.
# =========================================================================== #
def ssd_net(inputs,
            num_classes=SSDNet.default_params.num_classes,
            feat_layers=SSDNet.default_params.feat_layers,
            anchor_sizes=SSDNet.default_params.anchor_sizes,
            anchor_ratios=SSDNet.default_params.anchor_ratios,
            normalizations=SSDNet.default_params.normalizations,
            is_training=True,
            dropout_keep_prob=0.5,
            prediction_fn=slim.softmax,
            reuse=None,
            scope='ssd_512_vgg',
            DSSD_FLAG = False
            ):
    """SSD net definition.
    """
    # End_points collect relevant activations for external use.
    end_points = {}
    if inputs.shape[2] == inputs.shape[3] :
        mode = 'bnwh'
    else:
        mode ='bwhn'
    with tf.variable_scope(scope, 'ssd_512_vgg', [inputs], reuse=reuse):
        # Original VGG-16 blocks.
        net = slim.repeat(inputs, 2, slim.conv2d, 64, [3, 3], scope='conv1')
        end_points['block1'] = net
        net = slim.max_pool2d(net, [2, 2], scope='pool1')
        # Block 2.
        net = slim.repeat(net, 2, slim.conv2d, 128, [3, 3], scope='conv2')
        end_points['block2'] = net
        net = slim.max_pool2d(net, [2, 2], scope='pool2')
        # Block 3.
        net = slim.repeat(net, 3, slim.conv2d, 256, [3, 3], scope='conv3')
        end_points['block3'] = net
        net = slim.max_pool2d(net, [2, 2], scope='pool3')
        # Block 4.
        net = slim.repeat(net, 3, slim.conv2d, 512, [3, 3], scope='conv4')
        end_points['block4'] = net
        net = slim.max_pool2d(net, [2, 2], scope='pool4')
        # Block 5.
        net = slim.repeat(net, 3, slim.conv2d, 512, [3, 3], scope='conv5')
        end_points['block5'] = net
        net = slim.max_pool2d(net, [3, 3], 1, scope='pool5')

        # Additional SSD blocks.
        # Block 6: let's dilate the hell out of it!
        net = slim.conv2d(net, 1024, [3, 3], rate=6, scope='conv6')
        end_points['block6'] = net
        # Block 7: 1x1 conv. Because the fuck.
        net = slim.conv2d(net, 1024, [1, 1], scope='conv7')
        end_points['block7'] = net

        # Block 8/9/10/11: 1x1 and 3x3 convolutions stride 2 (except lasts).
        end_point = 'block8'
        with tf.variable_scope(end_point):
            net = slim.conv2d(net, 256, [1, 1], scope='conv1x1')
            net = custom_layers.pad2d(net, pad=(1, 1))
            net = slim.conv2d(net, 512, [3, 3], stride=2, scope='conv3x3', padding='VALID')
        end_points[end_point] = net
        end_point = 'block9'
        with tf.variable_scope(end_point):
            net = slim.conv2d(net, 128, [1, 1], scope='conv1x1')
            net = custom_layers.pad2d(net, pad=(1, 1))
            net = slim.conv2d(net, 256, [3, 3], stride=2, scope='conv3x3', padding='VALID')
        end_points[end_point] = net
        end_point = 'block10'
        with tf.variable_scope(end_point):
            net = slim.conv2d(net, 128, [1, 1], scope='conv1x1')
            net = custom_layers.pad2d(net, pad=(1, 1))
            net = slim.conv2d(net, 256, [3, 3], stride=2, scope='conv3x3', padding='VALID')
        end_points[end_point] = net
        end_point = 'block11'
        with tf.variable_scope(end_point):
            net = slim.conv2d(net, 128, [1, 1], scope='conv1x1')
            net = custom_layers.pad2d(net, pad=(1, 1))
            net = slim.conv2d(net, 256, [3, 3], stride=2, scope='conv3x3', padding='VALID')
        end_points[end_point] = net
        end_point = 'block12'
        with tf.variable_scope(end_point):
            net = slim.conv2d(net, 128, [1, 1], scope='conv1x1')
            net = custom_layers.pad2d(net, pad=(1, 1))
            net = slim.conv2d(net, 256, [4, 4], scope='conv4x4', padding='VALID')
            # Fix padding to match Caffe version (pad=1).
            # pad_shape = [(i-j) for i, j in zip(layer_shape(net), [0, 1, 1, 0])]
            # net = tf.slice(net, [0, 0, 0, 0], pad_shape, name='caffe_pad')
        end_points[end_point] = net

        # Prediction and localisations layers.
        # rever_feat_layers = list(reversed(feat_layers))
        # for i, l in enumerate(rever_feat_layers):
        #     if i == 0: continue
        #     l_ = rever_feat_layers[i - 1]
        #
        #     end_points[l] = tf.concat([upbilinear([end_points[l_], end_points[l]], name=l_), end_points[l]],axis=1)

        # with tf.variable_scope("fpn11"):
        #
        #
        #     end_points['block11'] = tf.add(upbilinear([end_points['block12'], end_points['block11']],name ="up_11",mode=mode),
        #                                    end_points['block11'],name= "fpn_block11")
        #
        # with tf.variable_scope("fpn10"):
        #
        #     end_points['block10'] = tf.add(upbilinear([end_points['block11'],end_points['block10']],name ="up_10",mode=mode),
        #                                    end_points['block10'],
        #                                    name="fpn_block10")
        # with tf.variable_scope("fpn9"):
        #     b9 = slim.conv2d(end_points['block10'], 256, [1, 1], scope='9conv1x1')
        #     b9_ = slim.conv2d(end_points['block9'], 256, [1, 1], scope='9_conv1x1')
        #     end_points['block9'] = tf.add(upbilinear([end_points['block10'],end_points['block9']],name ="up_9",mode=mode),
        #                                   end_points['block9'],
        #                                    name="fpn_block9")
        # with tf.variable_scope("fpn8"):
        #     b8 = slim.conv2d(end_points['block9'], 512, [1, 1], scope='8conv1x1')
        #
        #     end_points['block8'] = tf.add(upbilinear([b8, end_points['block8']],name ="up_8",mode=mode), end_points['block8'],
        #                                    name="fpn_block8")
        # with tf.variable_scope("fpn7"):
        #     b7 = slim.conv2d(end_points['block8'], 1024, [1, 1], scope='7conv1x1')
        #
        #     end_points['block7'] = tf.add(upbilinear([b7, end_points['block7']],name ="up_7",mode=mode), end_points['block7'],
        #                                   name="fpn_block7")
        # with tf.variable_scope("fpn4"):
        #     b4 = slim.conv2d(end_points['block7'], 512, [1, 1], scope='4conv1x1')
        #
        #     end_points['block4'] = tf.add(upbilinear([b4, end_points['block4']],name ="up_4",mode=mode), end_points['block4'],
        #                                   name="fpn_block4")

        if DSSD_FLAG:
            with tf.variable_scope("dssd11"):

                de_12 = slim.conv2d_transpose(end_points['block12'],512,[3,3],stride=2,scope="de_12")
                con_12 = slim.conv2d(de_12,512,[3,3],scope='conv_12')
                bn_12 = slim.batch_norm(con_12, is_training=is_training)

                con_11 = slim.conv2d(end_points["block11"],512,[3,3],scope="conv11")
                bn_11 = slim.batch_norm(con_11, is_training=is_training)
                relu_11 = tf.nn.relu(bn_11)
                con_11 = slim.conv2d(relu_11,512,[3,3],scope="conv11_2")
                bn_11 = slim.batch_norm(con_11, is_training=is_training)

                end_points["block11"] = tf.nn.relu(tf.multiply(bn_12,bn_11))

            with tf.variable_scope("dssd10"):

                de_11 = slim.conv2d_transpose(end_points['block11'],512,[3,3],stride=2,scope="de_11")
                con_11 = slim.conv2d(de_11,512,[3,3],scope='conv_11')
                bn_11 = slim.batch_norm(con_11, is_training=is_training)

                con_10 = slim.conv2d(end_points["block10"],512,[3,3],scope="conv10")
                bn_10 = slim.batch_norm(con_10, is_training=is_training)
                relu_10 = tf.nn.relu(bn_10)
                con_10 = slim.conv2d(relu_10,512,[3,3],scope="conv10_2")
                bn_10 = slim.batch_norm(con_10, is_training=is_training)

                end_points["block10"] = tf.nn.relu(tf.multiply(bn_11,bn_10))


            with tf.variable_scope("dssd9"):

                de_10 = slim.conv2d_transpose(end_points['block10'],512,[3,3],stride=2,scope="de_10")
                con_10 = slim.conv2d(de_10,512,[3,3],scope='conv_10')
                bn_10 = slim.batch_norm(con_10, is_training=is_training)

                con_9 = slim.conv2d(end_points["block9"],512,[3,3],scope="conv9")
                bn_9 = slim.batch_norm(con_9, is_training=is_training)
                relu_9 = tf.nn.relu(bn_9)
                con_9 = slim.conv2d(relu_9,512,[3,3],scope="conv9_2")
                bn_9= slim.batch_norm(con_9, is_training=is_training)

                end_points["block9"] = tf.nn.relu(tf.multiply(bn_10,bn_9))

            with tf.variable_scope("dssd8"):

                de_9 = slim.conv2d_transpose(end_points['block9'],512,[3,3],stride=2,scope="de_9")
                con_9 = slim.conv2d(de_9,512,[3,3],scope='conv_9')
                bn_9 = slim.batch_norm(con_9, is_training=is_training)

                con_8 = slim.conv2d(end_points["block8"],512,[3,3],scope="conv8")
                bn_8 = slim.batch_norm(con_8, is_training=is_training)
                relu_8 = tf.nn.relu(bn_8)
                con_8= slim.conv2d(relu_8,512,[3,3],scope="conv8_2")
                bn_8= slim.batch_norm(con_8, is_training=is_training)

                end_points["block8"] = tf.nn.relu(tf.multiply(bn_9,bn_8))


            with tf.variable_scope("dssd7"):

                de_8 = slim.conv2d_transpose(end_points['block8'],512,[3,3],stride=2,scope="de_8")
                con_8 = slim.conv2d(de_8,512,[3,3],scope='conv_8')
                bn_8 = slim.batch_norm(con_8, is_training=is_training)

                con_7 = slim.conv2d(end_points["block7"],512,[3,3],scope="conv7")
                bn_7 = slim.batch_norm(con_7, is_training=is_training)
                relu_7 = tf.nn.relu(bn_7)
                con_7= slim.conv2d(relu_7,512,[3,3],scope="conv7_2")
                bn_7= slim.batch_norm(con_7, is_training=is_training)

                end_points["block7"] = tf.nn.relu(tf.multiply(bn_8,bn_7))


            with tf.variable_scope("dssd4"):

                de_7 = slim.conv2d_transpose(end_points['block7'],512,[3,3],stride=2,scope="de_7")
                con_7 = slim.conv2d(de_7,512,[3,3],scope='conv_7')
                bn_7 = slim.batch_norm(con_7, is_training=is_training)

                con_4 = slim.conv2d(end_points["block4"],512,[3,3],scope="conv4")
                bn_4 = slim.batch_norm(con_4, is_training=is_training)
                relu_4 = tf.nn.relu(bn_4)
                con_4= slim.conv2d(relu_4,512,[3,3],scope="conv4_2")
                bn_4= slim.batch_norm(con_4, is_training=is_training)

                end_points["block4"] = tf.nn.relu(tf.multiply(bn_7,bn_4))



        #
        predictions = []
        logits = []
        localisations = []
        for i, layer in enumerate(feat_layers):
            with tf.variable_scope(layer + '_box'):
                p, l = ssd_vgg_300.ssd_multibox_layer(end_points[layer],
                                                      num_classes,
                                                      anchor_sizes[i],
                                                      anchor_ratios[i],
                                                      normalizations[i])
            predictions.append(prediction_fn(p))
            logits.append(p)
            localisations.append(l)

        return predictions, localisations, logits, end_points
ssd_net.default_image_size = 512


def ssd_arg_scope(weight_decay=0.0005, data_format='NHWC'):
    """Defines the VGG arg scope.

    Args:
      weight_decay: The l2 regularization coefficient.

    Returns:
      An arg_scope.
    """
    with slim.arg_scope([slim.conv2d, slim.fully_connected,slim.conv2d_transpose],
                        activation_fn=tf.nn.relu,
                        weights_regularizer=slim.l2_regularizer(weight_decay),
                        weights_initializer=tf.contrib.layers.xavier_initializer(),
                        biases_initializer=tf.zeros_initializer()):
        with slim.arg_scope([slim.conv2d, slim.max_pool2d,slim.conv2d_transpose],
                            padding='SAME',
                            data_format=data_format):
            with slim.arg_scope([custom_layers.pad2d,
                                 custom_layers.l2_normalization,
                                 custom_layers.channel_to_last],
                                data_format=data_format) as sc:
                return sc


# =========================================================================== #
# Caffe scope: importing weights at initialization.
# =========================================================================== #
def ssd_arg_scope_caffe(caffe_scope):
    """Caffe scope definition.

    Args:
      caffe_scope: Caffe scope object with loaded weights.

    Returns:
      An arg_scope.
    """
    # Default network arg scope.
    with slim.arg_scope([slim.conv2d],
                        activation_fn=tf.nn.relu,
                        weights_initializer=caffe_scope.conv_weights_init(),
                        biases_initializer=caffe_scope.conv_biases_init()):
        with slim.arg_scope([slim.fully_connected],
                            activation_fn=tf.nn.relu):
            with slim.arg_scope([custom_layers.l2_normalization],
                                scale_initializer=caffe_scope.l2_norm_scale_init()):
                with slim.arg_scope([slim.conv2d, slim.max_pool2d],
                                    padding='SAME') as sc:
                    return sc


# =========================================================================== #
# SSD loss function.
# =========================================================================== #
def ssd_losses(logits, localisations,
               gclasses, glocalisations, gscores,
               match_threshold=0.5,
               negative_ratio=3.,
               alpha=1.,
               label_smoothing=0.,
               scope=None):
    """Loss functions for training the SSD 300 VGG network.

    This function defines the different loss components of the SSD, and
    adds them to the TF loss collection.

    Arguments:
      logits: (list of) predictions logits Tensors;
      localisations: (list of) localisations Tensors;
      gclasses: (list of) groundtruth labels Tensors;
      glocalisations: (list of) groundtruth localisations Tensors;
      gscores: (list of) groundtruth score Tensors;
    """
    with tf.name_scope(scope, 'ssd_losses'):
        l_cross_pos = []
        l_cross_neg = []
        l_loc = []
        for i in range(len(logits)):
            dtype = logits[i].dtype
            with tf.name_scope('block_%i' % i):
                # Determine weights Tensor.
                pmask = gscores[i] > match_threshold
                fpmask = tf.cast(pmask, dtype)
                n_positives = tf.reduce_sum(fpmask) #正样本个数

                # Select some random negative entries.
                # n_entries = np.prod(gclasses[i].get_shape().as_list())
                # r_positive = n_positives / n_entries
                # r_negative = negative_ratio * n_positives / (n_entries - n_positives)

                # Negative mask.
                no_classes = tf.cast(pmask, tf.int32)
                predictions = slim.softmax(logits[i])
                nmask = tf.logical_and(tf.logical_not(pmask),
                                       gscores[i] > -0.5)
                fnmask = tf.cast(nmask, dtype)
                nvalues = tf.where(nmask,           #选着出来负样本
                                   predictions[:, :, :, :, 0],
                                   1. - fnmask)
                nvalues_flat = tf.reshape(nvalues, [-1])
                # Number of negative entries to select.
                n_neg = tf.cast(negative_ratio * n_positives, tf.int32) #正样本数量 × negative_ratio ，将负样本数量变为正样本的3倍
                n_neg = tf.maximum(n_neg, tf.size(nvalues_flat) // 8)
                n_neg = tf.maximum(n_neg, tf.shape(nvalues)[0] * 4)
                max_neg_entries = 1 + tf.cast(tf.reduce_sum(fnmask), tf.int32)
                n_neg = tf.minimum(n_neg, max_neg_entries)  #负样本个数

                val, idxes = tf.nn.top_k(-nvalues_flat, k=n_neg)
                minval = val[-1]
                # Final negative mask.
                nmask = tf.logical_and(nmask, -nvalues > minval)#选出预测值接近于0的样本，阈值为minval（选出的负样本个数中，预测负样本概率最小的值）
                fnmask = tf.cast(nmask, dtype)

                # Add cross-entropy loss.
                with tf.name_scope('cross_entropy_pos'):#正样本类别损失
                    loss = tf.nn.sparse_softmax_cross_entropy_with_logits(logits=logits[i],
                                                                          labels=gclasses[i])
                    loss = tf.losses.compute_weighted_loss(loss, fpmask)
                    l_cross_pos.append(loss)

                with tf.name_scope('cross_entropy_neg'):#负样本类别损失
                    loss = tf.nn.sparse_softmax_cross_entropy_with_logits(logits=logits[i],
                                                                          labels=no_classes)
                    loss = tf.losses.compute_weighted_loss(loss, fnmask)
                    l_cross_neg.append(loss)

                # Add localization loss: smooth L1, L2, ...
                with tf.name_scope('localization'):
                    # Weights Tensor: positive mask + random negative.
                    weights = tf.expand_dims(alpha * fpmask, axis=-1)
                    loss = custom_layers.abs_smooth(localisations[i] - glocalisations[i])
                    loss = tf.losses.compute_weighted_loss(loss, weights)
                    l_loc.append(loss)

        # Additional total losses...
        with tf.name_scope('total'):
            total_cross_pos = tf.add_n(l_cross_pos, 'cross_entropy_pos')
            total_cross_neg = tf.add_n(l_cross_neg, 'cross_entropy_neg')
            total_cross = tf.add(total_cross_pos, total_cross_neg, 'cross_entropy')
            total_loc = tf.add_n(l_loc, 'localization')

            # Add to EXTRA LOSSES TF.collection
            tf.add_to_collection('EXTRA_LOSSES', total_cross_pos)
            tf.add_to_collection('EXTRA_LOSSES', total_cross_neg)
            tf.add_to_collection('EXTRA_LOSSES', total_cross)
            tf.add_to_collection('EXTRA_LOSSES', total_loc)
