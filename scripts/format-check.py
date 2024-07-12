import os
import txt_parser as txt
import yaml_parser as yaml


def main():
    num_files = 0
    num_errors = 0
    for root, dirs, files in os.walk("."):
        for file in files:
            if file == "recipe.txt" or file == "recipe.yaml" or file == "recipe.yml":
                num_files += 1
                file_path = os.path.join(root, file)
                valid, error = check_format(file_path)
                if valid != 0:
                    print(
                        f"File {file_path} does not follow the specified format. Error {valid}:\n{error}"
                    )
                    num_errors += 1

    if num_errors > 0:
        print(f"Found {num_errors} errors in {num_files} files. Exiting.")
        exit(1)
    else:
        print(f"Found {num_files} files. All files follow the specified format.")


def check_format(file_path):
    if file_path.endswith(".txt"):
        return txt.verify(file_path)
    elif file_path.endswith(".yaml") or file_path.endswith(".yml"):
        return yaml.verify(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_path}")


if __name__ == "__main__":
    main()
