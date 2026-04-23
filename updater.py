"""
updater.py
----------
Helper kecil yang bertugas:
1. Tunggu proses lama (neotest.exe) benar-benar tutup
2. Ganti file EXE lama dengan yang baru
3. Jalankan EXE baru
4. Hapus file temporary
5. Tutup diri sendiri

Build command:
  pyinstaller --onefile --noconsole updater.py
"""

import sys
import os
import time
import shutil
import subprocess
import psutil


def wait_process_exit(pid, timeout=30):
    """Tunggu proses dengan PID tertentu benar-benar berhenti."""
    print(f"[Updater] Menunggu proses PID {pid} berhenti...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            proc = psutil.Process(pid)
            if not proc.is_running():
                break
        except psutil.NoSuchProcess:
            break
        time.sleep(0.5)
    print(f"[Updater] Proses {pid} sudah berhenti.")


def main():
    """
    Argumen yang diterima:
      updater.exe <old_pid> <new_exe_path> <target_exe_path>

      old_pid         = PID neotest.exe yang sedang berjalan
      new_exe_path    = path file EXE baru (temporary)
      target_exe_path = path neotest.exe yang akan diganti
    """
    if len(sys.argv) < 4:
        print("[Updater] Argumen tidak lengkap!")
        print("Usage: updater.exe <old_pid> <new_exe> <target_exe>")
        sys.exit(1)

    old_pid         = int(sys.argv[1])
    new_exe_path    = sys.argv[2]
    target_exe_path = sys.argv[3]

    print(f"[Updater] PID lama    : {old_pid}")
    print(f"[Updater] EXE baru    : {new_exe_path}")
    print(f"[Updater] Target      : {target_exe_path}")

    # 1. Tunggu proses lama tutup
    wait_process_exit(old_pid, timeout=30)
    time.sleep(1)  # jeda tambahan

    # 2. Backup EXE lama
    backup_path = target_exe_path + ".backup"
    try:
        if os.path.exists(backup_path):
            os.remove(backup_path)
        shutil.copy2(target_exe_path, backup_path)
        print(f"[Updater] Backup: {backup_path}")
    except Exception as e:
        print(f"[Updater] Gagal backup: {e}")

    # 3. Ganti EXE lama dengan yang baru
    try:
        # Hapus dulu EXE lama
        if os.path.exists(target_exe_path):
            os.remove(target_exe_path)

        # Pindahkan EXE baru ke posisi EXE lama
        shutil.move(new_exe_path, target_exe_path)
        print(f"[Updater] EXE berhasil diperbarui!")

    except Exception as e:
        print(f"[Updater] Gagal ganti EXE: {e}")
        # Rollback
        if os.path.exists(backup_path):
            try:
                shutil.copy2(backup_path, target_exe_path)
                print("[Updater] Rollback berhasil.")
            except Exception as re:
                print(f"[Updater] Rollback gagal: {re}")
        sys.exit(1)

    # 4. Jalankan EXE baru
    time.sleep(0.5)
    try:
        subprocess.Popen(
            [target_exe_path],
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        print(f"[Updater] EXE baru dijalankan: {target_exe_path}")
    except Exception as e:
        print(f"[Updater] Gagal jalankan EXE baru: {e}")
        sys.exit(1)

    # 5. Hapus backup (opsional, biarkan saja untuk safety)
    # os.remove(backup_path)

    print("[Updater] Update selesai. Updater menutup diri.")
    sys.exit(0)


if __name__ == "__main__":
    main()
