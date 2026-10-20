"""Download and verify public models at setup/build time, never on upload."""
import hashlib
from urllib.request import urlopen
from model_config import ASSETS, model_root


def main():
    folder = model_root()
    folder.mkdir(parents=True, exist_ok=True)
    for name, (url, expected) in ASSETS.items():
        target = folder / name
        if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == expected:
            print(f'Verified {name}')
            continue
        with urlopen(url, timeout=60) as response:
            data = response.read(50_000_001)
        if hashlib.sha256(data).hexdigest() != expected:
            raise RuntimeError(f'Model checksum mismatch: {name}; nothing installed for this file')
        temporary = target.with_suffix('.download')
        temporary.write_bytes(data)
        temporary.replace(target)
        print(f'Installed and verified {name}')


if __name__ == '__main__':
    main()
