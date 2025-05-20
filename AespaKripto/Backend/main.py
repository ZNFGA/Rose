#!/usr/bin/env python3
"""
Digital License System using ECC Cryptography and Audio Steganography
This system creates and verifies digital licenses embedded in audio files
"""

import os
import json
import base64
import hashlib
import argparse
from datetime import datetime, timedelta

# Third-party dependencies
import numpy as np
from scipy.io import wavfile
from scipy.fftpack import dct, idct
from tinyec import registry
import secrets

# Local modules
from ecc_crypto import encrypt_ecc, decrypt_ecc, generate_ecc_keypair
from audio_stego import embed_data_in_audio, extract_data_from_audio


def generate_license(customer_info, private_key_file, output_file, expiry_days=365):
    """Generate a digital license based on customer information"""
    # Create license data
    issue_date = datetime.now()
    expiry_date = issue_date + timedelta(days=expiry_days)
    
    license_data = {
        "customer": customer_info,
        "issue_date": issue_date.strftime("%Y-%m-%d"),
        "expiry_date": expiry_date.strftime("%Y-%m-%d"),
        "license_id": secrets.token_hex(8),
        "type": "standard",
        "features": ["feature1", "feature2", "feature3"]
    }
    
    # Convert to JSON string
    license_json = json.dumps(license_data, indent=2)
    
    # Calculate SHA-256 hash
    hash_obj = hashlib.sha256(license_json.encode())
    license_hash = hash_obj.hexdigest()
    
    # Add hash to the license data
    license_data["hash"] = license_hash
    license_json = json.dumps(license_data, indent=2)
    
    print(f"Generated license data:")
    print(license_json)
    
    # Load private key
    with open(private_key_file, "r") as f:
        private_key = f.read().strip()
    
    # Encrypt with ECC
    encrypted_data = encrypt_ecc(license_json, private_key)
    
    # Encode to Base64
    base64_data = base64.b64encode(encrypted_data).decode("utf-8")
    
    # Save encrypted license
    with open(output_file, "w") as f:
        f.write(base64_data)
    
    print(f"License saved to {output_file}")
    return base64_data


def embed_license_in_audio(license_data, audio_input, audio_output):
    """Embed license data into audio file using DCT steganography"""
    return embed_data_in_audio(license_data, audio_input, audio_output)


def extract_and_verify_license(audio_file, public_key_file):
    """Extract license from audio file and verify it"""
    # Extract data from audio
    extracted_data = extract_data_from_audio(audio_file)
    
    if not extracted_data:
        print("Failed to extract license data from audio")
        return None
    
    # Decode from Base64
    try:
        encrypted_data = base64.b64decode(extracted_data)
    except:
        print("Error: Invalid Base64 data")
        return None
    
    # Load public key
    with open(public_key_file, "r") as f:
        public_key = f.read().strip()
    
    # Decrypt with ECC
    try:
        decrypted_json = decrypt_ecc(encrypted_data, public_key)
    except Exception as e:
        print(f"Decryption error: {e}")
        return None
    
    # Parse JSON
    try:
        license_data = json.loads(decrypted_json)
    except json.JSONDecodeError:
        print("Error: Invalid JSON data")
        return None
    
    # Verify hash if present
    if "hash" in license_data:
        stored_hash = license_data.pop("hash")
        license_json_for_hash = json.dumps(license_data, indent=2)
        calculated_hash = hashlib.sha256(license_json_for_hash.encode()).hexdigest()
        
        if calculated_hash != stored_hash:
            print("Warning: License hash verification failed")
        else:
            print("License hash verified successfully")
    
    # Check expiry date
    if "expiry_date" in license_data:
        try:
            expiry_date = datetime.strptime(license_data["expiry_date"], "%Y-%m-%d")
            if expiry_date < datetime.now():
                print("Warning: License has expired")
        except:
            print("Warning: Invalid expiry date format")
    
    return license_data


def main():
    parser = argparse.ArgumentParser(description="Digital License System with ECC & Audio Steganography")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Generate keypair
    keygen_parser = subparsers.add_parser("keygen", help="Generate ECC key pair")
    keygen_parser.add_argument("--output", "-o", default="keys", help="Output directory for keys")
    
    # Generate license
    gen_parser = subparsers.add_parser("generate", help="Generate license")
    gen_parser.add_argument("--customer", "-c", required=True, help="Customer name")
    gen_parser.add_argument("--email", "-e", required=True, help="Customer email")
    gen_parser.add_argument("--private-key", "-k", required=True, help="Private key file")
    gen_parser.add_argument("--output", "-o", default="license.dat", help="Output license file")
    gen_parser.add_argument("--days", "-d", type=int, default=365, help="License validity in days")
    
    # Embed license in audio
    embed_parser = subparsers.add_parser("embed", help="Embed license in audio")
    embed_parser.add_argument("--license", "-l", required=True, help="License file")
    embed_parser.add_argument("--audio", "-a", required=True, help="Input audio file (WAV)")
    embed_parser.add_argument("--output", "-o", required=True, help="Output audio file")
    
    # Verify license
    verify_parser = subparsers.add_parser("verify", help="Verify license from audio")
    verify_parser.add_argument("--audio", "-a", required=True, help="Audio file with embedded license")
    verify_parser.add_argument("--public-key", "-k", required=True, help="Public key file")
    
    args = parser.parse_args()
    
    if args.command == "keygen":
        os.makedirs(args.output, exist_ok=True)
        private_key, public_key = generate_ecc_keypair()
        
        with open(os.path.join(args.output, "private_key.pem"), "w") as f:
            f.write(private_key)
        
        with open(os.path.join(args.output, "public_key.pem"), "w") as f:
            f.write(public_key)
        
        print(f"Keys generated in {args.output} directory")
    
    elif args.command == "generate":
        customer_info = {
            "name": args.customer,
            "email": args.email
        }
        generate_license(customer_info, args.private_key, args.output, args.days)
    
    elif args.command == "embed":
        with open(args.license, "r") as f:
            license_data = f.read()
        
        embed_license_in_audio(license_data, args.audio, args.output)
    
    elif args.command == "verify":
        license_data = extract_and_verify_license(args.audio, args.public_key)
        if license_data:
            print("\nVerified License Information:")
            print(json.dumps(license_data, indent=2))
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
