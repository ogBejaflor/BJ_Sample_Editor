import os
import sys
import shutil
import atexit
import librosa
import numpy as np
import soundfile as sf 
import simpleaudio as sa
import matplotlib.pyplot as plt
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QInputDialog
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QMainWindow, QApplication, QFileDialog, QVBoxLayout, QPushButton, QWidget, QHBoxLayout, QLabel, QSlider, QScrollBar, QTreeWidget, QTreeWidgetItem, QCheckBox, QLineEdit, QScrollArea
from chopper_module import SampleChopper
from list_module import SampleListManager
from utility_module import UtilityProcessor
from silence_module import SilenceProcessor
from signature_module import SignatureProcessor



class SampleChopperApp(QMainWindow):
    def __init__(self):
        """Initializes the UI layout."""
        super().__init__()

        self.signature_processor = SignatureProcessor()

        #Initialize the UI
        self.setMinimumSize(1500, 900)  # Adjust this size as needed

        # Show the tutorial pop-up on startup
        self.show_tutorial_popup()

        # Initialize toggles for signing pack and samples
        self.sign_pack_enabled = False
        self.sign_samples_enabled = False

        # Initialize processors
        self.utility_processor = UtilityProcessor()
        self.silence_processor = SilenceProcessor()

        # Track whether the silence module is enabled
        self.crop_silences_enabled = False

        self.playhead_time = None  # Initialize playhead_time as None
        self.playhead_line = None  # Initialize playhead_line as None

        # Initialize current_xlim to track the x-axis limits
        self.current_xlim = None
        self.zoom_level = 1.0
        self.markers = []

        # Temporary folder for storing samples
        self.temp_folder = os.path.join(os.getcwd(), "temp_samples")
        os.makedirs(self.temp_folder, exist_ok=True)

        # Initialize sample manager with temp_folder
        self.sample_manager = SampleListManager(self.temp_folder)

        # Track the currently playing audio object
        self.current_play_obj = None  # Track the currently playing audio object

        # Set a minimum size for the window to ensure visibility of all elements
        self.setMinimumSize(1000, 800)  # Adjust this size as needed

        # Main layout and central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # Add top, middle, and bottom sections
        self.init_top_section()
        self.init_middle_section()
        self.init_bottom_section()

        # Register cleanup of temp folder at exit
        atexit.register(self.cleanup_temp_folder)

    def init_top_section(self):
        """Top section UI with pack name and toggles."""
        top_layout = QHBoxLayout()

        # First column: Pack folder and individual samples toggle
        first_col_layout = QVBoxLayout()
        self.create_pack_folder_checkbox = QCheckBox("Create Pack Folder")
        first_col_layout.addWidget(self.create_pack_folder_checkbox)

        self.name_individual_samples_checkbox = QCheckBox("Name Individual Samples")
        first_col_layout.addWidget(self.name_individual_samples_checkbox)
        
        top_layout.addLayout(first_col_layout)

        # Second column: Pack name input
        second_col_layout = QVBoxLayout()
        self.pack_name_label = QLabel("Pack Name:")
        second_col_layout.addWidget(self.pack_name_label)
        self.pack_name_entry = QLineEdit(self)
        second_col_layout.addWidget(self.pack_name_entry)
        
        top_layout.addLayout(second_col_layout)

        # Third column: Signature input
        third_col_layout = QVBoxLayout()
        self.signature_label = QLabel("Signature:")
        third_col_layout.addWidget(self.signature_label)
        self.signature_entry = QLineEdit(self)
        third_col_layout.addWidget(self.signature_entry)
        
        top_layout.addLayout(third_col_layout)

        # Fourth column: Sign pack and sign samples toggles
        fourth_col_layout = QVBoxLayout()
        self.sign_pack_checkbox = QCheckBox("Sign Pack")
        fourth_col_layout.addWidget(self.sign_pack_checkbox)

        self.sign_samples_checkbox = QCheckBox("Sign Samples")
        fourth_col_layout.addWidget(self.sign_samples_checkbox)
        
        top_layout.addLayout(fourth_col_layout)

        # Add the completed top layout to the main layout
        self.layout.addLayout(top_layout)

    def init_middle_section(self):
        """Middle section UI with the sample list and controls."""
        middle_layout = QHBoxLayout()

        # Left column: List of samples and tags
        self.sample_tree = QTreeWidget()
        self.sample_tree.setHeaderLabels(["Sample Name", "Tag"])
        middle_layout.addWidget(self.sample_tree)

        # Connect double-click event for renaming samples or editing tags
        self.sample_tree.itemDoubleClicked.connect(self.handle_item_double_click)

        # Middle column: Controls for loading and manipulating samples
        controls_layout = QVBoxLayout()

        # Load Samples button
        self.load_samples_button = QPushButton("Load Samples", self)
        self.load_samples_button.clicked.connect(self.load_samples)
        controls_layout.addWidget(self.load_samples_button)

        # Play When Clicked toggle
        self.play_when_clicked_checkbox = QCheckBox("Play When Clicked")
        self.play_when_clicked_checkbox.stateChanged.connect(self.toggle_play_when_clicked)
        controls_layout.addWidget(self.play_when_clicked_checkbox)

        # Play Sample button
        self.play_sample_button = QPushButton("Play Sample", self)
        self.play_sample_button.clicked.connect(self.play_sample)
        controls_layout.addWidget(self.play_sample_button)

        # Clear List button
        self.clear_list_button = QPushButton("Clear List", self)
        self.clear_list_button.clicked.connect(self.clear_list)
        controls_layout.addWidget(self.clear_list_button)

        # Different Folders Based on Tags toggle
        self.different_folders_by_tags_checkbox = QCheckBox("Different Folders Based on Tags")
        controls_layout.addWidget(self.different_folders_by_tags_checkbox)

        # Load Audio for Chopping button
        self.load_button = QPushButton("Load Audio for Chopping", self)
        self.load_button.clicked.connect(self.load_audio)
        controls_layout.addWidget(self.load_button)

        # Minimum Duration Slider
        self.min_duration_label = QLabel("Minimum Duration (s): 0.3")
        controls_layout.addWidget(self.min_duration_label)
        self.min_duration_slider = QSlider(Qt.Horizontal)
        self.min_duration_slider.setRange(1, 20)
        self.min_duration_slider.setValue(3)
        self.min_duration_slider.valueChanged.connect(self.update_min_duration)
        controls_layout.addWidget(self.min_duration_slider)

        # Maximum Duration Slider
        self.max_duration_label = QLabel("Maximum Duration (s): 0.5")
        controls_layout.addWidget(self.max_duration_label)
        self.max_duration_slider = QSlider(Qt.Horizontal)
        self.max_duration_slider.setRange(1, 20)
        self.max_duration_slider.setValue(5)
        self.max_duration_slider.valueChanged.connect(self.update_max_duration)
        controls_layout.addWidget(self.max_duration_slider)

        # Onset Threshold Slider
        self.threshold_label = QLabel("Onset Threshold: 0.1")
        controls_layout.addWidget(self.threshold_label)
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setRange(1, 100)
        self.threshold_slider.setValue(10)
        self.threshold_slider.valueChanged.connect(self.update_threshold)
        controls_layout.addWidget(self.threshold_slider)

        # Detect Onsets button
        self.detect_onsets_button = QPushButton("Detect Onsets", self)
        self.detect_onsets_button.clicked.connect(self.detect_onsets)
        controls_layout.addWidget(self.detect_onsets_button)

        # Chop Audio button
        self.chop_audio_button = QPushButton("Chop Audio", self)
        self.chop_audio_button.clicked.connect(self.chop_audio)
        controls_layout.addWidget(self.chop_audio_button)

        # Connect the selection change event to handle playing the sample if the toggle is on
        self.sample_tree.itemSelectionChanged.connect(self.auto_play_sample)

        # Right column: Silence module controls
        silence_controls_layout = QVBoxLayout()

        # Crop Silences toggle
        self.crop_silences_checkbox = QCheckBox("Crop Silences", self)
        self.crop_silences_checkbox.stateChanged.connect(self.toggle_crop_silences)
        silence_controls_layout.addWidget(self.crop_silences_checkbox)

        # Silence Threshold slider
        self.silence_threshold_label = QLabel("Silence Threshold (dB): -40")
        silence_controls_layout.addWidget(self.silence_threshold_label)
        self.silence_threshold_slider = QSlider(Qt.Horizontal)
        self.silence_threshold_slider.setRange(-60, 0)
        self.silence_threshold_slider.setValue(-40)
        self.silence_threshold_slider.valueChanged.connect(self.update_silence_threshold)
        silence_controls_layout.addWidget(self.silence_threshold_slider)

        # Fade-in slider
        self.fade_in_label = QLabel("Fade In (s): 0.0")
        silence_controls_layout.addWidget(self.fade_in_label)
        self.fade_in_slider = QSlider(Qt.Horizontal)
        self.fade_in_slider.setRange(0, 30)  # 0 to 3 seconds, represented as 0-30 (0.1 increments)
        self.fade_in_slider.setValue(0)
        self.fade_in_slider.valueChanged.connect(self.update_fade_in)
        silence_controls_layout.addWidget(self.fade_in_slider)

        # Fade-out slider
        self.fade_out_label = QLabel("Fade Out (s): 0.0")
        silence_controls_layout.addWidget(self.fade_out_label)
        self.fade_out_slider = QSlider(Qt.Horizontal)
        self.fade_out_slider.setRange(0, 30)  # 0 to 3 seconds, represented as 0-30 (0.1 increments)
        self.fade_out_slider.setValue(0)
        self.fade_out_slider.valueChanged.connect(self.update_fade_out)
        silence_controls_layout.addWidget(self.fade_out_slider)

        # Sample rate input
        self.sample_rate_label = QLabel("Sample Rate (Hz):")
        silence_controls_layout.addWidget(self.sample_rate_label)
        self.sample_rate_input = QLineEdit(self)
        self.sample_rate_input.setText("44100")  # Default value of 44,100 Hz
        self.sample_rate_input.editingFinished.connect(self.update_sample_rate)
        silence_controls_layout.addWidget(self.sample_rate_input)

        # Normalize Samples toggle
        self.normalize_checkbox = QCheckBox("Normalize Samples", self)
        self.normalize_checkbox.stateChanged.connect(self.toggle_normalize_samples)
        silence_controls_layout.addWidget(self.normalize_checkbox)

        # Target dB slider
        self.target_db_label = QLabel("Target dB for Normalization: -3")
        silence_controls_layout.addWidget(self.target_db_label)
        self.target_db_slider = QSlider(Qt.Horizontal)
        self.target_db_slider.setRange(-20, 0)  # Range from -20 dB to 0 dB
        self.target_db_slider.setValue(-3)
        self.target_db_slider.valueChanged.connect(self.update_target_db)
        silence_controls_layout.addWidget(self.target_db_slider)

        # Save Samples button
        self.save_samples_button = QPushButton("Save Samples", self)
        self.save_samples_button.clicked.connect(self.save_samples_with_signature)
        silence_controls_layout.addWidget(self.save_samples_button)

        # Add the layouts to the middle layout in the correct order
        middle_layout.addLayout(controls_layout)  # Middle column (controls)
        middle_layout.addLayout(silence_controls_layout)  # Right column (silence module)

        # Finally add the middle layout to the main layout
        self.layout.addLayout(middle_layout)

    def init_bottom_section(self):
        """Bottom section UI with marker count, waveform display, zoom controls, and scrollbar."""
        bottom_layout = QVBoxLayout()

        # Reset View button
        self.reset_view_button = QPushButton("Reset View")
        self.reset_view_button.clicked.connect(self.reset_view)
        bottom_layout.addWidget(self.reset_view_button)

        # Zoom Controls (Zoom In/Out Buttons Side by Side)
        zoom_layout = QHBoxLayout()
        self.zoom_in_button = QPushButton("+ Zoom In")
        self.zoom_in_button.clicked.connect(self.zoom_in)
        self.zoom_out_button = QPushButton("- Zoom Out")
        self.zoom_out_button.clicked.connect(self.zoom_out)
        zoom_layout.addWidget(self.zoom_in_button)
        zoom_layout.addWidget(self.zoom_out_button)
        bottom_layout.addLayout(zoom_layout)

        # Waveform Display
        self.fig, self.ax = plt.subplots(figsize=(8, 4))
        self.canvas = FigureCanvas(self.fig)

        # Connect the canvas to mouse click events for adding/removing markers
        self.fig.canvas.mpl_connect('button_press_event', self.on_click)
        bottom_layout.addWidget(self.canvas)

        # Scrollbar for panning
        self.scrollbar = QScrollBar(Qt.Horizontal)
        self.scrollbar.setRange(0, 100)  # Initial range
        self.scrollbar.sliderMoved.connect(self.scroll_waveform)
        bottom_layout.addWidget(self.scrollbar)

        # Marker Count Display
        self.marker_count_label = QLabel("Markers Placed: 0")
        bottom_layout.addWidget(self.marker_count_label)

        self.layout.addLayout(bottom_layout)



