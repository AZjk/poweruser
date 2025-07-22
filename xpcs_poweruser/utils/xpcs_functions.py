
def Read_Frames_8IDI_Rigaku(full_path_fn,det_size):

    import numpy as np
    import scipy as sp
    from scipy.sparse import csr_matrix

    with open(full_path_fn, 'r') as f:
        a = np.fromfile(f, dtype=np.uint64)

    b = (a >> 5+11)
    pix_ind = (b & 2**21-1).astype(int)
    pix_count = (a & 2**12-1).astype(int)
    pix_frame = (a >> 64-24).astype(int)

    img = csr_matrix((pix_count, (pix_frame, pix_ind)), shape=(max(pix_frame)+1, det_size[0]*det_size[1]), dtype='float')
    return img


def Muititau_Corr(img,dpl):

    import numpy as np 
    import scipy as sp
    import math
    from scipy.sparse import csr_matrix

    [num_frame,num_pixel]=img.shape

    multitau_length_lim = (int(math.log(num_frame,2))+1)*dpl

    G2 = np.zeros([multitau_length_lim,num_pixel])
    IP = np.zeros([multitau_length_lim,num_pixel])
    IF = np.zeros([multitau_length_lim,num_pixel])
    t_el = np.zeros([multitau_length_lim])

    
    for ii in range(dpl):

        delay_orig = ii+1        
        print ("MultiTau Spacing %2i with %7i Total Number of Frames" %(delay_orig,num_frame))

        G2[ii,:] = csr_matrix.multiply(img[delay_orig:,:],img[:-delay_orig,:]).mean(axis=0)     
        IP[ii,:] = (img[delay_orig:,:]).mean(axis=0)
        IF[ii,:] = (img[:-delay_orig,:]).mean(axis=0)  
        t_el[ii] = delay_orig

    level = 0         
    img_bin = img

    count = dpl

    while True:
        for kk in range(dpl):

            delay_bin = kk+dpl+1            
            delay_orig = 2**level*delay_bin
            print ("MultiTau Spacing %2i with %7i Total Number of Frames" %(delay_orig,img.shape[0]))

            if delay_bin >= img_bin.shape[0]:
                G2 = G2[:count,:]
                IP = IP[:count,:]
                IF = IF[:count,:]
                t_el = t_el[:count]
                return G2,IP,IF,t_el
            else:
                G2[count,:] = csr_matrix.multiply(img_bin[delay_bin:,:],img_bin[:-delay_bin,:]).mean(axis=0)  
                IP[count,:] = img_bin[delay_bin:,:].mean(axis=0)
                IF[count,:] = img_bin[:-delay_bin,:].mean(axis=0) 
                t_el[count] = delay_orig

                count = count + 1

        even_end = 2*int(img_bin.shape[0]/2)
        img_bin = img_bin[:even_end,:]               
        index_even = np.where(np.arange(0,even_end)%2)[0]
        index_odd = np.where(np.arange(1,even_end+1)%2)[0]       
        img_bin = (img_bin[index_even,:]+img_bin[index_odd,:])/2
        
        level = level +1


def Read_Qmap_8IDI(full_path_fn):

    import h5py

    with h5py.File(full_path_fn, 'r') as f:

        qmap_dyn = f.get('/data/dynamicMap')[()]
        qmap_sta = f.get('/data/staticMap')[()]
        ql_sta = f.get('/data/sqval')[()]
        ql_dyn = f.get('data/dqval')[()]
        mask = f.get('data/mask')[()]

    return qmap_dyn,qmap_sta,ql_sta,ql_dyn,mask


def SAXS(img,mask,ql_sta,qmap_sta,det_size):

    import numpy as np

    chunk_size = int(img.shape[0]/10)

    Iq = np.zeros((1,ql_sta.size),dtype=float)
    Iq_par = np.zeros((10,ql_sta.size),dtype=float)

    img_2D = np.transpose(img.mean(axis=0).reshape(det_size[1],det_size[0]))
    img_2D = np.multiply(img_2D,mask)
               
    for ii in range(ql_sta.size):
        idx = (qmap_sta == ii+1)
        Iq[0,ii] = np.mean(img_2D[idx])


    for kk in range(10):
        tmp = np.transpose(img[kk*chunk_size:(kk+1)*chunk_size:].mean(axis=0).reshape(det_size[1],det_size[0]))
        for ii in range(ql_sta.size):
            idx = (qmap_sta == ii+1)
            Iq_par[kk,ii] = np.mean(tmp[idx])

    I_t = img.mean(axis=1)

    return img_2D, Iq, Iq_par, I_t


