"""
Mask R-CNN
Configurations and data loading code for the synthetic Shapes dataset.
This is a duplicate of the code in the noteobook train_shapes.ipynb for easy
import into other notebooks, such as inspect_model.ipynb.

Copyright (c) 2017 Matterport, Inc.
Licensed under the MIT License (see LICENSE for details)
Written by Waleed Abdulla
"""

import numpy as np, cv2, os
from maskrcnn.config import Config
from tqdm import tqdm
import maskrcnn.utils as utils

# Structure of data from Jeff.
# depth_ims: image_{:06d}.png
# gray_ims: image_{:06d}.png
# occluded_segmasks: image_{:06d}_channel_{:03d}.png
# semantic_segmasks: image_{:06d}
# unoccluded_segmasks: image_{:06d}_channel_{:03d}.png
# splits/fold_{:02d}/{train,test}_indices.npy

base_dir = '/nfs/diskstation/projects/dex-net/segmentation/datasets/pile_segmasks_01_28_18'

class ClutterConfig(Config):
  """Configuration for training on the toy shapes dataset.
  Derives from the base Config class and overrides values specific
  to the toy shapes dataset.
  """
  # Give the configuration a recognizable name
  NAME = "clutter"

  # Train on 1 GPU and 8 images per GPU. We can put multiple images on each
  # GPU because the images are small. Batch size is 8 (GPUs * images/GPU).
  GPU_COUNT = 1
  IMAGES_PER_GPU = 2

  # Number of classes (including background)
  NUM_CLASSES = 1 + 1  # background + 3 shapes

  # Use small images for faster training. Set the limits of the small side
  # the large side, and that determines the image shape.
  IMAGE_MIN_DIM = 512
  IMAGE_MAX_DIM = 512

  # Use smaller anchors because our image and objects are small
  RPN_ANCHOR_SCALES = (8, 16, 32, 64, 128)  # anchor side in pixels

  # Reduce training ROIs per image because the images are small and have
  # few objects. Aim to allow ROI sampling to pick 33% positive ROIs.
  TRAIN_ROIS_PER_IMAGE = 32

  # Use a small epoch since the data is simple
  STEPS_PER_EPOCH = 10000/IMAGES_PER_GPU

  # use small validation steps since the epoch is small
  VALIDATION_STEPS = 50

  DETECTION_MIN_CONFIDENCE = 0.4

  def __init__(self, mean):
    # Overriding things here.
    super(ClutterConfig, self).__init__()
    self.IMAGE_SHAPE[2] = 3
    self.MEAN_PIXEL = np.array([mean, mean, mean])

class ClutterDataset(utils.Dataset):
  """Generates the shapes synthetic dataset. The dataset consists of simple
  shapes (triangles, squares, circles) placed randomly on a blank surface.
  The images are generated on the fly. No file access required.
  """
  def load(self, imset, typ='depth', fold=0):
    # Load the indices for imset.
    self.base_path = os.path.join('/nfs/diskstation/projects/dex-net/segmentation/datasets/pile_segmasks_01_28_18')
    split_file = os.path.join(self.base_path, 'splits',
      'fold_{:02d}'.format(fold), '{:s}_indices.npy'.format(imset))
    self.image_id = np.load(split_file)

    self.add_class('clutter', 1, 'fg')
    flips = [0, 1, 2, 3] if imset == 'train' else [0]

    count = 0

    for i in self.image_id:
      p = os.path.join(self.base_path, '{:s}_ims'.format(typ),
        'image_{:06d}.png'.format(i))
      count += 1

      for flip in flips:
        self.add_image('clutter', image_id=i, path=p, width=256, height=256, flip=flip)

  def flip(self, image, flip):
    if flip == 0:
      image = image
    elif flip == 1:
      image = image[::-1,:,:]
    elif flip == 2:
      image = image[:,::-1,:]
    elif flip == 3:
      image = image[::-1,::-1,:]
    return image

  def load_image(self, image_id):
    """Generate an image from the specs of the given image ID.
    Typically this function loads the image from a file, but
    in this case it generates the image on the fly from the
    specs in image_info.
    """
    info = self.image_info[image_id]

    # modify path- depth_ims to depth_ims_resized

    # image = cv2.imread(info['path'].replace('depth_ims', 'depth_ims_resized'), cv2.IMREAD_UNCHANGED)
    image = cv2.imread(info['path'])
    return image
    assert(image is not None)
    if image.ndim == 2: image = np.tile(image[:,:,np.newaxis], [1,1,3])
    image = self.flip(image, info['flip'])
    return image

  def image_reference(self, image_id):
    """Return the shapes data of the image."""
    info = self.image_info[image_id]
    if info["source"] == "clutter":
      return info["path"] + "-{:d}".format(info["flip"])
    else:
      super(self.__class__).image_reference(self, image_id)

  def load_mask(self, image_id):
    """Generate instance masks for shapes of the given image ID.
    """
    info = self.image_info[image_id]
    _image_id = info['id']
    Is = []
    file_name = os.path.join(self.base_path, 'modal_segmasks_project_resized',
      'image_{:06d}.png'.format(_image_id))

    all_masks = cv2.imread(file_name, cv2.IMREAD_UNCHANGED)

    for i in range(25):
      # file_name = os.path.join(self.base_path, 'occluded_segmasks',
      #   'image_{:06d}_channel_{:03d}.png'.format(_image_id, i))
      # I = cv2.imread(file_name, cv2.IMREAD_UNCHANGED) > 0
      I = all_masks == i+1
      if np.any(I):
        I = I[:,:,np.newaxis]
        Is.append(I)
    if len(Is) > 0: mask = np.concatenate(Is, 2)
    else: mask = np.zeros([info['height'], info['width'], 0], dtype=np.bool)
    # Making sure masks are always contiguous.
    # block = np.any(np.any(mask,0),0)
    # assert((not np.any(block)) or (not np.any(block[np.where(block)[0][-1]+1:])))
    # print(block)
    mask = self.flip(mask, info['flip'])
    class_ids = np.array([1 for _ in range(mask.shape[2])])
    return mask, class_ids.astype(np.int32)

