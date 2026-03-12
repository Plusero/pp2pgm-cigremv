import numpy as np
from matplotlib import pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.colors import TwoSlopeNorm
from matplotlib.colors import TwoSlopeNorm

def find_max_id(input_data):
    """
    Find the largest component ID across all component types.

    Args:
        input_data: The input data of the Power Grid Model.

    Returns:
        max_id: The largest component ID across all component types.
    """
    max_id = -1
    for component_type in input_data:
        max_id = max(max_id, max(input_data[component_type]["id"]))
    return max_id


def get_component_indices(component_ids, input_data, component_type):
    """Get indices for component IDs in input data.

    Args:
        component_ids: List of component IDs to find indices for
        input_data: Power grid model input data
        component_type: ComponentType enum value (e.g., ComponentType.node)

    Returns:
        List of indices corresponding to the component IDs

    Raises:
        ValueError: If any component ID is not found
    """
    id_to_index = {
        comp_id: index for index, comp_id in enumerate(input_data[component_type]["id"])
    }

    # Validate all IDs exist
    invalid_ids = [cid for cid in component_ids if cid not in id_to_index]
    if invalid_ids:
        raise ValueError(f"Unknown {component_type.name} ID(s): {invalid_ids}")

    return [id_to_index[cid] for cid in component_ids]


def log_steps(max):
    """
    Generate a list of logarithmic steps from 1 to max.
    The steps are in the form of 1, 2, ..., 9 followed by powers of ten.

    Args:
        max: The maximum value to generate steps for.

    Returns:
        steps: A list of logarithmic steps from 1 to max. The steps are 1/10 of its order of magnitude.
    """
    order = int(np.log10(max)) + 1  # Get order of magnitude
    list = [i * 10**j for j in range(order)
            for i in range(1, 10) if i * 10**j < max]
    return np.array(list)