def Multitau_Group_g2(G2,IP,IF,qmap_sta,qmap_dyn):

    import numpy as np

    ql_sta_dim = np.amax(qmap_sta)
    ql_dyn_dim = np.amax(qmap_dyn)
    
    G2q=np.zeros([G2.shape[0],ql_sta_dim])
    IPq=np.zeros([G2.shape[0],ql_sta_dim])
    IFq=np.zeros([G2.shape[0],ql_sta_dim])

    g2=np.zeros([G2.shape[0],ql_dyn_dim])
    g2_err=np.zeros([G2.shape[0],ql_dyn_dim])


    IP_IF = np.multiply(IP,IF)
    IP_IF = (np.where(IP_IF!=0,IP_IF,10000))
    g2_per_pixel = np.divide(G2,IP_IF)

    for ii in range(ql_sta_dim):
        idx = (qmap_sta == ii+1)
        idx_corr = np.transpose(idx)
        _ = G2[:,idx_corr.flatten()]
        G2q[:,ii] = np.mean(_,axis=1)
        _ = IP[:,idx_corr.flatten()]
        IPq[:,ii] = np.mean(_,axis=1)
        _ = IF[:,idx_corr.flatten()]
        IFq[:,ii] = np.mean(_,axis=1)

    Isymmq = np.multiply(IPq,IFq)

    for ii in range(ql_dyn_dim):
        idx = (qmap_dyn == ii+1)
        idx_corr = np.transpose(idx)
        _ = g2_per_pixel[:,idx_corr.flatten()]
        g2_err[:,ii] = np.std(_,axis=1)/np.sqrt(_.shape[1])

    for ii in range(ql_dyn_dim):
        _ = qmap_sta[np.where(qmap_dyn==ii+1)]
        tmpG2q = G2q[:,(np.amin(_)-1):(np.amax(_)-1)]
        tmpIsymmq= Isymmq[:,(np.amin(_)-1):(np.amax(_)-1)]
        g2[:,ii] = np.mean(np.divide(tmpG2q,tmpIsymmq),axis=1)


    return g2, g2_err



