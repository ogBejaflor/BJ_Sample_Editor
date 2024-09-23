import os
import numpy as np
import librosa
import soundfile as sf

class SilenceProcessor:
    def __init__(self, silence_threshold=-40.0, fade_in_duration=0.0, fade_out_duration=0.0):
        self.silence_threshold = silence_threshold  # Silence threshold in dB
        self.fade_in_duration = fade_in_duration    # Fade-in duration in seconds
        self.fade_out_duration = fade_out_duration  # Fade-out duration in seconds

    def crop_silence(self, audio, sample_rate, buffer_duration=0.5):
        """Crops silence from the start and end of the audio based on the silence threshold."""
        # Detect non-silent parts of the audio using librosa's effects.split
        non_silent_intervals = librosa.effects.split(audio, top_db=-self.silence_threshold)

        if len(non_silent_intervals) == 0:
            print("Audio is entirely silent, returning original")
            return audio  # If the entire sample is silent, return the original audio

        # Start point: First interval start, with 0.5 sec buffer
        start_idx = max(0, non_silent_intervals[0][0] - int(buffer_duration * sample_rate))

        # End point: Last interval end, with 0.5 sec buffer
        end_idx = min(len(audio), non_silent_intervals[-1][1] + int(buffer_duration * sample_rate))

        # Crop the audio between start and end points
        cropped_audio = audio[start_idx:end_idx]

        print(f"Cropping from {start_idx/sample_rate:.2f}s to {end_idx/sample_rate:.2f}s")
        return cropped_audio

    def apply_fade(self, audio, sample_rate):
        """Applies fade-in and fade-out to the audio based on the set durations."""
        fade_in_samples = int(self.fade_in_duration * sample_rate)
        fade_out_samples = int(self.fade_out_duration * sample_rate)

        total_samples = len(audio)

        # Apply fade-in
        if fade_in_samples > 0:
            fade_in_curve = np.linspace(0.0, 1.0, fade_in_samples)
            audio[:fade_in_samples] *= fade_in_curve

        # Apply fade-out
        if fade_out_samples > 0 and fade_out_samples <= total_samples:
            fade_out_curve = np.linspace(1.0, 0.0, fade_out_samples)
            audio[-fade_out_samples:] *= fade_out_curve

        return audio

    def process_sample(self, file_path, temp_folder):
        """Processes the sample by cropping silence and applying fade in/out, saving to a temp folder."""
        try:
            # Load the audio file
            audio, sample_rate = librosa.load(file_path, sr=None)

            # Crop silence
            audio = self.crop_silence(audio, sample_rate)

            # Apply fade in/out
            audio = self.apply_fade(audio, sample_rate)

            # Generate processed file name
            base_name = os.path.basename(file_path)
            processed_file_path = os.path.join(temp_folder, f"processed_{base_name}")

            # Save the processed audio
            sf.write(processed_file_path, audio, sample_rate)
            print(f"Processed and saved: {processed_file_path}")

            return processed_file_path  # Return the new path of the processed file
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return None

