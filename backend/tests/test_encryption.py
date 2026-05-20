"""
Teste pentru modulul de criptare (EncryptedString TypeDecorator + Fernet).
Teste pure unitare — nu necesită bază de date sau HTTP.
"""
import pytest
from app.core.encryption import encrypt, decrypt, EncryptedString


class TestEncryptDecrypt:
    def test_encrypt_produces_different_value(self):
        """Valoarea criptată trebuie să difere de plaintext."""
        plaintext = "1234567890123"
        result = encrypt(plaintext)
        assert result != plaintext

    def test_decrypt_reverses_encrypt(self):
        """decrypt(encrypt(x)) == x"""
        plaintext = "date sensibile"
        assert decrypt(encrypt(plaintext)) == plaintext

    def test_encrypt_empty_string_returns_empty(self):
        """Șirul gol nu se criptează."""
        assert encrypt("") == ""

    def test_decrypt_empty_string_returns_empty(self):
        """Decriptarea unui șir gol returnează șirul gol."""
        assert decrypt("") == ""

    def test_encrypt_none_returns_none(self):
        """None nu se criptează (None-ul e tratat de TypeDecorator, nu de encrypt)."""
        # encrypt() nu primește None direct în logica normală,
        # dar EncryptedString.process_bind_param verifică înainte
        enc = EncryptedString()
        assert enc.process_bind_param(None, None) is None

    def test_decrypt_plain_text_returns_original(self):
        """
        Fallback pentru date vechi necriptate — decrypt() returnează
        textul original dacă nu e un token Fernet valid.
        """
        old_plaintext = "masculin"
        result = decrypt(old_plaintext)
        assert result == old_plaintext

    def test_fernet_is_nondeterministic(self):
        """Același plaintext criptat de două ori produce texte diferite."""
        plaintext = "test"
        enc1 = encrypt(plaintext)
        enc2 = encrypt(plaintext)
        assert enc1 != enc2  # Fernet include timestamp + IV random

    def test_cnp_roundtrip(self):
        """CNP (13 cifre) se criptează și decriptează corect."""
        cnp = "1900101123456"
        assert decrypt(encrypt(cnp)) == cnp

    def test_long_text_roundtrip(self):
        """Text lung (câmp alergii/condiții) se criptează corect."""
        text = "penicilină, amoxicilină, aspirină, ibuprofen, lactate" * 3
        assert decrypt(encrypt(text)) == text

    def test_special_characters_roundtrip(self):
        """Caractere speciale și diacritice se păstrează."""
        text = "Diabet zaharat tip II — insulino-dependent; HTA gr.2 (≥160/100)"
        assert decrypt(encrypt(text)) == text


class TestEncryptedStringTypeDecorator:
    def test_process_bind_param_encrypts_value(self):
        """process_bind_param() criptează valoarea înainte de INSERT."""
        enc = EncryptedString()
        plaintext = "valoare sensibilă"
        result = enc.process_bind_param(plaintext, None)
        assert result != plaintext
        assert result.startswith("g")  # token Fernet începe cu 'g' (base64 URL-safe)

    def test_process_bind_param_none_returns_none(self):
        """None rămâne None — câmpul e nullable."""
        enc = EncryptedString()
        assert enc.process_bind_param(None, None) is None

    def test_process_bind_param_empty_returns_empty(self):
        """Șirul gol rămâne gol."""
        enc = EncryptedString()
        assert enc.process_bind_param("", None) == ""

    def test_process_result_value_decrypts(self):
        """process_result_value() decriptează la citire din DB."""
        enc = EncryptedString()
        plaintext = "valoare test"
        encrypted = encrypt(plaintext)
        result = enc.process_result_value(encrypted, None)
        assert result == plaintext

    def test_process_result_value_none_returns_none(self):
        """None din DB rămâne None."""
        enc = EncryptedString()
        assert enc.process_result_value(None, None) is None

    def test_process_result_value_old_plaintext_fallback(self):
        """Date vechi necriptate se returnează ca atare (migrare transparentă)."""
        enc = EncryptedString()
        old_value = "masculin"
        result = enc.process_result_value(old_value, None)
        assert result == old_value

    def test_roundtrip_through_type_decorator(self):
        """Simulare completă bind_param → result_value."""
        enc = EncryptedString()
        original = "1234567890123"
        stored = enc.process_bind_param(original, None)
        retrieved = enc.process_result_value(stored, None)
        assert retrieved == original
