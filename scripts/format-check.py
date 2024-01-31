import os
import re


def verify_format(file_path):
    with open(file_path, 'r') as file:
        # Flags for each section
        in_tags = False
        in_ingredients = False
        in_common_ingredients = False
        in_items = False
        in_instructions = False
        in_note = False

        def reset_flags():
            nonlocal in_tags, in_ingredients, in_common_ingredients, in_items, in_instructions, in_note
            in_tags = False
            in_ingredients = False
            in_common_ingredients = False
            in_items = False
            in_instructions = False
            in_note = False

        # Flags to verify all required sections are present
        found_ingredients = False
        found_items = False
        found_instructions = False

        for line in file:
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue

            if line == 'TAGS':
                reset_flags()
                in_tags = True
                continue
            elif line == 'INGREDIENTS':
                if found_ingredients:
                    return 7, 'Duplicate INGREDIENTS section'
                reset_flags()
                in_ingredients = True
                found_ingredients = True
                continue
            elif line == 'COMMON INGREDIENTS':
                reset_flags()
                in_common_ingredients = True
                continue
            elif line == 'ITEMS':
                if found_items:
                    return 7, 'Duplicate ITEMS section'
                reset_flags()
                in_items = True
                found_items = True
                continue
            elif line == 'INSTRUCTIONS':
                if found_instructions:
                    return 7, 'Duplicate INSTRUCTIONS section'
                reset_flags()
                in_instructions = True
                found_instructions = True
                continue
            elif line == 'NOTE':
                reset_flags()
                in_note = True
                continue
            

            # Verify line format based on current section
            if in_tags:
                if not re.match(r'^[^:]+$', line):
                    return 2, line
            elif in_ingredients or in_common_ingredients:
                if not re.match(r'^[^:]+ :: \d+(\.\d+)? :: [^:]+$', line):
                    return 3, line
            elif in_items:
                if not re.match(r'^[^:]+ :: \d+$', line):
                    return 4, line
            elif in_instructions:
                if not re.match(r'^[^;]+$', line):
                    return 5, line
            elif in_note:
                if not re.match(r'^[^;]+$', line):
                    return 6, line
            else:
                # Verify the header line format
                if not re.match(r'^\d+ :: [^;]+ :: \d+ :: \d+ :: [1-5] :: [1-5]$', line):
                    return 1, line

        # Check if all required sections are found
        if not (found_ingredients and found_items and found_instructions):
            missing_sections = []
            if not found_ingredients:
                missing_sections.append('INGREDIENTS')
            if not found_items:
                missing_sections.append('ITEMS')
            if not found_instructions:
                missing_sections.append('INSTRUCTIONS')
            return 6, 'Missing required sections: ' + ', '.join(missing_sections)

        return 0, None

def main():
    has_error = False
    num_errors = 0
    for root, dirs, files in os.walk('.'):  # Walk through the directory tree
        for file in files:
            if file == 'recipe.txt':  # Check for 'recipe.txt'
                file_path = os.path.join(root, file)
                print(f"Checking {file_path}")
                valid, error = verify_format(file_path)
                if valid != 0:
                    has_error = True
                    print(f"File does not follow the specified format. Error {valid}:")
                    print(f"{error}")
                    print()
                    num_errors += 1
    
    if has_error:
        print(f"Found {num_errors} errors.")
        exit(1)
    else:
        print("All recipe.txt files follow the specified format.")

if __name__ == "__main__":
    main()
