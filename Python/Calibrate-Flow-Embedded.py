#################################################################
# Prusa Extrusion Multiplier Calibration Post Processing Script (Embedded Version)
# V1.0
# Created by: Kevin Pidliskey
# https://github.com/myevo8u/Prusa-Slicer-Extrusion-Multiplier-Calibration-Script/
#################################################################

import sys
import os
import re
from pathlib import Path

argv_gcode_file         = 1
argv_stl_file           = 2
argv_multiplier_low     = 3
argv_multiplier_high    = 4
argv_len_required       = 5
argv_output_file        = 5

modified_by_PPScript = "Modified by PPScript"

def usage():
    print("Usage:")
    print("       python Calibrate-Flow-Embedded.py  InputGCodeFilename  StlFilename  LowExtrusionMultiplier  HighExtrusionMultiplier [OutputGCodeFilename]")
    print("")
    print("       If you don't specify an OutputGCodeFilename, then you must recreate the input gcode file every time before you run this app.  Otherwise, you will not get the results you expect.")
    sys.exit(1)


if len(sys.argv) < argv_len_required:
    usage()


def get_multiplier(value):
    # User can specify multiplier as a percentage (0.70) or as a whole number (70)
    # We will convert to percentage as needed.
    # Values will probably be between 0.5 and 1.5 or 50 and 150, but we'll take anything.
    result = 0
    try:
        result = float(value)
        if result > 10:
            result /= 100
    except:
        print(f"{value} is not a number")
        sys.exit(2)

    return result


def get_filename(param):
    if not param:
        usage()

    file_full_path = os.path.abspath(param)
    file_folder = os.path.dirname(file_full_path)
    file_name = os.path.basename(param)
    return file_full_path, file_folder, file_name


def multiplier_key(id, copy):
    return str(id)+"_"+str(copy)


gcode_file_path, gcode_file_folder, gcode_file_name = get_filename(sys.argv[argv_gcode_file])
stl_file_path,   stl_file_folder, stl_file_name   = get_filename(sys.argv[argv_stl_file])

multiplier_low  = get_multiplier(sys.argv[argv_multiplier_low])
multiplier_high = get_multiplier(sys.argv[argv_multiplier_high])

output_file_path = gcode_file_path
if len(sys.argv) > argv_len_required and sys.argv[argv_output_file]:
    output_file_path = sys.argv[argv_output_file]
output_file_path, output_file_folder, output_file_name =  get_filename(output_file_path)

if gcode_file_path == output_file_path:
    print("WARNING:  If you run this app multiple times on the same gcode file,")
    print("          you will NOT get the results you expect.")
    print("          Consider providing an output filename.")

try:
    with open(gcode_file_path, 'r') as file:
        file_content = file.read()
        print(f"G-Code file loaded: {gcode_file_name}")
except:
    print(f"G-Code file not found: {gcode_file_name}")
    sys.exit(3)

unique_lines = list()

# Find each time we switch to a new model
for line in file_content.split("\n"):
    if line.startswith(f"; printing object {stl_file_name}") and line not in unique_lines:
        unique_lines.append(line)
    already_modified = re.search(modified_by_PPScript, line)
    if already_modified:
        print("This gcode file has already been modified.  Please recreate the gcode file and try again.")
        sys.exit(5)
unique_lines.sort()

num_models = len(unique_lines)  # Get the unique count of lines
print(f"Found {num_models} models in G-Code")
if num_models == 0:
    sys.exit(4)

# In PrusaSlicer 2.5.0:
# It's OK if a user copies and pastes an object many times, then deletes one of them.
# It's OK if a user does Add Instances of an object many times, then deletes one of them.
# The id and copy numbers will each be sequential, starting with 0.
max_id_number = 0
max_copy_number = 0
for l in unique_lines:
    # ; printing object 30x30x3.stl id:0 copy 1
    search_result = re.search(".* id:([0-9]*) copy ([0-9]*)", l)
    
    extracted_id_number = int(search_result.group(1))
    max_id_number = max(max_id_number, extracted_id_number)

    extracted_copy_number = int(search_result.group(2))
    max_copy_number = max(max_copy_number, extracted_copy_number)

print(f"Highest id number found in gcode is: {max_id_number}")
print(f"Highest copy number found in gcode is: {max_copy_number}\n")
num_ids = max_id_number + 1
num_copies = max_copy_number + 1
num_values = num_ids * num_copies
multiplier_inc = (multiplier_high-multiplier_low) / (num_values-1)

multipliers = dict()
for id in range(num_ids):
    for copy in range(num_copies):
        multipliers[multiplier_key(id, copy)] = round(multiplier_low + (multiplier_inc * (id+1) * copy), 2)

base_extrusion_Multiplier = 0.0
for value in multipliers.values():
    base_extrusion_Multiplier = max(base_extrusion_Multiplier, value)

replacementsmade = []
modified_content = file_content
for l in unique_lines:
    search_result = re.search("; printing object (.*) id:([0-9]*) copy ([0-9]*)", l)
    obj_name = search_result.group(1)
    id = search_result.group(2)
    copy = search_result.group(3)
    print(f"Modifying Object: {obj_name}, id:{id}, copy:{copy}")
    # Get the new Extrusion Multiplier for model
    extrusion_Multiplier = multipliers[multiplier_key(id, copy)]
    M221_value = round(extrusion_Multiplier, 2)*100
    
    # Perform operations specific to each model
    for j, line in enumerate(modified_content.split("\n")):
        if line == l:
            replacecount = modified_content.count(line)
            modified_line = line + f"\nM221 S{M221_value} ; Set Extrusion Multiplier to {M221_value} : {modified_by_PPScript}"  # Modify the line
            modified_content = modified_content.replace(line, modified_line)  # Replace the line in modified_content
            replacementsmade.append(f'Object {obj_name} modified: {replacecount} times | Extrusion Multiplier set to: {M221_value}')
            break
    print(f"G-Code Extrusion Multiplier Modifications for Object {obj_name}: M221 S{M221_value}")


print(f"Writing output to '{output_file_path}'")
Path(output_file_folder).mkdir(parents=True, exist_ok=True)
with open(output_file_path, 'w') as file:
    file.write(modified_content)

print(f"********************Modifications Complete*******************************\n")
for i in replacementsmade:
    print(i)

# exit = input("\nPress Enter to Exit: ")