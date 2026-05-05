-- Fix password_hash column length for scrypt hashes
ALTER TABLE "user" ALTER COLUMN password_hash TYPE VARCHAR(255);
