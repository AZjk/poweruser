import unittest
import tempfile
import shutil
import os
import h5py
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import concurrent.futures

# Import the functions to test
from poweruser_xpcs.utils.convert_legacy_datasets import (
    copy_dataset_safe,
    process_subfolder,
    walk_subfolders,
    worker_process_subfolder,
    process_folder,
    FIELD_MAPPING,
    MAX_DEPTH
)


class TestCopyDatasetSafe(unittest.TestCase):
    """Test cases for copy_dataset_safe function."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.src_file = os.path.join(self.temp_dir, 'source.h5')
        self.dst_file = os.path.join(self.temp_dir, 'dest.h5')
        
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
        
    def test_copy_dataset_basic(self):
        """Test basic dataset copying."""
        # Create source file with data
        with h5py.File(self.src_file, 'w') as src:
            src.create_dataset('/test/data', data=np.array([1, 2, 3, 4, 5]))
            
        # Create destination file
        with h5py.File(self.dst_file, 'w') as dst:
            dst.create_group('/output')
            
        # Copy dataset
        with h5py.File(self.src_file, 'r') as src, h5py.File(self.dst_file, 'r+') as dst:
            copy_dataset_safe(src, dst, '/test/data', '/output/data')
            
        # Verify
        with h5py.File(self.dst_file, 'r') as f:
            np.testing.assert_array_equal(f['/output/data'][:], [1, 2, 3, 4, 5])
            
    def test_copy_dataset_with_scale(self):
        """Test dataset copying with scaling."""
        # Create source file with data
        with h5py.File(self.src_file, 'w') as src:
            src.create_dataset('/test/data', data=np.array([1.0, 2.0, 3.0]))
            
        # Create destination file
        with h5py.File(self.dst_file, 'w') as dst:
            dst.create_group('/output')
            
        # Copy dataset with scale
        with h5py.File(self.src_file, 'r') as src, h5py.File(self.dst_file, 'r+') as dst:
            copy_dataset_safe(src, dst, '/test/data', '/output/data', scale=0.001)
            
        # Verify
        with h5py.File(self.dst_file, 'r') as f:
            np.testing.assert_array_almost_equal(f['/output/data'][:], [0.001, 0.002, 0.003])
            
    def test_copy_dataset_overwrite(self):
        """Test dataset copying with overwrite."""
        # Create files with existing data
        with h5py.File(self.src_file, 'w') as src:
            src.create_dataset('/test/data', data=np.array([10, 20, 30]))
            
        with h5py.File(self.dst_file, 'w') as dst:
            dst.create_dataset('/output/data', data=np.array([1, 2, 3]))
            
        # Copy dataset (should overwrite)
        with h5py.File(self.src_file, 'r') as src, h5py.File(self.dst_file, 'r+') as dst:
            copy_dataset_safe(src, dst, '/test/data', '/output/data')
            
        # Verify
        with h5py.File(self.dst_file, 'r') as f:
            np.testing.assert_array_equal(f['/output/data'][:], [10, 20, 30])
            
    def test_copy_dataset_scalar(self):
        """Test copying scalar dataset."""
        # Create source file with scalar in (1,1) array
        with h5py.File(self.src_file, 'w') as src:
            src.create_dataset('/test/scalar', data=np.array([[42.0]]))
            
        # Create destination file
        with h5py.File(self.dst_file, 'w') as dst:
            dst.create_group('/output')
            
        # Copy dataset
        with h5py.File(self.src_file, 'r') as src, h5py.File(self.dst_file, 'r+') as dst:
            copy_dataset_safe(src, dst, '/test/scalar', '/output/scalar')
            
        # Verify - should be stored as scalar
        with h5py.File(self.dst_file, 'r') as f:
            self.assertEqual(f['/output/scalar'][()], 42.0)
            
    def test_copy_dataset_missing_source(self):
        """Test copying non-existent dataset."""
        # Create files
        with h5py.File(self.src_file, 'w') as src:
            src.create_group('/test')
            
        with h5py.File(self.dst_file, 'w') as dst:
            dst.create_group('/output')
            
        # Try to copy non-existent dataset (should not raise exception)
        with h5py.File(self.src_file, 'r') as src, h5py.File(self.dst_file, 'r+') as dst:
            copy_dataset_safe(src, dst, '/test/nonexistent', '/output/data')
            
        # Verify destination doesn't have the dataset
        with h5py.File(self.dst_file, 'r') as f:
            self.assertNotIn('/output/data', f)


class TestProcessSubfolder(unittest.TestCase):
    """Test cases for process_subfolder function."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.source_folder = Path(self.temp_dir) / 'source'
        self.dest_folder = Path(self.temp_dir) / 'dest'
        self.source_folder.mkdir()
        self.dest_folder.mkdir()
        
        # Create a mock metadata template
        self.original_meta_template = Path(__file__).parent.parent / 'src' / 'poweruser_xpcs' / 'utils' / 'sample_metadata.hdf'
        self.mock_meta_template = self.source_folder / 'sample_metadata.hdf'
        with h5py.File(self.mock_meta_template, 'w') as f:
            # Create minimal structure for template
            for new_path, _ in FIELD_MAPPING.values():
                parts = new_path.strip('/').split('/')
                group_path = '/' + '/'.join(parts[:-1])
                if group_path not in f:
                    f.create_group(group_path)
                f.create_dataset(new_path, data=0.0)
                
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
        
    @patch('poweruser_xpcs.utils.convert_legacy_datasets.META_TEMPLATE', new_callable=lambda: MagicMock())
    def test_process_subfolder_basic(self, mock_template):
        """Test basic subfolder processing."""
        # Setup mock template
        mock_template.exists.return_value = True
        mock_template.__str__.return_value = str(self.mock_meta_template)
        
        # Create test subfolder with required files
        subfolder = self.source_folder / 'test_data'
        subfolder.mkdir()
        
        # Create raw data file
        raw_file = subfolder / 'data.bin'
        raw_file.write_bytes(b'test data')
        
        # Create metadata file with test data
        meta_file = subfolder / 'metadata.hdf'
        with h5py.File(meta_file, 'w') as f:
            # Add some fields from FIELD_MAPPING
            f.create_dataset('/measurement/instrument/detector/exposure_period', data=0.1)
            f.create_dataset('/measurement/instrument/detector/distance', data=7800.0)
            
        # Save original shutil.copy2 before patching
        import shutil as real_shutil
        original_copy2 = real_shutil.copy2
        
        # Use real shutil.copy2 to avoid recursion issues
        with patch('shutil.copy2') as mock_copy2:
            # Only mock when copying the template file
            def copy_side_effect(src, dst):
                if str(src) == str(mock_template):
                    # Use the actual template file we created
                    original_copy2(str(self.mock_meta_template), dst)
                else:
                    original_copy2(src, dst)
            mock_copy2.side_effect = copy_side_effect
            
            # Process subfolder
            process_subfolder(subfolder, self.source_folder, self.dest_folder, '.bin', copy_data=False)
        
        # Verify results
        result_folder = self.dest_folder / 'test_data'
        self.assertTrue(result_folder.exists())
        
        # Check symbolic link
        link_file = result_folder / 'data.bin'
        self.assertTrue(link_file.exists())
        self.assertTrue(link_file.is_symlink())
        
        # Check metadata file
        meta_result = result_folder / 'data_metadata.hdf'
        self.assertTrue(meta_result.exists())
        
    @patch('poweruser_xpcs.utils.convert_legacy_datasets.META_TEMPLATE', new_callable=lambda: MagicMock())
    def test_process_subfolder_copy_data(self, mock_template):
        """Test subfolder processing with data copying."""
        mock_template.exists.return_value = True
        mock_template.__str__.return_value = str(self.mock_meta_template)
        
        # Create test subfolder
        subfolder = self.source_folder / 'test_data'
        subfolder.mkdir()
        
        # Create files
        raw_file = subfolder / 'data.bin'
        raw_file.write_bytes(b'test data content')
        
        meta_file = subfolder / 'metadata.hdf'
        with h5py.File(meta_file, 'w') as f:
            f.create_dataset('/measurement/sample/thickness', data=1.5)
            
        # Save original shutil.copy2 before patching
        import shutil as real_shutil
        original_copy2 = real_shutil.copy2
        
        # Use real shutil.copy2 to avoid recursion issues
        with patch('shutil.copy2') as mock_copy2:
            def copy_side_effect(src, dst):
                if str(src) == str(mock_template):
                    original_copy2(str(self.mock_meta_template), dst)
                else:
                    original_copy2(src, dst)
            mock_copy2.side_effect = copy_side_effect
            
            # Process with copy_data=True
            process_subfolder(subfolder, self.source_folder, self.dest_folder, '.bin', copy_data=True)
        
        # Verify copied file
        result_file = self.dest_folder / 'test_data' / 'data.bin'
        self.assertTrue(result_file.exists())
        self.assertFalse(result_file.is_symlink())
        self.assertEqual(result_file.read_bytes(), b'test data content')
        
    @patch('poweruser_xpcs.utils.convert_legacy_datasets.META_TEMPLATE', new_callable=lambda: MagicMock())
    @patch('builtins.print')
    def test_process_subfolder_wrong_file_count(self, mock_print, mock_template):
        """Test processing with wrong number of files."""
        mock_template.exists.return_value = True
        
        # Create subfolder with multiple .bin files
        subfolder = self.source_folder / 'test_data'
        subfolder.mkdir()
        (subfolder / 'data1.bin').touch()
        (subfolder / 'data2.bin').touch()
        (subfolder / 'metadata.hdf').touch()
        
        # Process subfolder
        process_subfolder(subfolder, self.source_folder, self.dest_folder, '.bin', copy_data=False)
        
        # Should skip and print message
        mock_print.assert_called()
        self.assertFalse((self.dest_folder / 'test_data').exists())
        
    @patch('poweruser_xpcs.utils.convert_legacy_datasets.META_TEMPLATE', new_callable=lambda: MagicMock())
    @patch('builtins.print')
    @patch('traceback.print_exc')
    def test_process_subfolder_error_handling(self, mock_traceback, mock_print, mock_template):
        """Test error handling in process_subfolder."""
        mock_template.exists.return_value = False  # Template doesn't exist
        
        # Create test subfolder
        subfolder = self.source_folder / 'test_data'
        subfolder.mkdir()
        (subfolder / 'data.bin').touch()
        (subfolder / 'metadata.hdf').touch()
        
        # Process subfolder - should handle error
        process_subfolder(subfolder, self.source_folder, self.dest_folder, '.bin', copy_data=False)
        
        # Should print error and clean up
        mock_print.assert_called()
        mock_traceback.assert_called()


