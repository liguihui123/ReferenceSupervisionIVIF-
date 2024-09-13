# -*- coding: utf-8 -*-
"""
Scipy version > 0.18 is needed, due to 'mode' option from scipy.misc.imread function
"""





import os
import glob
import h5py
import random
import matplotlib.pyplot as plt

from PIL import Image  # for loading images as YCbCr format
import scipy.misc
import scipy.ndimage
import numpy as np
import tensorflow.compat.v1 as tf
from scipy.misc import imread, imsave, imresize
import cv2


def read_data(path):
  """
  Read h5 format data file
  
  Args:
    path: file path of desired file
    data: '.h5' file format that contains train data values
    label: '.h5' file format that contains train label values
  """
  with h5py.File(path, 'r') as hf:
    data = np.array(hf.get('data'))
    weight = np.array(hf.get('weight'))
    return data,weight

def preprocess(path, scale=3):
  """
  Preprocess single image file 
    (1) Read original image as YCbCr format (and grayscale as default)
    (2) Normalize
    (3) Apply image file with bicubic interpolation

  Args:
    path: file path of desired file
    input_: image applied bicubic interpolation (low-resolution)
    label_: image with original resolution (high-resolution)
  """

  image = imread(path, is_grayscale=True)
  image = (image)/255 
  input_ = scipy.ndimage.interpolation.zoom(input_, (scale/1.), prefilter=False)
  return input_

def read_txt(txt_path):
    data = []
    weight = []
    lines = []
    for line in open(txt_path, "r"): 
        lines.append(line)

    for line in lines:  
        line = line.strip('\n')
        line1,line2 = line.split(',')
        data.append(line1)
        lin2_new = np.reshape(float(line2), [1, 1, 1])
        weight.append(lin2_new)
    return data, weight
  
def prepare_data(args, dataset):
  """
  Args:
    dataset: choose train dataset or test dataset
    
    For train dataset, output data would be ['.../t1.bmp', '.../t2.bmp', ..., '.../t99.bmp']
  """
  data, weight = read_txt(dataset) 
  return data, weight

def make_data(args, data,weight,data_dir,check_path):
  """
  Make input data as h5 file format
  Depending on 'is_train' (flag value), savepath would be changed.
  """
  print(os.path.join(check_path,data_dir,'train.h5'))
  savepath = os.path.join('.', os.path.join(check_path,data_dir,'train.h5'))
  if not os.path.exists(os.path.join('.',os.path.join(check_path,data_dir))):
      os.makedirs(os.path.join('.',os.path.join(check_path,data_dir)))
 
  with h5py.File(savepath, 'w') as hf:
    hf.create_dataset('data', data=data)
    hf.create_dataset('weight', data=weight)

def imread(path, is_grayscale=True):
  """
  Read image using its path.
  Default value is gray-scale, and image is read by YCbCr format as the paper said.
  """
  if is_grayscale:
    #flatten=True
    return scipy.misc.imread(path, flatten=True, mode='L').astype(np.float)
  else:
    return scipy.misc.imread(path, mode='YCbCr').astype(np.float)

def modcrop(image, scale=3):
  """
  To scale down and up the original image, first thing to do is to have no remainder while scaling operation.
  
  We need to find modulo of height (and width) and scale factor.
  Then, subtract the modulo from height (and width) of original image size.
  There would be no remainder even after scaling operation.
  """
  if len(image.shape) == 3:
    h, w, _ = image.shape
    h = h - np.mod(h, scale)
    w = w - np.mod(w, scale)
    image = image[0:h, 0:w, :]
  else:
    h, w = image.shape
    h = h - np.mod(h, scale)
    w = w - np.mod(w, scale)
    image = image[0:h, 0:w]
  return image

