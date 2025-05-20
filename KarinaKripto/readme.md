# Digital License System with ECC Cryptography and Audio Steganography

This system creates and verifies digital licenses embedded in audio files using Elliptic Curve Cryptography (ECC) and DCT-based audio steganography.

## System Architecture

1. License Creation:
   - Create license data in JSON format
   - Calculate SHA-256 hash
   - Encrypt using ECC
   - Encode to Base64
   - Embed in audio file using DCT steganography

2. License Verification:
   - Extract data from audio using DCT
   - Decode Base64
   - Decrypt using ECC
   - Verify hash
   - Display license information

## Requirements

- Python 3.6+
- Dependencies listed in `requirements.txt`

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/digital-license-system.git
cd digital-license-system

# Install required dependencies
pip install -r requirements.txt
```

## Usage

### 1. Generate ECC Key Pair

```bash
python main.py keygen --output ./keys
```

This will create `private_key.pem` and `public_key.pem` in the specified directory.

### 2. Generate License

```bash
python main.py generate --customer "Company Name" --email "email@example.com" --private-key ./keys/private_key.pem --output license.dat --days 365
```

### 3. Embed License in Audio

```bash
python main.py embed --license license.dat --audio input.wav --output license_audio.wav
```

### 4. Verify License from Audio

```bash
python main.py verify --audio license_audio.wav --public-key ./keys/public_key.pem
```

## File Structure

```
digital-license-system/
├── main.py                # Main script for user interaction
├── ecc_crypto.py          # ECC cryptography functions
├── audio_stego.py         # Audio steganography using DCT
├── requirements.txt       # Python dependencies
├── README.md              # This file
├── keys/                  # Generated keys directory
│   ├── private_key.pem    # Private key for license creation
│   └── public_key.pem     # Public key for license verification
└── examples/              # Example files
    ├── input.wav          # Sample audio file for embedding
    └── license_audio.wav  # Audio with embedded license
```

## Security Considerations

1. **Key Management**: Keep the private key secure. Only the license issuer should have access to it.
2. **Encryption Strength**: This system uses ECC (secp256r1 curve) which provides strong security.
3. **Steganography Robustness**: The DCT-based method can withstand some audio processing, but extreme modifications may corrupt the embedded data.

## License Format

The license JSON includes:
- Customer information
- Issue and expiry dates
- License ID
- SHA-256 hash for integrity verification
- Feature flags

## Technical Details

### ECC Cryptography
- Uses the SECP256R1 curve (NIST P-256)
- Implements hybrid encryption scheme
- Key size: 256 bits

### Audio Steganography
- Uses Discrete Cosine Transform (DCT)
- Embeds data in mid-frequency coefficients
- Modifies coefficient parity to encode bits

## Limitations

- Works only with WAV audio files
- Audio file must be long enough to hold the license data
- Some audio processing might corrupt the embedded license

## Future Improvements

- Add support for MP3 and other audio formats
- Implement stronger encryption for the license data
- Add QR code generation for license distribution
- Add license revocation mechanism
