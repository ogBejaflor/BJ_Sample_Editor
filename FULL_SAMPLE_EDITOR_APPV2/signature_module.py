import os

class SignatureProcessor:
    def __init__(self, signature="", apply_to_samples=True, apply_to_pack=True, as_prefix=True):
        """Initializes the SignatureProcessor."""
        self.signature = signature
        self.apply_to_samples = apply_to_samples
        self.apply_to_pack = apply_to_pack
        self.as_prefix = as_prefix

    def add_signature(self, name, signature, signature_position):
        """
        Adds the signature to the given name as a prefix or suffix based on the position.

        :param name: The name to which the signature will be added.
        :param signature: The signature to be applied.
        :param signature_position: The position to apply the signature ('prefix' or 'suffix').
        :return: The new name with the signature added.
        """
        name, ext = os.path.splitext(name)  # Separate the name and extension

        # Apply the signature as a prefix or suffix
        if signature_position == "prefix":
            new_name = f"{signature}_{name}"
        else:
            new_name = f"{name}_{signature}"

        return f"{new_name}{ext}"  # Return the new name with the original extension

    def apply_signature_to_folder(self, folder_path, signature, as_prefix=True):
        """
        Applies the signature to the folder name as a prefix or suffix.

        :param folder_path: The path to the folder.
        :param signature: The signature to be added to the folder name.
        :param as_prefix: Boolean flag to apply signature as prefix or suffix (default: True).
        :return: The new folder path after renaming.
        """
        folder_name = os.path.basename(folder_path)
        if as_prefix:
            new_folder_name = f"{signature}_{folder_name}"
        else:
            new_folder_name = f"{folder_name}_{signature}"

        new_folder_path = os.path.join(os.path.dirname(folder_path), new_folder_name)
        
        try:
            os.rename(folder_path, new_folder_path)
            print(f"Pack folder renamed to: {new_folder_name}")
            return new_folder_path
        except OSError as e:
            print(f"Error renaming folder: {e}")
            return folder_path  # Return the original folder path if renaming fails
