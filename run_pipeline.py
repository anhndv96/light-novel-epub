import sys
import os
import subprocess
import glob

def main():
    if len(sys.argv) < 4:
        print("Usage: python run_pipeline.py <series_name> <chapter_index> <pixiv_url>")
        sys.exit(1)
        
    series_name = sys.argv[1]
    chapter_index = sys.argv[2]
    url = sys.argv[3]
    out_dir = "downloads"
    
    # Ghi nhận danh sách file EPUB hiện có để tìm ra file mới sau khi download
    os.makedirs(out_dir, exist_ok=True)
    existing_epubs = set(glob.glob(os.path.join(out_dir, "*.epub")))
    
    print(f"==================================================")
    print(f"BƯỚC 1: TẢI VÀ CHUYỂN ĐỔI EPUB")
    print(f"==================================================")
    try:
        subprocess.run([sys.executable, "download_and_convert.py", url, series_name, chapter_index], check=True)
    except subprocess.CalledProcessError as e:
        print(f"[!] Lỗi khi chạy download_and_convert.py: {e}")
        sys.exit(1)
        
    # Tìm file EPUB vừa được tạo ra
    current_epubs = set(glob.glob(os.path.join(out_dir, "*.epub")))
    new_epubs = current_epubs - existing_epubs
    
    if not new_epubs:
        print("[!] Không tìm thấy file EPUB nào được tạo ra sau bước 1. Có thể đã xảy ra lỗi.")
        # Fallback lấy file mới nhất nếu bị lỗi logic so sánh
        if current_epubs:
            print("[*] Thử lấy file EPUB mới nhất trong thư mục...")
            new_epub = max(current_epubs, key=os.path.getctime)
        else:
            sys.exit(1)
    else:
        new_epub = new_epubs.pop()
        
    print(f"\n[+] Đã tạo file EPUB gốc: {new_epub}")
    
    print(f"\n==================================================")
    print(f"BƯỚC 2: TỰ ĐỘNG DỊCH THUẬT EPUB")
    print(f"==================================================")
    try:
        subprocess.run([sys.executable, "epub_translator.py", new_epub, "--index", chapter_index], check=True)
    except subprocess.CalledProcessError as e:
        print(f"[!] Lỗi khi chạy epub_translator.py: {e}")
        sys.exit(1)
        
    print("\n==================================================")
    print("[✓] HOÀN TẤT TOÀN BỘ QUÁ TRÌNH TẢI VÀ DỊCH!")
    print(f"Vui lòng kiểm tra file tiếng Việt trong thư mục: {out_dir}")
    print("==================================================")

if __name__ == "__main__":
    main()
