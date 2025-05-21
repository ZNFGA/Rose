#!/usr/bin/env python3
"""
Audio Steganography module using DCT (Discrete Cosine Transform)
Handles embedding and extracting data from audio files
"""

import numpy as np
from scipy.io import wavfile
from scipy.fftpack import dct, idct
import math

# Constants for DCT steganography
BLOCK_SIZE = 8192  # Size of audio blocks for DCT
USABLE_COEFFS = 1000  # Number of DCT coefficients to use for embedding
ALPHA = 0.08  # Strength of embedding (higher = more robust but more audible)
MAX_REASONABLE_LENGTH = 1000000000000  # Maximum reasonable length for embedded data


def string_to_bit_array(text):
    """Convert a string to a bit array"""
    bits = []
    for char in text.encode('utf-8'):
        # ubah setiap karakter jadi 8 bit
        bits.extend([int(b) for b in bin(char)[2:].zfill(8)])
    return bits


def bit_array_to_string(bits):
    """Convert a bit array to a string"""
    # Pastikan panjang bits kelipatan 8
    while len(bits) % 8 != 0:
        bits.append(0)  # padding 0 jika kurang

    bytes_arr = bytearray()
    for i in range(0, len(bits), 8):
        byte_val = 0
        for bit in bits[i:i+8]:
            byte_val = (byte_val << 1) | bit
        bytes_arr.append(byte_val)

    # Hapus padding null bytes di akhir (jika ada)
    while bytes_arr and bytes_arr[-1] == 0:
        bytes_arr.pop()

    try:
        return bytes_arr.decode('utf-8')
    except UnicodeDecodeError:
        # Jika error decode, coba decode sampai bagian valid terakhir
        for i in range(len(bytes_arr), 0, -1):
            try:
                return bytes_arr[:i].decode('utf-8')
            except UnicodeDecodeError:
                continue
        return ""


def embed_data_in_audio(data, input_audio_path, output_audio_path):
    """Embed data in audio file using DCT steganography"""
    print(f"Embedding data in audio file: {input_audio_path}")

    try:
        sample_rate, audio_data = wavfile.read(input_audio_path)

        # Jika stereo, konversi ke mono dengan rata-rata channel
        if audio_data.ndim > 1:
            audio_data = audio_data.mean(axis=1).astype(audio_data.dtype)

        audio_float = audio_data.astype(float)

        bit_array = string_to_bit_array(data)
        data_length = len(bit_array)

        # Hitung berapa blok yang dibutuhkan
        total_blocks = math.ceil(data_length / USABLE_COEFFS)
        required_samples = (total_blocks + 1) * BLOCK_SIZE  # +1 blok untuk header

        if required_samples > len(audio_float):
            raise ValueError(f"Audio file terlalu pendek untuk menyisipkan {data_length} bit. Butuh minimal {required_samples} samples.")

        # Embed panjang data di blok pertama
        length_bits = [int(b) for b in bin(data_length)[2:].zfill(32)]

        stego_audio = audio_float.copy()

        # Proses blok header (blok pertama)
        block = stego_audio[:BLOCK_SIZE]
        block_dct = dct(block, norm='ortho')

        for i in range(32):
            coeff_index = i + 10  # lewati koefisien awal yg besar energinya
            coeff_val = block_dct[coeff_index]

            # Jika bit 1, buat nilai koefisien menjadi ganjil
            if length_bits[i] == 1:
                if int(abs(coeff_val)) % 2 == 0:
                    # tambah atau kurang ALPHA agar ganjil
                    block_dct[coeff_index] += ALPHA if coeff_val >= 0 else -ALPHA
            else:
                # Jika bit 0, buat nilai koefisien genap
                if int(abs(coeff_val)) % 2 == 1:
                    block_dct[coeff_index] += ALPHA if coeff_val < 0 else -ALPHA

        stego_audio[:BLOCK_SIZE] = idct(block_dct, norm='ortho')

        # Embed data bit ke blok berikutnya
        bit_index = 0
        for block_index in range(1, total_blocks + 1):
            start = block_index * BLOCK_SIZE
            end = start + BLOCK_SIZE

            block = stego_audio[start:end]
            block_dct = dct(block, norm='ortho')

            for i in range(USABLE_COEFFS):
                if bit_index >= data_length:
                    break

                coeff_index = i + 10
                coeff_val = block_dct[coeff_index]

                if bit_array[bit_index] == 1:
                    if int(abs(coeff_val)) % 2 == 0:
                        block_dct[coeff_index] += ALPHA if coeff_val >= 0 else -ALPHA
                else:
                    if int(abs(coeff_val)) % 2 == 1:
                        block_dct[coeff_index] += ALPHA if coeff_val < 0 else -ALPHA

                bit_index += 1

            stego_audio[start:end] = idct(block_dct, norm='ortho')

            if bit_index >= data_length:
                break

        # Konversi kembali ke tipe data awal
        if np.issubdtype(audio_data.dtype, np.integer):
            info = np.iinfo(audio_data.dtype)
            stego_audio = np.clip(stego_audio, info.min, info.max)
            stego_audio = stego_audio.astype(audio_data.dtype)

        wavfile.write(output_audio_path, sample_rate, stego_audio)
        print(f"Data berhasil disisipkan ke {output_audio_path}")
        return True

    except Exception as e:
        print(f"Error saat embed data: {e}")
        return False