#TUTORIAL
    def show_tutorial_popup(self):
        """Displays a tutorial pop-up when the app starts."""
        # Create a non-modal dialog with the Qt.WindowStaysOnTopHint flag to keep it above the main window
        dialog = QDialog(self, Qt.Window | Qt.WindowStaysOnTopHint)
        
        dialog.setWindowTitle("Welcome to the Sample Editor App!")
        dialog.setMinimumSize(1000, 700)

        # Set up the layout for the dialog
        layout = QVBoxLayout()

        # Create a scroll area
        scroll_area = QScrollArea(dialog)
        scroll_area.setWidgetResizable(True)

        # Create a widget to hold the tutorial text and set it as the scroll area's widget
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Add the tutorial message
        tutorial_label = QLabel("""
            🎉 <b>Welcome to the Sample Editor App!</b> 🎉 <br><br>
            <p style="text-indent: 20px;">    We’re super excited to have you here! This app is all about making sample editing easy, fun, and super powerful for your music production workflow.<br>
            <p style="text-indent: 20px;">    Whether you're chopping up beats, organizing a sample pack, or applying custom fades, you’ve come to the right place.<br>
            <p style="text-indent: 20px;">   <b><i>Let’s dive in!</i></b> 🎧</p><br><br><br>

            🛠️ <b>What Can You Do With This App?</b><br>
            <p style="text-indent: 20px;">    Here are the core features you’ll be using:<br><br><br>

            <b>Sample Chopper</b> 🥁<br>
            <p style="text-indent: 20px;">    Easily chop up audio based on transients (onsets) or add your own markers manually by clicking. Use command+click to preview 5 secs of audio! <br>
            <p style="text-indent: 20px;">    This is great for breaking down loops or isolating drum hits!<br><br><br>
           
            <b>List Samples & Batch Rename</b> 📋<br>
            <p style="text-indent: 20px;">    Organize your samples with ease! Load samples into a list, rename them in batches, and tag them for easy reference.<br><br><br>
            
            <b>Crop Silence & Apply Fades </b>🎚️<br>
            <p style="text-indent: 20px;">    Want to clean up your samples by trimming silence? Crop unwanted silences from the start and end of samples. <br>
            <p style="text-indent: 20px;">    You can also apply fade-ins and fade-outs to make those transitions smooth.<br><br><br>
            
            <b>Normalize & Resample</b> 🎛️<br>
            <p style="text-indent: 20px;">    Normalize your samples to a set dB level to ensure they're loud enough without clipping, and resample them to match the sample rate you need.<br><br><br>
            
            <b>Create Pack Folder</b> 📁<br>
            <p style="text-indent: 20px;">    Ready to organize your samples into a pack? Create a folder and save your samples with custom names, tags, and signatures. <br>
            <p style="text-indent: 20px;">    Perfect for prepping sample packs to share!<br><br><br>
            
            ------------------------------------------------------------------------------------------------------------------------------------------------------  <br><br>                  
            
            🚀 <b>How To Use the Sample Editor App</b><br><br>
                                
            Step 1: <b>Load Your Samples</b><br>
            <p style="text-indent: 20px;">    Click the "Load Samples" button to bring in your audio files. <br>
            <p style="text-indent: 20px;">    You can load individual files or entire folders of samples. <br>
            <p style="text-indent: 20px;">    They’ll show up in the list, where you can edit names, add tags, and listen to them.<br><br>

            Step 2: <b>Chop It Up</b> 🪓<br>
            <p style="text-indent: 20px;">    Ready to chop up a sound design session? <br>
            <p style="text-indent: 20px;">    Click "Load Audio for Chopping" and use the sliders to detect transients (onsets) automatically. <br>
            <p style="text-indent: 20px;">    You can also click on the waveform to add or remove markers for custom chopping. <br>
            <p style="text-indent: 20px;">    Command+click plays a 5sec preview starting from where you clicked!<br>
            <p style="text-indent: 20px;">    Once your markers are set, click "Chop Audio" to split your audio into chunks. <br>
            <p style="text-indent: 20px;">    Each chop will be listed so you can rename or tag it.<br><br>

            Step 3: <b>Crop Silence & Apply Fades</b> 🔕<br>
            <p style="text-indent: 20px;">    Want to clean up your samples? <br>
            <p style="text-indent: 20px;">    Toggle "Crop Silences", adjust the silence threshold, and set fade-in/fade-out times to get your samples sounding clean. <br>
            <p style="text-indent: 20px;">    The app will trim off any silence at the beginning and end of the sample and smooth things out with fades.<br><br>

            Step 4: <b>Normalize & Resample</b> 🔊<br>
            <p style="text-indent: 20px;">    If your samples need a volume boost, toggle "Normalize Samples" and set your target dB level. <br>
            <p style="text-indent: 20px;">    This ensures all samples are as loud as they can be without distortion. <br>
            <p style="text-indent: 20px;">    You can also resample them to a new sample rate if needed.<br><br>

            Step 5: <b>Save & Organize</b> 📂<br>
            <p style="text-indent: 20px;">    Once you’ve got your samples just right, hit the "Save Samples" button. You can save them as-is or:<br><br><br>

                                
            Add a custom Pack Name (like "MyCoolPack").<br>
            Sign your samples with a unique Signature (prefix or suffix).<br>
            Save them in different folders based on tags.<br>
            Choose to create a Pack Folder to organize your samples into a neat folder ready to be shared.<br><br><br>
            
                                
            <b>BONUS: Play Your Samples</b> 🎶<br>
            Want to quickly listen to a sample? <br>
            Just click on it or hit "Play Sample". <br>
            You can also enable "Play When Clicked" to automatically preview samples when you select them.<br><br>

            🌟 <b>Have Fun & Get Creative!</b><br>
            This app is designed to help you fine-tune and organize your samples with ease. <br><br>
                                
            🎶 Don’t be afraid to experiment with different settings to get the best out of your sounds. <br>
            And remember—every sample is an opportunity for creativity!<br><br>

            <b>Enjoy your time in the Sample Editor App and let your sounds shine!</b> ✨<br>
            """)

        tutorial_label.setWordWrap(True)
        scroll_layout.addWidget(tutorial_label)

        # Add a 'Got it!' button to close the pop-up
        got_it_button = QPushButton("Got it!")
        got_it_button.clicked.connect(dialog.close)
        scroll_layout.addWidget(got_it_button)

        # Set the scrollable widget as the content of the scroll area
        scroll_area.setWidget(scroll_widget)

        # Add the scroll area to the layout
        layout.addWidget(scroll_area)

        # Set the dialog layout
        dialog.setLayout(layout)

        # Show the dialog without blocking the main app (non-modal)
        dialog.show()



