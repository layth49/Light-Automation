import os
import math
import time  # Added for debounce functionality
import pyaudio
import struct
import winsound
import asyncio
from kasa import Discover

ipAddress = os.environ["IP_ADDRESS"]

def main():
    # Define audio recording parameters
    CHUNK = 30000  # Samples to read from the microphone in each chunk
    FORMAT = pyaudio.paInt16  # Audio format (16-bit signed integer)
    CHANNELS = 1  # Mono audio
    RATE = 44100  # Sample rate (44.1 kHz)

    # Initialize PyAudio object
    p = pyaudio.PyAudio()

    # Open an audio stream for recording
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)


    def calculate_dB(data):
        """
        It takes a chunk of audio data, converts it to a list of 16-bit signed integers,
        squares each integer, sums the squares, divides by the number of samples, and
        then takes the log of the result
    
        :param data: the raw audio data
        :return: The decibel level of the audio.
        """
        count = len(data)/2
        format = '%dh'%(count)
        shorts = struct.unpack( format, data )
        sum_squares = 1e-6
        for sample in shorts:
            n = sample * (1.0/32768)
            sum_squares += n*n
        return 10*math.log10( sum_squares / count ) + 110

    async def smart_plug():
        dev = await Discover.discover_single(ipAddress)
        if(dev.is_off):
            await dev.turn_on()
            await dev.update()
            print("Light was turned on")
        elif(dev.is_on):
            await dev.turn_off()
            await dev.update()
            print("Light was turned off")

    # Define threshold for clap detection and debounce parameters
    threshold = 75
    debounce_time = 3  # Time in seconds to wait after detecting a clap



    def is_clap(dB, threshold):
        """
        Checks if the decibel value of a chunk is above a certain threshold, indicating a possible clap.
        """
        return dB >= threshold


    # Flag to track last clap detection time (initially set to False)
    last_clap_detected = False

    print("Start clapping! Press Ctrl+C to stop.")

    try:
        while True:
            # Read audio data from the microphone
            data = stream.read(CHUNK, exception_on_overflow = False)
            decibel_level = calculate_dB(data)
            print(f"Decibel level: {int(decibel_level)} dB", end="\r")
        
            # Check for clap based on decibel level and threshold, considering debounce
            if is_clap(decibel_level, threshold) and not last_clap_detected:
                print("Clap detected!")
                last_clap_detected = True  # Set flag to True after detection

                asyncio.run(smart_plug())

                # Wait for debounce time before allowing next detection
                time.sleep(debounce_time)

                # Reset flag after debounce period
                last_clap_detected = False

    except KeyboardInterrupt:
        # Handle Ctrl+C interruption
        print("Stopping...")

    # Close the audio stream and terminate PyAudio
    stream.stop_stream()
    stream.close()
    p.terminate()

main()