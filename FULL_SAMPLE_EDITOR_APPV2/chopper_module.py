import os
import numpy as np
import librosa
import soundfile as sf  # Use soundfile for writing audio
from pydub import AudioSegment

class SampleChopper:
    def __init__(self, file_path, min_duration=0.3, max_duration=0.5, threshold=0.1):
        self.file_path = file_path
        self.audio_data, self.sample_rate = librosa.load(file_path, sr=None)
        self.full_duration = AudioSegment.from_file(file_path).duration_seconds
        self.min_duration = min_duration
        self.max_duration = max_duration
        self.threshold = threshold
        self.markers = []
        self.onsets = []

    def detect_onsets(self, min_duration, max_duration, threshold):
        """Detect onsets and return their shifted times based on provided parameters."""
        if self.audio_data is None:
            return []

        # Detect onset strengths and frames using librosa
        onset_env = librosa.onset.onset_strength(y=self.audio_data, sr=self.sample_rate)
        onset_env = np.where(onset_env > threshold * np.max(onset_env), onset_env, 0)
        onset_frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=self.sample_rate, units='frames')

        # Convert onset frames to time
        onset_times = librosa.frames_to_time(onset_frames, sr=self.sample_rate)

        # Initialize filtered onsets, ensure there's at least one onset
        if len(onset_times) == 0:
            return []  # Return an empty list if no onsets are detected

        filtered_onsets = [onset_times[0]]  # Start with the first onset
        for i in range(1, len(onset_times)):
            if onset_times[i] - filtered_onsets[-1] >= min_duration:
                filtered_onsets.append(onset_times[i])

        # Shift all detected onsets backward by 0.025 seconds, ensuring no negative values
        shifted_onsets = [max(onset - 0.025, 0) for onset in filtered_onsets]

        return shifted_onsets
    
    def save_chopped_sample(self, filepath, audio_data, sample_rate):
        """Save the chopped audio sample to a .wav file."""
        sf.write(filepath, audio_data, sample_rate)  # Use soundfile.write instead of librosa.output.write_wav

    def chop_samples(self, markers, temp_folder):
        """Chop the audio based on markers and save chunks to the temp folder."""
        # Load the full audio file using pydub
        audio_segment = AudioSegment.from_file(self.file_path)
        chopped_files = []
        
        for i in range(len(markers)):
            start_time = int(markers[i] * 1000)  # Convert seconds to milliseconds
            if i == len(markers) - 1:
                end_time = int(self.full_duration * 1000)  # Last marker to the end of the file
            else:
                end_time = int(markers[i + 1] * 1000)  # From marker i to marker i+1

            # Slice the audio and save to the temp folder
            chunk = audio_segment[start_time:end_time]
            output_path = os.path.join(temp_folder, f"chop_{i + 1}.wav")
            chunk.export(output_path, format="wav")  # You can detect the original format if needed
            chopped_files.append(output_path)

        return chopped_files