class TestWalkSubfolders(unittest.TestCase):
    """Test cases for walk_subfolders function."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.base_path = Path(self.temp_dir)
        
        # Create nested directory structure
        (self.base_path / 'level1').mkdir()
        (self.base_path / 'level1' / 'level2').mkdir()
        (self.base_path / 'level1' / 'level2' / 'level3').mkdir()
        (self.base_path / 'another1').mkdir()
        
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
        
    def test_walk_subfolders_max_depth(self):
        """Test walking with max depth limit."""
        # Walk with max_depth=1
        folders = list(walk_subfolders(self.base_path, max_depth=1))
        folder_names = [f.name for f in folders]
        
        # Should include level1 and another1, and level2 (depth 1)
        self.assertIn('level1', folder_names)
        self.assertIn('another1', folder_names)
        self.assertIn('level2', folder_names)
        # Should not include level3 (depth 2)
        self.assertNotIn('level3', folder_names)
        
    def test_walk_subfolders_all_depths(self):
        """Test walking all depths."""
        # Walk with high max_depth
        folders = list(walk_subfolders(self.base_path, max_depth=10))
        folder_names = [f.name for f in folders]
        
        # Should include all folders
        self.assertIn('level1', folder_names)
        self.assertIn('level2', folder_names)
        self.assertIn('level3', folder_names)
        self.assertIn('another1', folder_names)
        
    def test_walk_subfolders_zero_depth(self):
        """Test walking with zero depth."""
        # Walk with max_depth=0
        folders = list(walk_subfolders(self.base_path, max_depth=0))
        folder_names = [f.name for f in folders]
        
        # Should only include immediate subdirectories
        self.assertIn('level1', folder_names)
        self.assertIn('another1', folder_names)
        self.assertNotIn('level2', folder_names)


class TestWorkerProcessSubfolder(unittest.TestCase):
    """Test cases for worker_process_subfolder function."""
    
    @patch('poweruser_xpcs.utils.convert_legacy_datasets.process_subfolder')
    def test_worker_process_subfolder(self, mock_process):
        """Test worker function."""
        args = ('/path/to/subfolder', '/source', '/dest', '.bin', False)
        
        worker_process_subfolder(args)
        
        # Verify process_subfolder was called with correct arguments
        mock_process.assert_called_once_with(
            Path('/path/to/subfolder'),
            Path('/source'),
            Path('/dest'),
            '.bin',
            False
        )


class TestProcessFolder(unittest.TestCase):
    """Test cases for process_folder function."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.source_folder = os.path.join(self.temp_dir, 'source')
        self.dest_folder = os.path.join(self.temp_dir, 'dest')
        os.makedirs(self.source_folder)
        
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
        
    @patch('poweruser_xpcs.utils.convert_legacy_datasets.walk_subfolders')
    @patch('poweruser_xpcs.utils.convert_legacy_datasets.worker_process_subfolder')
    @patch('tqdm.tqdm')
    def test_process_folder_sequential(self, mock_tqdm, mock_worker, mock_walk):
        """Test sequential processing (max_workers=1)."""
        # Mock walk_subfolders to return some folders
        mock_folders = [Path('folder1'), Path('folder2')]
        mock_walk.return_value = mock_folders
        mock_tqdm.side_effect = lambda x, **kwargs: x
        
        # Process folder sequentially
        process_folder(self.source_folder, self.dest_folder, max_workers=1)
        
        # Verify worker was called for each folder
        self.assertEqual(mock_worker.call_count, 2)
        
        # Verify destination folder was created
        self.assertTrue(os.path.exists(self.dest_folder))
        
    @patch('poweruser_xpcs.utils.convert_legacy_datasets.walk_subfolders')
    @patch('concurrent.futures.ProcessPoolExecutor')
    @patch('tqdm.tqdm')
    def test_process_folder_parallel(self, mock_tqdm, mock_executor_class, mock_walk):
        """Test parallel processing."""
        # Mock walk_subfolders
        mock_folders = [Path('folder1'), Path('folder2'), Path('folder3')]
        mock_walk.return_value = mock_folders
        
        # Mock executor
        mock_executor = MagicMock()
        mock_executor_class.return_value.__enter__.return_value = mock_executor
        mock_executor.map.return_value = [None, None, None]
        
        mock_tqdm.side_effect = lambda x, **kwargs: list(x)
        
        # Process folder with multiple workers
        process_folder(self.source_folder, self.dest_folder, max_workers=4)
        
        # Verify executor was created with correct max_workers
        mock_executor_class.assert_called_once_with(max_workers=4)
        
        # Verify map was called
        mock_executor.map.assert_called_once()
        
    @patch('poweruser_xpcs.utils.convert_legacy_datasets.walk_subfolders')
    @patch('poweruser_xpcs.utils.convert_legacy_datasets.worker_process_subfolder')
    @patch('tqdm.tqdm')
    def test_process_folder_different_file_types(self, mock_tqdm, mock_worker, mock_walk):
        """Test processing with different file types."""
        mock_folders = [Path('folder1')]
        mock_walk.return_value = mock_folders
        mock_tqdm.side_effect = lambda x, **kwargs: x
        
        # Process with .imm file type
        process_folder(self.source_folder, self.dest_folder, max_workers=1, ftype='.imm')
        
        # Verify worker was called with .imm file type
        args = mock_worker.call_args[0][0]
        self.assertEqual(args[3], '.imm')
        
    @patch('poweruser_xpcs.utils.convert_legacy_datasets.walk_subfolders')
    @patch('poweruser_xpcs.utils.convert_legacy_datasets.worker_process_subfolder')
    @patch('tqdm.tqdm')
    def test_process_folder_copy_data(self, mock_tqdm, mock_worker, mock_walk):
        """Test processing with copy_data option."""
        mock_folders = [Path('folder1')]
        mock_walk.return_value = mock_folders
        mock_tqdm.side_effect = lambda x, **kwargs: x
        
        # Process with copy_data=True
        process_folder(self.source_folder, self.dest_folder, max_workers=1, copy_data=True)
        
        # Verify worker was called with copy_data=True
        args = mock_worker.call_args[0][0]
        self.assertEqual(args[4], True)


class TestFieldMapping(unittest.TestCase):
    """Test cases for FIELD_MAPPING constant."""
    
    def test_field_mapping_structure(self):
        """Test that FIELD_MAPPING has correct structure."""
        for old_path, (new_path, scale) in FIELD_MAPPING.items():
            # Check that paths start with /
            self.assertTrue(old_path.startswith('/'))
            self.assertTrue(new_path.startswith('/'))
            
            # Check that scale is either None or a number
            if scale is not None:
                self.assertIsInstance(scale, (int, float))
                
    def test_field_mapping_completeness(self):
        """Test that FIELD_MAPPING contains expected fields."""
        # Check some key mappings exist
        self.assertIn('/measurement/instrument/detector/exposure_period', FIELD_MAPPING)
        self.assertIn('/measurement/instrument/detector/distance', FIELD_MAPPING)
        self.assertIn('/measurement/sample/thickness', FIELD_MAPPING)
        
        # Check that unit conversions are present where expected
        distance_scale = FIELD_MAPPING['/measurement/instrument/detector/distance'][1]
        self.assertEqual(distance_scale, 0.001)  # mm to m conversion


if __name__ == '__main__':
    unittest.main()
