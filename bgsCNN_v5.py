from utilities import *
import numpy as np
import tensorflow as tf
from tensorflow.contrib.slim.nets import vgg
from tensorflow.contrib import slim
from tensorflow.python.framework import ops
from tensorflow.contrib.layers.python.layers import initializers

class bgsCNN_v5:
    def __init__(self,
                 train_file = "train.tfrecords", test_file = "test.tfrecords",
                 log_dir = "logs",
                 train_batch_size = 40, test_batch_size  = 200,
                 max_iteration = 10000,
                 image_height = 320, image_width = 320, image_depth = 7):
        self.train_file = train_file
        self.test_file  = test_file
        self.log_dir = log_dir
        self.train_batch_size = train_batch_size
        self.test_batch_size = test_batch_size
        self.max_iteration = max_iteration
        self.image_height = image_height
        self.image_width = image_width
        self.image_depth = image_depth
        self.build_inputs()
        self.build_model()
        self.build_loss()
        self.build_optimizer()
        self.build_summary()

    def build_inputs(self):
        with tf.name_scope("input_data"):
            self.input_data = tf.placeholder(tf.float32, [None, self.image_height, self.image_height, 6])
            self.gt = tf.placeholder(tf.int32, [None, self.image_height, self.image_height])
            self.learning_rate = tf.placeholder(tf.float32, [])
            frame = tf.slice(self.input_data, [0,0,0,0], [-1,self.image_height, self.image_height, 3])
            bg = tf.slice(self.input_data, [0,0,0,3], [-1,self.image_height, self.image_height, 3])
            gt = tf.expand_dims(tf.cast(self.gt,tf.float32), 3)
            tf.summary.image("frame", frame, max_outputs=3)
            tf.summary.image("background", bg, max_outputs=3)
            tf.summary.image("groundtruth", gt, max_outputs=3)

    def build_model(self):
        self.variables_collections = {'weights':['weights'], 'biases':['biases']}
        # pre_conv, output shape: 320X320X3
        pre_conv = slim.conv2d(self.input_data, 3,[3,3], scope='pre_conv', biases_initializer=None,
                            weights_initializer=initializers.xavier_initializer(uniform=False),
                            activation_fn=None, variables_collections=self.variables_collections)
        tf.summary.image("pre_conv_out", pre_conv, max_outputs=3, family="pre_conv")
        # vgg_16, output shape: 10X10X512
        with slim.arg_scope(vgg.vgg_arg_scope()):
            net, argmax, __ = vgg_16(
                pre_conv,
                spatial_squeeze = False,
                variables_collections = self.variables_collections)
        tf.summary.image("channel1", tf.slice(net, [0,0,0,0],[-1,10,10,1]), max_outputs=3, family="vgg_16")
        tf.summary.image("channel2", tf.slice(net, [0,0,0,1],[-1,10,10,1]), max_outputs=3, family="vgg_16")
        tf.summary.image("channel3", tf.slice(net, [0,0,0,2],[-1,10,10,1]), max_outputs=3, family="vgg_16")
        tf.summary.image("channel4", tf.slice(net, [0,0,0,3],[-1,10,10,1]), max_outputs=3, family="vgg_16")
        # deconv_1, output shape: 10X10X512
        deconv_1 = slim.repeat(net, 3, slim.conv2d_transpose, 512, [3, 3], scope='deconv1',
            weights_initializer=initializers.xavier_initializer(uniform=False), biases_initializer=None,
            variables_collections=self.variables_collections)
        tf.summary.image("channel1", tf.slice(deconv_1, [0,0,0,0],[-1,10,10,1]), max_outputs=3, family="deconv1")
        tf.summary.image("channel2", tf.slice(deconv_1, [0,0,0,1],[-1,10,10,1]), max_outputs=3, family="deconv1")
        tf.summary.image("channel3", tf.slice(deconv_1, [0,0,0,2],[-1,10,10,1]), max_outputs=3, family="deconv1")
        tf.summary.image("channel4", tf.slice(deconv_1, [0,0,0,3],[-1,10,10,1]), max_outputs=3, family="deconv1")
        # unpool_1, output shape: 20X20X512
        unpool_1 = unpool(deconv_1, argmax[4], shape=[-1,20,20,512], scope='unpool1')
        tf.summary.image("channel1", tf.slice(unpool_1, [0,0,0,0],[-1,20,20,1]), max_outputs=3, family="unpool1")
        tf.summary.image("channel2", tf.slice(unpool_1, [0,0,0,1],[-1,20,20,1]), max_outputs=3, family="unpool1")
        tf.summary.image("channel3", tf.slice(unpool_1, [0,0,0,2],[-1,20,20,1]), max_outputs=3, family="unpool1")
        tf.summary.image("channel4", tf.slice(unpool_1, [0,0,0,3],[-1,20,20,1]), max_outputs=3, family="unpool1")
        # deconv_2, output shape: 20X20X512
        deconv_2 = slim.repeat(unpool_1, 3, slim.conv2d_transpose, 512, [3, 3], scope='deconv2',
            weights_initializer=initializers.xavier_initializer(uniform=False), biases_initializer=None,
            variables_collections=self.variables_collections)
        tf.summary.image("channel1", tf.slice(deconv_2, [0,0,0,0],[-1,20,20,1]), max_outputs=3, family="deconv2")
        tf.summary.image("channel2", tf.slice(deconv_2, [0,0,0,1],[-1,20,20,1]), max_outputs=3, family="deconv2")
        tf.summary.image("channel3", tf.slice(deconv_2, [0,0,0,2],[-1,20,20,1]), max_outputs=3, family="deconv2")
        tf.summary.image("channel4", tf.slice(deconv_2, [0,0,0,3],[-1,20,20,1]), max_outputs=3, family="deconv2")
        # unpool_2, output shape: 40X40X512
        unpool_2 = unpool(deconv_2, argmax[3], shape=[-1,40,40,512], scope='unpool2')
        tf.summary.image("channel1", tf.slice(unpool_2, [0,0,0,0],[-1,40,40,1]), max_outputs=3, family="unpool2")
        tf.summary.image("channel2", tf.slice(unpool_2, [0,0,0,1],[-1,40,40,1]), max_outputs=3, family="unpool2")
        tf.summary.image("channel3", tf.slice(unpool_2, [0,0,0,2],[-1,40,40,1]), max_outputs=3, family="unpool2")
        tf.summary.image("channel4", tf.slice(unpool_2, [0,0,0,3],[-1,40,40,1]), max_outputs=3, family="unpool2")
        # deconv_3, output shape: 40X40x256
        deconv_3 = slim.repeat(unpool_2, 3, slim.conv2d_transpose, 256, [3, 3], scope='deconv3',
            weights_initializer=initializers.xavier_initializer(uniform=False), biases_initializer=None,
            variables_collections=self.variables_collections)
        tf.summary.image("channel1", tf.slice(deconv_3, [0,0,0,0],[-1,40,40,1]), max_outputs=3, family="deconv3")
        tf.summary.image("channel2", tf.slice(deconv_3, [0,0,0,1],[-1,40,40,1]), max_outputs=3, family="deconv3")
        tf.summary.image("channel3", tf.slice(deconv_3, [0,0,0,2],[-1,40,40,1]), max_outputs=3, family="deconv3")
        tf.summary.image("channel4", tf.slice(deconv_3, [0,0,0,3],[-1,40,40,1]), max_outputs=3, family="deconv3")
        # unpool_3, output shape: 80X80X256
        unpool_3 = unpool(deconv_3, argmax[2],shape=[-1,80,80,256], scope='unpool3')
        tf.summary.image("channel1", tf.slice(unpool_3, [0,0,0,0],[-1,80,80,1]), max_outputs=3, family="unpool3")
        tf.summary.image("channel2", tf.slice(unpool_3, [0,0,0,1],[-1,80,80,1]), max_outputs=3, family="unpool3")
        tf.summary.image("channel3", tf.slice(unpool_3, [0,0,0,2],[-1,80,80,1]), max_outputs=3, family="unpool3")
        tf.summary.image("channel4", tf.slice(unpool_3, [0,0,0,3],[-1,80,80,1]), max_outputs=3, family="unpool3")
        # deconv_4, output shape: 80X80X128
        deconv_4 = slim.repeat(unpool_3, 2, slim.conv2d_transpose, 128, [3, 3], scope='deconv4',
            weights_initializer=initializers.xavier_initializer(uniform=False), biases_initializer=None,
            variables_collections=self.variables_collections)
        tf.summary.image("channel1", tf.slice(deconv_4, [0,0,0,0],[-1,80,80,1]), max_outputs=3, family="deconv4")
        tf.summary.image("channel2", tf.slice(deconv_4, [0,0,0,1],[-1,80,80,1]), max_outputs=3, family="deconv4")
        tf.summary.image("channel3", tf.slice(deconv_4, [0,0,0,2],[-1,80,80,1]), max_outputs=3, family="deconv4")
        tf.summary.image("channel4", tf.slice(deconv_4, [0,0,0,3],[-1,80,80,1]), max_outputs=3, family="deconv4")
        # unpool_4, output shape: 160X160X128
        unpool_4 = unpool(deconv_4, argmax[1], shape=[-1,160,160,128], scope='unpool4')
        tf.summary.image("channel1", tf.slice(unpool_4, [0,0,0,0],[-1,160,160,1]), max_outputs=3, family="unpool4")
        tf.summary.image("channel2", tf.slice(unpool_4, [0,0,0,1],[-1,160,160,1]), max_outputs=3, family="unpool4")
        tf.summary.image("channel3", tf.slice(unpool_4, [0,0,0,2],[-1,160,160,1]), max_outputs=3, family="unpool4")
        tf.summary.image("channel4", tf.slice(unpool_4, [0,0,0,3],[-1,160,160,1]), max_outputs=3, family="unpool4")
        # deconv_5, output shape: 160X160X64
        deconv_5 = slim.repeat(unpool_4, 2, slim.conv2d_transpose, 64, [3, 3], scope='deconv5',
            weights_initializer=initializers.xavier_initializer(uniform=False), biases_initializer=None,
            variables_collections=self.variables_collections)
        tf.summary.image("channel1", tf.slice(deconv_5, [0,0,0,0],[-1,160,160,1]), max_outputs=3, family="deconv5")
        tf.summary.image("channel2", tf.slice(deconv_5, [0,0,0,1],[-1,160,160,1]), max_outputs=3, family="deconv5")
        tf.summary.image("channel3", tf.slice(deconv_5, [0,0,0,2],[-1,160,160,1]), max_outputs=3, family="deconv5")
        tf.summary.image("channel4", tf.slice(deconv_5, [0,0,0,3],[-1,160,160,1]), max_outputs=3, family="deconv5")
        # unpool_5, output shape: 320X320X64
        unpool_5 = unpool(deconv_5, argmax[0],shape=[-1,320,320,64], scope='unpool5')
        tf.summary.image("channel1", tf.slice(unpool_5, [0,0,0,0],[-1,320,320,1]), max_outputs=3, family="unpool5")
        tf.summary.image("channel2", tf.slice(unpool_5, [0,0,0,1],[-1,320,320,1]), max_outputs=3, family="unpool5")
        tf.summary.image("channel3", tf.slice(unpool_5, [0,0,0,2],[-1,320,320,1]), max_outputs=3, family="unpool5")
        tf.summary.image("channel4", tf.slice(unpool_5, [0,0,0,3],[-1,320,320,1]), max_outputs=3, family="unpool5")
        # conv, output shape: 320X320X2
        conv = slim.conv2d(unpool_5, 64, [3,3], scope='conv1', biases_initializer=None,
            weights_initializer=initializers.xavier_initializer(uniform=False),
            variables_collections=self.variables_collections)
        # conv = slim.dropout(conv, keep_prob=0.8, is_training=self.is_training, scope='dropout1')
        conv = slim.conv2d(conv, 2, [3, 3], scope='conv2', biases_initializer=None,
            weights_initializer=initializers.xavier_initializer(uniform=False),
            variables_collections=self.variables_collections)
        # conv = slim.dropout(conv, keep_prob=0.8, is_training=self.is_training, scope='dropout2')
        conv_1 = tf.slice(conv, [0,0,0,0], [-1,self.image_height, self.image_height, 1])
        conv_2 = tf.slice(conv, [0,0,0,1], [-1,self.image_height, self.image_height, 1])
        tf.summary.image("channel1", conv_1, max_outputs=3, family="conv")
        tf.summary.image("channel2", conv_1, max_outputs=3, family="conv")
        # final result
        with tf.name_scope("result"):
            output = tf.nn.softmax(conv)
            pred = tf.expand_dims(tf.argmax(output, axis=3), axis=3)
            result = 255 * tf.cast(pred, tf.uint8)
            tf.summary.image("segmentation", result, max_outputs=3)
        self.logits = conv
        self.output = output
        weights = ops.get_collection("weights")
        for weight in weights:
            L = weight.name.split('/')
            name = L[-2] + '/' + L[-1]
            family = L[0]
            tf.summary.histogram(name=name, values=weight, family=family)

    def build_loss(self):
        with tf.name_scope("evaluation"):
            self.cross_entropy = tf.reduce_mean(tf.nn.sparse_softmax_cross_entropy_with_logits(
                    labels = self.gt, logits = self.logits))
            tf.summary.scalar("loss", self.cross_entropy)

    def build_optimizer(self):
        with tf.name_scope('training_op'):
            optimizer = tf.train.AdamOptimizer(learning_rate = self.learning_rate)
            self.train_step = optimizer.minimize(self.cross_entropy)

    def build_summary(self):
        self.summary = tf.summary.merge_all()

    def train(self):
        img_size = [self.image_height, self.image_width, self.image_depth]
        train_batch = tf.train.shuffle_batch([read_tfrecord(self.train_file, img_size)],
                    batch_size = self.train_batch_size,
                    capacity = 2000,
                    num_threads = 2,
                    min_after_dequeue = 1000)
        test_batch = tf.train.shuffle_batch([read_tfrecord(self.test_file, img_size)],
                    batch_size = self.test_batch_size,
                    capacity = 500,
                    num_threads = 2,
                    min_after_dequeue = 300)
        init = tf.global_variables_initializer()
        init_fn = slim.assign_from_checkpoint_fn("vgg_16.ckpt", slim.get_model_variables('vgg_16'))
        saver = tf.train.Saver()
        with tf.Session() as sess:
            sess.run(init)
            init_fn(sess)
            train_writer = tf.summary.FileWriter(self.log_dir + "/train", sess.graph)
            test_writer  = tf.summary.FileWriter(self.log_dir + "/test", sess.graph)
            coord = tf.train.Coordinator()
            threads = tf.train.start_queue_runners(sess=sess, coord=coord)
            inputs_test, outputs_gt_test = build_img_pair(sess.run(test_batch), mode='softmax')
            for iter in range(self.max_iteration):
                inputs_train, outputs_gt_train = build_img_pair(sess.run(train_batch), mode='softmax')
                # train with dynamic learning rate
                if iter <= 500:
                    self.train_step.run({self.input_data:inputs_train, self.gt:outputs_gt_train, self.learning_rate:1e-4})
                elif iter <= self.max_iteration - 1000:
                    self.train_step.run({self.input_data:inputs_train, self.gt:outputs_gt_train, self.learning_rate:0.5e-4})
                else:
                    self.train_step.run({self.input_data:inputs_train, self.gt:outputs_gt_train, self.learning_rate:1e-5})
                # print training loss and test loss
                if iter%10 == 0:
                    summary_train = sess.run(self.summary, {self.input_data:inputs_train, self.gt:outputs_gt_train})
                    train_writer.add_summary(summary_train, iter)
                    train_writer.flush()
                    summary_test = sess.run(self.summary, {self.input_data:inputs_test, self.gt:outputs_gt_test})
                    test_writer.add_summary(summary_test, iter)
                    test_writer.flush()
                # record training loss and test loss
                if iter%10 == 0:
                    train_loss  = self.cross_entropy.eval({self.input_data:inputs_train, self.gt:outputs_gt_train})
                    test_loss   = self.cross_entropy.eval({self.input_data:inputs_test, self.gt:outputs_gt_test})
                    print("iter step %d trainning batch loss %f"%(iter, train_loss))
                    print("iter step %d test loss %f\n"%(iter, test_loss))
                # record model
                if iter%100 == 0:
                    saver.save(sess, self.log_dir + "/model.ckpt", global_step=iter)
            coord.request_stop()
            coord.join(threads)
