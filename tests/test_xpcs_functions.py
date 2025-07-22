import unittest
import numpy as np
import tempfile
import os
import h5py
from unittest.mock import patch, MagicMock
from scipy.sparse import csr_matrix

# Import the functions to test
from poweruser_xpcs.utils.xpcs_functions import (
    Read_Frames_8IDI_Rigaku,
    Muititau_Corr,
    Read_Qmap_8IDI,
    SAXS,
    Multitau_Group_g2,
    Write_HDF_Result
)


class TestReadFrames8IDIRigaku(unittest.TestCase):
    """Test cases for Read_Frames_8IDI_Rigaku function."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, 'test_data.bin')
        
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
        
    def test_read_frames_basic(self):
        """Test basic functionality of reading frames."""
        # Create test data
        det_size = (512, 1024)
        num_pixels = det_size[0] * det_size[1]
        
        # Create mock binary data
        # Format: 64-bit integers with frame, pixel index, and count encoded
        test_data = []
        for frame in range(3):
            for i in range(10):  # 10 pixels per frame
                pix_ind = np.random.randint(0, num_pixels)
                pix_count = np.random.randint(1, 100)
                # Encode according to the function's decoding logic
                value = (frame << 40) | (pix_ind << 16) | pix_count
                test_data.append(value)
        
        test_array = np.array(test_data, dtype=np.uint64)
        with open(self.test_file, 'wb') as f:
            test_array.tofile(f)
        
        # Read frames
        result = Read_Frames_8IDI_Rigaku(self.test_file, det_size)
        
        # Verify result
        self.assertIsInstance(result, csr_matrix)
        self.assertEqual(result.shape[0], 3)  # 3 frames
        self.assertEqual(result.shape[1], num_pixels)
        
    def test_read_frames_empty_file(self):
        """Test reading an empty file."""
        # Create empty file
        open(self.test_file, 'wb').close()
        
        det_size = (512, 1024)
        # Empty file should raise an error or return empty matrix
        try:
            result = Read_Frames_8IDI_Rigaku(self.test_file, det_size)
            # If no error, check for empty matrix
            self.assertEqual(result.shape[1], det_size[0] * det_size[1])
            self.assertEqual(result.nnz, 0)  # No non-zero elements
        except ValueError:
            # Expected behavior for empty file
            pass


class TestMultitauCorr(unittest.TestCase):
    """Test cases for Muititau_Corr function."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create sample sparse image data
        self.num_frames = 100
        self.num_pixels = 1000
        self.dpl = 4  # delays per level
        
        # Create random sparse matrix
        density = 0.1
        self.img = csr_matrix(
            np.random.rand(self.num_frames, self.num_pixels) * (np.random.rand(self.num_frames, self.num_pixels) < density)
        )
        
    @patch('builtins.print')  # Mock print to suppress output
    def test_multitau_corr_basic(self, mock_print):
        """Test basic multitau correlation calculation."""
        G2, IP, IF, t_el = Muititau_Corr(self.img, self.dpl)
        
        # Check output shapes
        self.assertEqual(G2.shape[1], self.num_pixels)
        self.assertEqual(IP.shape[1], self.num_pixels)
        self.assertEqual(IF.shape[1], self.num_pixels)
        self.assertEqual(len(t_el), G2.shape[0])
        
        # Check that delay times are correct
        self.assertTrue(np.all(t_el > 0))
        
    @patch('builtins.print')
    def test_multitau_corr_small_frames(self, mock_print):
        """Test with small number of frames."""
        small_img = csr_matrix(np.random.rand(10, 100))
        G2, IP, IF, t_el = Muititau_Corr(small_img, 2)
        
        # Should still work with small frame count
        self.assertGreater(G2.shape[0], 0)
        self.assertEqual(G2.shape[1], 100)


class TestReadQmap8IDI(unittest.TestCase):
    """Test cases for Read_Qmap_8IDI function."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, 'test_qmap.h5')
        
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
        
    def test_read_qmap_basic(self):
        """Test reading qmap from HDF5 file."""
        # Create test HDF5 file
        with h5py.File(self.test_file, 'w') as f:
            f.create_dataset('/data/dynamicMap', data=np.random.randint(0, 10, (512, 1024)))
            f.create_dataset('/data/staticMap', data=np.random.randint(0, 10, (512, 1024)))
            f.create_dataset('/data/sqval', data=np.linspace(0.001, 0.1, 100))
            f.create_dataset('/data/dqval', data=np.linspace(0.001, 0.05, 50))
            f.create_dataset('/data/mask', data=np.ones((512, 1024), dtype=int))
        
        # Read qmap
        qmap_dyn, qmap_sta, ql_sta, ql_dyn, mask = Read_Qmap_8IDI(self.test_file)
        
        # Verify outputs
        self.assertEqual(qmap_dyn.shape, (512, 1024))
        self.assertEqual(qmap_sta.shape, (512, 1024))
        self.assertEqual(len(ql_sta), 100)
        self.assertEqual(len(ql_dyn), 50)
        self.assertEqual(mask.shape, (512, 1024))
        
    def test_read_qmap_missing_dataset(self):
        """Test reading qmap with missing dataset."""
        # Create incomplete HDF5 file
        with h5py.File(self.test_file, 'w') as f:
            f.create_dataset('/data/dynamicMap', data=np.zeros((10, 10)))
            # Missing other datasets
        
        # Should raise error
        with self.assertRaises(Exception):
            Read_Qmap_8IDI(self.test_file)


class TestSAXS(unittest.TestCase):
    """Test cases for SAXS function."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.det_size = (512, 1024)
        self.num_frames = 100
        
        # Create test sparse image
        self.img = csr_matrix(np.random.rand(self.num_frames, self.det_size[0] * self.det_size[1]))
        
        # Create test mask and qmap
        self.mask = np.ones(self.det_size)
        self.qmap_sta = np.random.randint(1, 11, self.det_size)
        self.ql_sta = np.arange(1, 11)
        
    def test_saxs_basic(self):
        """Test basic SAXS calculation."""
        img_2D, Iq, Iq_par, I_t = SAXS(self.img, self.mask, self.ql_sta, self.qmap_sta, self.det_size)
        
        # Check output shapes
        self.assertEqual(img_2D.shape, self.det_size)
        self.assertEqual(Iq.shape, (1, len(self.ql_sta)))
        self.assertEqual(Iq_par.shape, (10, len(self.ql_sta)))
        self.assertEqual(len(I_t), self.num_frames)
        
    def test_saxs_with_zero_mask(self):
        """Test SAXS with zero mask."""
        zero_mask = np.zeros(self.det_size)
        img_2D, Iq, Iq_par, I_t = SAXS(self.img, zero_mask, self.ql_sta, self.qmap_sta, self.det_size)
        
        # img_2D should be all zeros
        self.assertTrue(np.all(img_2D == 0))


