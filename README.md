# Cisco Meraki MR33 – OpenWrt NAND Recovery via U-Boot

<img width="622" height="492" alt="image" src="https://github.com/user-attachments/assets/50f8bd31-5810-41db-83ad-036a6c0b0487" />

This project documents how I successfully unbricked and installed **OpenWrt** on a **Cisco Meraki MR33** by patching the NAND image using a hardware programmer and custom Python script.

---

## 🖥️ System Info

- **Target Device:** Cisco Meraki MR33
- **Bootloader:** U-Boot 2017.07-RELEASE-g78ed34f31579 (Sep 29 2017 -0700)
- **Tools Used:**
  - [XGecu T48 programmer](https://www.xgecu.com/)
  - Python 3.x on Windows
  - Putty (115200 baud serial)
  - NAND dump and patch files
  - Original & uboot old file: [Google Drive](https://drive.google.com/drive/folders/1yo3IyedajK82GsJlJkOw4OKro0svAW70)

---

## 🛠️ Recovery Steps

### 1. Desolder the NAND

Remove the NAND chip adt 350-380 celcius and dump it using the XGecu T48 programmer.

<img width="600" height="445" alt="image" src="https://github.com/user-attachments/assets/f0920362-a182-4b50-aa6c-9677e031d1b7" />

![Image](https://github.com/user-attachments/assets/62510006-f71a-4ed3-9516-42f700a1912d)

![Image](https://github.com/user-attachments/assets/24ab95c7-1b4e-4ebd-9b27-9a0964a11493)

![Image](https://github.com/user-attachments/assets/a144da7f-30a8-4fc1-8873-1e90e549d6e5)

![Image](https://github.com/user-attachments/assets/74381654-a622-406f-90a6-50f5d2a186d4)

---

### 2. Patch NAND Image

Run the `patch_nand.py` script to inject required U-Boot and UBI partitions:

```bash
python patch_nand.py original_dump.bin patched_dump.bin
````

This script:

* Validates NAND dump size (expected 0x8400000 bytes)
* Injects:

  * `ubootmr332012.bin` at block 56
  * `ubimr33.bin` at block 96
  * *(Optional)* `art_repaired.bin` at block 88

> 📝 Make sure the `.bin` files are placed in the same directory.

---

### 3. Flash Patched Image

Write `patched_dump.bin` back to the NAND using the XGecu T48.

---

### 4. Restore ART Partition from Serial Console

After booting, use Putty to connect via serial (115200 baud). Then:

```sh
cat /dev/mtd10 > /tmp/art.bin
ubiupdatevol /dev/ubi0_6 /tmp/art.bin
```

✅ Done!

![Image](https://github.com/user-attachments/assets/9610a169-ee45-4f71-80c9-109a3dd67c90)

---

## 📜 Script: `patch_nand.py`

```python
import os
import sys
import shutil

BLOCK_SIZE = 135168  # 0x21000
EXPECTED_SIZE = 138412032  # 0x8400000

def error(message):
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)

def write_binary_section(target_file, source_file, seek_blocks):
    offset = BLOCK_SIZE * seek_blocks
    with open(source_file, 'rb') as sf:
        data = sf.read()
    with open(target_file, 'r+b') as tf:
        tf.seek(offset)
        tf.write(data)

def main(infile, outfile):
    if not os.path.exists(infile):
        error("Source image missing")
    if not outfile:
        error("Target image not provided")
    if os.path.abspath(infile) == os.path.abspath(outfile):
        error("Source equals target, will not overwrite the source file")
    if os.path.exists(outfile):
        error("Target image already exists. Refusing to overwrite!")

    if os.path.getsize(infile) != EXPECTED_SIZE:
        error("Source image has invalid size. Was it dumped without OOB data?")

    shutil.copyfile(infile, outfile)

    write_binary_section(outfile, "ubootmr332012.bin", seek_blocks=56)
    write_binary_section(outfile, "ubimr33.bin", seek_blocks=96)
    # Uncomment if restoring ART:
    # write_binary_section(outfile, "art_repaired.bin", seek_blocks=88)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <infile> <outfile>")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])
```

---

## 🙏 Credits

* Special thanks to [@Leo-PL](https://github.com/Leo-PL) for guidance on UBI volume restoration.
* Inspired by community recoveries and OpenWrt projects.

---

## 📄 License

MIT
