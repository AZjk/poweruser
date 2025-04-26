import numpy as np
from rigaku_handler import RigakuDataset
import matplotlib.pyplot as plt
import skimage.io as skio
from tqdm import trange

def main_example():
    shape = (512, 1024)
    # prepare blemish file
    # mask = skio.imread('rigaku3m_blemish.tiff')

    # prepare dataset
    batch_size = 1000   # number of frames per batch, since there are so many
                        # frames in each dataset
    fname = "A029_AgNO3_2ml_TEOS_20ml_025C_att00_Rq0_00001.bin"
    dset = RigakuDataset(fname, batch_size=batch_size)
    frame_sum = 0
    # read data
    for idx in trange(dset.batch_num):
        batch = dset[idx].reshape(batch_size, *shape)
        # each batch has 1000 2D 2D frames
        frame_sum += batch.sum(axis=0)
        # if idx == 10:
        #     break
    
    # frame_sum = frame_sum * mask 
    plt.imshow(np.log10(frame_sum + 1))
    plt.show()
    
    
if __name__ == '__main__':
    main_example()