#LIST
    def load_samples(self):
        """Loads samples and displays them in the sample list."""
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Select Audio Files", "", "Audio Files (*.wav *.mp3)")
        
        if file_paths:
            # Use the SampleListManager to handle loading samples
            sample_items = self.sample_manager.load_samples(file_paths)
            
            # Add the loaded samples to the sample_tree in the UI
            for sample_name, tag in sample_items:
                item = QTreeWidgetItem([sample_name, tag])
                self.sample_tree.addTopLevelItem(item)

            # Show a success message after loading samples
            success_msg = QLabel("Samples loaded successfully.")
            success_msg.setStyleSheet("color: green; font-weight: bold;")
            self.layout.addWidget(success_msg)
            QTimer.singleShot(3000, lambda: self.layout.removeWidget(success_msg))  # Remove the message after 3 seconds

    def toggle_play_when_clicked(self, state):
        """Enable or disable 'Play When Clicked' based on the toggle state."""
        if state == Qt.Checked:
            print("Play when clicked enabled.")
        else:
            print("Play when clicked disabled.")

    def auto_play_sample(self):
        """Automatically play the sample if 'Play When Clicked' is enabled."""
        if self.play_when_clicked_checkbox.isChecked():
            QTimer.singleShot(100, self.play_selected_sample)

    def play_selected_sample(self):
        """Play the selected sample, stopping the previous playback if any."""
        selected_item = self.sample_tree.currentItem()  # Get the currently selected item
        
        # Ensure that an item is selected before trying to play it
        if selected_item:
            sample_name = selected_item.text(0)  # Get the sample name from the selected item

            # Stop any previous playback before starting a new one
            if self.current_play_obj is not None:
                try:
                    self.current_play_obj.stop()
                except AttributeError:
                    pass  # If there is no valid play_obj or it's already stopped

            # Play the new sample and store the play object
            self.current_play_obj = self.sample_manager.play_sample(sample_name)
        else:
            print("No sample selected to play.")
            self.current_play_obj = None  # Ensure no play object is active if no sample is selected

    def handle_item_double_click(self, item, column):
        """Handles double-click on the sample tree."""
        self.edit_sample_or_tag(item, column)

    def edit_sample_or_tag(self, item, column):
        """Handles renaming of samples or updating tags."""
        sample_name = item.text(0)  # Get the current sample name
        if column == 0:  # Rename sample
            # Extract the name and extension separately
            name, extension = os.path.splitext(sample_name)  # This will split 'sample.wav' into 'sample' and '.wav'
            
            # Show only the name (without extension) in the rename dialog
            new_name, ok = QInputDialog.getText(self, "Rename Sample", "Enter new name:", QLineEdit.Normal, name)
            
            if ok and new_name:
                # Append the original extension back after renaming
                full_new_name = new_name + extension
                self.sample_manager.rename_sample(sample_name, full_new_name)  # Rename the sample in the manager
                item.setText(0, full_new_name)  # Update the name in the UI

        elif column == 1:  # Editing the tag
            current_tag = item.text(1)
            new_tag, ok = QInputDialog.getText(self, "Edit Tag", "Enter new tag:", QLineEdit.Normal, current_tag)
            if ok:
                # Call the sample manager to update the tag
                self.sample_manager.update_tag(sample_name, new_tag)
                
                # Update the UI with the new tag
                item.setText(1, new_tag)

    def play_sample(self):
        """Play the selected sample."""
        if self.sample_tree.topLevelItemCount() == 0:  # Check if there are no items in the list
            error_msg = QLabel("No samples in list.")
            error_msg.setStyleSheet("color: red; font-weight: bold;")
            self.layout.addWidget(error_msg)
            QTimer.singleShot(3000, lambda: self.layout.removeWidget(error_msg))  # Remove the message after 3 seconds
            return

        selected_item = self.sample_tree.currentItem()
        if selected_item:
            sample_name = selected_item.text(0)  # Get the sample name from the selected item
            self.sample_manager.play_sample(sample_name)  # Pass the sample name to the sample manager
        else:
            error_msg = QLabel("No sample selected.")
            error_msg.setStyleSheet("color: red; font-weight: bold;")
            self.layout.addWidget(error_msg)
            QTimer.singleShot(3000, lambda: self.layout.removeWidget(error_msg))  # Remove the message after 3 seconds

    def stop_current_sample(self, play_obj):
        """Stops the currently playing sample if any."""
        if play_obj is not None:
            play_obj.stop()  # Stop playback

    def clear_list(self):
        """Clear the list of samples using SampleListManager."""
        # Stop any currently playing audio
        if self.current_play_obj is not None:
            self.stop_current_sample(self.current_play_obj)
            self.current_play_obj = None  # Reset the current playing object

        # Clear the sample tree UI
        self.sample_tree.clear()

        # Clear the sample manager's list and temp folder
        self.sample_manager.clear_list()

        # Reset any UI elements or references
        self.markers = []  # Reset markers
        self.current_xlim = None  # Reset zoom level





