import yaml

def load_config(path_file:str):
    """Load config file for models

    Args:
        path_file (str): config file path

    Returns:
        dict: dictionary of config
    """
    with open(path_file) as f:
        config = yaml.safe_load(f)
    return config

