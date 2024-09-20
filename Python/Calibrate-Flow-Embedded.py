#################################################################
# Prusa Extrusion Multiplier Calibration Post Processing Script (Embedded Version)
# V1.0
# Created by: Kevin Pidliskey
# https://github.com/myevo8u/Prusa-Slicer-Extrusion-Multiplier-Calibration-Script/
#################################################################

import sys
import os
import re


def usage():
    print("Usage:")
    print("       python Calibrate-Flow-Embedded.py  GCodeFilename  StlFilename  LowExtrusionMultiplier  HighExtrusionMultiplier")
    exit


if len(sys.argv) < 5:
    usage()


def get_float(value):
    result = 0
    try:
        result = float(value)
    except:
        print(f"{result} is not a number")
        exit
    return result


def get_filename(param):
    file_path = param
    if not file_path:
        usage()
    file_name = os.path.basename(file_path)
    return file_path, file_name


def multiplier_key(id, copy):
    return str(id)+"_"+str(copy)


gcode_file_path, gcode_file_name = get_filename(sys.argv[1])
stl_file_path,   stl_file_name   = get_filename(sys.argv[2])

multiplier_low  = get_float(sys.argv[3])
multiplier_high = get_float(sys.argv[4])

try:
    with open(gcode_file_path, 'r') as file:
        file_content = file.read()
        print(f"G-Code file loaded: {gcode_file_name}")
except:
    print(f"G-Code file not found: {gcode_file_name}")
    exit

unique_lines = set()  # Set to store unique lines

# Find each time we switch to a new model
for line in file_content.split("\n"):
    if line.startswith(f"; printing object {stl_file_name}") and line not in unique_lines:
        unique_lines.add(line)

num_models = len(unique_lines)  # Get the unique count of lines
print(f"Found {num_models} models in G-Code")
if num_models == 0:
    exit

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
    percentage_remaining = (extrusion_Multiplier / base_extrusion_Multiplier) * 100
    rounded_percentage = round(percentage_remaining, 2)
    
    # Perform operations specific to each model
    for j, line in enumerate(modified_content.split("\n")):
        if line == l:
            replacecount = modified_content.count(line)
            modified_line = line + f"\nM221 S{extrusion_Multiplier} ; Set Extrusion Multiplier to {extrusion_Multiplier} : Modified by PPScript"  # Modify the line
            modified_content = modified_content.replace(line, modified_line)  # Replace the line in modified_content
            replacementsmade.append(f'Object {obj_name} modified: {replacecount} times | Flow set to: {rounded_percentage}% | Extrusion Multiplier set to: {extrusion_Multiplier}')
            break
    print(f"G-Code Extrusion Multiplier Modifications for Object {obj_name}: M221 S{extrusion_Multiplier}")

# Save the modified content back to the file
with open(gcode_file_path, 'w') as file:
    file.write(modified_content)

print(f"********************Modifications Complete*******************************\n")
for i in replacementsmade:
    print(i)

# exit = input("\nPress Enter to Exit: ")