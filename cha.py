import json
from base64 import b64encode, b64decode
from Crypto.Cipher import ChaCha20_Poly1305 as ChaCha
from Crypto.Random import get_random_bytes

#---------- ENCRYPT ------------
# set up
plaintext = b'Attack at dawn'
pt2 = b'o come all ye faithful'
key = get_random_bytes(32)

# encrypt message

# get nonce from cipher and create B64 strings
cipher1 = ChaCha.new(key=key)
ciphertext = cipher1.encrypt(plaintext)
nonce = b64encode(cipher1.nonce).decode('utf-8')
ct = b64encode(ciphertext).decode('utf-8')

# create json wrapper for b64 stuff
json_input = {'nonce':nonce, 'ciphertext':ct}

#---------- DECRYPT ------------
b64 = json_input
nonce = b64decode(b64['nonce'])
ciphertext = b64decode(b64['ciphertext'])

cipher = ChaCha.new(key=key, nonce=nonce)
plaintext = cipher.decrypt(ciphertext).decode('utf8')
print("The message was " + plaintext)

# reuse decoder
cipher2 = ChaCha.new(key=key)
ct3 = cipher2.encrypt(pt2)
n3 = cipher2.nonce
cipher = ChaCha.new(key=key, nonce=n3)

print(cipher.decrypt(ct3).decode('utf8'))   
print(f'{n3} == {nonce}: {n3 == nonce}')