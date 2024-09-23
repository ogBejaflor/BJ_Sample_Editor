import os
import shutil
import simpleaudio as sa

class SampleListManager:
    def __init__(self, temp_folder):
        """Initialize the Sample List Manager."""
        self.temp_folder = temp_folder
        os.makedirs(self.temp_folder, exist_ok=True)

        # Dictionary to store new names of samples and their paths
        self.samples = []
        self.file_reference = {}  # Original sample names mapped to file paths
        self.sample_new_names = {}  # Store the new names of the samples
        self.tags = {}  # Store tags for each sample
        self.file_paths = {}  # Store the file paths for each sample
        self.tag_file_path = os.path.join(self.temp_folder, "sample_tags.txt")

    def load_samples(self, file_paths):
        """Loads samples, copies them to the temp folder, and returns a list of (sample_name, tag)."""
        sample_items = []
        
        for file in file_paths:
            file_name = os.path.basename(file)
            new_file_path = os.path.join(self.temp_folder, file_name)

            try:
                shutil.copy(file, new_file_path)
            except FileNotFoundError as e:
                print(f"Error copying {file}: {e}")
                continue

            # Add to the sample list
            self.samples.append(new_file_path)
            self.file_reference[file_name] = new_file_path
            self.sample_new_names[file_name] = file_name
            self.file_paths[file_name] = new_file_path  # Store the file path

            # Each sample has a default empty tag initially
            self.tags[file_name] = ""
            sample_items.append((file_name, ""))

        # Update the tag file
        self.update_tag_file()

        return sample_items
    
    def add_sample_paths(self, file_paths):
        """Adds the paths of chopped samples to the sample manager without copying."""
        for file in file_paths:
            file_name = os.path.basename(file)
            
            # Add to samples and file paths
            self.samples.append(file)
            self.file_paths[file_name] = file  # Directly map the file name to its path
            
            # Also update file_reference and sample_new_names
            self.file_reference[file_name] = file  # Store file reference
            self.sample_new_names[file_name] = file_name  # Initialize new names as original

        # Update the tag file (even if tags are empty, this ensures consistency)
        self.update_tag_file()

    def rename_sample(self, original_name, new_name):
        """Renames the sample in the temp folder and updates internal references."""
        original_file = os.path.join(self.temp_folder, original_name)
        new_file_path = os.path.join(self.temp_folder, new_name)

        if os.path.exists(original_file):
            # Rename the file in the temp folder
            os.rename(original_file, new_file_path)

            # Update all references to the new name
            self.file_reference[new_name] = self.file_reference.pop(original_name)
            self.sample_new_names[new_name] = new_name
            self.file_paths[new_name] = new_file_path  # Update the path to reflect the new name in the temp folder

            # Remove the old reference from file_paths and sample_new_names
            self.file_paths.pop(original_name, None)
            self.sample_new_names.pop(original_name, None)

            # Update the tag file to reflect the new name
            self.update_tag_file()
        else:
            print(f"Error: {original_name} not found in temp folder.")

    def update_tag(self, sample_name, new_tag):
        """Updates the tag for a given sample."""
        self.tags[sample_name] = new_tag  # Update the tag for the sample
        self.update_tag_file()

    def update_tag_file(self):
        """Updates the tag file with the latest sample and tag information."""
        with open(self.tag_file_path, 'w') as f:
            for sample_name in self.file_reference.keys():
                tag = self.tags.get(sample_name, "")  # Get tag or empty if not set
                f.write(f"{sample_name},{tag}\n")  # Write sample name and tag

    def play_sample(self, sample_name):
        """Plays the sample given its name."""
        # Look for the sample name in file_paths (which should have the temp folder path)
        full_path = self.file_paths.get(sample_name)
        if full_path and os.path.exists(full_path):
            wave_obj = sa.WaveObject.from_wave_file(full_path)
            play_obj = wave_obj.play()
            return play_obj
        return None
                
    def clear_list(self):
        """Clears the list of samples and deletes all temporary files."""
        self.samples.clear()
        self.file_reference.clear()
        self.sample_new_names.clear()

        # Remove files in temp folder
        if os.path.exists(self.temp_folder):
            shutil.rmtree(self.temp_folder)
        os.makedirs(self.temp_folder, exist_ok=True)

        # Update the tag file
        self.update_tag_file()

    def get_sample_names(self):
        """Returns a list of all sample names currently loaded."""
        return list(self.sample_new_names.keys())

    def save_samples(self, save_dir, pack_name=None, include_pack_name=False, pack_name_position="prefix"):
        """Saves renamed samples to a specified directory, adding pack name as prefix or suffix if needed."""
        if not save_dir:
            return

        for original_name, new_name in self.sample_new_names.items():
            final_name = new_name

            if include_pack_name and pack_name:
                if pack_name_position == "prefix":
                    final_name = f"{pack_name}_{new_name}"
                elif pack_name_position == "suffix":
                    final_name = f"{new_name}_{pack_name}"

            original_file = self.file_paths[original_name]
            new_file_path = os.path.join(save_dir, final_name)

            try:
                shutil.copy(original_file, new_file_path)
                print(f"Saved {final_name} to {new_file_path}")
            except Exception as e:
                print(f"Error saving {final_name}: {e}")
                
    def cleanup_temp_folder(self):
        """Deletes the temporary folder on exit."""
        if os.path.exists(self.temp_folder):
            shutil.rmtree(self.temp_folder)
