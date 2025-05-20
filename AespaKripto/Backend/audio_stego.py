#!/usr/bin/env python3
"""
Audio Steganography module using DCT (Discrete Cosine Transform)
Handles embedding and extracting data from audio files
"""

import numpy as np
from scipy.io import wavfile
from scipy.fftpack import dct, idct
import struct
import math

# Constants for DCT steganography
BLOCK_SIZE = 8192  # Size of audio blocks for DCT
USABLE_COEFFS = 1000  # Number of DCT coefficients to use for embedding
ALPHA = 0.08  # Strength of embedding (higher = more robust but more audible)
MAX_REASONABLE_LENGTH = 1000000  # Maximum reasonable length for embedded data


def string_to_bit_array(text):
    """Convert a string to a bit array"""
    result = []
    for char in text.encode('utf-8'):
        bits = bin(char)[2:].zfill(8)
        for bit in bits:
            result.append(int(bit))
    return result


def bit_array_to_string(bits):
    """Convert a bit array to a string"""
    # Ensure bit array length is multiple of 8
    while len(bits) % 8 != 0:
        bits.append(0)
    
    result = bytearray()
    for i in range(0, len(bits), 8):
        byte_bits = bits[i:i+8]
        byte_val = 0
        for j in range(8):
            byte_val = (byte_val << 1) | byte_bits[j]
        result.append(byte_val)
    
    # Remove padding null bytes from the end
    while result and result[-1] == 0:
        result.pop()
    
    try:
        return result.decode('utf-8')
    except UnicodeDecodeError:
        # In case of decode error, return up to the last valid character
        for i in range(len(result), 0, -1):
            try:
                return result[:i].decode('utf-8')
            except UnicodeDecodeError:
                continue
        return ""


def embed_data_in_audio(data, input_audio_path, output_audio_path):
    """Embed data in audio file using DCT steganography"""
    print(f"Embedding data in audio file: {input_audio_path}")
    
    try:
        # Read the audio file
        sample_rate, audio_data = wavfile.read(input_audio_path)
        
        # Ensure audio data is float and mono
        if len(audio_data.shape) > 1:
            # Convert stereo to mono by averaging channels
            audio_data = np.mean(audio_data, axis=1).astype(audio_data.dtype)
        
        # Convert to float for DCT
        audio_float = audio_data.astype(float)
        
        # Convert data to bit array
        bit_array = string_to_bit_array(data)
        data_length = len(bit_array)
        
        # Calculate how many blocks we need
        total_blocks = math.ceil(data_length / USABLE_COEFFS)
        required_samples = total_blocks * BLOCK_SIZE
        
        if required_samples > len(audio_float):
            raise ValueError(f"Audio file too short for embedding {data_length} bits. Need at least {required_samples} samples.")
        
        # Embed data length at the beginning
        length_bits = bin(data_length)[2:].zfill(32)
        length_bit_array = [int(bit) for bit in length_bits]
        
        # Create a copy of the audio for embedding
        stego_audio = audio_float.copy()
        
        # Embed length information in the first block
        block = stego_audio[:BLOCK_SIZE]
        block_dct = dct(block, type=2, norm='ortho')
        
        for i in range(32):
            coeff_index = i + 10  # Skip the first few coefficients (they contain more energy)
            if length_bit_array[i] == 1:
                # Make the coefficient odd (for bit 1)
                if abs(block_dct[coeff_index]) % 2 < 1:
                    block_dct[coeff_index] += ALPHA
            else:
                # Make the coefficient even (for bit 0)
                if abs(block_dct[coeff_index]) % 2 >= 1:
                    block_dct[coeff_index] -= ALPHA
        
        # Inverse DCT and update the audio
        stego_audio[:BLOCK_SIZE] = idct(block_dct, type=2, norm='ortho')
        
        # Embed the actual data
        bit_index = 0
        for block_index in range(1, total_blocks + 1):
            start_idx = block_index * BLOCK_SIZE
            end_idx = start_idx + BLOCK_SIZE
            
            # Skip if we're at the end of the audio
            if end_idx > len(stego_audio):
                break
            
            block = stego_audio[start_idx:end_idx]
            block_dct = dct(block, type=2, norm='ortho')
            
            # Embed data in the mid-frequency coefficients
            for i in range(USABLE_COEFFS):
                if bit_index >= data_length:
                    break
                    
                coeff_index = i + 10  # Skip the first few coefficients
                
                if bit_array[bit_index] == 1:
                    # Make the coefficient odd (for bit 1)
                    if abs(block_dct[coeff_index]) % 2 < 1:
                        block_dct[coeff_index] += ALPHA
                else:
                    # Make the coefficient even (for bit 0)
                    if abs(block_dct[coeff_index]) % 2 >= 1:
                        block_dct[coeff_index] -= ALPHA
                
                bit_index += 1
            
            # Inverse DCT and update the audio
            stego_audio[start_idx:end_idx] = idct(block_dct, type=2, norm='ortho')
            
            if bit_index >= data_length:
                break
        
        # Convert back to the original data type
        if np.issubdtype(audio_data.dtype, np.integer):
            # Clip to the original data type range
            info = np.iinfo(audio_data.dtype)
            stego_audio = np.clip(stego_audio, info.min, info.max)
            stego_audio = stego_audio.astype(audio_data.dtype)
        
        # Save the output audio file
        wavfile.write(output_audio_path, sample_rate, stego_audio)
        print(f"Data embedded successfully. Output saved to {output_audio_path}")
        
        return True
    
    except Exception as e:
        print(f"Error embedding data in audio: {e}")
        return False