def input_setup(args,data_path,data_dir,check_path,index=0):
  """
  Read image files and make their sub-images and saved them as a h5 file format.
  """
  # Load data path
  data, weight = prepare_data(args, dataset = data_path + data_dir)
  sub_input_sequence = []
  weight_patch = []
  padding = abs(args.image_size) / 2 # 6
  data_dir1 = data_dir.split('.')
  print(data_dir1[0])
  path = data_path+(data_dir1[0])+'/'
  for i in range(len(data)):
    weight1 = weight[i]
    input_ = (imread(path + data[i]))/255
    label_ = input_
    if len(input_.shape) == 3:
      h, w, _ = input_.shape
    else:
      h, w = input_.shape
        
      for x in range(0, h-args.image_size+1, 256):
        for y in range(0, w-args.image_size+1,256):
          sub_input = input_[x:x+args.image_size, y:y+args.image_size] # [33 x 33]  
          padding = int(padding)       
          sub_label = label_[x+padding:x+padding+120, y+padding:y+padding+120] # [21 x 21]
          sub_input=cv2.resize(input_, (args.image_size,args.image_size),interpolation=cv2.INTER_CUBIC)
          sub_input = sub_input.reshape([args.image_size, args.image_size, 1])
          sub_label=cv2.resize(label_, (120,120),interpolation=cv2.INTER_CUBIC)
          sub_label = sub_label.reshape([120, 120, 1])
          weight_tmp=weight1*len(sub_input)
          weight_patch.append(weight_tmp)
          sub_input_sequence.append(sub_input)

  """
  len(sub_input_sequence) : the number of sub_input (33 x 33 x ch) in one image
  (sub_input_sequence[0]).shape : (33, 33, 1)
  """
  # Make list to numpy array. With this transform
  arrdata = np.asarray(sub_input_sequence) # [?, 33, 33, 1]
  # arrlabel = np.asarray(sub_label_sequence) # [?, 21, 21, 1]
  arrweight = np.asarray(weight_patch)
  data_dir1=data_dir.split('.')
  make_data(args, arrdata,arrweight,data_dir1[0],check_path)
  
def imsave(image, path):
      return scipy.misc.imsave(path, image)

def merge(images, size):
  h, w = images.shape[1], images.shape[2]
  img = np.zeros((h*size[0], w*size[1], 1))
  for idx, image in enumerate(images):
    i = idx % size[1]
    j = idx // size[1]
    img[j*h:j*h+h, i*w:i*w+w, :] = image

  return (img*255)
  
def gradient(input):
    filter=tf.reshape(tf.constant([[0.,1.,0.],[1.,-4.,1.],[0.,1.,0.]]),[3,3,1,1])
    d=tf.nn.conv2d(input,filter,strides=[1,1,1,1], padding='SAME')
    return d
    
def weights_spectral_norm(weights, u=None, iteration=1, update_collection=None, reuse=False, name='weights_SN'):
    with tf.variable_scope(name) as scope:
        if reuse:
            scope.reuse_variables()
        w_shape = weights.get_shape().as_list()
        w_mat = tf.reshape(weights, [-1, w_shape[-1]])
        if u is None:
            u = tf.get_variable('u', shape=[1, w_shape[-1]], initializer=tf.truncated_normal_initializer(), trainable=False)
        def power_iteration(u, ite):
            v_ = tf.matmul(u, tf.transpose(w_mat))
            v_hat = l2_norm(v_)
            u_ = tf.matmul(v_hat, w_mat)
            u_hat = l2_norm(u_)
            return u_hat, v_hat, ite+1        
        u_hat, v_hat,_ = power_iteration(u,iteration)        
        sigma = tf.matmul(tf.matmul(v_hat, w_mat), tf.transpose(u_hat))        
        w_mat = w_mat/sigma
        
        if update_collection is None:
            with tf.control_dependencies([u.assign(u_hat)]):
                w_norm = tf.reshape(w_mat, w_shape)
        else:
            if not(update_collection == 'NO_OPS'):
                print(update_collection)
                tf.add_to_collection(update_collection, u.assign(u_hat))
            
            w_norm = tf.reshape(w_mat, w_shape)
        return w_norm
    
def lrelu(x, leak=0.2):
    return tf.maximum(x, leak * x)
    
def l2_norm(input_x, epsilon=1e-12):
    input_x_norm = input_x/(tf.reduce_sum(input_x**2)**0.5 + epsilon)
    return input_x_norm