def Write_HDF_Result(XPCS_Result):

    import h5py
    import numpy as np

    qmap_dyn = XPCS_Result["qmap_dyn"]
    qmap_sta = XPCS_Result["qmap_sta"]
    ql_sta = XPCS_Result["ql_sta"]
    ql_dyn = XPCS_Result["ql_dyn"] 
    t_el = XPCS_Result["t_el"]
    frame_num = XPCS_Result["frame_num"]
    img_2D = XPCS_Result["img_2D"]
    Iq = XPCS_Result["Iq"]
    Iq_par =  XPCS_Result["Iq_par"]
    I_t =  XPCS_Result["I_t"]
    g2 =  XPCS_Result["g2"]
    g2_err =  XPCS_Result["g2_err"]
    exposure_period = XPCS_Result["exposure_period"]
    exposure_time = XPCS_Result["exposure_time"]
    mask = XPCS_Result["mask"]
    filename = XPCS_Result["filename"]

    t_dim = t_el.size

    timestamp = np.zeros((2,frame_num))
    timestamp[0,:]=np.arange(frame_num)+1
    timestamp[1,:]=np.arange(frame_num)

    frameSum = np.zeros((2,frame_num))
    frameSum[0,:]=np.arange(frame_num)+1
    frameSum[1,:]=np.reshape(I_t,(1,frame_num))

    with h5py.File('./cluster_results'+filename, 'w') as f2:

        f2.create_dataset('/exchange/norm-0-g2', data=g2)
        f2.create_dataset('/exchange/norm-0-stderr', data=g2_err)
        f2.create_dataset('/exchange/pixelSum', data=img_2D)
        f2.create_dataset('/exchange/tau', data=np.reshape(t_el,(1,t_dim)))
        f2.create_dataset('/exchange/partition-mean-total', data=Iq)
        f2.create_dataset('/exchange/partition-mean-partial', data=Iq_par)
        f2.create_dataset('/exchange/timestamp_clock', data=timestamp)
        f2.create_dataset('/exchange/timestamp_tick', data=timestamp)
        f2.create_dataset('/exchange/frameSum', data=frameSum)

        f2.create_dataset('/measurement/instrument/detector/adu_per_photon', data=1.0)
        f2.create_dataset('/measurement/instrument/detector/exposure_period', data=exposure_period)
        f2.create_dataset('/measurement/instrument/detector/exposure_time', data=exposure_time)
        f2.create_dataset('/measurement/instrument/detector/manufacturer', data='RIGAKU500K')
        f2.create_dataset('/measurement/instrument/detector/x_pixel_size', data=0.076)
        f2.create_dataset('/measurement/instrument/detector/y_pixel_size', data=0.076)
        f2.create_dataset('/measurement/instrument/detector/x_dimension', data=512)
        f2.create_dataset('/measurement/instrument/detector/y_dimension', data=1024)
        f2.create_dataset('/measurement/instrument/source_begin/energy', data=10.94)
        f2.create_dataset('/measurement/instrument/detector/distance', data=7800.0)

        f2.create_dataset('/measurement/instrument/acquisition/stage_x', data=0)
        f2.create_dataset('/measurement/instrument/acquisition/stage_zero_x', data=0)
        f2.create_dataset('/measurement/instrument/acquisition/stage_z', data=0)
        f2.create_dataset('/measurement/instrument/acquisition/stage_zero_z', data=0)
        f2.create_dataset('/measurement/instrument/acquisition/beam_center_x', data=511)
        f2.create_dataset('/measurement/instrument/acquisition/beam_center_y', data=253)

        f2.create_dataset('/xpcs/analysis_type', data='Multitau')
        f2.create_dataset('/xpcs/data_begin_todo', data=1)
        f2.create_dataset('/xpcs/data_end_todo', data=1)
        f2.create_dataset('/xpcs/dphilist', data=ql_dyn)
        f2.create_dataset('/xpcs/dphispan', data=[1,1]) 
        f2.create_dataset('/xpcs/dqlist', data=ql_dyn)
        f2.create_dataset('/xpcs/dqmap', data=qmap_dyn)

        f2.create_dataset('/xpcs/sphilist', data=ql_sta)
        f2.create_dataset('/xpcs/sphispan', data=[1,1])
        f2.create_dataset('/xpcs/sqmap', data=qmap_sta)
        f2.create_dataset('/xpcs/sqlist', data=ql_sta)
        f2.create_dataset('/xpcs/snoq', data=270)
        f2.create_dataset('/xpcs/snophi', data=1)
        f2.create_dataset('/xpcs/dnoq', data=27)
        f2.create_dataset('/xpcs/dnophi', data=1)
        f2.create_dataset('/xpcs/avg_frames', data=1)
        f2.create_dataset('/xpcs/stride_frames', data=1)
        f2.create_dataset('/xpcs/stride_frames_burst', data=1)
        f2.create_dataset('/xpcs/mask', data=mask)

        tmp = np.zeros((1,ql_sta.size+1))
        tmp[0,0] = ql_sta[0,0]
        tmp[0,1:] = ql_sta
        f2.create_dataset('/xpcs/sqspan', data=tmp)

        tmp = np.zeros((1,ql_dyn.size+1))
        tmp[0,0] = ql_dyn[0,0]
        tmp[0,1:] = ql_dyn
        f2.create_dataset('/xpcs/dqspan', data=tmp)

        f2.create_dataset('/xpcs/kinetics', data='DISABLED') 
        f2.create_dataset('/xpcs/output_data', data='/exchange') 
        f2.create_dataset('/xpcs/qmap_hdf5_filename', data='None') 
        f2.create_dataset('/xpcs/specfile', data='dufresne20190729') 
        f2.create_dataset('/xpcs/specscan_data_number', data=1) 
        f2.create_dataset('/xpcs/input_file_local', data='A021_Silica_D100nm_att3_Rq0.bin') 

