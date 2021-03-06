# pylint: disable=invalid-name

from __future__ import absolute_import
#from tensorflow.keras.applications import Res # TensorFlow ONLY

import numpy as np
import tensorflow as tf


def var_random(name, shape, regularizable=False):
    '''
    Initialize a random variable using xavier initialization.
    Add regularization if regularizable=True
    :param name:
    :param shape:
    :param regularizable:
    :return:
    '''
    v = tf.get_variable(name, shape=shape, initializer=tf.contrib.layers.xavier_initializer())
    if regularizable:
        with tf.name_scope(name + '/Regularizer/'):
            tf.add_to_collection(tf.GraphKeys.REGULARIZATION_LOSSES, tf.nn.l2_loss(v))
    return v


def max_2x2pool(incoming, name):
    '''
    max pooling on 2 dims.
    :param incoming:
    :param name:
    :return:
    '''
    with tf.variable_scope(name):
        return tf.nn.max_pool(incoming, ksize=(1, 2, 2, 1), strides=(1, 2, 2, 1), padding='SAME')


def max_2x1pool(incoming, name):
    '''
    max pooling only on image width
    :param incoming:
    :param name:
    :return:
    '''
    with tf.variable_scope(name):
        return tf.nn.max_pool(incoming, ksize=(1, 2, 1, 1), strides=(1, 2, 1, 1), padding='SAME')


def ConvRelu(incoming, num_filters, filter_size, name):
    '''
    Add a convolution layer followed by a Relu layer.
    :param incoming:
    :param num_filters:
    :param filter_size:
    :param name:
    :return:
    '''
    num_filters_from = incoming.get_shape().as_list()[3]
    with tf.variable_scope(name):
        conv_W = var_random(
            'W',
            tuple(filter_size) + (num_filters_from, num_filters),
            regularizable=True
        )

        after_conv = tf.nn.conv2d(incoming, conv_W, strides=(1, 1, 1, 1), padding='SAME')

        return tf.nn.relu(after_conv)


def batch_norm(incoming, is_training):
    '''
    batch normalization
    :param incoming:
    :param is_training:
    :return:
    '''
    return tf.contrib.layers.batch_norm(incoming, is_training=is_training, scale=True, decay=0.99)


def ConvReluBN(incoming, num_filters, filter_size, name, is_training):
    '''
    Convolution -> Batch normalization -> Relu
    :param incoming:
    :param num_filters:
    :param filter_size:
    :param name:
    :param is_training:
    :return:
    '''
    num_filters_from = incoming.get_shape().as_list()[3]
    with tf.variable_scope(name):
        conv_W = var_random(
            'W',
            tuple(filter_size) + (num_filters_from, num_filters),
            regularizable=True
        )

        after_conv = tf.nn.conv2d(incoming, conv_W, strides=(1, 1, 1, 1), padding='SAME')

        after_bn = batch_norm(after_conv, is_training)

        return tf.nn.relu(after_bn)

#_______________________________________Change: Create residual Block________________________________
def residual_block(incoming, num_filters, filter_size, name = 'residual'):
    
    """Create a Residual Block with 2 Conv layers"""
    
    # num_filters_from = input_channels
    # outchannels = num_filters
    
    #num_filters_from = incoming.get_shape().as_list()[3]
    input_channels = int(incoming.get_shape()[-1])
    
    conv1 = ConvReluBN(incoming, num_filters, filter_size, name = '{}_conv1'.format(name), is training)
    conv2 = ConvReluBN(conv1, num_filters, filter_size, name = '{}_conv2'.format(name), is training)
    
    if input_channels != num_filters:
        # Identity mapping with Zero-Padding
        # This method doesn't introduce extar parameters.
        shortcut = tf.pad(incoming, [[0, 0], [0, 0], [0, 0], [0, num_filters - input_channels]])
    else:
        # Identity mapping.
        shortcut = x
    
    # Element wise addition.
    out = conv2 + shortcut
    
    return out
#_______________________________________________________________________________________________________         
    


    
def dropout(incoming, is_training, keep_prob=0.5):
    return tf.contrib.layers.dropout(incoming, keep_prob=keep_prob, is_training=is_training)


def tf_create_attention_map(incoming):
    '''
    flatten hight and width into one dimention of size attn_length
    :param incoming: 3D Tensor [batch_size x cur_h x cur_w x num_channels]
    :return: attention_map: 3D Tensor [batch_size x attn_length x attn_size].
    '''
    shape = incoming.get_shape().as_list()
    return tf.reshape(incoming, (-1, np.prod(shape[1:3]), shape[3]))



class CNN(object):
    """
    Usage for tf tensor output:
    o = CNN(x).tf_output()

    """

    def __init__(self, input_tensor, is_training):
        self._build_network(input_tensor, is_training)
        #_____________________________Change for ResNet______________________
        self.NUM_CONV = 3

    def _build_network(self, input_tensor, is_training):
        """
        https://github.com/bgshih/crnn/blob/master/model/crnn_demo/config.lua
        :return:
        """
        net = tf.add(input_tensor, (-128.0))
        net = tf.multiply(net, (1/128.0))
        
        #________________________________________________Keras ResNet Transfer Learning_________________________________
        base_model = tf.keras.applications.ResNet50V2(
            weights='imagenet',  # Load weights pre-trained on ImageNet.
            input_shape=incoming.get_shape(),
            include_top=False)  # Do not include the ImageNet classifier at the top.

        base_model.trainable = False
        
        net = base_model(net, training=False)
        
        #_______________________________________________________________________________________________________

        
        net = ConvReluBN(net, 512, (3, 3), 'conv_conv5', is_training)
        net = ConvRelu(net, 512, (3, 3), 'conv_conv6')
        net = max_2x1pool(net, 'conv_pool4')
        
        net = ConvReluBN(net, 1024, (2, 2), 'conv_conv7', is_training)
        net = max_2x1pool(net, 'conv_pool5')
        net = dropout(net, is_training)


        net = tf.squeeze(net, axis=1)

        self.model = net

    def tf_output(self):
        # if self.input_tensor is not None:
        return self.model

    # def __call__(self, input_tensor):
    #     return self.model(input_tensor)

    def save(self):
        pass
