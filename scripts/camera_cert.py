"""Prepare a local development CA and HTTPS certificate; install no system trust."""
import argparse
import ipaddress
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID


def write_key(path, key):
    path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('hosts', nargs='*')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    folder = root / '.certs'
    folder.mkdir(exist_ok=True)
    now = datetime.now(timezone.utc)
    if (folder / 'ca-key.pem').exists() and (folder / 'ca.pem').exists():
        ca_key = serialization.load_pem_private_key((folder / 'ca-key.pem').read_bytes(), password=None)
        ca = x509.load_pem_x509_certificate((folder / 'ca.pem').read_bytes())
        if ca.not_valid_after_utc <= now + timedelta(days=91):
            raise RuntimeError('Development CA is expiring. Renew it and install the new certificate on your phone.')
    else:
        ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'HELP Park Local Development CA')])
        ca = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(ca_key.public_key())
              .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=5))
              .not_valid_after(now+timedelta(days=730)).add_extension(x509.BasicConstraints(ca=True,path_length=0),critical=True)
              .add_extension(x509.KeyUsage(digital_signature=True,key_encipherment=False,key_cert_sign=True,
                  crl_sign=True,content_commitment=False,data_encipherment=False,key_agreement=False,
                  encipher_only=False,decipher_only=False),critical=True).sign(ca_key,hashes.SHA256()))
        write_key(folder / 'ca-key.pem', ca_key)
        (folder / 'ca.pem').write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    names = []
    for host in sorted(set(['localhost','127.0.0.1'] + args.hosts)):
        try: names.append(x509.IPAddress(ipaddress.ip_address(host)))
        except ValueError: names.append(x509.DNSName(host))
    key = rsa.generate_private_key(public_exponent=65537,key_size=2048)
    cert = (x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'HELP Park Local Camera')]))
            .issuer_name(ca.subject).public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now-timedelta(minutes=5)).not_valid_after(now+timedelta(days=90))
            .add_extension(x509.SubjectAlternativeName(names),critical=False)
            .add_extension(x509.BasicConstraints(ca=False,path_length=None),critical=True)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),critical=False)
            .sign(ca_key,hashes.SHA256()))
    write_key(folder / 'server-key.pem', key)
    (folder / 'server.pem').write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    public = root / 'public'
    public.mkdir(exist_ok=True)
    # Only the public CA certificate is served. Private signing keys stay ignored.
    (public / 'help-park-dev-ca.crt').write_bytes(ca.public_bytes(serialization.Encoding.DER))
    print('Local camera certificate prepared. Run npm run dev:camera.')
    print('Install and trust public/help-park-dev-ca.crt on the phone once. Keep .certs private.')


if __name__ == '__main__':
    main()
