import  numpy as np
import tensorflow as tf
# from tensorflow.python import pywrap_tensorflow
ckpt = tf.train.get_checkpoint_state("./checkpoints")

reader = tf.train.NewCheckpointReader(ckpt.model_checkpoint_path)
var_to_shape_map = reader.get_variable_to_shape_map()
var_to_shape_map_ = reader.get_tensor()
print(var_to_shape_map)


