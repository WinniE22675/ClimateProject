import os

def clear_upload_folder(file_path=r"D:\Students\YearFour\Project\ClimateRiskMap\ClimReact\my-app\backend\upload"):
    abs_path = os.path.abspath(file_path)
    print(f"Checking folder: {abs_path}")

    # ตรวจว่ามีโฟลเดอร์จริงไหม
    if not os.path.isdir(abs_path):
        print("Path not found or not a directory.")
        return

    files = os.listdir(abs_path)
    print(f"Found {len(files)} files: {files}")

    if not files:
        print("Folder is empty — nothing to remove.")
        return

    # ลบไฟล์ทั้งหมดในโฟลเดอร์
    for f in files:
        file_to_remove = os.path.join(abs_path, f)
        if os.path.isfile(file_to_remove):
            try:
                os.remove(file_to_remove)
                print(f"Removed: {file_to_remove}")
            except Exception as e:
                print(f"Error removing {file_to_remove}: {e}")
        else:
            print(f"Skipped (not file): {file_to_remove}")

    # ตรวจหลังลบเสร็จ
    remaining = os.listdir(abs_path)
    print(f"Remaining files: {remaining if remaining else 'None (all removed!)'}")

clear_upload_folder()