def extract_data_from_audio(audio_path):
    """Extract data from audio file using DCT steganography"""
    print(f"Extracting data from audio file: {audio_path}")

    try:
        sample_rate, audio_data = wavfile.read(audio_path)

        if audio_data.ndim > 1:
            audio_data = audio_data.mean(axis=1).astype(audio_data.dtype)

        audio_float = audio_data.astype(float)

        if len(audio_float) < BLOCK_SIZE:
            print("Audio terlalu pendek untuk ekstraksi data")
            return None

        first_block = audio_float[:BLOCK_SIZE]
        first_block_dct = dct(first_block, norm='ortho')

        length_bits = []
        for i in range(32):
            coeff_index = i + 10
            coeff_val = first_block_dct[coeff_index]

            bit = 1 if int(abs(coeff_val)) % 2 == 1 else 0
            length_bits.append(bit)

        data_length = int("".join(map(str, length_bits)), 2)

        if data_length <= 0 or data_length > MAX_REASONABLE_LENGTH:
            print(f"Panjang data tidak valid: {data_length}")
            return None

        total_blocks = math.ceil(data_length / USABLE_COEFFS)
        required_samples = (total_blocks + 1) * BLOCK_SIZE

        if required_samples > len(audio_float):
            print("Audio terlalu pendek untuk ekstraksi data")
            return None

        extracted_bits = []
        bits_extracted = 0

        for block_index in range(1, total_blocks + 1):
            start = block_index * BLOCK_SIZE
            end = start + BLOCK_SIZE

            block = audio_float[start:end]
            block_dct = dct(block, norm='ortho')

            for i in range(USABLE_COEFFS):
                if bits_extracted >= data_length:
                    break

                coeff_index = i + 10
                coeff_val = block_dct[coeff_index]

                bit = 1 if int(abs(coeff_val)) % 2 == 1 else 0
                extracted_bits.append(bit)
                bits_extracted += 1

            if bits_extracted >= data_length:
                break

        extracted_data = bit_array_to_string(extracted_bits)

        # Validasi sederhana: apakah data tampak JSON atau base64?
        import re
        if re.match(r'^[A-Za-z0-9+/=]+$', extracted_data) or (extracted_data.startswith('{') and extracted_data.endswith('}')):
            return extracted_data

        print("Data yang di-ekstrak tidak valid")
        return None

    except Exception as e:
        print(f"Error saat ekstraksi data: {e}")
        return None


# Jika file ini dijalankan langsung, lakukan test embed dan extract
if __name__ == "__main__":
    import os

    test_message = "Ini adalah pesan tes untuk audio steganography menggunakan DCT"
    input_audio = "input.wav"
    output_audio = "output_stego.wav"

    if not os.path.exists(input_audio):
        print(f"File {input_audio} tidak ditemukan, lewati test.")
    else:
        embed_data_in_audio(test_message, input_audio, output_audio)
        extracted = extract_data_from_audio(output_audio)
        print(f"Original: {test_message}")
        print(f"Extracted: {extracted}")
        assert test_message == extracted, "Test steganography gagal!"
