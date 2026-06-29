import os
import sys
import argparse
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import ebooklib
from ebooklib import epub
import concurrent.futures
import re

# ==========================================
# CẤU HÌNH API MÁY CHỦ (OPENAI COMPATIBLE)
# ==========================================
#API_URL = "http://localhost:1234/v1/chat/completions" 
API_URL = "https://api.deepseek.com/v1/chat/completions"
API_KEY = "sk-b0494de4672e49a7beb0433f2241a106"       
#MODEL_NAME = "qwen3.5-9b-uncensored-hauhaucs-aggressive" 
#MODEL_NAME = "gemma-4-e4b-uncensored-hauhaucs-aggressive"
#MODEL_NAME = "gemma-4-e4b-it-ultra-uncensored-heretic"
#MODEL_NAME = "qwen3.5-9b-claude-4.6-opus-uncensored-distilled"
#MODEL_NAME = "gemma-4-12b-it-uncensored"
MODEL_NAME = "deepseek-v4-flash" 
#MODEL_NAME = "deepseek-v4-pro"

def call_local_llm(prompt, system_prompt=""):
    """Gọi API theo chuẩn OpenAI Compatible để xử lý dịch thuật"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    if "deepseek" in API_URL:
        payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": 0.2, 
            "stream": False,
            "extra_body": {"thinking": {"type": "disabled"}}
        }
    else:
        payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": 0.2, 
            "stream": False
        }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        return response.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    except Exception as e:
        print(f"[Lỗi LLM]: Không thể kết nối hoặc xử lý. Chi tiết: {e}")
        return None

def translate_text(text, context_history=""):
    """Dịch một đoạn văn bản sử dụng kỹ thuật trượt ngữ cảnh (Sliding Window)"""
    if not text.strip():
        return text

    system_prompt = (
        "Bạn là một dịch giả Light Novel chuyên nghiệp từ tiếng Trung sang tiếng Việt. "
        "Hãy dịch đoạn văn bản sau một cách tự nhiên, mượt mà, giữ đúng văn phong văn học mạng. "
        "Chú ý nhất quán đại từ nhân xưng dựa trên ngữ cảnh được cung cấp. "
        "TUYỆT ĐỐI KHÔNG để lại bất kỳ chữ Hán (tiếng Trung) nào trong bản dịch. "
        "KHÔNG thêm các chú thích trong ngoặc đơn kiểu như 'chữ Hán (tiếng Việt)'. "
        "CHỈ trả về bản dịch tiếng Việt 100% nguyên chất, KHÔNG thêm bất kỳ lời giải thích nào."
    )
    
    prompt = ""
    if context_history:
        prompt += f"--- NGỮ CẢNH TRƯỚC ĐÓ ---\n{context_history}\n\n"
    prompt += f"--- VĂN BẢN CẦN DỊCH ---\n{text}"

    translated = call_local_llm(prompt, system_prompt)
    
    # Kiểm tra xem bản dịch có còn chứa chữ Hán không (Range: \u4e00-\u9fff)
    if translated and re.search(r'[\u4e00-\u9fff]', translated):
        print("      [!] Phát hiện chữ Hán sót lại, đang yêu cầu LLM dịch lại...")
        retry_prompt = (
            f"Bản dịch trước của bạn cho đoạn văn bản này bị lỗi vì vẫn giữ lại chữ Hán (nửa nạc nửa mỡ):\n{translated}\n\n"
            f"Hãy DỊCH LẠI đoạn văn bản gốc dưới đây. Yêu cầu chuyển 100% các từ nhạy cảm (như 自慰 thành tự sướng/tự an ủi/thủ dâm, 撒娇 thành làm nũng) sang tiếng Việt.\n"
            f"--- VĂN BẢN CẦN DỊCH ---\n{text}"
        )
        translated_retry = call_local_llm(retry_prompt, system_prompt)
        if translated_retry:
            translated = translated_retry

    return translated if translated else text

def translate_metadata_value(tag_name, value):
    """Dịch các giá trị thẻ Metadata và lọc bỏ các từ rác do LLM tự sinh ra"""
    if not value or not str(value).strip():
        return value
        
    system_prompt = (
        "Bạn là máy dịch thuật tự động từ tiếng Trung sang tiếng Việt. "
        "TUYỆT ĐỐI CHỈ TRẢ VỀ văn bản đã được dịch. "
        "KHÔNG lặp lại câu hỏi, KHÔNG thêm các tiền tố như 'Bản dịch:', 'Giá trị:', 'Tags:' và KHÔNG giải thích."
    )
    
    # Chỉ truyền đúng nội dung cần dịch, không truyền thêm "Thẻ thuộc tính" để tránh LLM bắt chước
    prompt = value
    translated = call_local_llm(prompt, system_prompt)
    
    if translated:
        # Lớp bảo vệ 2: Cắt bỏ các cụm từ thừa (nếu LLM vẫn dính vào)
        prefixes_to_remove = [
            "Tags:", "Thẻ tag", "Giá trị gốc", "Thẻ thuộc tính", 
            "Bản dịch", "Dịch", f"{tag_name}"
        ]
        
        # Lọc nhiều lần đề phòng dính nhiều tiền tố cùng lúc
        for _ in range(2): 
            for prefix in prefixes_to_remove:
                # Xóa nếu khớp không phân biệt hoa thường
                if translated.lower().startswith(prefix.lower()):
                    translated = translated[len(prefix):].strip()
                    
            # Gọt sạch các dấu hai chấm, gạch ngang, khoảng trắng dư thừa ở ngay đầu chuỗi
            while translated and translated[0] in [':', '-', ' ']:
                translated = translated[1:].strip()
                
        return translated
        
    return value

def translate_filename(filename):
    """Dịch tên file sang tiếng Việt"""
    name_without_ext, ext = os.path.splitext(filename)
    clean_name = name_without_ext.replace('_', ' ').replace('-', ' ')
    
    system_prompt = (
        "Bạn là một dịch giả sách. Hãy dịch tên tiêu đề tệp sách tiếng Trung này sang tiếng Việt sao cho hay và tự nhiên nhất. "
        "CHỈ trả về tên tệp đã dịch, không kèm phần mở rộng (.epub) và không thêm chữ gì khác."
    )
    translated = call_local_llm(clean_name, system_prompt)
    if translated:
        for char in ['/', '\\', '?', '%', '*', ':', '|', '"', '<', '>']:
            translated = translated.replace(char, '')
        return f"{translated.strip()}{ext}"
    return filename

def main():
    parser = argparse.ArgumentParser(description="Script dịch tự động EPUB Light Novel và ComicInfo.xml bằng Local LLM.")
    parser.add_argument("input_file", help="Đường dẫn tới file EPUB gốc cần dịch")
    parser.add_argument("--index", help="Index của chapter để đánh số tên file", default="")
    args = parser.parse_args()

    input_path = args.input_file
    if not os.path.exists(input_path):
        print(f"[Lỗi]: File không tồn tại tại đường dẫn: {input_path}")
        sys.exit(1)

    print(f"[*] Đang đọc file EPUB: {input_path}")
    book = epub.read_epub(input_path)

    # 1. Dịch tên file
    orig_filename = os.path.basename(input_path)
    print("[*] Đang dịch tên file...")
    translated_filename = translate_filename(orig_filename)
    
    if args.index:
        # Thêm số 0 ở đầu nếu là số (thành 3 chữ số: 001, 002...)
        try:
            idx_str = str(int(args.index)).zfill(3)
        except ValueError:
            idx_str = str(args.index).zfill(3)
        translated_filename = f"{idx_str} - {translated_filename}"
        
    output_path = os.path.join(os.path.dirname(input_path), translated_filename)
    print(f"[=>] Tên file mới sẽ là: {translated_filename}")

    # 2. Dịch các thẻ Metadata trong file EPUB
    print("\n[*] Đang kiểm tra và dịch Metadata trong file EPUB...")
    
    # Dịch các thẻ DC (title, description, subject)
    for tag in ['title', 'description', 'subject']:
        metadata_list = book.get_metadata('DC', tag)
        if metadata_list:
            # Xóa metadata cũ để ghi đè
            book.metadata['http://purl.org/dc/elements/1.1/'][tag] = []
            for val, attrs in metadata_list:
                if val and str(val).strip():
                    orig_val = str(val)
                    print(f"   - Dịch thẻ Metadata 'DC:{tag}': {orig_val[:40]}...")
                    trans_val = translate_metadata_value(tag, orig_val)
                    book.add_metadata('DC', tag, trans_val if trans_val else val, attrs)
                else:
                    book.add_metadata('DC', tag, val, attrs)
                    
    # Không dịch thẻ calibre:series nữa theo yêu cầu
    print("[✓] Đã kiểm tra và dịch Metadata thành công")

    # 3. Dịch nội dung văn bản chính trong EPUB
    print("\n[*] Đang dịch nội dung các chương truyện (Vui lòng chờ)...")
    
    items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
    total_items = len(items)
    
    MAX_WORKERS = 4 # Số luồng chạy song song
    BATCH_SIZE = 15 # Số dòng gom trong 1 batch

    def translate_batch_worker(batch_nodes, context_text=""):
        if not batch_nodes:
            return []
        
        lines = [str(node).strip() for node in batch_nodes]
        text_to_translate = "\n".join(lines)
        
        system_prompt = (
            "Bạn là một dịch giả Light Novel chuyên nghiệp từ tiếng Trung sang tiếng Việt. "
            "Hãy dịch đoạn văn bản sau một cách tự nhiên, mượt mà, giữ đúng văn phong văn học mạng. "
            "CHÚ Ý QUAN TRỌNG: Văn bản gồm nhiều dòng phân cách bằng ký tự xuống dòng (\\n). "
            "Bạn PHẢI dịch và giữ nguyên số lượng dòng, tuyệt đối không gộp dòng hay bỏ dòng. "
            "TUYỆT ĐỐI KHÔNG để lại bất kỳ chữ Hán (tiếng Trung) nào trong bản dịch. "
            "KHÔNG thêm các chú thích trong ngoặc đơn kiểu như 'chữ Hán (tiếng Việt)'. "
            "CHỈ trả về bản dịch tiếng Việt 100% nguyên chất, KHÔNG thêm bất kỳ lời giải thích nào."
        )
        
        prompt = ""
        if context_text:
            prompt += f"--- NGỮ CẢNH TRƯỚC ĐÓ ---\n{context_text}\n\n"
        prompt += f"--- VĂN BẢN CẦN DỊCH ---\n{text_to_translate}"
        
        translated = call_local_llm(prompt, system_prompt)
        
        if translated and re.search(r'[\u4e00-\u9fff]', translated):
            print("      [!] Batch chứa chữ Hán sót lại, đang yêu cầu LLM dịch lại...")
            retry_prompt = (
                f"Bản dịch trước của bạn bị lỗi vì vẫn giữ lại chữ Hán (nửa nạc nửa mỡ):\n{translated}\n\n"
                f"Hãy DỊCH LẠI toàn bộ các dòng dưới đây. Yêu cầu chuyển 100% các từ (như 自慰 thành tự sướng/tự an ủi/thủ dâm) sang tiếng Việt.\n"
                f"--- VĂN BẢN CẦN DỊCH ---\n{text_to_translate}"
            )
            translated_retry = call_local_llm(retry_prompt, system_prompt)
            if translated_retry:
                translated = translated_retry
                
        result_lines = []
        
        if translated:
            trans_lines = [line.strip() for line in translated.split('\n') if line.strip()]
            if len(trans_lines) == len(lines):
                result_lines = trans_lines
            else:
                # Fallback: dịch từng dòng nếu số dòng không khớp
                for line in lines:
                    res = translate_text(line, context_text)
                    result_lines.append(res if res else line)
        else:
            result_lines = lines
            
        return result_lines

    for idx, item in enumerate(items, 1):
        print(f"\n   [Chương {idx}/{total_items}] Xử lý: {item.get_name()}")
        content = item.get_content()
        soup = BeautifulSoup(content, 'html.parser')
        
        translated_count = 0
        
        # Lấy tất cả các node cần dịch
        nodes_to_translate = []
        for text_node in soup.find_all(string=True):
            if text_node.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
                continue
            orig_text = str(text_node).strip()
            if len(orig_text) > 1:
                nodes_to_translate.append(text_node)
        
        # Tạo batch
        batches = [nodes_to_translate[i:i + BATCH_SIZE] for i in range(0, len(nodes_to_translate), BATCH_SIZE)]
        
        # Lấy ngữ cảnh cho từng batch (là văn bản của batch ngay trước nó)
        contexts = []
        prev_text = ""
        for batch in batches:
            contexts.append(prev_text)
            prev_text = "\n".join([str(n).strip() for n in batch])[-2000:]
            
        if batches:
            print(f"      -> Tìm thấy {len(nodes_to_translate)} dòng, chia thành {len(batches)} batch để xử lý song song...")
        
        batch_results = []
        # Xử lý đa luồng
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Map futures để giữ nguyên thứ tự
            futures = [executor.submit(translate_batch_worker, batch, contexts[i]) for i, batch in enumerate(batches)]
            for future in futures:
                batch_results.append(future.result())
        
        # Cập nhật DOM tree trên luồng chính (main thread) để tránh lỗi crash BS4
        for batch, results in zip(batches, batch_results):
            for node, trans_line in zip(batch, results):
                if trans_line and trans_line != str(node).strip():
                    node.replace_with(trans_line)
                    translated_count += 1
        
        print(f"   => Đã dịch {translated_count} đoạn trong chương này.")
        item.set_content(str(soup).encode('utf-8'))

    # 4. Lưu thành file EPUB mới
    print(f"\n[*] Đang đóng gói và lưu file mới tại: {output_path}")
    epub.write_epub(output_path, book)
    print("[✓] Hoàn thành! Quá trình dịch kết thúc thành công.")

if __name__ == "__main__":
    main()