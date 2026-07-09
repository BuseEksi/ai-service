"""
Bazı e-posta gönderenleri (özellikle toplu mail servisleri) UTF-8 içeriği
yanlış encode/declare ediyor. Bunun sonucunda "GÃ¼venlik" gibi bozuk
karakterler (mojibake) ortaya çıkıyor - bu, aslında doğru olan UTF-8
metnin yanlışlıkla Latin-1 olarak yorumlanıp tekrar encode edilmesinden
kaynaklanır. Bu modül hem bu tarz bozukluğu, hem de e-posta başlıklarında
sık görülen RFC 2047 (=?UTF-8?B?...?=) encoding'ini düzeltir.
"""
from email.header import decode_header


def fix_mojibake(text: str) -> str:
    if not text:
        return text

    # RFC 2047 encoded-word formatı (örn. "=?UTF-8?B?R8O8dmVubGlr?=")
    if "=?" in text and "?=" in text:
        try:
            parts = decode_header(text)
            decoded = "".join(
                chunk.decode(enc or "utf-8", errors="ignore") if isinstance(chunk, bytes) else chunk
                for chunk, enc in parts
            )
            text = decoded
        except Exception:  # noqa: BLE001
            pass

    if "Ã" not in text and "Â" not in text and "Ä" not in text and "Å" not in text:
        return text

    # Doğru UTF-8 metnin yanlışlıkla tek-baytlık bir kodlamayla (Latin-1 veya
    # Windows-1252 - gönderene göre değişebiliyor) yorumlanıp tekrar UTF-8'e
    # encode edilmesinden kaynaklanan bozukluğu onarmayı dene. İkisini de
    # sırayla dener, hangisi bilinen bozuk karakter kalıntısı bırakmadan
    # temiz bir sonuç veriyorsa onu kullanır.
    for source_encoding in ("cp1252", "latin-1"):
        try:
            repaired = text.encode(source_encoding).decode("utf-8")
            if "Ã" not in repaired and "Â" not in repaired and "\ufffd" not in repaired:
                return repaired
        except (UnicodeDecodeError, UnicodeEncodeError):
            continue

    return text