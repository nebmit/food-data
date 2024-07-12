import yaml


def verify(file_path):
    with open(file_path, "r") as file:
        try:
            data = yaml.safe_load(file)
        except yaml.YAMLError as exc:
            return 1, f"Error parsing YAML file {file_path}: {exc}"

        # Define the expected structure
        required_keys = {
            "portion": {
                "quantity": int,
                "descriptor": str,
                "active_time_minutes": int,
                "passive_time_minutes": int,
                "complexity_rating": int,
                "mayhem_rating": int,
            },
            "ingredients": [
                {"name": str, "quantity": (int, float), "measurement": str}
            ],
            "items": [{"name": str, "quantity": (int, float)}],
            "instructions": [str],
        }

        optional_keys = {
            "tags": [str],
            "common_ingredients": [
                {"name": str, "quantity": (int, float), "measurement": str}
            ],
            "note": [str],
        }

        def validate_dict_structure(data, structure):
            if not isinstance(data, dict):
                return False, f"Data is not a dictionary: {data}"
            for key, value_type in structure.items():
                if key not in data:
                    return False, f"Missing key '{key}'"
                if isinstance(value_type, dict):
                    valid, msg = validate_dict_structure(data[key], value_type)
                    if not valid:
                        return False, f"Key '{key}' validation failed: {msg}"
                elif isinstance(value_type, list) and value_type:
                    if not isinstance(data[key], list):
                        return False, f"Key '{key}' is not a list"
                    if isinstance(value_type[0], dict):
                        for item in data[key]:
                            valid, msg = validate_dict_structure(item, value_type[0])
                            if not valid:
                                return (
                                    False,
                                    f"List item validation failed in key '{key}': {msg}",
                                )
                    else:
                        for item in data[key]:
                            if not isinstance(item, value_type[0]):
                                return (
                                    False,
                                    f"List item '{item}' is not of type {value_type[0]} in key '{key}'",
                                )
                elif not isinstance(data[key], value_type):
                    return (
                        False,
                        f"Key '{key}' is not of type {value_type}: {data[key]}",
                    )
            return True, "Validation successful"

        # Validate required keys
        valid, msg = validate_dict_structure(data, required_keys)
        if not valid:
            return 2, msg

        # Validate optional keys if they exist
        for key, value_type in optional_keys.items():
            if key in data:
                valid, msg = validate_dict_structure(
                    {key: data[key]}, {key: value_type}
                )
                if not valid:
                    return (3, msg)

        return 0, f"File {file_path} is valid."
