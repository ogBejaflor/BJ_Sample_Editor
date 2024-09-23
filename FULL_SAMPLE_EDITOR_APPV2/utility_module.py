import librosa
import soundfile as sf
import numpy as np

class UtilityProcessor:
    def __init__(self):
        self.target_sample_rate = 44100  # Default sample rate
        self.normalize_enabled = False
        self.target_db = -3  # Default normalization level in dB

    def process_sample(self, file_path, output_path):
        """Processes a sample by resampling and normalizing if enabled."""
        if self.normalize_enabled:
            self.normalize_sample(file_path, output_path)
        else:
            self.resample_sample(file_path, output_path)

    def resample_sample(self, file_path, target_sample_rate):
        """Resample the audio file to the target sample rate."""
        try:
            # Load the original audio file
            audio_data, original_sample_rate = librosa.load(file_path, sr=None)
            
            # Resample the audio to the target sample rate
            resampled_audio = librosa.resample(y=audio_data, orig_sr=original_sample_rate, target_sr=target_sample_rate)
            
            # Save the resampled audio back to the file
            sf.write(file_path, resampled_audio, target_sample_rate)
            print(f"Successfully resampled {file_path} to {target_sample_rate} Hz")
        except Exception as e:
            print(f"Error while resampling: {e}")
            
    def normalize_sample(self, sample_path, target_db):
        """Normalizes the sample to the specified target dB level."""
        try:
            # Convert the target_db to a float (ensure it's numeric)
            target_db = float(target_db)
            
            audio_data, sample_rate = sf.read(sample_path)
            
            # Calculate the gain needed to reach the target dB level
            rms = np.sqrt(np.mean(audio_data**2))
            current_db = 20 * np.log10(rms)
            gain = 10 ** ((target_db - current_db) / 20)
            
            # Apply the gain
            normalized_audio = audio_data * gain
            
            # Save the normalized audio back to the file
            sf.write(sample_path, normalized_audio, sample_rate)
            print(f"Successfully normalized {sample_path} to {target_db} dB")
        
        except Exception as e:
            print(f"Error while normalizing: {e}")