class TestMultitauGroupG2(unittest.TestCase):
    """Test cases for Multitau_Group_g2 function."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.num_delays = 50
        # Create qmaps first to determine pixel count
        self.qmap_shape = (32, 32)
        self.num_pixels = self.qmap_shape[0] * self.qmap_shape[1]  # 1024 pixels
        
        # Create test data matching the qmap dimensions
        self.G2 = np.random.rand(self.num_delays, self.num_pixels)
        self.IP = np.random.rand(self.num_delays, self.num_pixels) + 0.1  # Avoid zeros
        self.IF = np.random.rand(self.num_delays, self.num_pixels) + 0.1
        
        # Create qmaps with correct shape
        self.qmap_sta = np.random.randint(1, 11, self.qmap_shape)
        self.qmap_dyn = np.random.randint(1, 6, self.qmap_shape)
        
    def test_multitau_group_g2_basic(self):
        """Test basic g2 grouping."""
        g2, g2_err = Multitau_Group_g2(self.G2, self.IP, self.IF, self.qmap_sta, self.qmap_dyn)
        
        # Check output shapes
        ql_dyn_dim = np.amax(self.qmap_dyn)
        self.assertEqual(g2.shape, (self.num_delays, ql_dyn_dim))
        self.assertEqual(g2_err.shape, (self.num_delays, ql_dyn_dim))
        
        # Check that g2 values are reasonable (should be around 1 for uncorrelated data)
        self.assertTrue(np.all(g2 > 0))
        
    def test_multitau_group_g2_with_zeros(self):
        """Test g2 grouping with zero values in IP/IF."""
        # Set some values to zero
        self.IP[:, :10] = 0
        self.IF[:, :10] = 0
        
        g2, g2_err = Multitau_Group_g2(self.G2, self.IP, self.IF, self.qmap_sta, self.qmap_dyn)
        
        # Should handle zeros gracefully
        self.assertFalse(np.any(np.isnan(g2)))
        self.assertFalse(np.any(np.isinf(g2)))


class TestWriteHDFResult(unittest.TestCase):
    """Test cases for Write_HDF_Result function."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        os.chdir(self.temp_dir)
        
        # Create test XPCS result dictionary
        self.XPCS_Result = {
            "qmap_dyn": np.random.randint(1, 10, (512, 1024)),
            "qmap_sta": np.random.randint(1, 10, (512, 1024)),
            "ql_sta": np.linspace(0.001, 0.1, 100).reshape(1, -1),
            "ql_dyn": np.linspace(0.001, 0.05, 50).reshape(1, -1),
            "t_el": np.logspace(0, 3, 50),
            "frame_num": 1000,
            "img_2D": np.random.rand(512, 1024),
            "Iq": np.random.rand(1, 100),
            "Iq_par": np.random.rand(10, 100),
            "I_t": np.random.rand(1000),
            "g2": np.random.rand(50, 50),
            "g2_err": np.random.rand(50, 50) * 0.1,
            "exposure_period": 0.1,
            "exposure_time": 0.09,
            "mask": np.ones((512, 1024), dtype=int),
            "filename": "_test_output.h5"
        }
        
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        os.chdir('..')
        shutil.rmtree(self.temp_dir)
        
    def test_write_hdf_result_basic(self):
        """Test writing HDF result file."""
        Write_HDF_Result(self.XPCS_Result)
        
        # Check that file was created
        output_file = './cluster_results_test_output.h5'
        self.assertTrue(os.path.exists(output_file))
        
        # Verify contents
        with h5py.File(output_file, 'r') as f:
            # Check key datasets
            self.assertIn('/exchange/norm-0-g2', f)
            self.assertIn('/exchange/norm-0-stderr', f)
            self.assertIn('/exchange/pixelSum', f)
            self.assertIn('/exchange/tau', f)
            self.assertIn('/measurement/instrument/detector/exposure_period', f)
            self.assertIn('/xpcs/dqmap', f)
            
            # Check data integrity
            np.testing.assert_array_equal(f['/exchange/norm-0-g2'][:], self.XPCS_Result['g2'])
            np.testing.assert_array_equal(f['/xpcs/mask'][:], self.XPCS_Result['mask'])
            
    def test_write_hdf_result_missing_keys(self):
        """Test writing HDF with missing keys."""
        # Remove a required key
        del self.XPCS_Result['g2']
        
        # Should raise KeyError
        with self.assertRaises(KeyError):
            Write_HDF_Result(self.XPCS_Result)


if __name__ == '__main__':
    unittest.main()
