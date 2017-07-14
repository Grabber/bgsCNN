import tensorflow as tf
import cv2
import numpy as np
import os
import os.path

from nets import resnet_v1
from tensorflow.contrib import slim

img = np.float32(cv2.imread("1.jpg"))
img = cv2.normalize(img, 0., 1. ,cv2.NORM_MINMAX)
inputs = np.ones([1,240, 320, 3], dtype = np.float32)
inputs[0,:,:,:] = img

with slim.arg_scope(resnet_v1.resnet_arg_scope()):
    net, end_points = resnet_v1.resnet_v1_152(
        inputs,
        num_classes = None,
        is_training = True,
        global_pool = False)

checkpoints_dir = 'CNN_models'
init_fn = slim.assign_from_checkpoint_fn(
        os.path.join(checkpoints_dir, "resnet_v1_152.ckpt"),
        slim.get_model_variables('resnet_v1'))

with tf.Session() as sess:
    init_fn(sess)
    n = sess.run(net)
    print n[0,:,:,0]
