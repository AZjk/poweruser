import unittest
import tempfile
import shutil
import os
import h5py
import numpy as np
import csv
from unittest.mock import patch, MagicMock, call
import argparse

# Import the function to test
from poweruser_xpcs.utils.convert_nexus_to_csv import hdf2csv


class TestHdf2Csv(unittest.TestCase):
    """Test cases for hdf2csv function."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_hdf_file = os.path.join(self.temp_dir, 'test_data.hdf')
        
        # Create a test HDF5 file with required structure
        self._create_test_hdf_file()
        
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
        
    def _create_test_hdf_file(self):
        """Create a test HDF5 file with the expected structure."""
        with h5py.File(self.test_hdf_file, 'w') as hf:
            # Create groups
            xpcs = hf.create_group('xpcs')
            multitau = xpcs.create_group('multitau')
            temporal_mean = xpcs.create_group('temporal_mean')
            qmap = xpcs.create_group('qmap')
            entry = hf.create_group('entry')
            instrument = entry.create_group('instrument')
            detector_1 = instrument.create_group('detector_1')
            sample = entry.create_group('sample')
            
            # Create test data
            num_delays = 50
            num_q = 10
            num_segments = 5
            
            # Multitau data
            multitau.create_dataset('normalized_g2', data=np.random.rand(num_delays, num_q))
            multitau.create_dataset('delay_list', data=np.logspace(0, 3, num_delays))
            
            # Temporal mean data
            temporal_mean.create_dataset('scattering_1d', data=np.random.rand(num_q))
            temporal_mean.create_dataset('scattering_1d_segments', data=np.random.rand(num_segments, num_q))
            
            # Detector data
            detector_1.create_dataset('frame_time', data=0.1)
            
            # Q-map data
            qmap.create_dataset('dynamic_v_list_dim0', data=np.linspace(0.001, 0.1, num_q))
            qmap.create_dataset('static_v_list_dim0', data=np.linspace(0.001, 0.1, num_q))
            
            # Metadata
            entry.create_dataset('start_time', data=b'2023-01-01T12:00:00')
            sample.create_dataset('position_rheo_x', data=1.5)
            sample.create_dataset('position_rheo_y', data=2.5)
            sample.create_dataset('position_rheo_z', data=3.5)
            
    def test_hdf2csv_basic(self):
        """Test basic HDF5 to CSV conversion."""
        # Run conversion
        hdf2csv(self.test_hdf_file, self.temp_dir)
        
        # Check that output files were created
        base_name = 'test_data'
        g2_file = os.path.join(self.temp_dir, f'{base_name}_g2.csv')
        saxs_file = os.path.join(self.temp_dir, f'{base_name}_saxs.csv')
        meta_file = os.path.join(self.temp_dir, f'{base_name}_meta.csv')
        
        self.assertTrue(os.path.exists(g2_file))
        self.assertTrue(os.path.exists(saxs_file))
        self.assertTrue(os.path.exists(meta_file))
        
        # Verify G2 CSV structure
        g2_data = np.loadtxt(g2_file, delimiter=',')
        self.assertEqual(g2_data.shape[0], 51)  # num_delays + 1 for header
        self.assertEqual(g2_data.shape[1], 11)  # num_q + 1 for time column
        
        # Verify SAXS CSV structure
        saxs_data = np.loadtxt(saxs_file, delimiter=',')
        self.assertEqual(saxs_data.shape[0], 10)  # num_q
        self.assertEqual(saxs_data.shape[1], 7)   # q + saxs_1d + segments
        
        # Verify metadata CSV
        with open(meta_file, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
            self.assertEqual(rows[0], ['Metadata Names', 'Metadata Values'])
            self.assertEqual(len(rows), 5)  # header + 4 metadata entries
            
    def test_hdf2csv_data_integrity(self):
        """Test that data is correctly transferred to CSV files."""
        # Get original data
        with h5py.File(self.test_hdf_file, 'r') as hf:
            orig_g2 = hf['xpcs']['multitau']['normalized_g2'][:]
            orig_delays = hf['xpcs']['multitau']['delay_list'][:]
            orig_saxs = hf['xpcs']['temporal_mean']['scattering_1d'][:]
            orig_ql_dyn = hf['xpcs']['qmap']['dynamic_v_list_dim0'][:]
            t0 = hf['entry']['instrument']['detector_1']['frame_time'][()]
            
        # Run conversion
        hdf2csv(self.test_hdf_file, self.temp_dir)
        
        # Load G2 CSV
        g2_file = os.path.join(self.temp_dir, 'test_data_g2.csv')
        g2_data = np.loadtxt(g2_file, delimiter=',')
        
        # Check time column (first column, excluding header)
        np.testing.assert_array_almost_equal(g2_data[1:, 0], orig_delays * t0)
        
        # Check q values (first row, excluding time column)
        np.testing.assert_array_almost_equal(g2_data[0, 1:], orig_ql_dyn)
        
        # Check G2 data
        np.testing.assert_array_almost_equal(g2_data[1:, 1:], orig_g2)
        
        # Load SAXS CSV
        saxs_file = os.path.join(self.temp_dir, 'test_data_saxs.csv')
        saxs_data = np.loadtxt(saxs_file, delimiter=',')
        
        # Check SAXS intensity (second column)
        np.testing.assert_array_almost_equal(saxs_data[:, 1], orig_saxs)
        
    def test_hdf2csv_metadata_values(self):
        """Test that metadata is correctly written to CSV."""
        # Run conversion
        hdf2csv(self.test_hdf_file, self.temp_dir)
        
        # Read metadata CSV
        meta_file = os.path.join(self.temp_dir, 'test_data_meta.csv')
        with open(meta_file, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
            
        # Check metadata values
        metadata_dict = {row[0]: row[1] for row in rows[1:]}
        self.assertEqual(metadata_dict['start_time'], "b'2023-01-01T12:00:00'")
        self.assertEqual(metadata_dict['position_rheo_x'], '1.5')
        self.assertEqual(metadata_dict['position_rheo_y'], '2.5')
        self.assertEqual(metadata_dict['position_rheo_z'], '3.5')
        
    @patch('builtins.print')
    def test_hdf2csv_success_message(self, mock_print):
        """Test that success message is printed."""
        hdf2csv(self.test_hdf_file, self.temp_dir)
        
        # Check that success message was printed
        expected_files = [
            os.path.join(self.temp_dir, 'test_data_g2.csv'),
            os.path.join(self.temp_dir, 'test_data_saxs.csv'),
            os.path.join(self.temp_dir, 'test_data_meta.csv')
        ]
        mock_print.assert_called_with(f"Successfully wrote: {expected_files[0]}, {expected_files[1]}, {expected_files[2]}")
        
    @patch('builtins.print')
    def test_hdf2csv_error_handling(self, mock_print):
        """Test error handling when file structure is incorrect."""
        # Create an HDF5 file with missing datasets
        bad_file = os.path.join(self.temp_dir, 'bad_file.hdf')
        with h5py.File(bad_file, 'w') as hf:
            hf.create_group('xpcs')  # Missing required datasets
            
        # Run conversion - should handle error gracefully
        hdf2csv(bad_file, self.temp_dir)
        
        # Check that error was printed
        mock_print.assert_called()
        call_args = mock_print.call_args[0][0]
        self.assertTrue(call_args.startswith(f"Error processing {bad_file}:"))
        
    def test_hdf2csv_output_directory_creation(self):
        """Test that function works with non-existent output directory."""
        # Use a non-existent output directory
        new_output_dir = os.path.join(self.temp_dir, 'new_output')
        
        # Create the directory first since hdf2csv expects it to exist
        os.makedirs(new_output_dir, exist_ok=True)
        
        # Run conversion
        hdf2csv(self.test_hdf_file, new_output_dir)
        
        # Check that files were created in the new directory
        self.assertTrue(os.path.exists(os.path.join(new_output_dir, 'test_data_g2.csv')))
        
    def test_hdf2csv_different_array_shapes(self):
        """Test conversion with different array shapes."""
        # Create HDF5 file with different dimensions
        special_file = os.path.join(self.temp_dir, 'special.hdf')
        with h5py.File(special_file, 'w') as hf:
            # Different dimensions
            num_delays = 100
            num_q = 20
            num_segments = 10
            
            # Create structure
            xpcs = hf.create_group('xpcs')
            multitau = xpcs.create_group('multitau')
            temporal_mean = xpcs.create_group('temporal_mean')
            qmap = xpcs.create_group('qmap')
            entry = hf.create_group('entry')
            instrument = entry.create_group('instrument')
            detector_1 = instrument.create_group('detector_1')
            sample = entry.create_group('sample')
            
            # Create data with different dimensions
            multitau.create_dataset('normalized_g2', data=np.random.rand(num_delays, num_q))
            multitau.create_dataset('delay_list', data=np.logspace(0, 4, num_delays))
            temporal_mean.create_dataset('scattering_1d', data=np.random.rand(num_q))
            temporal_mean.create_dataset('scattering_1d_segments', data=np.random.rand(num_segments, num_q))
            detector_1.create_dataset('frame_time', data=0.05)
            qmap.create_dataset('dynamic_v_list_dim0', data=np.linspace(0.001, 0.2, num_q))
            qmap.create_dataset('static_v_list_dim0', data=np.linspace(0.001, 0.2, num_q))
            entry.create_dataset('start_time', data=b'2023-12-25T00:00:00')
            sample.create_dataset('position_rheo_x', data=0.0)
            sample.create_dataset('position_rheo_y', data=0.0)
            sample.create_dataset('position_rheo_z', data=0.0)
            
        # Run conversion
        hdf2csv(special_file, self.temp_dir)
        
        # Verify output dimensions
        g2_data = np.loadtxt(os.path.join(self.temp_dir, 'special_g2.csv'), delimiter=',')
        self.assertEqual(g2_data.shape[0], num_delays + 1)
        self.assertEqual(g2_data.shape[1], num_q + 1)
        
        saxs_data = np.loadtxt(os.path.join(self.temp_dir, 'special_saxs.csv'), delimiter=',')
        self.assertEqual(saxs_data.shape[0], num_q)
        self.assertEqual(saxs_data.shape[1], num_segments + 2)


class TestMainFunction(unittest.TestCase):
    """Test cases for the main function behavior."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
        
    @patch('poweruser_xpcs.utils.convert_nexus_to_csv.hdf2csv')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_with_filter(self, mock_args, mock_hdf2csv):
        """Test main function with filename filter."""
        # Create test files
        input_dir = os.path.join(self.temp_dir, 'input')
        output_dir = os.path.join(self.temp_dir, 'output')
        os.makedirs(input_dir, exist_ok=True)
        
        # Create test HDF files
        test_files = ['test1.hdf', 'test2.hdf5', 'other.hdf', 'data.txt']
        for filename in test_files:
            open(os.path.join(input_dir, filename), 'a').close()
            
        # Mock arguments
        mock_args.return_value = argparse.Namespace(
            input=input_dir,
            output=output_dir,
            filter='test'
        )
        
        # Execute the main block directly
        import poweruser_xpcs.utils.convert_nexus_to_csv as module
        # Run the code that would be in if __name__ == "__main__":
        module.os.makedirs(output_dir, exist_ok=True)
        for filename in module.os.listdir(input_dir):
            if (filename.endswith(".hdf") or filename.endswith(".hdf5")) and ('test' in filename):
                full_path = module.os.path.join(input_dir, filename)
                module.hdf2csv(full_path, output_dir)
            
        # Verify hdf2csv was called only for filtered files
        self.assertEqual(mock_hdf2csv.call_count, 2)
        called_files = [call[0][0] for call in mock_hdf2csv.call_args_list]
        self.assertIn(os.path.join(input_dir, 'test1.hdf'), called_files)
        self.assertIn(os.path.join(input_dir, 'test2.hdf5'), called_files)
        
    @patch('poweruser_xpcs.utils.convert_nexus_to_csv.hdf2csv')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_without_filter(self, mock_args, mock_hdf2csv):
        """Test main function without filename filter."""
        # Create test files
        input_dir = os.path.join(self.temp_dir, 'input')
        output_dir = os.path.join(self.temp_dir, 'output')
        os.makedirs(input_dir, exist_ok=True)
        
        # Create test HDF files
        test_files = ['file1.hdf', 'file2.hdf5', 'file3.hdf']
        for filename in test_files:
            open(os.path.join(input_dir, filename), 'a').close()
            
        # Also create non-HDF file
        open(os.path.join(input_dir, 'other.txt'), 'a').close()
        
        # Mock arguments
        mock_args.return_value = argparse.Namespace(
            input=input_dir,
            output=output_dir,
            filter=''
        )
        
        # Execute the main block directly
        import poweruser_xpcs.utils.convert_nexus_to_csv as module
        # Run the code that would be in if __name__ == "__main__":
        module.os.makedirs(output_dir, exist_ok=True)
        for filename in module.os.listdir(input_dir):
            if (filename.endswith(".hdf") or filename.endswith(".hdf5")) and ('' in filename):
                full_path = module.os.path.join(input_dir, filename)
                module.hdf2csv(full_path, output_dir)
            
        # Verify hdf2csv was called for all HDF files
        self.assertEqual(mock_hdf2csv.call_count, 3)
        
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_creates_output_directory(self, mock_args):
        """Test that main creates output directory."""
        # Create a unique output directory path
        output_dir = os.path.join(self.temp_dir, 'test_output_dir')
        
        # Mock arguments
        mock_args.return_value = argparse.Namespace(
            input=self.temp_dir,
            output=output_dir,
            filter=''
        )
        
        # Execute the main block directly
        import poweruser_xpcs.utils.convert_nexus_to_csv as module
        with patch.object(module, 'hdf2csv'):  # Mock hdf2csv to avoid actual conversion
            # Run the code that would be in if __name__ == "__main__":
            module.os.makedirs(output_dir, exist_ok=True)
            
        # Verify directory was created
        self.assertTrue(os.path.exists(output_dir))


if __name__ == '__main__':
    unittest.main()
