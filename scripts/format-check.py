import os
import yaml_parser as yaml


def main():
    num_files = 0
    num_errors = 0
    for root, dirs, files in os.walk("."):
        for file in files:
            if file == "recipe.yaml" or file == "recipe.yml":
                num_files += 1
                file_path = os.path.join(root, file)
                valid, error = yaml.verify(file_path)
                if valid != 0:
                    print(
                        f"File {file_path} does not follow the specified format. Error {valid}:\n{error}\n"
                    )
                    num_errors += 1

    if num_errors > 0:
        print(f"Found {num_errors} errors in {num_files} files. Exiting.")
        exit(1)
    else:
        print(f"Found {num_files} files. All files follow the specified format.")


if __name__ == "__main__":
    main()