def extract_data_from_audio(audio_path):
    """Extract data from audio file using DCT steganography"""
    print(f"Extracting data from audio file: {audio_path}")
    
    try:
        # Read the audio file
        sample_rate, audio_data = wavfile.read(audio_path)
        
        # Ensure audio data is float and mono
        if len(audio_data.shape) > 1:
            # Convert stereo to mono by averaging channels
            audio_data = np.mean(audio_data, axis=1).astype(audio_data.dtype)
        
        # Convert to float for DCT
        audio_float = audio_data.astype(float)
        
        # Check if audio file is long enough for the header
        if len(audio_float) < BLOCK_SIZE:
            print("Audio file too short to contain embedded data")
            return None
        
        # Extract data length from the first block
        first_block = audio_float[:BLOCK_SIZE]
        first_block_dct = dct(first_block, type=2, norm='ortho')
        
        length_bits = []
        for i in range(32):
            coeff_index = i + 10
            # Check if coefficient is odd or even
            if abs(first_block_dct[coeff_index]) % 2 >= 1:
                length_bits.append(1)  # Odd coefficient = bit 1
            else:
                length_bits.append(0)  # Even coefficient = bit 0
        
        # Convert length bits to integer
        binary_str = ''.join(map(str, length_bits))
        data_length = int(binary_str, 2)
        
        if data_length <= 0 or data_length > MAX_REASONABLE_LENGTH:  # Sanity check
            print(f"Invalid data length extracted: {data_length}")
            print("Trying alternative extraction method...")
            
            # Try to extract a fixed number of bits and see if we can find valid data
            extracted_bits = []
            total_blocks = 20  # Try the first 20 blocks
            
            for block_index in range(1, total_blocks + 1):
                start_idx = block_index * BLOCK_SIZE
                end_idx = start_idx + BLOCK_SIZE
                
                if end_idx > len(audio_float):
                    break
                
                block = audio_float[start_idx:end_idx]
                block_dct = dct(block, type=2, norm='ortho')
                
                for i in range(USABLE_COEFFS):
                    coeff_index = i + 10
                    if abs(block_dct[coeff_index]) % 2 >= 1:
                        extracted_bits.append(1)
                    else:
                        extracted_bits.append(0)
            
            # Try to decode different chunks to find valid data
            for chunk_size in [1000, 2000, 4000, 8000]:
                if len(extracted_bits) < chunk_size:
                    continue
                    
                for start in range(0, len(extracted_bits) - chunk_size, 1000):
                    chunk = extracted_bits[start:start+chunk_size]
                    try:
                        data = bit_array_to_string(chunk)
                        if len(data) > 20 and '{' in data and '}' in data:  # Probably valid JSON
                            print(f"Found potentially valid data at offset {start} with length {chunk_size}")
                            return data
                    except:
                        continue
            
            return None
        
        print(f"Detected embedded data length: {data_length} bits")
        
        # Calculate how many blocks we need
        total_blocks = math.ceil(data_length / USABLE_COEFFS)
        required_samples = (total_blocks + 1) * BLOCK_SIZE  # +1 for the header block
        
        if required_samples > len(audio_float):
            print(f"Audio file too short for extracting {data_length} bits")
            return None
            
        # Extract the actual data
        extracted_bits = []
        bits_extracted = 0
        
        for block_index in range(1, total_blocks + 1):
            start_idx = block_index * BLOCK_SIZE
            end_idx = start_idx + BLOCK_SIZE
            
            # Skip if we're at the end of the audio
            if end_idx > len(audio_float):
                break
            
            block = audio_float[start_idx:end_idx]
            block_dct = dct(block, type=2, norm='ortho')
            
            # Extract data from the mid-frequency coefficients
            for i in range(USABLE_COEFFS):
                if bits_extracted >= data_length:
                    break
                    
                coeff_index = i + 10  # Skip the first few coefficients
                
                # Check if coefficient is odd or even
                if abs(block_dct[coeff_index]) % 2 >= 1:
                    extracted_bits.append(1)  # Odd coefficient = bit 1
                else:
                    extracted_bits.append(0)  # Even coefficient = bit 0
                
                bits_extracted += 1
            
            if bits_extracted >= data_length:
                break
        
        # Convert bit array to string
        extracted_data = bit_array_to_string(extracted_bits)
        
        # Basic validation - check if it's likely a Base64 string
        import re
        if re.match(r'^[A-Za-z0-9+/=]+$', extracted_data):
            return extracted_data
        
        # Check if it looks like JSON
        if extracted_data.startswith('{') and extracted_data.endswith('}'):
            return extracted_data
        
        print("Extracted data doesn't appear to be valid")
        return None
    
    except Exception as e:
        print(f"Error extracting data from audio: {e}")
        return None


# Test the functions if executed directly
if __name__ == "__main__":
    import os
    
    test_message = "This is a test message for audio steganography using DCT"
    input_audio = "input.wav"
    output_audio = "output_stego.wav"
    
    if not os.path.exists(input_audio):
        print(f"Test file {input_audio} not found. Skipping test.")
    else:
        # Embed
        embed_data_in_audio(test_message, input_audio, output_audio)
        
        # Extract
        extracted = extract_data_from_audio(output_audio)
        
        print(f"Original: {test_message}")
        print(f"Extracted: {extracted}")
        
        assert test_message == extracted, "Steganography test failed"