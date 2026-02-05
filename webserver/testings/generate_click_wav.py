import wave
import math
import struct

output_path = '/home/essi/Code/libre_genie/webserver/static/btn_click.wav'

# Config
sample_rate = 44100
duration_ms = 100  # 0.1 second
volume = 0.3      # Not too loud

n_frames = int(sample_rate * (duration_ms / 1000.0))

with wave.open(output_path, 'w') as wav_file:
    wav_file.setnchannels(1) # Mono
    wav_file.setsampwidth(2) # 2 bytes (16 bit)
    wav_file.setframerate(sample_rate)
    
    data = []
    # Create a generic "woodblock" style click (sine wave with rapid decay)
    frequency = 1000.0
    
    for i in range(n_frames):
        t = float(i) / sample_rate
        # Exponential decay is nice for percussion
        decay = math.exp(-15.0 * t)
        
        value = math.sin(2.0 * math.pi * frequency * t) * volume * decay
        
        # Clip just in case
        if value > 1.0: value = 1.0
        if value < -1.0: value = -1.0
        
        # Scale to 16-bit integer
        packed_value = struct.pack('<h', int(value * 32767.0))
        data.append(packed_value)
        
    wav_file.writeframes(b''.join(data))

print(f"Successfully generated standard WAV file at: {output_path}")
