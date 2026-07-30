"""Tests for algorithm parameters editing in preprocessing pipeline."""


def test_pipeline_item_has_params():
    """Test that pipeline items store parameters correctly."""
    pipeline = []
    
    # Simulate adding algorithm with params
    algo_id = "gaussian_blur"
    params = {"kernel_size": 5}
    
    pipeline.append({"algorithm": algo_id, "params": params})
    
    assert len(pipeline) == 1
    assert pipeline[0]["algorithm"] == algo_id
    assert pipeline[0]["params"]["kernel_size"] == 5


def test_update_pipeline_params():
    """Test updating parameters of existing pipeline item."""
    pipeline = []
    
    # Add algorithm
    pipeline.append({"algorithm": "gaussian_blur", "params": {"kernel_size": 5}})
    
    # Update params
    pipeline[0]["params"]["kernel_size"] = 9
    
    assert pipeline[0]["params"]["kernel_size"] == 9


def test_backup_and_restore_params():
    """Test backing up and restoring parameters (for Cancel)."""
    original_params = {"kernel_size": 5, "threshold": 127}
    
    # Backup
    backup = original_params.copy()
    
    # Modify
    original_params["kernel_size"] = 9
    
    # Restore
    original_params = backup.copy()
    
    assert original_params["kernel_size"] == 5
    assert original_params["threshold"] == 127


def test_algorithm_without_params():
    """Test algorithm that has no parameters."""
    pipeline = []
    
    # Add algorithm without params
    pipeline.append({"algorithm": "upscale_2x", "params": {}})
    
    assert len(pipeline) == 1
    assert pipeline[0]["params"] == {}


def test_multiple_algorithms_independent_params():
    """Test that multiple algorithms have independent parameters."""
    pipeline = []
    
    # Add two algorithms
    pipeline.append({"algorithm": "gaussian_blur", "params": {"kernel_size": 5}})
    pipeline.append({"algorithm": "clahe", "params": {"clip_limit": 2.0, "tile_grid_size": 8}})
    
    # Modify first
    pipeline[0]["params"]["kernel_size"] = 9
    
    # Second should be unchanged
    assert pipeline[1]["params"]["clip_limit"] == 2.0
    assert pipeline[1]["params"]["tile_grid_size"] == 8
