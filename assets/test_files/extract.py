import os
import zipfile

# Define the directory to iterate over
directory = './'

# Iterate over all files in the directory
for filename in os.listdir(directory):
    # Check if the file is a .zip file
    if filename.endswith('.zip'):
        zip_file_path = os.path.join(directory, filename)
        collection_json_path = os.path.join(directory, 'collection.json')
        json_file_path = zip_file_path.replace('.zip', '.json')

        # Check if collection.json already exists
        if not os.path.exists(json_file_path):
            try:
                # Open the zip file and extract metabook.json if it exists
                with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                    if 'metabook.json' in zip_ref.namelist():
                        # Extract metabook.json and rename it to collection.json
                        zip_ref.extract('metabook.json', directory)
                        os.rename(os.path.join(directory, 'metabook.json'), json_file_path)
                        print(f"Extracted and renamed metabook.json from {filename}")
                    else:
                        print(f"metabook.json not found in {filename}")
            except zipfile.BadZipFile:
                print(f"Error: {filename} is not a valid zip file")
        else:
            print(f"collection.json already exists, skipping {filename}")
