import numpy as np
from rigaku_3M_handler import Rigaku3MDataset
import matplotlib.pyplot as plt
import skimage.io as skio

def main_example():
    shape = (1676, 2100)
    # prepare blemish file
    mask = skio.imread('rigaku3m_blemish.tiff')

    # prepare dataset
    batch_size = 1000   # number of frames per batch, since there are so many
                        # frames in each dataset
    fname = "../E0139_dohedode3_a0050_f100000_t120C_r00195/E0139_dohedode3_a0050_f100000_t120C_r00195.bin.000"
    dset = Rigaku3MDataset(fname, batch_size=1000)

    frame_sum = 0
    # read data
    for idx in range(dset.batch_num):
        frame = dset[idx].reshape(batch_size, *shape)
        print(idx, frame.shape)
        frame_sum += frame.sum(axis=0)
        # if idx == 10:
        #     break
    
    frame_sum = frame_sum * mask 
    plt.imshow(np.log10(frame_sum + 1))
    plt.show()
    
    
if __name__ == '__main__':
    main_example()