#CHOPPER
    def load_audio(self):
        """Load audio for chopping and display waveform."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Audio File", "", "Audio Files (*.wav *.mp3 *.aiff)")
        
        if file_path:
            # Initialize the chopper with the selected audio file
            self.chopper = SampleChopper(file_path)
            self.audio_data = self.chopper.audio_data
            self.sample_rate = self.chopper.sample_rate

            # Clear and plot the waveform
            self.ax.clear()
            time_axis = np.linspace(0, self.chopper.full_duration, num=len(self.audio_data))
            self.ax.plot(time_axis, self.audio_data, color='b')

            # Set scrollbar range and reset its value to 0
            self.scrollbar.setRange(0, 100)
            self.scrollbar.setValue(0)

            self.canvas.draw()

            # Initialize the zoom state (current_xlim) right after loading the audio
            self.current_xlim = self.ax.get_xlim()  # Set the initial zoom level after loading the audio

            # Show "Audio loaded for chopping" message
            success_msg = QLabel("Audio loaded for chopping.")
            success_msg.setStyleSheet("color: green; font-weight: bold;")  # Customize the success message
            self.layout.addWidget(success_msg)  # Add the success message to the layout
            QTimer.singleShot(3000, lambda: self.layout.removeWidget(success_msg))  # Remove after 3 seconds

    def update_min_duration(self):
        """Update the minimum duration based on slider value."""
        self.min_duration = self.min_duration_slider.value() / 10.0
        self.min_duration_label.setText(f"Minimum Duration (s): {self.min_duration:.1f}")

    def update_max_duration(self):
        """Update the maximum duration based on slider value."""
        self.max_duration = self.max_duration_slider.value() / 10.0
        self.max_duration_label.setText(f"Maximum Duration (s): {self.max_duration:.1f}")

    def update_threshold(self):
        """Update the onset detection threshold based on slider value."""
        self.threshold = self.threshold_slider.value() / 100.0
        self.threshold_label.setText(f"Onset Threshold: {self.threshold:.2f}")

    def detect_onsets(self):
        """Detect onsets and add markers based on updated slider values."""
        if not hasattr(self, 'chopper') or self.audio_data is None:
            self.show_error_message("No audio loaded for chopping.")
            return

        # Get the updated slider values from the UI
        min_duration = self.min_duration_slider.value() / 10.0
        max_duration = self.max_duration_slider.value() / 10.0
        threshold = self.threshold_slider.value() / 100.0

        # Call the chopper's detect_onsets method with the updated values
        onsets = self.chopper.detect_onsets(min_duration, max_duration, threshold)
        
        if not onsets:
            self.show_error_message("No onsets detected.")
            return

        # Update the markers and the waveform
        self.markers = onsets
        self.update_waveform()
        self.update_marker_count()

        # Show success message after detecting onsets
        self.show_success_message("Onsets detected.")

        # Restore the playhead if it's currently in use
        if hasattr(self, 'playhead_time'):
            self.playhead_line = self.ax.axvline(x=self.playhead_time, color='blue', linestyle='-', linewidth=2)
            self.canvas.draw()

    def chop_audio(self):
        """Chop the audio based on the markers and save to the temp folder using pydub."""
        # Check if audio is loaded
        if not hasattr(self, 'chopper') or self.audio_data is None:
            error_msg = QLabel("No audio loaded for chopping.")
            error_msg.setStyleSheet("color: red; font-weight: bold;")
            self.layout.addWidget(error_msg)
            QTimer.singleShot(3000, lambda: self.layout.removeWidget(error_msg))
            return

        # Check if markers are present
        if not self.markers:
            error_msg = QLabel("Can't chop without markers or onset detection.")
            error_msg.setStyleSheet("color: red; font-weight: bold;")
            self.layout.addWidget(error_msg)
            QTimer.singleShot(3000, lambda: self.layout.removeWidget(error_msg))
            return

        # Sort the markers to ensure correct order of chopping
        self.markers.sort()

        # Use the chopper's chop_samples method to save the chunks to the temp folder
        chopped_files = self.chopper.chop_samples(self.markers, self.temp_folder)

        # Load the chopped samples into the list for renaming and tagging
        chopped_samples = [os.path.basename(f) for f in chopped_files]
        self.load_chopped_samples_to_list(chopped_samples)

        # Show success message after chopping is done
        success_msg = QLabel("Audio successfully chopped and loaded into the list.")
        success_msg.setStyleSheet("color: green; font-weight: bold;")
        self.layout.addWidget(success_msg)
        QTimer.singleShot(3000, lambda: self.layout.removeWidget(success_msg))

        # Reset playhead after chopping
        self.playhead_time = None
        self.playhead_end = None

        # Clear the playhead line properly
        if hasattr(self, 'playhead_line'):
            self.playhead_line.remove()  # Remove the line from the axes completely
            del self.playhead_line  # Delete the reference to it

        # Redraw the canvas
        self.canvas.draw()

    def load_chopped_samples_to_list(self, chopped_samples):
        """Loads chopped samples into the sample list without copying."""
        # Add the chopped samples to the sample_tree in the UI
        for sample_name in chopped_samples:
            item = QTreeWidgetItem([sample_name, ""])  # Adding an empty tag for now
            self.sample_tree.addTopLevelItem(item)

        # Add the file paths directly to the sample manager (no need to copy)
        chopped_sample_paths = [os.path.join(self.temp_folder, sample) for sample in chopped_samples]
        self.sample_manager.add_sample_paths(chopped_sample_paths)

    def on_click(self, event):
        """Handles marker placement, removal, and playback on command-click."""
        if event.inaxes == self.ax:  # Check if the click happened inside the axes (waveform area)
            
            # Get the current modifiers (keys pressed during the click)
            modifiers = event.guiEvent.modifiers()

            # Detect if command (Mac) or control (Windows/Linux) is being held during the click
            is_command_click = modifiers & Qt.MetaModifier or modifiers & Qt.ControlModifier

            if is_command_click:
                self.play_from_click(event.xdata)  # Play from the click position if command-click is detected
                return  # Skip marker placement for command-click

            # Marker placement logic (only if not command-click)
            for marker in self.markers:
                if abs(marker - event.xdata) < 0.05:  # If clicked near a marker, remove it
                    self.markers.remove(marker)
                    self.update_waveform()
                    self.update_marker_count()

                    # Update playhead after marker change
                    self.update_playhead_after_marker_change()  # Ensure playhead is updated after changes
                    return

            # Add a new marker at the click position
            self.markers.append(event.xdata)
            self.update_waveform()
            self.update_marker_count()

            # Update playhead after marker change
            self.update_playhead_after_marker_change()  # Ensure playhead is updated after changes

            # Restore the playhead if it's currently in use BJ FIX
            if hasattr(self, 'playhead_time'):
                self.playhead_line = self.ax.axvline(x=self.playhead_time, color='blue', linestyle='-', linewidth=2)
                self.canvas.draw()

    def update_playhead_after_marker_change(self):
        """Update the playhead position after marker changes."""
        if hasattr(self, 'playhead_time') and self.playhead_time is not None:
            # Update or recreate the playhead line
            if hasattr(self, 'playhead_line'):
                self.playhead_line.set_xdata([self.playhead_time, self.playhead_time])  # Reposition the playhead line
            else:
                self.playhead_line = self.ax.axvline(x=self.playhead_time, color='b', linestyle='--', linewidth=2)

            self.canvas.draw()  # Redraw the canvas to update the playhead position

    def play_from_click(self, time_position):
        """Plays the audio starting from the clicked position for 5 seconds."""
        if not hasattr(self, 'chopper') or self.audio_data.size == 0:
            self.show_error_message("No audio loaded for chopping")
            return

        # Convert time position to the corresponding sample index
        start_sample = int(time_position * self.sample_rate)
        
        # Set the duration to 5 seconds or the remaining duration if less
        play_duration = min(5, self.chopper.full_duration - time_position)
        end_sample = start_sample + int(play_duration * self.sample_rate)
        
        # Slice the audio data for the specified duration
        sliced_audio = self.audio_data[start_sample:end_sample]
        
        # Play the sliced audio
        temp_audio_path = os.path.join(self.temp_folder, 'temp_playback.wav')
        sf.write(temp_audio_path, sliced_audio, self.sample_rate)
        wave_obj = sa.WaveObject.from_wave_file(temp_audio_path)
        play_obj = wave_obj.play()

        # Set playhead properties
        self.playhead_time = time_position
        self.playhead_end = time_position + play_duration

        # Check if playhead_line is None or not initialized
        if getattr(self, 'playhead_line', None) is None:
            # Create the playhead line for the first time
            self.playhead_line = self.ax.axvline(x=self.playhead_time, color='b', linestyle='--', linewidth=2)
        else:
            # If playhead already exists, update its position
            self.playhead_line.set_xdata([self.playhead_time, self.playhead_time])

        self.canvas.draw()

        # Start a timer to move the playhead
        self.playhead_timer = QTimer(self)
        self.playhead_timer.timeout.connect(self.move_playhead)
        self.playhead_timer.start(100)  # Update every 100 ms

        # Store the play object to stop playback later if needed
        self.current_play_obj = play_obj

    def update_playhead(self, start_time, play_duration):
        """Updates the playhead position in real-time as the audio plays."""
        self.playhead_time = start_time  # Set the initial playhead position
        self.playhead_end = start_time + play_duration  # Set the end of the playhead movement

        # Create or update the playhead line
        if not hasattr(self, 'playhead_line'):
            # Create the playhead line for the first time
            self.playhead_line = self.ax.axvline(x=self.playhead_time, color='b', linestyle='--', linewidth=2)
        else:
            # If playhead already exists, update its position
            self.playhead_line.set_xdata([self.playhead_time, self.playhead_time])

        self.canvas.draw()

        # Use QTimer to update the playhead every 100ms (0.1 seconds)
        self.playhead_timer = QTimer(self)
        self.playhead_timer.timeout.connect(self.move_playhead)  # Connect to the separate move_playhead method
        self.playhead_timer.start(100)  # Update every 100ms
 
    def move_playhead(self):
        """Moves the playhead in real-time based on the playback position."""
        if self.playhead_time >= self.playhead_end:
            # Stop the playhead movement once the audio section has finished playing
            self.playhead_timer.stop()
            self.playhead_line.set_xdata([None])  # Clear the playhead line properly
            self.canvas.draw()
        else:
            self.playhead_time += 0.1  # Move the playhead by 0.1 seconds
            self.playhead_line.set_xdata([self.playhead_time, self.playhead_time])  # Update playhead line position
            self.canvas.draw()

    def clear_playhead(self):
        """Stops any ongoing playhead animation and resets playhead."""
        if hasattr(self, 'playhead_timer'):
            self.playhead_timer.stop()
        if hasattr(self, 'playhead_line'):
            self.playhead_line.remove()  # Remove the line from the plot
        self.playhead_time = None
        self.canvas.draw()

    def update_marker_count(self):
        """Update the label that shows the number of markers placed."""
        self.marker_count_label.setText(f"Markers Placed: {len(self.markers)}")

    def update_waveform(self):
        """Update the waveform while preserving the current zoom and pan states."""
        if self.current_xlim:
            cur_xlim = self.ax.get_xlim()
        else:
            cur_xlim = None

        self.ax.clear()

        # Redraw the waveform
        time_axis = np.linspace(0, self.chopper.full_duration, num=len(self.audio_data))
        self.ax.plot(time_axis, self.audio_data, color='b')

        # Redraw the markers
        for marker in self.markers:
            self.ax.axvline(x=marker, color='r', linestyle='--')  # Draw a vertical line for each marker

        # Restore the zoom and pan state if applicable
        if cur_xlim:
            self.ax.set_xlim(cur_xlim)

        self.ax.figure.canvas.draw()
        self.current_xlim = self.ax.get_xlim()  # Update the xlim for next redraw

    def zoom_in(self):
        """Zoom in on the waveform."""
        if not hasattr(self, 'chopper') or self.audio_data.size == 0:
            self.show_error_message("No audio loaded for chopping")
            return
        
        self.zoom_level *= 0.8
        self.update_view_limits()

    def zoom_out(self):
        """Zoom out of the waveform."""
        if not hasattr(self, 'chopper') or self.audio_data.size == 0:
            self.show_error_message("No audio loaded for chopping")
            return
        
        self.zoom_level /= 0.8
        self.update_view_limits()

    def reset_view(self):
        """Reset the zoom level and pan to show the entire waveform."""
        if not hasattr(self, 'chopper') or self.audio_data.size == 0:
            self.show_error_message("No audio loaded for chopping")
            return

        self.zoom_level = 1.0
        self.ax.set_xlim(0, self.chopper.full_duration)
        self.canvas.draw()

    def update_view_limits(self):
        visible_duration = self.chopper.full_duration * self.zoom_level
        cur_xlim = self.ax.get_xlim()
        midpoint = (cur_xlim[0] + cur_xlim[1]) / 2
        new_xlim = [midpoint - visible_duration / 2, midpoint + visible_duration / 2]
        new_xlim[0] = max(new_xlim[0], 0)
        new_xlim[1] = min(new_xlim[1], self.chopper.full_duration)

        self.ax.set_xlim(new_xlim)
        self.canvas.draw()

    def scroll_waveform(self, value):
        """Scroll the waveform left and right based on scrollbar movement."""
        if not hasattr(self, 'chopper'):  # Check if self.chopper exists before scrolling
            return

        visible_duration = self.chopper.full_duration * self.zoom_level
        max_scroll_value = self.scrollbar.maximum() - self.scrollbar.minimum()
        scroll_ratio = value / max_scroll_value
        start_time = scroll_ratio * (self.chopper.full_duration - visible_duration)

        self.ax.set_xlim(start_time, start_time + visible_duration)
        self.canvas.draw()

    def show_error_message(self, message):
        """Displays an error message in the app."""
        error_msg = QLabel(message)
        error_msg.setStyleSheet("color: red; font-weight: bold;")
        self.layout.addWidget(error_msg)
        QTimer.singleShot(3000, lambda: self.layout.removeWidget(error_msg))  # Remove the message after 3 seconds

    def show_success_message(self, message):
        """Displays a success message in the app."""
        success_msg = QLabel(message)
        success_msg.setStyleSheet("color: green; font-weight: bold;")
        self.layout.addWidget(success_msg)
        QTimer.singleShot(3000, lambda: self.layout.removeWidget(success_msg))  # Remove the message after 3 seconds

    def cleanup_temp_folder(self):
        """Delete the temporary folder and its contents."""
        if os.path.exists(self.temp_folder):
            shutil.rmtree(self.temp_folder)



#SILENCE
    def process_sample_with_silence_module(self, file_path, output_path):
        """Processes the sample using the silence and utility modules if enabled."""
        # Create a temporary file path
        temp_output_path = os.path.join(self.temp_folder, 'temp_processed.wav')

        # If silence processing is enabled
        if self.crop_silences_enabled:
            # Process with SilenceProcessor
            self.silence_processor.process_sample(file_path, temp_output_path)
        else:
            # Copy the original file to temp path
            shutil.copy(file_path, temp_output_path)

        # Process with UtilityProcessor
        self.utility_processor.process_sample(temp_output_path, output_path)

        # Remove the temporary file
        if os.path.exists(temp_output_path):
            os.remove(temp_output_path)

    def toggle_crop_silences(self, state):
        """Enables or disables the silence module."""
        self.crop_silences_enabled = state == Qt.Checked

    def update_silence_threshold(self, value):
        """Updates the silence threshold in the silence processor."""
        self.silence_threshold_label.setText(f"Silence Threshold (dB): {value}")
        self.silence_processor.silence_threshold = value

    def update_fade_in(self, value):
        """Updates the fade-in duration in the silence processor."""
        fade_in_seconds = value / 10.0  # Convert slider value to seconds
        self.fade_in_label.setText(f"Fade In (s): {fade_in_seconds:.1f}")
        self.silence_processor.fade_in_duration = fade_in_seconds

    def update_fade_out(self, value):
        """Updates the fade-out duration in the silence processor."""
        fade_out_seconds = value / 10.0  # Convert slider value to seconds
        self.fade_out_label.setText(f"Fade Out (s): {fade_out_seconds:.1f}")
        self.silence_processor.fade_out_duration = fade_out_seconds



#UTILITY
    def toggle_normalize_samples(self, state):
        """Enables or disables normalization in the utility processor."""
        self.utility_processor.normalize_enabled = state == Qt.Checked

    def update_target_db(self, value):
        """Updates the target dB level for normalization."""
        self.target_db_label.setText(f"Target dB for Normalization: {value}")
        self.utility_processor.target_db = value

    def toggle_normalize_samples(self, state):
        """Enables or disables normalization in the utility processor."""
        self.utility_processor.normalize_enabled = state == Qt.Checked

    def update_sample_rate(self):
        """Updates the target sample rate in the utility processor."""
        try:
            sample_rate = int(self.sample_rate_input.text())
            if sample_rate > 0:
                self.utility_processor.target_sample_rate = sample_rate
            else:
                self.show_error_message("Sample rate must be a positive integer.")
        except ValueError:
            self.show_error_message("Invalid sample rate input.")



#SIGNATURE
    def toggle_sign_pack(self, state):
        """Handle the toggle for 'Sign Pack'."""
        self.sign_pack_enabled = state == Qt.Checked
        if self.sign_pack_enabled:
            print("Sign Pack enabled")
        else:
            print("Sign Pack disabled")

    def save_samples_with_signature(self):
        """Save samples, applying various processing based on the toggles."""
        save_dir = QFileDialog.getExistingDirectory(self, "Select Directory to Save Samples")
        if not save_dir:
            return

        sample_names = self.sample_manager.get_sample_names()

        # Process the pack name and folder creation
        if self.create_pack_folder_checkbox.isChecked():
            pack_name = self.pack_name_entry.text().replace(" ", "_")  # Replace spaces with underscores
            if not pack_name:
                self.show_error_message("Please provide a pack name.")
                return
            save_dir = os.path.join(save_dir, pack_name)
            os.makedirs(save_dir, exist_ok=True)

            # Check if we need to sign the folder
            if self.sign_pack_checkbox.isChecked():
                signature = self.signature_entry.text().replace(" ", "_")  # Ensure no spaces in signature
                if signature:
                    signature_position = self.get_prefix_or_suffix_choice("signature to folde:")  # Ask user for prefix/suffix
                    save_dir = self.signature_processor.apply_signature_to_folder(save_dir, signature, signature_position)
                else:
                    self.show_error_message("No signature provided for folder, skipping.")
        else:
            if self.sign_pack_checkbox.isChecked():
                self.show_error_message("No pack folder to sign, skipping folder signing.")

        # Ask once for the prefix/suffix choice for the individual samples
        pack_name_position = None
        signature_position = None
        signature = None

        if self.name_individual_samples_checkbox.isChecked():
            pack_name_position = self.get_prefix_or_suffix_choice("pack name to samples:")  # Ask once

        if self.sign_samples_checkbox.isChecked():
            signature = self.signature_entry.text().replace(" ", "_")  # Replace spaces with underscores
            if signature:
                signature_position = self.get_prefix_or_suffix_choice("signature to sample:")  # Ask once

        # Set the default final_save_dir
        final_save_dir = save_dir  # This ensures that the variable is always assigned

        # Process individual samples
        for sample_name in sample_names:
            # Use the renamed sample if it has been renamed
            final_sample_name = self.sample_manager.sample_new_names.get(sample_name, sample_name)
            sample_path = os.path.join(self.temp_folder, final_sample_name)

            if not os.path.exists(sample_path):
                self.show_error_message(f"Sample {final_sample_name} not found in temp folder.")
                return

            # Apply pack name as prefix/suffix if enabled
            if self.name_individual_samples_checkbox.isChecked():
                final_sample_name = self.apply_name(final_sample_name, self.pack_name_entry.text().replace(" ", "_"), pack_name_position)

            # Apply signature to samples as prefix/suffix if enabled
            if self.sign_samples_checkbox.isChecked() and signature:
                final_sample_name = self.signature_processor.add_signature(final_sample_name, signature, signature_position)

            # Process silence cropping if enabled
            if self.crop_silences_checkbox.isChecked():
                sample_path = self.silence_processor.process_sample(sample_path, self.temp_folder)

                if not sample_path:  # Ensure sample_path is valid after processing
                    self.show_error_message(f"Error processing {final_sample_name}: Invalid file after silence cropping.")
                    return

            # Normalize samples if enabled
            if self.normalize_checkbox.isChecked():
                if os.path.exists(sample_path):  # Ensure sample_path is valid before normalization
                    self.utility_processor.normalize_sample(sample_path, self.target_db_slider.value())
                else:
                    self.show_error_message(f"Error normalizing {final_sample_name}: Invalid file after silence cropping.")
                    return

            # Resample to the defined sample rate
            if os.path.exists(sample_path):  # Ensure sample_path is valid before resampling
                self.utility_processor.resample_sample(sample_path, int(self.sample_rate_input.text()))
            else:
                self.show_error_message(f"Error resampling {final_sample_name}: Invalid file.")
                return

            # Handle tag-based folder creation
            if self.different_folders_by_tags_checkbox.isChecked():
                tag = self.sample_manager.tags.get(sample_name, "")
                if tag:
                    final_save_dir = os.path.join(save_dir, tag)
                    os.makedirs(final_save_dir, exist_ok=True)

            # Save the final processed sample
            final_sample_path = os.path.join(final_save_dir, final_sample_name)
            if sample_path:  # Ensure sample_path is valid before copying
                shutil.copyfile(sample_path, final_sample_path)
                print(f"Saved {final_sample_name} to {final_sample_path}")
            else:
                self.show_error_message(f"Failed to save {final_sample_name}: Invalid file path.")

        # Display success message in the app
        success_msg = QLabel("Samples saved successfully!")
        success_msg.setStyleSheet("color: green; font-weight: bold;")
        self.layout.addWidget(success_msg)

        # Remove the success message after 3 seconds using proper widget handling
        QTimer.singleShot(3000, lambda: success_msg.deleteLater())

    def get_prefix_or_suffix_choice(self, name_type):
        """Ask the user if they want to apply the name/signature as a prefix or suffix."""
        choice, ok = QInputDialog.getItem(self, f"Choose {name_type} Position", f"Apply {name_type} as:", ["Prefix", "Suffix"], 0, False)
        if ok:
            return choice.lower()
        return "prefix"  # Default to prefix if canceled

    def apply_name(self, sample_name, name_to_apply, position):
        """Apply a given name (pack name or signature) to the sample name as a prefix or suffix."""
        base_name, ext = os.path.splitext(sample_name)
        if position == "prefix":
            return f"{name_to_apply}_{base_name}{ext}"
        return f"{base_name}_{name_to_apply}{ext}"



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SampleChopperApp()
    window.show()
    sys.exit(app.exec_())