def test_clutter_dataset():
  clutter_dataset = ClutterDataset()
  # clutter_dataset.load('train', 'gray')
  clutter_dataset.load('test', 'depth')
  clutter_dataset.prepare()
  image_ids = clutter_dataset.image_ids
  Is = []
  for i in tqdm(image_ids):
    I = clutter_dataset.load_image(i)
    clutter_dataset.load_mask(i)
    Is.append(I)
  print(np.mean(np.array(Is)))

def concat_segmasks():
  print("CONCATENATING SEGMASKS")
  bads = []
  for i in tqdm(range(10000)):
    Is = []
    masks = np.zeros((150, 200), dtype=np.uint8)
    for j in range(21):
      file_name = os.path.join(base_dir, 'modal_segmasks',
        'image_{:06d}_channel_{:03d}.png'.format(i, j))

      im = cv2.imread(file_name, cv2.IMREAD_UNCHANGED)
      if im is not None:
        I = im > 0
        masks[I] = j+1
        I = I[:,:,np.newaxis]; Is.append(I)
    Is = np.concatenate(Is, 2)
    Is = Is*1
    file_name = os.path.join(base_dir, 'modal_segmasks_project',
      'image_{:06d}.png'.format(i))
    cv2.imwrite(file_name, masks)
    bads.append(len(np.where(np.sum(Is,2) > 1)[0]))
  print(bads)

def resize_images(max_dim=512):
  """Resizes all images so their maximum dimension is 512. Saves to new directory."""
  print("RESIZING IMAGES")
  dirs = ['depth_ims', 'modal_segmasks_project' ] # directories of images that need resizing
  resized_dirs = [d + '_resized' for d in dirs]
  for d in resized_dirs:
    # create new dirs for resized images
    if not os.path.exists(os.path.join(base_dir, d)):
      os.makedirs(os.path.join(base_dir, d))
  print dirs, resized_dirs
  for d, r_d in zip(dirs[1:], resized_dirs[1:]):
    old_path = os.path.join(base_dir, d)
    new_path = os.path.join(base_dir, r_d)
    for im_path in os.listdir(old_path):
      im_old_path = os.path.join(old_path, im_path)
      im = cv2.imread(im_old_path, cv2.IMREAD_UNCHANGED)
      scale = 512.0 / min(im.shape) # scale so max dimension is 512
      scale_dim = tuple([int(d * scale) for d in im.shape[:2]])
      im = cv2.resize(im, scale_dim, interpolation=cv2.INTER_NEAREST)
      y_margin = (im.shape[1] - 512) // 2
      x_margin = (im.shape[0] - 512) // 2
      im = im[y_margin : im.shape[1] - y_margin, x_margin : im.shape[0] - x_margin]
      im_new_path = os.path.join(new_path, im_path)
      cv2.imwrite(im_new_path, im)

if __name__ == '__main__':
  # test_clutter_dataset()
  # concat_segmasks()
  resize_images()
  # test_display_images()
