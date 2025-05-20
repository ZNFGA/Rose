#!/usr/bin/env python3
"""
ECC Cryptography module for the Digital License System
Handles key generation, encryption, and decryption using Elliptic Curve Cryptography
"""

import os
import secrets
import hashlib
from tinyec import registry
import base64

def generate_ecc_keypair():
    """Generate an ECC key pair"""
    # Use the SECP256R1 curve (also known as NIST P-256)
    curve = registry.get_curve('secp256r1')
    
    # Generate private key
    private_key = secrets.randbelow(curve.field.n)
    
    # Generate public key
    public_key = private_key * curve.g
    
    # Format private key
    private_key_str = hex(private_key)[2:]
    
    # Format public key
    public_key_str = f"04{hex(public_key.x)[2:].zfill(64)}{hex(public_key.y)[2:].zfill(64)}"
    
    return private_key_str, public_key_str


def point_from_hex(curve, hex_string):
    """Convert hex string to curve point"""
    if hex_string.startswith('04'):
        hex_string = hex_string[2:]  # Remove '04' prefix for uncompressed point format
    
    if len(hex_string) != 128:
        raise ValueError("Invalid public key format")
    
    x_hex = hex_string[:64]
    y_hex = hex_string[64:]
    
    x = int(x_hex, 16)
    y = int(y_hex, 16)
    
    return curve.point(x, y)


def encrypt_ecc(message, private_key_hex):
    """
    Encrypt a message using ECC
    
    This uses a hybrid encryption scheme:
    1. Generate ephemeral key pair
    2. Derive shared secret
    3. Use shared secret to encrypt message with AES
    """
    # Convert message to bytes
    message_bytes = message.encode('utf-8')
    
    # Get the curve
    curve = registry.get_curve('secp256r1')
    
    # Convert private key from hex
    private_key = int(private_key_hex, 16)
    
    # Generate ephemeral key pair
    eph_private_key = secrets.randbelow(curve.field.n)
    eph_public_key = eph_private_key * curve.g
    
    # Calculate shared secret
    shared_point = private_key * eph_public_key
    shared_secret = hashlib.sha256(f"{shared_point.x},{shared_point.y}".encode()).digest()
    
    # XOR encryption (for simplicity)
    # In a production system, use AES or another strong cipher
    encrypted = bytearray()
    for i, byte in enumerate(message_bytes):
        encrypted.append(byte ^ shared_secret[i % len(shared_secret)])
    
    # Encode ephemeral public key
    eph_public_key_hex = f"04{hex(eph_public_key.x)[2:].zfill(64)}{hex(eph_public_key.y)[2:].zfill(64)}"
    
    # Combine ephemeral public key and encrypted message
    result = eph_public_key_hex.encode() + b':' + bytes(encrypted)
    
    return result


def decrypt_ecc(encrypted_data, public_key_hex):
    """
    Decrypt a message using ECC
    
    This uses the same hybrid encryption scheme as encrypt_ecc
    """
    # Get the curve
    curve = registry.get_curve('secp256r1')
    
    # Split the data
    parts = encrypted_data.split(b':')
    if len(parts) != 2:
        raise ValueError("Invalid encrypted data format")
    
    eph_public_key_hex = parts[0].decode()
    encrypted_message = parts[1]
    
    # Convert public key to point
    public_key = point_from_hex(curve, public_key_hex)
    
    # Convert ephemeral public key to point
    eph_public_key = point_from_hex(curve, eph_public_key_hex)
    
    # Calculate shared secret
    shared_point = public_key * int(eph_public_key_hex[2:66], 16)  # Use x-coordinate as scalar for simplicity
    shared_secret = hashlib.sha256(f"{shared_point.x},{shared_point.y}".encode()).digest()
    
    # XOR decryption
    decrypted = bytearray()
    for i, byte in enumerate(encrypted_message):
        decrypted.append(byte ^ shared_secret[i % len(shared_secret)])
    
    return decrypted.decode('utf-8')


# Test the functions if executed directly
if __name__ == "__main__":
    # Generate key pair
    private_key, public_key = generate_ecc_keypair()
    print(f"Private key: {private_key}")
    print(f"Public key: {public_key}")
    
    # Test encryption and decryption
    message = "This is a test message for ECC encryption"
    encrypted = encrypt_ecc(message, private_key)
    decrypted = decrypt_ecc(encrypted, public_key)
    
    print(f"Original: {message}")
    print(f"Encrypted: {encrypted[:50]}...")  # Show only part of the encrypted data
    print(f"Decrypted: {decrypted}")
    assert message == decrypted, "Encryption/decryption test failed"
